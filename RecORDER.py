import asyncio
import sys
import threading
from glob import glob
from os import makedirs
from os import path as os_path
from pathlib import Path
from re import sub
from shutil import move as move_file

import obspython as obs

# Author: oxypatic! (61553947+padiix@users.noreply.github.com)

# TODO: Implement a way for storing the UUID and Signals that react to it's deletion, etc. (Not figured out by me yet)
# TODO: Config instead of the Classes storing the data (Need to think if it's necessary, but probably not)


# >>> ONLY PLACE WHERE MODIFICATIONS ARE SAFE FOR YOU TO DO! <<<
# Table of capturing video source names
sourceNames = ["Game Capture", "Window Capture"]
# >>> ONLY PLACE WHERE MODIFICATIONS ARE SAFE FOR YOU TO DO! <<<

if sys.version_info[0] < 3 or sys.version_info[1] < 11:
    print("Python version < 3.11, correct behaviour is not guaranteed")


# CLASSES

class GlobalVariables:
    """Class that holds and allows better control over the Global variables used in this script"""

    def __init__(self):
        # [PROPERTIES]
        self.add_game_title_to_recording_name = None
        self.recording_extension = None
        self.screenshot_extension = None
        self.time_to_wait = 0.02

        # [Related to RECORDING]
        self.defaultRecordingName = "Manual Recording"
        self.isRecording = False
        self.isReplayActive = False
        self.current_recording_path = None
        self.game_title = self.defaultRecordingName
        self.output_directory = None
        self.source_uuid = None

    def load_func(self, add_game_title_to_recording_name: bool, recording_extension: str, screenshot_extension: str,
                  output_directory: str):
        self.add_game_title_to_recording_name = add_game_title_to_recording_name
        self.recording_extension = recording_extension
        self.screenshot_extension = screenshot_extension
        self.output_directory = output_directory

    # ---

    def get_add_game_title_to_recording_name(self):
        return self.add_game_title_to_recording_name

    def get_recording_extension(self):
        return self.recording_extension

    def get_screenshot_extension(self):
        return self.screenshot_extension

    def get_recording_extension_mask(self):
        return f"*.{self.recording_extension}"

    def get_screenshot_extension_mask(self):
        return f"*.{self.screenshot_extension}"

    def get_time_to_wait(self):
        return self.time_to_wait

    # ---

    def get_default_recording_name(self):
        return self.defaultRecordingName

    def get_is_recording(self):
        return self.isRecording

    def set_is_recording(self, value: bool):
        self.isRecording = value

    def get_is_replay_active(self):
        return self.isReplayActive

    def set_is_replay_active(self, value: bool):
        self.isReplayActive = value

    def get_current_recording(self):
        return self.current_recording_path

    def set_current_recording(self, value):
        self.current_recording_path = value

    def get_game_title(self):
        return self.game_title

    def set_game_title(self, value: str):
        self.game_title = remove_unusable_title_characters(value)

    def get_output_dir(self):
        return self.output_directory

    def get_source_uuid(self):
        return self.source_uuid

    def set_source_uuid(self, value: str):
        self.source_uuid = value

    # ---

    def unload_func(self):
        self.add_game_title_to_recording_name = None
        self.recording_extension = None
        self.screenshot_extension = None
        self.defaultRecordingName = None
        self.source_uuid = None
        self.isRecording = None
        self.isReplayActive = None
        self.current_recording_path = None
        self.game_title = None
        self.output_directory = None


