import glob
import obspython as obs  # type: ignore
import re
import os
import time
from pathlib import Path

# Rewriting whole script using the Signals!
# "file_changed" signal = lets move the automatically splitted file to a folder
# "get_hooked" procedure = if you start recording and the script didn't get yet notified of the hooking, it will check it itself

# TODO: Implement a way for storing the UUID and Signals that react to it's deletion, etc. (Not figured out by me yet)
# TODO: Config instead of the Classes storing the data (Need to think if it's necessary, but probably not)


# Global variables

addTitleBool = None
recordingExtension = None
recordingExtensionMask = None
outputDir = None


# Values supporting smooth working and less calls

sourceUUID = None
sett = None


# Values connected to recording

currentRecording = None
gameTitle = None
isRecording = False
defaultRecordingTitle = "Manual Recording"


# SIGNAL-RELATED


def file_changed_sh():
    """Signal handler function reacting to automatic file splitting."""

    output = obs.obs_frontend_get_recording_output()
    sh = obs.obs_output_get_signal_handler(output)
    obs.signal_handler_connect(sh, "file_changed", file_changed_cb)
    obs.obs_output_release(output)


def file_changed_cb(calldata):
    """Callback function reacting to the file_changed_sh signal handler function being triggered."""
    print("------------------------------")
    print("Refreshing sourceUUID...")
    refresh_source_uuid()

    print("Running get_hooked procedure to get current app title...")
    check_if_hooked_and_update_title()

    print("Recording automatic splitting detected!")
    print("Moving saved recording...")

    # GETTING THE PREVIOUS FILE FIRST
    # I'm not happy with that, but it will have to do

    global currentRecording, recordingExtensionMask, outputDir
    currentRecording = find_latest_file(outputDir, recordingExtensionMask)
    print(f"Saved recording: {currentRecording}")

    rec = Recording(customPath=currentRecording)
    rec.create_new_folder()
    rec.remember_and_move()

    print("Done!")
    print(f"New path: {rec.get_newPath()}")

    currentRecording = None
    currentRecording = obs.calldata_string(calldata, "next_file")
    print(f"Current file: {currentRecording}")
    print("------------------------------")


# EVENTS


def start_recording_handler(event):
    """Event function reacting to OBS Event of starting the recording."""

    if event == obs.OBS_FRONTEND_EVENT_RECORDING_STARTING:
        print("------------------------------")
        print("Recording has started...\n")
        print("Reloading the signals!\n")

        file_changed_sh()  # Respond to splitting the recording (ex. automatic recording split)

        print("Signals reloaded!\n")
        print("Reseting the recording related values...\n")

        global isRecording, currentRecording
        global gameTitle, defaultRecordingTitle

        isRecording = True
        currentRecording = None
        gameTitle = defaultRecordingTitle

        print(f"Recording started: {isRecording}")
        print(f"CurrentRecording is {currentRecording}")
        print(f"Game title set to {gameTitle}")
        print("------------------------------")


def start_buffer_handler(event):
    """Event function reacting to OBS Event of starting the replay buffer."""

    if event == obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_STARTING:
        print("------------------------------")
        print("Replay buffer has started...\n")
        print("Reloading the signals!\n")
        print("Signals reloaded!\n")
        print("Reseting the recording related values...\n")

        global isRecording, currentRecording
        global gameTitle, defaultRecordingTitle

        isRecording = True
        currentRecording = None
        gameTitle = defaultRecordingTitle

        print(f"Recording started: {isRecording}")
        print(f"CurrentRecording is {currentRecording}")
        print(f"Game title set to {gameTitle}")
        print("------------------------------")


