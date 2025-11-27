import asyncio
import sys
import threading
from os import makedirs
from os import path as os_path
from re import sub
from shutil import move as move_file

import obspython as obs # type: ignore

# Author: oxypatic! (61553947+padiix@users.noreply.github.com)

# TODO: Implement a way for storing the UUID and Signals that react to it's deletion, etc. (Not figured out by me yet)
# TODO: Config instead of the Classes storing the data (Need to think if it's necessary, but probably not)


# >>> ONLY PLACE WHERE MODIFICATIONS ARE SAFE FOR YOU TO DO! <<<
# Table of capturing video source names
sourceNames = ["Game Capture", "Window Capture"]
# >>> ONLY PLACE WHERE MODIFICATIONS ARE SAFE FOR YOU TO DO! <<<

if sys.version_info < (3, 11):
    print("Python version < 3.11, correct behaviour is not guaranteed!")


# Values supporting smooth working and fewer calls

sett = None
file_changed_sh_ref = None


# CLASSES

class GlobalVariables:
    """Class that holds and allows better control over the Global variables used in this script"""

    def __init__(self):
        # [PROPERTIES]
        self.add_game_title_to_recording_name = None
        self.time_to_wait = 0.5

        # [Related to RECORDING]
        self.defaultRecordingName = "Manual Recording"
        self.isRecording = False
        self.isReplayActive = False
        self.last_recording_path = None
        self.game_title = self.defaultRecordingName
        self.source_uuid = None

    def load_func(self, add_game_title_to_recording_name: bool):
        self.add_game_title_to_recording_name = add_game_title_to_recording_name

    # ---

    def get_add_game_title_to_recording_name(self):
        return self.add_game_title_to_recording_name

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

    def get_last_recording(self):
        return self.last_recording_path

    def set_last_recording(self, value):
        self.last_recording_path = value

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
        for key in list(self.__dict__.keys()):
            if not key.startswith('_'):
                self.__dict__[key] = None


class MediaFile:
    """Base class for managing media files (recordings and screenshots)"""

    def __init__(self, custom_path: str | None = None, media_type: str = "recording") -> None:
        """Initialize media file with common path handling.
        
        Args:
            custom_path: Optional custom path to file
            media_type: Type of media - 'recording', 'replay', or 'screenshot'
        """
        global globalVariables
        
        self.game_title = globalVariables.get_game_title()
        self.add_title_prefix = globalVariables.get_add_game_title_to_recording_name()
        self.media_type = media_type
        
        # Set custom subfolder name based on media type
        if media_type == "recording":
            self.subfolder_name = None  # No subfolder for recordings
        elif media_type == "replay":
            self.subfolder_name = "Replays"
        elif media_type == "screenshot":
            self.subfolder_name = "Screenshots"
        else:
            self.subfolder_name = None
        
        # Determine file path
        if custom_path:
            self.path = custom_path
        elif media_type == "replay":
            self.path = obs.obs_frontend_get_last_replay()
        elif media_type == "screenshot":
            self.path = obs.obs_frontend_get_last_screenshot()
        else:
            self.path = obs.obs_frontend_get_last_recording()
        
        # Extract directory and filename
        self.dir = os_path.dirname(self.path)
        self.filename = os_path.basename(self.path)
    
    def get_filename(self) -> str:
        """Returns the base file name.
        
        Returns:
            str: name of the file
        """
        return self.filename
    
    def get_new_folder(self) -> str:
        """Returns the target folder path for this media file.
        
        Returns:
            str: path to the target folder
        """
        if self.subfolder_name:
            return os_path.normpath(os_path.join(self.dir, self.game_title, self.subfolder_name))
        else:
            return os_path.normpath(os_path.join(self.dir, self.game_title))
    
    def get_new_filename(self) -> str:
        """Returns the new filename with optional game title prefix.
        
        Returns:
            str: new filename for the file
        """
        if self.add_title_prefix:
            return f"{self.game_title} - {self.get_filename()}"
        else:
            return self.get_filename()
    
    def get_old_path(self) -> str:
        """Returns the original file path.
        
        Returns:
            str: original full path of the file
        """
        return os_path.normpath(os_path.join(self.dir, self.get_filename()))
    
    def get_new_path(self) -> str:
        """Returns the target file path.
        
        Returns:
            str: target full path for the file
        """
        return os_path.normpath(os_path.join(self.get_new_folder(), self.get_new_filename()))
    
    def create_new_folder(self) -> None:
        """Creates the target folder if it doesn't exist."""
        if not os_path.exists(self.get_new_folder()):
            makedirs(self.get_new_folder())