class Recording:
    """Class that allows better control over files for the needs of this script"""

    def __init__(self, custom_path: str = None, is_replay: bool = False) -> None:
        """Create a file based on either specified path or path that was configured in Scripts settings

        Args:
            custom_path (str): Path to a file that needs to be moved
            is_replay (bool): Set to true if handled recording is from replay buffer
        """

        global globalVariables

        self.replaysFolderName = "Replays"
        self.gameTitle = globalVariables.get_game_title()
        self.addTitleBool = globalVariables.get_add_game_title_to_recording_name()

        # If this object is created during Replay Buffer handling, it will do additional stuff needed
        if is_replay:
            self.isReplay = is_replay
        else:
            self.isReplay = False

        # Allow to specify a custom path where the file is located.
        if custom_path is not None:
            self.path = custom_path
        elif self.isReplay:
            self.path = obs.obs_frontend_get_last_replay()
        elif not self.isReplay:
            self.path = obs.obs_frontend_get_last_recording()

        # Prepare paths needed for functions
        self.dir = os_path.dirname(self.path)
        self.raw_file = os_path.basename(self.path)

    def get_filename(self) -> str:
        """Returns the file name

        Returns:
            str: name of a file
        """
        return self.raw_file

    def get_new_folder(self) -> str:
        """Returns a path to a folder where recording will be moved to
        If recording is a replay buffer, it will return the path towards the replays folder inside of folder above

        Returns:
            str: name of the new folder where the recording will be located
        """
        if self.isReplay:
            return os_path.normpath(os_path.join(self.dir, self.gameTitle, self.replaysFolderName))
        else:
            return os_path.normpath(os_path.join(self.dir, self.gameTitle))

    def get_new_filename(self) -> str:
        """Returns the name of a file based on the choice of the user
        If user decided to have game title before recording name, it will add it.

        Returns:
            str: name of the recording
        """
        if self.addTitleBool:
            return f"{self.gameTitle} - {self.get_filename()}"
        else:
            return self.get_filename()

    def get_old_path(self) -> str:
        """Returns previous path the file was located in

        Returns:
            str: previous path of file
        """
        return os_path.normpath(os_path.join(self.dir, self.get_filename()))

    def get_new_path(self) -> str:
        """Returns current path where file is located

        Returns:
            str: current path of file
        """
        return os_path.normpath(os_path.join(self.get_new_folder(), self.get_new_filename()))

    def create_new_folder(self) -> None:
        """Creates a new folder based on title of the captured fullscreen application"""
        if not os_path.exists(self.get_new_folder()):
            makedirs(self.get_new_folder())


class Screenshot:
    """Class that allows better control over screenshots for the needs of this script"""

    def __init__(self, custom_path: str = None) -> None:
        """Create a file based on either specified path or path that was configured in Scripts settings

        Args:
            custom_path (str): Path to a file that needs to be moved
        """
        global globalVariables

        self.screenshots_folder_name = "Screenshots"
        self.game_title = globalVariables.get_game_title()
        self.add_game_title_to_recording_name = globalVariables.get_add_game_title_to_recording_name()

        # Allow to specify a custom path where the file is located.
        if custom_path is not None:
            self.path = custom_path
        else:
            self.path = obs.obs_frontend_get_last_screenshot()

        # Prepare paths needed for functions
        self.dir = os_path.dirname(self.path)
        self.raw_file = os_path.basename(self.path)

    def get_file_name(self) -> str:
        """Returns the file name

        Returns:
            str: name of a file
        """
        return self.raw_file

    def get_new_folder(self) -> str:
        """Returns a path to a folder where recording will be moved to
        If recording is a replay buffer, it will return the path towards the replays folder inside of folder above

        Returns:
            str: name of the new folder where the recording will be located
        """
        return os_path.normpath(os_path.join(self.dir, self.game_title, self.screenshots_folder_name))

    def get_new_filename(self) -> str:
        """Returns the name of a file based on the choice of the user
        If user decided to have game title before recording name, it will add it.

        Returns:
            str: name of the recording
        """
        if self.add_game_title_to_recording_name:
            return f"{self.game_title} - {self.get_file_name()}"
        else:
            return self.get_file_name()

    def get_old_path(self) -> str:
        """Returns previous path the file was located in

        Returns:
            str: previous path of file
        """
        return os_path.normpath(os_path.join(self.dir, self.get_file_name()))

    def get_new_path(self) -> str:
        """Returns current path where file is located

        Returns:
            str: current path of file
        """
        return os_path.normpath(os_path.join(self.get_new_folder(), self.get_new_filename()))

    def create_new_folder(self) -> None:
        """Creates a new folder based on title of the captured fullscreen application"""
        if not os_path.exists(self.get_new_folder()):
            makedirs(self.get_new_folder())

# Values supporting smooth working and fewer calls

sett = None
file_changed_sh_ref = None


# ASYNC FUNCTIONS

async def remember_and_move(old_path, new_path) -> None:
    """Moves the recording to new location using 'os.renames'"""
    time_to_wait = globalVariables.get_time_to_wait()

    new_dir = None
    for x in range(0, 4):
        try:
            new_dir = move_file(old_path, new_path)
            exc = None
        except Exception as e:
            exc = str(e)

        if exc:
            print(exc)
            await asyncio.sleep(time_to_wait)
            time_to_wait *= 5
        else:
            break

    if new_dir is None:
        print("(Asyncio) File was not moved.")
        return

    print(">remember_and_move<>remember_and_move<>remember_and_move<")
    print("(Asyncio) Done!")
    print(f"(Asyncio) File moved to: {new_dir}")
    print(">remember_and_move<>remember_and_move<>remember_and_move<\n")