def recording_stop_handler(event):
    """Event function reacting to OBS Event of recording fully stopping."""
    if event == obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED:
        print("------------------------------")
        print("Refreshing sourceUUID...")
        refresh_source_uuid()

        print("Recording has stopped, moving the last file into right folder...")
        print("Running get_hooked procedure to get current app title...")
        check_if_hooked_and_update_title()

        global currentRecording, isRecording, recordingExtensionMask, outputDir
        if currentRecording is None:
            currentRecording = find_latest_file(outputDir, recordingExtensionMask)

        rec = Recording(customPath=currentRecording)
        rec.create_new_folder()
        rec.remember_and_move()

        print("Job's done. The file was moved.")
        print(f"Recording: {rec.get_filename()}")
        print(f"New path: {rec.get_newPath()}")

        currentRecording = None

        isRecording = False
        print("------------------------------")


def replay_buffer_handler(event):
    """Event function reacting to OBS Event of saving the replay buffer."""
    if event == obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_SAVED:
        print("------------------------------")
        print("Saving the Replay Buffer...")

        print("Refreshing sourceUUID...")
        refresh_source_uuid()

        print("Running get_hooked procedure to get current app title...")
        check_if_hooked_and_update_title()

        rec = Recording(isReplay=True)

        rec.create_new_folder()

        rec.remember_and_move()

        print(f"Old path: {rec.get_oldPath()}")
        print(f"New path: {rec.get_newPath()}")
        print("------------------------------")


def check_if_hooked_and_update_title():
    """Function checks if source selected by user is hooked to any window and takes the title of hooked window

    Raises:
        TypeError: Only triggers when sourceUUID is None and causes the title to reset to defaultRecordingName
    """
    global sourceUUID, gameTitle, defaultRecordingTitle

    try:
        if sourceUUID is None:
            raise TypeError

    except TypeError:
        print("Source UUID is empty. Defaulting to 'Manual Recording'")
        gameTitle = defaultRecordingTitle
        return

    calldata = get_hooked(sourceUUID)
    print("Checking if source is hooked to any window...")
    if calldata is not None:
        if not gh_isHooked(calldata):
            obs.calldata_destroy(calldata)
            gameTitle = defaultRecordingTitle
            print("Call data was empty, using default name for uncaptured windows...")
            return
        print("Hooked!")
        gameTitle = gh_title(calldata)
        print(f"Current GameTitle: {gameTitle}")
    obs.calldata_destroy(calldata)


def get_hooked(uuid):
    source = obs.obs_get_source_by_uuid(uuid)
    cd = obs.calldata_create()
    ph = obs.obs_source_get_proc_handler(source)
    obs.proc_handler_call(ph, "get_hooked", cd)
    obs.obs_source_release(source)
    return cd


def gh_isHooked(calldata) -> bool:
    return obs.calldata_bool(calldata, "hooked")


def gh_title(calldata) -> str:
    return remove_unusable_title_characters(obs.calldata_string(calldata, "title"))


# HELPER FUNCTIONS

def remove_unusable_title_characters(title):
    # Remove non-alphanumeric characters (ex. ':')
    title = re.sub(r"[^A-Za-z0-9 ]+", "", title)

    # Remove whitespaces at the end
    title = "".join(title.rstrip())

    # Remove additional whitespaces
    title = " ".join(title.split())

    return title


def get_recording_source_uuid(configured_source):
    """Checks if the source selected by user exists in the scene and returns found information.

    Returns:
        UUID: Source UUID or None
    """

    global sourceUUID

    current_scene_as_source = obs.obs_frontend_get_current_scene()

    if current_scene_as_source:
        current_scene = obs.obs_scene_from_source(current_scene_as_source)
        scene_item = obs.obs_scene_find_source_recursive(
            current_scene, configured_source
        )
        if scene_item:
            source = obs.obs_sceneitem_get_source(scene_item)
            source_uuid = obs.obs_source_get_uuid(source)
        else:
            source_uuid = None

    obs.obs_source_release(current_scene_as_source)

    return source_uuid


def refresh_source_uuid():
    global sett, sourceUUID
    s_name = obs.obs_data_get_string(sett, "source")

    if len(s_name) > 0:
        try:
            sourceUUID = get_recording_source_uuid(s_name)
            if sourceUUID is None:
                raise TypeError
        except TypeError:
            print("Source not selected, please refresh and re-select")
            sourceUUID = None
    else:
        sourceUUID = None


