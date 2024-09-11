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
screenshotExtension = None
screenshotExtensionMask = None
outputDir = None
file_changed_sh_ref = None


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
    global file_changed_sh_ref
    if file_changed_sh_ref:
        return
    output = obs.obs_frontend_get_recording_output()
    file_changed_sh_ref = obs.obs_output_get_signal_handler(output)
    obs.signal_handler_connect(file_changed_sh_ref, "file_changed", file_changed_cb)
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

    global currentRecording, recordingExtensionMask, outputDir
    currentRecording = find_latest_file(outputDir, recordingExtensionMask)
    
    print(f"Saved recording: {currentRecording}")

    rec = Recording(customPath=currentRecording)
    rec.create_new_folder()
    rec.remember_and_move()

    print("Done!")
    print(f"New path: {rec.get_newPath()}")
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
        # print("[recording_stop_handler]")
        print("Refreshing sourceUUID...")
        refresh_source_uuid()

        print("Recording has stopped, moving the last file into right folder...")
        print("Running get_hooked procedure to get current app title...")
        check_if_hooked_and_update_title()

        global currentRecording, isRecording

        rec = Recording()
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
        # print("[replay_buffer_handler]")
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
        
def screenshot_handler_event(event):
    """Event function reacting to OBS Event of taking the screenshot."""
    
    if event == obs.OBS_FRONTEND_EVENT_SCREENSHOT_TAKEN:
        print("------------------------------")
        print("Taking the screenshot...")

        print("Refreshing sourceUUID...")
        refresh_source_uuid()

        print("Running get_hooked procedure to get current app title...")
        check_if_hooked_and_update_title()
        
        scrnst = Screenshot()
        scrnst.create_new_folder()
        scrnst.remember_and_move()
        
        print(f"Old path: {scrnst.get_oldPath()}")
        print(f"New path: {scrnst.get_newPath()}")
        print("------------------------------")


def check_if_hooked_and_update_title():
    """Function checks if source selected by user is hooked to any window and takes the title of hooked window

    Raises:
        TypeError: Only triggers when sourceUUID is None and causes the title to reset to defaultRecordingName
    """
    global sourceUUID, gameTitle, defaultRecordingTitle

    # print("[check_if_hooked_and_update_title]")
    
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
        try:
            gameTitle = gh_title(calldata)
        except TypeError:
            print("Failed to get title, using default name - restart OBS or captured app.")
            gameTitle = defaultRecordingTitle
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

    # print("[refresh_source_uuid]")

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

# OBS FUNCTIONS

def script_load(settings):
    # Loading in settings
    global sett
    sett = settings

    # Loading in Signals
    file_changed_sh()  # Respond to splitting the recording (ex. automatic recording split)

    # Loading in Frontend events
    obs.obs_frontend_add_event_callback(start_buffer_handler)
    obs.obs_frontend_add_event_callback(replay_buffer_handler)
    obs.obs_frontend_add_event_callback(start_recording_handler)
    obs.obs_frontend_add_event_callback(recording_stop_handler)
    obs.obs_frontend_add_event_callback(screenshot_handler_event)


def script_defaults(settings):
    obs.obs_data_set_default_string(settings, "extension", "mkv")
    obs.obs_data_set_default_string(settings, "ss_extension", "png")