# HELPER FUNCTIONS

def remove_unusable_title_characters(title: str):
    # Remove non-alphanumeric characters (ex. ':')
    title = sub(r"[^A-Za-z0-9 ]+", "", title)

    # Remove whitespaces at the end
    title = "".join(title.rstrip())

    # Remove additional whitespaces
    title = " ".join(title.split())

    return title


def find_latest_file(folder_path: str, file_type: str):
    path_with_mask = os_path.join(folder_path, file_type)
    files = glob(path_with_mask)
    # print(files)
    if files:
        max_file = max(files, key=os_path.getctime)
        # print(max_file)
        return os_path.normpath(max_file)


def rec_file_asyncio(rec):
    asyncio.run(remember_and_move(rec.get_old_path(), rec.get_new_path()))


def screenshot_file_asyncio(screenshot):
    asyncio.run(remember_and_move(screenshot.get_old_path(), screenshot.get_new_path()))


# SIGNAL-RELATED

def file_changed_sh(recreate: bool = False):
    """Signal handler function reacting to automatic file splitting."""
    global file_changed_sh_ref
    if not file_changed_sh_ref:
        output = obs.obs_frontend_get_recording_output()
        file_changed_sh_ref = obs.obs_output_get_signal_handler(output)
        obs.signal_handler_connect(file_changed_sh_ref, "file_changed", file_changed_cb)
        obs.obs_output_release(output)
    else:
        obs.signal_handler_disconnect(file_changed_sh_ref, "file_changed", file_changed_cb)
        if recreate:
            output = obs.obs_frontend_get_recording_output()
            file_changed_sh_ref = obs.obs_output_get_signal_handler(output)
            obs.signal_handler_connect(file_changed_sh_ref, "file_changed", file_changed_cb)
            obs.obs_output_release(output)


# noinspection SpellCheckingInspection,PyUnusedLocal
def file_changed_cb(calldata):
    """Callback function reacting to the file_changed_sh signal handler function being triggered."""

    print("<>--------------------------<>")
    print("Recording automatic splitting detected!\n")

    global globalVariables
    print("Looking for split file...")
    globalVariables.set_current_recording(
        find_latest_file(globalVariables.get_output_dir(), globalVariables.get_recording_extension_mask()))

    if globalVariables.get_game_title() == globalVariables.get_default_recording_name():
        print("Running get_hooked procedure to get current app title...\n")
        check_if_hooked_and_update_title()

    print("Moving saved recording...")
    rec = Recording(custom_path=globalVariables.get_current_recording())
    rec.create_new_folder()
    thread = threading.Thread(target=rec_file_asyncio, name="remember_and_move", args=(rec,))
    thread.start()

    print("<>--------------------------<>\n")


def hooked_sh():
    print("<>--------------------------<>")
    global sourceNames, globalVariables
    scene_item_source = None

    print("Checking available sources for a match with source table...")

    current_scene_as_source = obs.obs_frontend_get_current_scene()
    scene = obs.obs_scene_from_source(current_scene_as_source)

    # noinspection PyArgumentList
    scene_items = obs.obs_scene_enum_items(scene)
    for item in scene_items:
        scene_item_source = obs.obs_sceneitem_get_source(item)
        name = obs.obs_source_get_name(scene_item_source)
        for source in sourceNames:
            if name == source:
                globalVariables.set_source_uuid(obs.obs_source_get_uuid(scene_item_source))
                print("Match found!")
                break

    obs.sceneitem_list_release(scene_items)
    obs.obs_source_release(current_scene_as_source)

    if not globalVariables.get_source_uuid():
        print("Nothing was found... Did you name your source in different way than in the 'sourceNames' array?")

    # print("Fetching the signal handler from the matching source...")
    source_sh_ref = obs.obs_source_get_signal_handler(scene_item_source)
    # print("Connecting the source signal handler to 'hooked' signal...")
    obs.signal_handler_connect(source_sh_ref, "hooked", hooked_cb)
    print("<>--------------------------<>\n")


def hooked_cb(calldata):
    print("<<>>--------------------------<<>>")
    global globalVariables

    print("Fetching data from calldata...")

    globalVariables.set_game_title(obs.calldata_string(calldata, "title"))
    print(f"gameTitle: {globalVariables.get_game_title()}")
    print("<<>>--------------------------<<>>")


# EVENTS

