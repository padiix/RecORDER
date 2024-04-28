import glob
import obspython as obs  # type: ignore
import re
import os
import os.path
import shutil
from pathlib import Path

# Rewriting whole script using the Signals!
# "file_changed" signal = lets move the automatically splitted file to a folder
# "hooked" signal = gets captured window and possibly a title of a captured game
#


# SIGNAL-RELATED
def start_rec_sh():
    sh = obs.obs_output_get_signal_handler(obs.obs_frontend_get_recording_output())
    obs.signal_handler_connect(sh, "activate", start_rec_cb)


def start_rec_cb(calldata):
    print("\n[-----]\n")
    print("Recording has started.")
    RecordingInfo.isRecording = True
    RecordingInfo.CurrentRecording = None
    print("Cleared the CurrentRecording variable in case of left over data." + "\n")


def file_changed_sh():
    sh = obs.obs_output_get_signal_handler(obs.obs_frontend_get_recording_output())
    obs.signal_handler_connect(sh, "file_changed", file_changed_cb)


def file_changed_cb(calldata):
    print("File was changed, moving the previous one to fitting folder...")
    print("\n========================================\n")

    # GETTING THE PREVIOUS FILE FIRST
    # I'm not happy with that, but it will have to do
    RecordingInfo.CurrentRecording = find_latest_file(
        Settings.OutputDir, Settings.ExtensionMask
    )
    print("Previous file: " + RecordingInfo.CurrentRecording)

    file = File(customPath=RecordingInfo.CurrentRecording)
    file.create_new_folder()
    file.remember_and_move()

    print("Moved the old file.")
    print("Old path: " + file.get_oldPath())
    print("New path: " + file.get_newPath())
    RecordingInfo.CurrentRecording = None
    print("\n========================================\n")

    print("Getting the new file...")
    RecordingInfo.CurrentRecording = obs.calldata_string(calldata, "next_file")
    print("Current file: " + RecordingInfo.CurrentRecording + "\n")


def hooked_sh():
    source = obs.obs_get_source_by_name(
        obs.obs_data_get_string(Settings.Sett, "source")
    )
    sh = obs.obs_source_get_signal_handler(source)

    obs.signal_handler_connect(sh, "hooked", refresh_captured_window_title_cb)

    obs.obs_source_release(source)


def refresh_captured_window_title_cb(calldata):
    scene_as_source = obs.obs_frontend_get_current_scene()

    if obs.obs_source_get_name(scene_as_source) != obs.obs_data_get_string(
        Settings.Sett, "scene"
    ):
        obs.obs_source_release(scene_as_source)
        return None

    scene_items = obs.obs_scene_enum_items(obs.obs_scene_from_source(scene_as_source))

    source = None
    for item in scene_items:
        source_item = obs.obs_sceneitem_get_source(item)
        source_name = obs.obs_source_get_name(source_item)
        if source_name == obs.obs_data_get_string(Settings.Sett, "source"):
            source = source_item
            break
    obs.sceneitem_list_release(scene_items)

    if source is None:
        print("Could not find selected source in current scene")
        return

    # Grab the title name
    RecordingInfo.GameTitle = remove_unusable_title_characters(
        obs.calldata_string(calldata, "title")
    )
    print("Game title changed: " + RecordingInfo.GameTitle + "\n")

    obs.obs_source_release(scene_as_source)


def unhooked_sh():
    source = obs.obs_get_source_by_name(
        obs.obs_data_get_string(Settings.Sett, "source")
    )
    sh = obs.obs_source_get_signal_handler(source)

    obs.signal_handler_connect(sh, "unhooked", reset_captured_window_title_cb)


def reset_captured_window_title_cb(calldata):
    if RecordingInfo.isRecording is True:
        return
    reset_game_title()


def stop_rec_sh():
    sh = obs.obs_output_get_signal_handler(obs.obs_frontend_get_recording_output())
    obs.signal_handler_connect(sh, "stop", stop_rec_cb)