class Recording(MediaFile):
    """Class for handling recording files"""

    def __init__(self, custom_path: str | None = None, is_replay: bool = False) -> None:
        """Create a recording file object.

        Args:
            custom_path (str): Optional path to a recording file
            is_replay (bool): Whether this is a replay buffer recording
        """
        media_type = "replay" if is_replay else "recording"
        super().__init__(custom_path=custom_path, media_type=media_type)


class Screenshot(MediaFile):
    """Class for handling screenshot files"""

    def __init__(self, custom_path: str | None = None) -> None:
        """Create a screenshot file object.

        Args:
            custom_path (str): Optional path to a screenshot file
        """
        super().__init__(custom_path=custom_path, media_type="screenshot")


# ASYNC FUNCTIONS

async def remember_and_move(old_path, new_path) -> None:
    """Moves the recording to new location using shutil.move() with retries."""
    
    if not os_path.exists(old_path):
        print(f"(Asyncio) File does not exist: {old_path}")
        return
    
    time_to_wait = globalVariables.get_time_to_wait()

    new_dir = None
    max_attempts = 4
    enlarge_timeout_value = 2
    for attempt in range(max_attempts):
        try:
            new_dir = move_file(old_path, new_path)
            break  # Success, exit retry loop
        except Exception as e:
            if attempt < 3:  # Don't print on last attempt (will print final error below)
                print(f"Move attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(time_to_wait)
                time_to_wait *= enlarge_timeout_value
            else:
                print(f"(Asyncio) File move failed after {attempt + 1} attempts: {e}")

    if new_dir is None:
        print("(Asyncio) File was not moved.")
        return

    print("(Asyncio) Done!")
    print(f"(Asyncio) File moved to: {new_dir}")

# HELPER FUNCTIONS

def remove_unusable_title_characters(title: str):
    # Remove non-alphanumeric characters (ex. ':')
    title = sub(r"[^A-Za-z0-9 ]+", "", title)

    # Remove whitespaces at the end
    title = "".join(title.rstrip())

    # Remove additional whitespaces
    title = " ".join(title.split())

    return title


def move_media_file_asyncio(media_file: MediaFile):
    asyncio.run(remember_and_move(media_file.get_old_path(), media_file.get_new_path()))
    
    
# SIGNAL-RELATED

def file_changed_sh(recreate: bool = False):
    """Signal handler function reacting to automatic file splitting."""
    global file_changed_sh_ref
    if not file_changed_sh_ref:
        output = obs.obs_frontend_get_recording_output()
        try:
            file_changed_sh_ref = obs.obs_output_get_signal_handler(output)
            obs.signal_handler_connect(file_changed_sh_ref, "file_changed", file_changed_cb)
        finally:
            obs.obs_output_release(output)
    else:
        obs.signal_handler_disconnect(file_changed_sh_ref, "file_changed", file_changed_cb)
        if recreate:
            output = obs.obs_frontend_get_recording_output()
            try:
                file_changed_sh_ref = obs.obs_output_get_signal_handler(output)
                obs.signal_handler_connect(file_changed_sh_ref, "file_changed", file_changed_cb)
            finally:
                obs.obs_output_release(output)


# noinspection SpellCheckingInspection,PyUnusedLocal
def file_changed_cb(calldata):
    """Callback function reacting to the file_changed_sh signal handler function being triggered."""

    print("Recording automatic splitting detected!\n")

    global globalVariables
    
    print("Looking for split file...")
    old_file = globalVariables.get_last_recording()
    new_file = obs.obs_frontend_get_last_recording()
    
    # Store the new file for next split
    globalVariables.set_last_recording(new_file)

    if old_file and old_file != new_file:
        print(f"Moving old recording: {old_file}")
        print(f"New recording detected: {new_file}")
        if globalVariables.get_game_title() == globalVariables.get_default_recording_name():
            print("Running get_hooked procedure to get current app title...\n")
            check_if_hooked_and_update_title()

        rec = Recording(custom_path=old_file)
        rec.create_new_folder()
        thread = threading.Thread(target=move_media_file_asyncio, args=(rec,), daemon=True)
        thread.start()


def hooked_sh():
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
        return

    # Only proceed if we found a valid source
    if scene_item_source is not None:
        try:
            # print("Fetching the signal handler from the matching source...")
            source_sh_ref = obs.obs_source_get_signal_handler(scene_item_source)
            # print("Connecting the source signal handler to 'hooked' signal...")
            obs.signal_handler_connect(source_sh_ref, "hooked", hooked_cb)
        except Exception as e:
            print(f"Error connecting hooked signal: {e}")
    else:
        print("Warning: No matching source item found.")
    
    
def hooked_cb(calldata):
    global globalVariables

    print("Fetching data from calldata...")

    globalVariables.set_game_title(obs.calldata_string(calldata, "title"))
    print(f"gameTitle: {globalVariables.get_game_title()}")


# EVENTS

def recording_handler(event):
    """Event function reacting to OBS Event of starting the recording."""

    global globalVariables

    if event == obs.OBS_FRONTEND_EVENT_RECORDING_STARTED:

        print("Recording has started...\n")
        print("Reloading the signals!\n")
        if not globalVariables.get_source_uuid():
            hooked_sh()  # Respond to selected source hooking to a window    
        globalVariables.set_last_recording(obs.obs_frontend_get_last_recording())
        
        file_changed_sh(recreate=True)  # Respond to splitting the recording (ex. automatic recording split)
        print("Signals reloaded!\n")
        print("Resetting the recording related values...\n")

        globalVariables.set_is_recording(True)
        globalVariables.set_game_title(globalVariables.get_default_recording_name())

        print(f"Recording started: {'Yes' if globalVariables.get_is_recording() else 'No'}")
        print(f"Current game title: {globalVariables.get_game_title()}")

    elif event == obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED:
        print("Recording has stopped, moving the last file into right folder...\n")

        if globalVariables.get_game_title() == globalVariables.get_default_recording_name():
            print("Running get_hooked procedure to get current app title...\n")
            check_if_hooked_and_update_title()

        rec = Recording()
        rec.create_new_folder()
        thread = threading.Thread(target=move_media_file_asyncio, args=(rec,), daemon=True)
        thread.start()

        print("Job's done. The file was moved.")
        globalVariables.set_last_recording(None)
        globalVariables.set_is_recording(False)


def replay_buffer_handler(event):
    """Event function reacting to OBS Event of saving the replay buffer."""

    global globalVariables

    if event == obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_STARTED:
        print("Replay buffer has started...\n")

        if not globalVariables.get_source_uuid():
            print("Reloading the signals!")
            hooked_sh()  # Respond to selected source hooking to a window
            print("Signals reloaded!\n")

        print("Resetting the recording related values...\n")

        globalVariables.set_is_replay_active(True)
        globalVariables.set_last_recording(obs.obs_frontend_get_last_recording())
        globalVariables.set_game_title(globalVariables.get_default_recording_name())

        print(f"Replay active? {'Yes' if globalVariables.get_is_replay_active() else 'No'}")
        print(f"CurrentRecording is {globalVariables.get_last_recording()}")
        print(f"Game title set to {globalVariables.get_game_title()}")

    elif event == obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_SAVED:
        print("Saving the Replay Buffer...")

        if globalVariables.get_game_title() == globalVariables.get_default_recording_name():
            print("Running get_hooked procedure to get current app title...")
            check_if_hooked_and_update_title()

        rec = Recording(is_replay=globalVariables.get_is_replay_active())
        rec.create_new_folder()
        thread = threading.Thread(target=move_media_file_asyncio, args=(rec,), daemon=True)
        thread.start()

    elif event == obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_STOPPED:
        globalVariables.set_is_replay_active(False)
        globalVariables.set_last_recording(None)
        print(f"Replay active? {'Yes' if globalVariables.get_is_replay_active() else 'No'}")


def screenshot_handler_event(event):
    """Event function reacting to OBS Event of taking the screenshot."""

    if event == obs.OBS_FRONTEND_EVENT_SCREENSHOT_TAKEN:
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
        thread = threading.Thread(target=move_media_file_asyncio, args=(screenshot,), daemon=True)
        thread.start()
        

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

    if globalVariables.get_source_uuid() is None:
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


def get_hooked(uuid: str) -> object:
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

    # Validate globalVariables is initialized
    if globalVariables is None:
        print("Error: globalVariables not initialized.")
        return

    # Loading in Signals
    file_changed_sh(recreate=True)  # Respond to splitting the recording (ex. automatic recording split)

    # Loading in Frontend events
    obs.obs_frontend_add_event_callback(recording_handler)
    obs.obs_frontend_add_event_callback(replay_buffer_handler)
    obs.obs_frontend_add_event_callback(screenshot_handler_event)
    obs.obs_frontend_add_event_callback(scene_collection_changing_event)


def script_defaults(settings):
    pass


def script_update(settings):
    global globalVariables

    # Loading in settings
    global sett
    sett = settings

    # Fetching the Settings
    globalVariables.load_func(obs.obs_data_get_bool(settings, "title_before_bool"))

    print("(script_update) Updated the settings!\n")


def script_description():
    desc = (
        "<h3> RecORDER </h3>"
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