def recording_handler(event):
    """Event function reacting to OBS Event of starting the recording."""

    global globalVariables

    if event == obs.OBS_FRONTEND_EVENT_RECORDING_STARTED:

        print("[]--------------------------[]")
        print("Recording has started...\n")
        print("Reloading the signals!\n")
        if not globalVariables.get_source_uuid():
            hooked_sh()  # Respond to selected source hooking to a window
        file_changed_sh(recreate=True)  # Respond to splitting the recording (ex. automatic recording split)

        print("Signals reloaded!\n")
        print("Resetting the recording related values...\n")

        globalVariables.set_is_recording(True)
        globalVariables.set_current_recording(None)
        globalVariables.set_game_title(globalVariables.get_default_recording_name())

        print(">--------------------------<\n")
        print(f"Recording started: {'Yes' if globalVariables.get_is_recording() else 'No'}")
        print(f"Current game title: {globalVariables.get_game_title()}")
        print("[]--------------------------[]\n")

    elif event == obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED:
        print("[]--------------------------[]")
        print("Recording has stopped, moving the last file into right folder...\n")

        if globalVariables.get_game_title() == globalVariables.get_default_recording_name():
            print("Running get_hooked procedure to get current app title...\n")
            check_if_hooked_and_update_title()

        rec = Recording()
        rec.create_new_folder()
        thread = threading.Thread(target=rec_file_asyncio, name="remember_and_move", args=(rec,))
        thread.start()

        print("Job's done. The file was moved.")
        globalVariables.set_current_recording(None)
        globalVariables.set_is_recording(False)
        print("[]--------------------------[]\n")


def replay_buffer_handler(event):
    """Event function reacting to OBS Event of saving the replay buffer."""

    global globalVariables

    if event == obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_STARTED:
        print("[]--------------------------[]")
        print("Replay buffer has started...\n")

        if not globalVariables.get_source_uuid():
            print("Reloading the signals!")
            hooked_sh()  # Respond to selected source hooking to a window
            print("Signals reloaded!\n")

        print("Resetting the recording related values...\n")

        globalVariables.set_is_replay_active(True)
        globalVariables.set_current_recording(None)
        globalVariables.set_game_title(globalVariables.get_default_recording_name())

        print(">--------------------------<")
        print(f"Replay active? {'Yes' if globalVariables.get_is_replay_active() else 'No'}")
        print(f"CurrentRecording is {globalVariables.get_current_recording()}")
        print(f"Game title set to {globalVariables.get_game_title()}")
        print("[]-------------------------[]\n")

    elif event == obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_SAVED:
        print("[]--------------------------[]")
        print("Saving the Replay Buffer...")

        if globalVariables.get_game_title() == globalVariables.get_default_recording_name():
            print("Running get_hooked procedure to get current app title...")
            check_if_hooked_and_update_title()

        rec = Recording(is_replay=globalVariables.get_is_replay_active())
        rec.create_new_folder()
        thread = threading.Thread(target=rec_file_asyncio, name="remember_and_move", args=(rec,))
        thread.start()

        print("[]--------------------------[]\n")

    elif event == obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_STOPPED:
        globalVariables.set_is_replay_active(False)

        print("[]--------------------------[]")
        print(f"Replay active? {'Yes' if globalVariables.get_is_replay_active() else 'No'}")
        print("[]--------------------------[]\n")


def screenshot_handler_event(event):
    """Event function reacting to OBS Event of taking the screenshot."""

    if event == obs.OBS_FRONTEND_EVENT_SCREENSHOT_TAKEN:
        print("[]--------------------------[]")
        global globalVariables

        if not globalVariables.get_source_uuid():
            print("Reloading the signals...")
            hooked_sh()  # Respond to selected source hooking to a window
            print("Signals reloaded.")

        print("Running get_hooked procedure to get current app title...")
        check_if_hooked_and_update_title()

        print("User took the screenshot...")

        screenshot = Screenshot()
        screenshot.create_new_folder()
        thread = threading.Thread(target=screenshot_file_asyncio, name="remember_and_move", args=(screenshot,))
        thread.start()

        print("[]--------------------------[]\n")


def scene_collection_changing_event(event):
    global globalVariables

    if event == obs.OBS_FRONTEND_EVENT_SCENE_COLLECTION_CHANGING:
        print("Scene Collection changing detected, freeing globals to avoid issues...")
        globalVariables.unload_func()

        if obs.obs_frontend_recording_active():
            print("Stopping recording...")
            obs.obs_frontend_recording_stop()

        if obs.obs_frontend_replay_buffer_active():
            print("Stopping replay...")
            obs.obs_frontend_replay_buffer_stop()