def script_update(settings):
    global addTitleBool, recordingExtension, recordingExtensionMask, outputDir, screenshotExtension, screenshotExtensionMask

    # Fetching the Settings
    addTitleBool = obs.obs_data_get_bool(settings, "title_before_bool")
    outputDir = os.path.normpath(obs.obs_data_get_string(settings, "outputdir"))

    recordingExtension = obs.obs_data_get_string(settings, "extension")
    recordingExtensionMask = "\*" + recordingExtension
    
    screenshotExtension = obs.obs_data_get_string(settings, "ss_extension")
    screenshotExtensionMask = "\*" + screenshotExtension

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
    current_scene_as_source = obs.obs_frontend_get_current_scene()
    scene = obs.obs_scene_from_source(current_scene_as_source)
    
    obs.obs_property_list_clear(list_property)
    sceneitems = obs.obs_scene_enum_items(scene)
    obs.obs_property_list_clear(list_property)
    obs.obs_property_list_add_string(list_property, "", "")
    for item in sceneitems:
        source = obs.obs_sceneitem_get_source(item)
        name = obs.obs_source_get_name(source)
        obs.obs_property_list_add_string(list_property, name, name)
    obs.source_list_release(sceneitems)
    obs.obs_source_release(current_scene_as_source)


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
    
    obs.obs_properties_add_text(
        props, "ss_extension", "Screenshot extension", obs.OBS_TEXT_DEFAULT
    )

    return props


def script_unload():
    # Fetching global variables
    global addTitleBool, recordingExtension, recordingExtensionMask, outputDir, screenshotExtension, screenshotExtensionMask, file_changed_sh_ref
    global sourceUUID, sett
    global currentRecording, gameTitle, isRecording, defaultRecordingTitle
    # Clear Settings class
    addTitleBool = None
    recordingExtension = None
    recordingExtensionMask = None
    screenshotExtension = None
    screenshotExtensionMask = None
    outputDir = None
    file_changed_sh_ref = None

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
        global recordingExtensionMask, outputDir

        self.replaysFolderName = "Replays"

        # If this object is created during Replay Buffer handling, it will do additional stuff needed
        if isReplay:
            self.isReplay = isReplay
        else:
            self.isReplay = False

        # Allow to specify a custom path where the file is located.
        if customPath is not None:
            self.path = customPath
        elif self.isReplay:
            self.path = obs.obs_frontend_get_last_replay()
        elif not self.isReplay:
            self.path = obs.obs_frontend_get_last_recording()

        # Prepare paths needed for functions
        self.dir = os.path.dirname(self.path)
        self.rawfile = os.path.basename(self.path)

    def get_filename(self) -> str:
        """Returns the file name

        Returns:
            str: name of a file
        """
        return self.rawfile

    def get_newFolder(self) -> str:
        """Returns a path to a folder where recording will be moved to
        If recording is a replay buffer, it will return the path towards the replays folder inside of folder above

        Returns:
            str: name of the new folder where the recording will be located
        """
        global gameTitle
        if self.isReplay:
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

    def remember_and_move(self, ttw=0.01) -> None:
        """Moves the recording to new location using os.renames"""
        
        oldPath = self.get_oldPath()
        newPath = self.get_newPath()

        time.sleep(ttw)
        try:
            os.renames(oldPath, newPath)
        except PermissionError:
            time.sleep(ttw)
            os.renames(oldPath, newPath)
        
class Screenshot:
    """Class that allows better control over screenshots for the needs of this script"""

    def __init__(self, customPath=None) -> None:
        """Create a file based on either specified path or path that was configured in Scripts settings

        Args:
            customPath (str): Path to a file that needs to be moved
            isReplay (bool): Set to true if handled recording is from replay buffer
        """
        global screenshotExtensionMask, outputDir

        self.screenshotsPath = outputDir
        self.screenshotsExtension = screenshotExtensionMask
        self.screenshotsFolderName = "Screenshots"

        # Allow to specify a custom path where the file is located.
        if customPath is not None:
            self.path = customPath
        else:
            self.path = find_latest_file(outputDir, screenshotExtensionMask, 0.01)

        # Prepare paths needed for functions
        self.dir = os.path.dirname(self.path)
        self.rawfile = os.path.basename(self.path)

    def get_filename(self) -> str:
        """Returns the file name

        Returns:
            str: name of a file
        """
        return self.rawfile

    def get_newFolder(self) -> str:
        """Returns a path to a folder where recording will be moved to
        If recording is a replay buffer, it will return the path towards the replays folder inside of folder above

        Returns:
            str: name of the new folder where the recording will be located
        """
        
        return os.path.join(self.dir, gameTitle, self.screenshotsFolderName)

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