def find_latest_file(folder_path, file_type):
    files = glob.glob(folder_path + file_type)
    if files:
        max_file = max(files, key=os.path.getctime)
        return os.path.normpath(max_file)
    else:
        textFile = script_path() + "latest_file.txt"
        text = "".join(str(x) for x in files)
        with open(textFile, "w") as f:
            f.write(text)

        with open(textFile, "r") as f:
            print(f.read())

        os.remove(textFile)
        return find_latest_file(folder_path, file_type)


# OBS FUNCTIONS

def script_load(settings):
    # Loading in settings
    global sett
    sett = settings

    # Loading in Signals
    file_changed_sh()  # Respond to splitting the recording (ex. automatic recording split)

    # Loading in Frontend events to deal with Replay Buffer saving

    obs.obs_frontend_add_event_callback(start_buffer_handler)
    obs.obs_frontend_add_event_callback(replay_buffer_handler)
    obs.obs_frontend_add_event_callback(start_recording_handler)
    obs.obs_frontend_add_event_callback(recording_stop_handler)


def script_defaults(settings):
    obs.obs_data_set_default_string(settings, "extension", "mkv")


def script_update(settings):
    global addTitleBool, recordingExtension, recordingExtensionMask, outputDir

    # Fetching the Settings
    addTitleBool = obs.obs_data_get_bool(settings, "title_before_bool")
    outputDir = os.path.normpath(obs.obs_data_get_string(settings, "outputdir"))

    recordingExtension = obs.obs_data_get_string(settings, "extension")
    recordingExtensionMask = "\*" + recordingExtension

    print("Updated the settings!")


def script_description():
    desc = (
        "<h3>OBS RecORDER </h3>"
        "<hr>"
        "Renames and organizes recordings/replays into subfolders similar to NVIDIA ShadowPlay (<i>NVIDIA GeForce Experience</i>).<br><br>"
        "<small>Created by:</small> <b>padii</b><br><br>"
        "<h4>Settings:</h4>"
    )
    return desc


def UUID_of_sel_src(props, prop, *args, **kwargs):
    p = obs.obs_properties_get(props, "src_uuid")
    refresh_source_uuid()
    obs.obs_property_set_description(p, f"UUID: {sourceUUID}")
    return True


def populate_list_property_with_source_names(list_property):
    obs.obs_property_list_clear(list_property)
    sources = obs.obs_enum_sources()
    obs.obs_property_list_clear(list_property)
    obs.obs_property_list_add_string(list_property, "", "")
    for source in sources:
        name = obs.obs_source_get_name(source)
        obs.obs_property_list_add_string(list_property, name, name)
    obs.source_list_release(sources)


def refresh_list_and_get_uuid(props, prop, *args, **kwargs):
    lst = obs.obs_properties_get(props, "source")
    populate_list_property_with_source_names(lst)

    p = obs.obs_properties_get(props, "src_uuid")
    refresh_source_uuid()
    obs.obs_property_set_description(p, f"UUID: {sourceUUID}")
    return True


def refresh_pressed(props, prop):
    print("Refreshed sources list!")


def script_properties():
    props = obs.obs_properties_create()

    # Title checkmark
    bool_p = obs.obs_properties_add_bool(
        props, "title_before_bool", "Add name of the game as a recording prefix"
    )
    obs.obs_property_set_long_description(
        bool_p,
        "Check if you want to have name of the application name appended as a prefix to the recording, else uncheck",
    )

    # Source list
    sources_for_recording = obs.obs_properties_add_list(
        props,
        "source",
        "Capturing source name",
        obs.OBS_COMBO_TYPE_LIST,
        obs.OBS_COMBO_FORMAT_STRING,
    )

    populate_list_property_with_source_names(sources_for_recording)
    obs.obs_property_set_modified_callback(sources_for_recording, UUID_of_sel_src)

    # Refresh button!
    b = obs.obs_properties_add_button(
        props, "button", "Refresh source list", refresh_pressed
    )
    obs.obs_property_set_modified_callback(b, refresh_list_and_get_uuid)

    # UUID of the selected source (debugging only)
    uuid_text = obs.obs_properties_add_text(props, "src_uuid", "", obs.OBS_TEXT_INFO)
    obs.obs_property_set_modified_callback(uuid_text, UUID_of_sel_src)

    # Output directory
    obs.obs_properties_add_path(
        props,
        "outputdir",
        "Recordings folder",
        obs.OBS_PATH_DIRECTORY,
        None,
        str(Path.home()),
    )

    # Extension of file
    obs.obs_properties_add_text(
        props, "extension", "Recording extension", obs.OBS_TEXT_DEFAULT
    )

    return props