# PROCEDURES

def check_if_hooked_and_update_title():
    """Function checks if source selected by user is hooked to any window and takes the title of hooked window

    Raises:
        TypeError: Only triggers when sourceUUID is None and causes the title to reset to defaultRecordingName
    """
    global globalVariables

    try:
        if globalVariables.get_source_uuid() is None:
            raise TypeError

    except TypeError:
        print("Source UUID is empty. Defaulting to 'Manual Recording'")
        globalVariables.set_game_title(globalVariables.get_default_recording_name())
        return

    calldata = get_hooked(globalVariables.get_source_uuid())
    print("Checking if source is hooked to any window...")
    if calldata is not None:
        if not gh_is_hooked(calldata):
            obs.calldata_destroy(calldata)
            globalVariables.set_game_title(globalVariables.get_default_recording_name())
            print("Call data was empty, using default name for un-captured windows...")
            return
        print("Hooked!")
        try:
            globalVariables.set_game_title(gh_title(calldata))
        except TypeError:
            print("Failed to get title, using default name - restart OBS or captured app.")
            globalVariables.set_game_title(globalVariables.get_default_recording_name())
        print(f"Current game title: {globalVariables.get_game_title()}")
    obs.calldata_destroy(calldata)


def get_hooked(uuid: str):
    source = obs.obs_get_source_by_uuid(uuid)
    cd = obs.calldata_create()
    ph = obs.obs_source_get_proc_handler(source)
    obs.proc_handler_call(ph, "get_hooked", cd)
    obs.obs_source_release(source)
    return cd


def gh_is_hooked(calldata) -> bool:
    return obs.calldata_bool(calldata, "hooked")


def gh_title(calldata) -> str:
    return obs.calldata_string(calldata, "title")


# OBS FUNCTIONS

# noinspection PyUnusedLocal
def script_load(settings):
    # Loading object of class holding global variables
    global globalVariables
    globalVariables = GlobalVariables()

    # Loading in Signals
    file_changed_sh(recreate=True)  # Respond to splitting the recording (ex. automatic recording split)

    # Loading in Frontend events
    obs.obs_frontend_add_event_callback(recording_handler)
    obs.obs_frontend_add_event_callback(replay_buffer_handler)
    obs.obs_frontend_add_event_callback(screenshot_handler_event)
    obs.obs_frontend_add_event_callback(scene_collection_changing_event)


def script_defaults(settings):
    obs.obs_data_set_default_string(settings, "outputdir", os_path.normpath(Path.home()))
    obs.obs_data_set_default_string(settings, "extension", "mkv")
    obs.obs_data_set_default_string(settings, "ss_extension", "png")


def script_update(settings):
    global globalVariables

    # Loading in settings
    global sett
    sett = settings

    # Fetching the Settings
    globalVariables.load_func(obs.obs_data_get_bool(settings, "title_before_bool"), 
                              obs.obs_data_get_string(settings, "extension"), 
                              obs.obs_data_get_string(settings, "ss_extension"),
                              os_path.normpath(obs.obs_data_get_string(settings, "outputdir")))

    print("(script_update) Updated the settings!\n")


def script_description():
    desc = (
        "<h3>OBS RecORDER </h3>"
        "<hr>"
        "Renames and organizes recordings/replays into subfolders similar to NVIDIA ShadowPlay (<i>NVIDIA GeForce Experience</i>).<br><br>"
        "<small>Created by:</small> <b>oxypatic</b><br><br>"
        ""
        "<h4>Please, make sure that your screen/game capturing source name is matching the 'sourceNames' array in the script!</h4>"
        "Fell free to edit the array in the script by pressing 'Edit script' button while RecORDER.py is selected"
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
        "Check if you want to have name of the application name appended as a prefix to the recording, else uncheck",
    )

    # Output directory
    obs.obs_properties_add_path(
        props,
        "outputdir",
        "Recordings folder",
        obs.OBS_PATH_DIRECTORY,
        None,
        os_path.normpath(Path.home()),
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
    global globalVariables, file_changed_sh_ref
    global sett

    # Clear events
    obs.obs_frontend_remove_event_callback(recording_handler)
    obs.obs_frontend_remove_event_callback(replay_buffer_handler)
    obs.obs_frontend_remove_event_callback(screenshot_handler_event)
    obs.obs_frontend_remove_event_callback(scene_collection_changing_event)

    # Clear global variables
    globalVariables.unload_func()

    # Clear signal for automatic splitting function
    file_changed_sh(recreate=False)

    # Clear cached settings and important global values
    sett = None