def stop_rec_cb(calldata):
    print("Recording has stopped, moving the last file into right folder...")

    if RecordingInfo.CurrentRecording is None:
        RecordingInfo.CurrentRecording = find_latest_file(
            Settings.OutputDir, Settings.ExtensionMask
        )

    file = File(customPath=RecordingInfo.CurrentRecording)
    file.create_new_folder()
    file.remember_and_move()

    print("Job's done. The file was moved.")
    print("File: " + file.get_filename())
    print("========================================")
    print("Old path: " + file.get_oldPath())
    print("New path: " + file.get_newPath())

    file.clear_variables()
    RecordingInfo.CurrentRecording = None

    OBS_OUTPUT_CODES = dict(
        [
            (0, "OBS_OUTPUT_SUCCESS"),
            (1, "OBS_OUTPUT_BAD_PATH"),
            (2, "OBS_OUTPUT_CONNECT_FAILED"),
            (3, "OBS_OUTPUT_INVALID_STREAM"),
            (4, "OBS_OUTPUT_ERROR"),
            (5, "OBS_OUTPUT_DISCONNECTED"),
            (6, "OBS_OUTPUT_UNSUPPORTED"),
            (7, "OBS_OUTPUT_NO_SPACE"),
            (8, "OBS_OUTPUT_ENCODE_ERROR"),
        ]
    )

    print(
        "Output signal returned: "
        + OBS_OUTPUT_CODES.get(obs.calldata_int(calldata, "code"))
        + "\n"
    )
    RecordingInfo.isRecording = False


def replay_buffer_handler(event):
    if event == obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_SAVED:
        print("Triggered when the replay buffer is saved.")

        file = File(isReplay=True)

        file.create_new_folder()

        file.remember_and_move()

        print("Old path: " + file.get_oldPath())
        print("New path: " + file.get_newPath() + "\n")

        file.clear_variables()


# HELPER FUNCTIONS
def remove_unusable_title_characters(title):
    # Remove non-alphanumeric characters (ex. ':')
    title = re.sub(r"[^A-Za-z0-9 ]+", "", title)
    # Remove whitespaces at the end
    title = "".join(title.rstrip())
    # Remove additional whitespaces
    title = " ".join(title.split())

    return title


def find_latest_file(folder_path, file_type):
    files = glob.glob(folder_path + file_type)
    max_file = max(files, key=os.path.getctime)
    return max_file


def reset_game_title():
    RecordingInfo.GameTitle = "Manual Recording"
    print("Game title changed: " + RecordingInfo.GameTitle + "\n")


# OBS FUNCTIONS
def script_load(settings):
    # Loading in settings
    Settings.Sett = settings

    # Loading in Signals
    hooked_sh()  # Respond to capturing any fullscreen window
    unhooked_sh()  # Respond to stopped capture of fullscreen window
    start_rec_sh()  # Respond to starting recording
    file_changed_sh()  # Respond to splitting the recording (ex. automatic recording split)
    stop_rec_sh()  # Respond to stopping the recording

    # Loading in Frontend events to deal with Replay Buffer saving
    obs.obs_frontend_add_event_callback(replay_buffer_handler)


def script_defaults(settings):
    obs.obs_data_set_default_string(settings, "extension", "mkv")


def script_update(settings):
    # Fetching the Settings
    Settings.AddTitleBool = obs.obs_data_get_bool(settings, "title_before_bool")
    Settings.OutputDir = obs.obs_data_get_string(settings, "outputdir")
    Settings.OutputDir = Settings.OutputDir.replace("/", "\\")
    Settings.Extension = obs.obs_data_get_string(settings, "extension")
    Settings.ExtensionMask = "\*" + Settings.Extension


def script_description():
    desc = (
        "<h3>OBS RecORDER </h3>"
        "<hr>"
        "Renames and organizes recordings/replays into subfolders similar to NVIDIA ShadowPlay (<i>NVIDIA GeForce Experience</i>).<br><br>"
        "<small>Created by:</small> <b>padii</b><br><br>"
        "<h4>Settings:</h4>"
    )
    return desc


def script_properties():
    props = obs.obs_properties_create()

    # Title checkmark
    bool_p = obs.obs_properties_add_bool(
        props, "title_before_bool", "Add name of the game as a recording prefix"
    )
    obs.obs_property_set_long_description(
        bool_p,
        "Check if you want to have name of the game appended as a prefix to the recording, else uncheck",
    )

    # Scene list
    scene_for_recording = obs.obs_properties_add_list(
        props,
        "scene",
        "Scene for recording",
        obs.OBS_COMBO_TYPE_LIST,
        obs.OBS_COMBO_FORMAT_STRING,
    )
    populate_list_property_with_scenes(scene_for_recording)

    # Source list
    sources_for_recording = obs.obs_properties_add_list(
        props,
        "source",
        "Source name",
        obs.OBS_COMBO_TYPE_LIST,
        obs.OBS_COMBO_FORMAT_STRING,
    )
    populate_list_property_with_source_names(sources_for_recording)

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
        props, "extension", "File extension", obs.OBS_TEXT_DEFAULT
    )

    return props