def script_unload():
    # Fetching global variables
    global addTitleBool, recordingExtension, recordingExtensionMask, outputDir
    global sourceUUID, sett
    global currentRecording, gameTitle, isRecording, defaultRecordingTitle
    # Clear Settings class
    addTitleBool = None
    recordingExtension = None
    recordingExtensionMask = None
    outputDir = None

    # Clear cached settings and important global values
    sourceUUID = None
    sett = None

    # Clear recording related values
    currentRecording = None
    gameTitle = None
    isRecording = False
    defaultRecordingTitle = None


class Recording:
    """Class that allows better control over files for the needs of this script"""

    def __init__(self, customPath=None, isReplay=False) -> None:
        """Create a file based on either specified path or path that was configured in Scripts settings

        Args:
            customPath (str): Path to a file that needs to be moved
            isReplay (bool): Set to true if handled recording is from replay buffer
        """
        global recordingExtension, recordingExtensionMask, outputDir

        self.dataExtension = "." + recordingExtension
        self.replaysFolderName = "Replays"

        # If this object is created during Replay Buffer handling, it will do additional stuff needed
        if isReplay:
            self.isReplay = isReplay
        else:
            self.isReplay = False

        # Allow to specify a custom path where the file is located.
        if customPath is not None:
            self.path = customPath
        else:
            self.path = find_latest_file(outputDir, recordingExtensionMask)

        # Prepare paths needed for functions
        self.dir = os.path.dirname(self.path)
        self.rawfile = os.path.basename(self.path)

    def get_filename(self) -> str:
        """Returns the file name

        Returns:
            str: name of a file
        """
        return self.rawfile[: -len(self.dataExtension)] + self.dataExtension

    def get_newFolder(self) -> str:
        """Returns a path to a folder where recording will be moved to
        If recording is a replay buffer, it will return the path towards the replays folder inside of folder above

        Returns:
            str: name of the new folder where the recording will be located
        """
        if self.isReplay:
            global gameTitle
            return os.path.join(self.dir, gameTitle, self.replaysFolderName)
        else:
            return os.path.join(self.dir, gameTitle)

    def get_newFilename(self) -> str:
        """Returns the name of a file based on the choice of the user
        If user decided to have game title before recording name, it will add it.

        Returns:
            str: name of the recording
        """
        global addTitleBool
        if addTitleBool:
            global gameTitle
            return gameTitle + " - " + self.get_filename()
        else:
            return self.get_filename()

    def get_oldPath(self) -> str:
        """Returns previous path the file was located in

        Returns:
            str: previous path of file
        """
        return os.path.join(self.dir, self.get_filename())

    def get_newPath(self) -> str:
        """Returns current path where file is located

        Returns:
            str: current path of file
        """
        return os.path.join(self.get_newFolder(), self.get_newFilename())

    def create_new_folder(self) -> None:
        """Creates a new folder based on title of the captured fullscreen application"""
        if not os.path.exists(self.get_newFolder()):
            os.makedirs(self.get_newFolder())

    def remember_and_move(self) -> None:
        """Moves the recording to new location using os.renames"""
        oldPath = self.get_oldPath()
        newPath = self.get_newPath()

        time.sleep(0.01)

        os.renames(oldPath, newPath)