def populate_list_property_with_scenes(list_property):
    scenes = obs.obs_frontend_get_scene_names()

    for scene in scenes:
        obs.obs_property_list_add_string(list_property, scene, scene)
    obs.source_list_release(scenes)


def populate_list_property_with_source_names(list_property):
    sources = obs.obs_enum_sources()
    obs.obs_property_list_clear(list_property)
    obs.obs_property_list_add_string(list_property, "", "")
    for source in sources:
        name = obs.obs_source_get_name(source)
        obs.obs_property_list_add_string(list_property, name, name)
    obs.source_list_release(sources)


def script_unload():
    # Clear Settings class
    Settings.AddTitleBool = None
    Settings.Extension = None
    Settings.ExtensionMask = None
    Settings.OutputDir = None
    Settings.Sett = None

    # Clear RecordingInfo class
    RecordingInfo.CurrentRecording = None
    RecordingInfo.GameTitle = None
    RecordingInfo.isRecording = False


# CLASSES
class RecordingInfo:
    """Class that holds important information about recording"""

    CurrentRecording = None
    GameTitle = "Manual Recording"
    isRecording = False


class Settings:
    """Class that holds data from Script settings to use in script"""

    AddTitleBool = None
    Extension = None
    ExtensionMask = None
    OutputDir = None
    Sett = None


class File:
    """Class that allows better control over files for the needs of this script"""

    def __init__(self, customPath=None, isReplay: bool = False) -> None:
        """Create a file based on either specified path or path that was configured in Scripts settings

        Args:
            customPath (str): Path to a file that needs to be moved
        """
        self.dataExtension = "." + Settings.Extension
        self.replaysFolderName = "Replays"

        if isReplay is not None:
            self.isReplay = isReplay
        else:
            self.isReplay = False

        # Lets the file_changed cb work as I intended
        if customPath is not None:
            self.path = customPath
        else:
            self.path = find_latest_file(Settings.OutputDir, Settings.ExtensionMask)

        self.dir = os.path.dirname(self.path)
        self.title = RecordingInfo.GameTitle

        self.rawfile = os.path.basename(self.path)
        self.file = self.rawfile[: -len(self.dataExtension)] + self.dataExtension
        self.newFolder = self.dir + "\\" + self.title

        if Settings.AddTitleBool is True:
            self.newfile = self.title + " - " + self.file
        else:
            self.newfile = self.file

    def get_filename(self) -> str:
        """Returns the file name

        Returns:
            str: name of a file
        """
        return self.file

    def get_oldPath(self) -> str:
        """Returns previous path the file was located in

        Returns:
            str: previous path of file
        """
        return self.dir + "\\" + self.file

    def get_newPath(self) -> str:
        """Returns current path where file is located

        Returns:
            str: current path of file
        """
        return self.newFolder + "\\" + self.newfile

    def create_new_folder(self) -> None:
        """Creates a new folder based on title of the captured fullscreen application"""
        if not os.path.exists(self.newFolder):
            os.makedirs(self.newFolder)

        if self.isReplay is True:
            if not os.path.exists(self.newFolder):
                self.newFolder = self.newFolder + "\\" + self.replaysFolderName
                os.makedirs(self.newFolder)

    def remember_and_move(self) -> None:
        """Remembers the previous location of the file and moves it to a new one"""
        oldPath = self.dir + "\\" + self.file
        newPath = self.newFolder + "\\" + self.newfile

        textFile = oldPath[:-3] + "txt"

        f = open(oldPath[:-3] + "txt", "w")
        f.write(newPath)
        f.close()

        shutil.move(oldPath, newPath)
        os.remove(textFile)

    def refresh_variables(self) -> None:
        """Refreshes information in parameters used by this class"""
        self.dataExtension = "." + Settings.Extension
        self.path = find_latest_file(Settings.OutputDir, Settings.ExtensionMask)
        self.dir = os.path.dirname(self.path)
        self.title = RecordingInfo.GameTitle

        self.rawfile = os.path.basename(self.path)
        self.file = self.rawfile[: -len(self.dataExtension)] + self.dataExtension
        self.newFolder = self.dir + "\\" + self.title

        if Settings.AddTitleBool is True:
            self.newfile = self.title + " - " + self.file
        else:
            self.newfile = self.file

    def clear_variables(self) -> None:
        """Clears parameters from data"""
        self.path = None
        self.dir = None
        self.title = None
        self.rawfile = None
        self.file = None
        self.newFolder = None
        self.isReplay = False
