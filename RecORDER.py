from asyncio import run as run_async
from asyncio import sleep as sleep_async
from glob import glob
from os import makedirs
from os import path as osPath
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


# Global variables

globalVariables = None

# Values supporting smooth working and less calls

sett = None
file_changed_sh_ref = None


# CLASSES

class GlobalVariables:
    """Class that holds and allows better control over the Global variables used in this script"""
    
    def __init__(self):
        #[PROPERTIES]
        self.addTitleBool = None
        self.recordingExtension = None
        self.screenshotExtension = None
        self.ttw = 0.5
        
        #[Related to RECORDING]
        self.defaultRecordingName = "Manual Recording"
        self.isRecording = False
        self.isReplayActive = False
        self.currentRecording = None
        self.gameTitle = self.defaultRecordingName
        self.outputDir = None
        self.sourceUUID = None
        
    def load_func(self, titleBool: bool, rcrdExt: str, scrnstExt: str, outDir: str):
        self.addTitleBool = titleBool
        self.recordingExtension = rcrdExt
        self.screenshotExtension = scrnstExt
        self.outputDir = outDir
    
    # ---
      
    def get_addTitleBool(self):
        return self.addTitleBool

    def get_recordingExtension(self):
        return self.recordingExtension
    
    def get_screenshotExtension(self):
        return self.screenshotExtension
    
    def get_recordingExtensionMask(self):
        return "\*" + self.recordingExtension
    
    def get_screenshotExtensionMask(self):
        return "\*" + self.screenshotExtension
    
    def get_ttw(self):
        return self.ttw
    
    # ---
    
    def get_defaultRecordingName(self):
        return self.defaultRecordingName
    
    def get_isRecording(self):
        return self.isRecording
    
    def set_isRecording(self, value: bool):
        self.isRecording = value
    
    def get_isReplayActive(self):
        return self.isReplayActive
        
    def set_isReplayActive(self, value: bool):
        self.isReplayActive = value
    
    def get_currentRecording(self):
        return self.currentRecording
    
    def set_currentRecording(self, value: str):
        self.currentRecording = value
        
    def get_gameTitle(self):
        return self.gameTitle
    
    def set_gameTitle(self, value: str):
        self.gameTitle = remove_unusable_title_characters(value)
        
    def get_outputDir(self):
        return self.outputDir
    
    def get_sourceUUID(self):
        return self.sourceUUID
    
    def set_sourceUUID(self, value: str):
        self.sourceUUID = value
        
    # ---
    
    def unload_func(self):
        self.addTitleBool = None
        self.recordingExtension = None
        self.screenshotExtension = None
        self.defaultRecordingName = None
        self.sourceUUID = None
        self.isRecording = None
        self.isReplayActive = None
        self.currentRecording = None
        self.gameTitle = None
        self.outputDir = None
    
class Recording:
    """Class that allows better control over files for the needs of this script"""

    def __init__(self, customPath: str = None, isReplay: bool = False) -> None:
        """Create a file based on either specified path or path that was configured in Scripts settings

        Args:
            customPath (str): Path to a file that needs to be moved
            isReplay (bool): Set to true if handled recording is from replay buffer
        """

        global globalVariables

        self.replaysFolderName = "Replays"
        self.gameTitle = globalVariables.get_gameTitle()
        self.addTitleBool = globalVariables.get_addTitleBool()
        
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
        self.dir = osPath.dirname(self.path)
        self.rawfile = osPath.basename(self.path)

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
        if self.isReplay:
            return osPath.normpath(osPath.join(self.dir, self.gameTitle, self.replaysFolderName))
        else:
            return osPath.normpath(osPath.join(self.dir, self.gameTitle))


    def get_newFilename(self) -> str:
        """Returns the name of a file based on the choice of the user
        If user decided to have game title before recording name, it will add it.

        Returns:
            str: name of the recording
        """
        if self.addTitleBool:
            return self.gameTitle + " - " + self.get_filename()
        else:
            return self.get_filename()

    def get_oldPath(self) -> str:
        """Returns previous path the file was located in

        Returns:
            str: previous path of file
        """
        return osPath.normpath(osPath.join(self.dir, self.get_filename()))

    def get_newPath(self) -> str:
        """Returns current path where file is located

        Returns:
            str: current path of file
        """
        return osPath.normpath(osPath.join(self.get_newFolder(), self.get_newFilename()))

    def create_new_folder(self) -> None:
        """Creates a new folder based on title of the captured fullscreen application"""
        if not osPath.exists(self.get_newFolder()):
            makedirs(self.get_newFolder())
            
class Screenshot:
    """Class that allows better control over screenshots for the needs of this script"""

    def __init__(self, customPath: str = None) -> None:
        """Create a file based on either specified path or path that was configured in Scripts settings

        Args:
            customPath (str): Path to a file that needs to be moved
            isReplay (bool): Set to true if handled recording is from replay buffer
        """
        global globalVariables

        self.screenshotsFolderName = "Screenshots"
        self.gameTitle = globalVariables.get_gameTitle()
        self.addTitleBool = globalVariables.get_addTitleBool()
        
        # Allow to specify a custom path where the file is located.
        if customPath is not None:
            self.path = customPath
        else:
            self.path = obs.obs_frontend_get_last_screenshot()

        # Prepare paths needed for functions
        self.dir = osPath.dirname(self.path)
        self.rawfile = osPath.basename(self.path)

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
        return osPath.normpath(osPath.join(self.dir, self.gameTitle, self.screenshotsFolderName))

    def get_newFilename(self) -> str:
        """Returns the name of a file based on the choice of the user
        If user decided to have game title before recording name, it will add it.

        Returns:
            str: name of the recording
        """
        if self.addTitleBool:
            return self.gameTitle + " - " + self.get_filename()
        else:
            return self.get_filename()

    def get_oldPath(self) -> str:
        """Returns previous path the file was located in

        Returns:
            str: previous path of file
        """
        return osPath.normpath(osPath.join(self.dir, self.get_filename()))

    def get_newPath(self) -> str:
        """Returns current path where file is located

        Returns:
            str: current path of file
        """
        return osPath.normpath(osPath.join(self.get_newFolder(), self.get_newFilename()))

    def create_new_folder(self) -> None:
        """Creates a new folder based on title of the captured fullscreen application"""
        if not osPath.exists(self.get_newFolder()):
            makedirs(self.get_newFolder())


# ASYNC FUNCTIONS

async def remember_and_move(old, new) -> None:
    """Moves the recording to new location using os.renames"""
    global globalVariables
    ttw = globalVariables.get_ttw()
    
    new_dir = None
    for x in range(0,3):
        try:
            new_dir = move_file(old, new)
            exc = None
        except Exception as e:
            exc = str(e)
            
        if exc:
            await sleep_async(ttw)
            ttw *= 2
        else:
            break

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

def find_latest_file(folder_path: str, file_type: str):
    files = glob(folder_path + file_type)
    if files:
        max_file = max(files, key=osPath.getctime)
        return osPath.normpath(max_file)


# SIGNAL-RELATED

def file_changed_sh():
    """Signal handler function reacting to automatic file splitting."""
    global file_changed_sh_ref
    if not file_changed_sh_ref:
        output = obs.obs_frontend_get_recording_output()
        file_changed_sh_ref = obs.obs_output_get_signal_handler(output)
        obs.signal_handler_connect(file_changed_sh_ref, "file_changed", file_changed_cb)
        obs.obs_output_release(output)

def file_changed_cb(calldata):
    """Callback function reacting to the file_changed_sh signal handler function being triggered."""
    
    print("[]--------------------------[]")
    print("Recording automatic splitting detected!")
    
    global globalVariables
    globalVariables.set_currentRecording(find_latest_file(globalVariables.get_outputDir(), globalVariables.get_recordingExtensionMask()))

    if globalVariables.get_gameTitle() == globalVariables.get_defaultRecordingName():
            print("Running get_hooked procedure to get current app title...")
            check_if_hooked_and_update_title()

    print(">--------------------------<")
    
    print("Moving saved recording...\n")
    rec = Recording(customPath=globalVariables.get_currentRecording())
    rec.create_new_folder()
    run_async(remember_and_move(rec.get_oldPath(), rec.get_newPath()))
    
    print("[]--------------------------[]\n")
    
def hooked_sh():
    global sourceNames, globalVariables
    sceneitem_source = None
    
    print("Checking available sources for a match with source table...")
    
    current_scene_as_source = obs.obs_frontend_get_current_scene()
    scene = obs.obs_scene_from_source(current_scene_as_source)

    sceneitems = obs.obs_scene_enum_items(scene)
    for item in sceneitems:
        sceneitem_source = obs.obs_sceneitem_get_source(item)
        name = obs.obs_source_get_name(sceneitem_source)
        for source in sourceNames:
            if name == source :
                globalVariables.set_sourceUUID(obs.obs_source_get_uuid(sceneitem_source))
                print("Match found!")
                break

    obs.sceneitem_list_release(sceneitems)
    obs.obs_source_release(current_scene_as_source)
    
    if not globalVariables.get_sourceUUID():
        print ("Nothing was found... Did you name your source in different way than in the 'sourceNames' array?")
    
    
    # print("Fetching the signal handler from the matching source...")
    source_sh_ref = obs.obs_source_get_signal_handler(sceneitem_source)
    # print("Connecting the source signal handler to 'hooked' signal...")
    obs.signal_handler_connect(source_sh_ref, "hooked", hooked_cb)
    
def hooked_cb(calldata):
    global globalVariables
    print("Fetching data from calldata...")

    globalVariables.set_gameTitle(obs.calldata_string(calldata, "title"))
    print(f"gameTitle: {globalVariables.get_gameTitle()}")


# EVENTS

def start_recording_handler(event):
    """Event function reacting to OBS Event of starting the recording."""

    if event == obs.OBS_FRONTEND_EVENT_RECORDING_STARTED:
        global globalVariables
        
        print("[]--------------------------[]")
        print("Recording has started...\n")
        print("Reloading the signals!")
        if not globalVariables.get_sourceUUID():
            hooked_sh()    # Respond to selected source hooking to a window
        file_changed_sh()  # Respond to splitting the recording (ex. automatic recording split)

        print("Signals reloaded!\n")
        print("Reseting the recording related values...\n")

        globalVariables.set_isRecording(True)
        globalVariables.set_currentRecording(None)
        globalVariables.set_gameTitle(globalVariables.get_defaultRecordingName())

        print(">--------------------------<")
        print(f"Recording started: {'Yes' if globalVariables.get_isRecording() else 'No'}")
        print(f"Current game title: {globalVariables.get_gameTitle()}")
        print("[]--------------------------[]\n")

def recording_stop_handler(event):
    """Event function reacting to OBS Event of recording fully stopping."""
    if event == obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED:
        print("[]--------------------------[]")
        print("Recording has stopped, moving the last file into right folder...")

        global globalVariables

        if globalVariables.get_gameTitle() == globalVariables.get_defaultRecordingName():
            print("Running get_hooked procedure to get current app title...")
            check_if_hooked_and_update_title()


        rec = Recording()
        rec.create_new_folder()
        run_async(remember_and_move(rec.get_oldPath(), rec.get_newPath()))
        
        print(">--------------------------<")
        print("Job's done. The file was moved.")
        globalVariables.set_currentRecording(None)
        globalVariables.set_isRecording(False)
        print("[]--------------------------[]\n")

def start_buffer_handler(event):
    """Event function reacting to OBS Event of starting the replay buffer."""

    if event == obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_STARTED:
        global globalVariables
        print("[]--------------------------[]")
        print("Replay buffer has started...\n")
        
        if not globalVariables.get_sourceUUID():
            print("Reloading the signals!")
            hooked_sh()    # Respond to selected source hooking to a window
            print("Signals reloaded!\n")
        
        print("Reseting the recording related values...\n")

        

        globalVariables.set_isReplayActive(True)
        globalVariables.set_currentRecording(None)
        globalVariables.set_gameTitle(globalVariables.get_defaultRecordingName())

        print(">--------------------------<")
        print(f"Replay active? {'Yes' if globalVariables.get_isReplayActive() else 'No'}")
        print(f"CurrentRecording is {globalVariables.get_currentRecording()}")
        print(f"Game title set to {globalVariables.get_gameTitle()}")
        print("[]-------------------------[]\n")

def replay_buffer_handler(event):
    """Event function reacting to OBS Event of saving the replay buffer."""
    if event == obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_SAVED:
        
        global globalVariables
        
        print("[]--------------------------[]")
        print("Saving the Replay Buffer...")
        
        if globalVariables.get_gameTitle() == globalVariables.get_defaultRecordingName():
            print("Running get_hooked procedure to get current app title...")
            check_if_hooked_and_update_title()

        rec = Recording(isReplay=globalVariables.get_isReplayActive())
        rec.create_new_folder()
        run_async(remember_and_move(rec.get_oldPath(), rec.get_newPath()))
        
        print("[]--------------------------[]\n")
           
def replay_buffer_stop_handler(event):
    if event == obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_STOPPED:
        global globalVariables
        globalVariables.set_isReplayActive(False)
        
        print("[]--------------------------[]")
        print(f"Replay active? {'Yes' if globalVariables.get_isReplayActive() else 'No'}")
        print("[]--------------------------[]\n")
        
def screenshot_handler_event(event):
    """Event function reacting to OBS Event of taking the screenshot."""
    
    if event == obs.OBS_FRONTEND_EVENT_SCREENSHOT_TAKEN:
        print("[]--------------------------[]")
        global globalVariables
        
        if not globalVariables.get_sourceUUID():
            print("Reloading the signals...")
            hooked_sh()    # Respond to selected source hooking to a window
            print("Signals reloaded.")
        
        if globalVariables.get_gameTitle() == globalVariables.get_defaultRecordingName():
            print("Running get_hooked procedure to get current app title...")
            check_if_hooked_and_update_title()
            
        print("User took the screenshot...")
        
        scrnst = Screenshot()
        scrnst.create_new_folder()
        run_async(remember_and_move(scrnst.get_oldPath(), scrnst.get_newPath()))
        
        print("[]--------------------------[]\n")

def scenecollection_changing_event(event):
    global globalVariables, file_changed_sh_ref
    if event == obs.OBS_FRONTEND_EVENT_SCENE_COLLECTION_CHANGING:
        print("Scene Collection changing detected, freeing globals to avoid issues...")
        globalVariables.unload_func()
        file_changed_sh_ref = None
        

# PROCEDURES

def check_if_hooked_and_update_title():
    """Function checks if source selected by user is hooked to any window and takes the title of hooked window

    Raises:
        TypeError: Only triggers when sourceUUID is None and causes the title to reset to defaultRecordingName
    """
    global globalVariables
    
    try:
        if globalVariables.get_sourceUUID() is None:
            raise TypeError

    except TypeError:
        print("Source UUID is empty. Defaulting to 'Manual Recording'")
        globalVariables.set_gameTitle(globalVariables.get_defaultRecordingName())
        return

    calldata = get_hooked(globalVariables.get_sourceUUID())
    print("Checking if source is hooked to any window...")
    if calldata is not None:
        if not gh_isHooked(calldata):
            obs.calldata_destroy(calldata)
            globalVariables.set_gameTitle(globalVariables.get_defaultRecordingName())
            print("Call data was empty, using default name for uncaptured windows...")
            return
        print("Hooked!")
        try:
            globalVariables.set_gameTitle(gh_title(calldata))
        except TypeError:
            print("Failed to get title, using default name - restart OBS or captured app.")
            globalVariables.set_gameTitle(globalVariables.get_defaultRecordingName())
        print(f"Current game title: {globalVariables.get_gameTitle()}")
    obs.calldata_destroy(calldata)

def get_hooked(uuid: str):
    source = obs.obs_get_source_by_uuid(uuid)
    cd = obs.calldata_create()
    ph = obs.obs_source_get_proc_handler(source)
    obs.proc_handler_call(ph, "get_hooked", cd)
    obs.obs_source_release(source)
    return cd

def gh_isHooked(calldata) -> bool:
    return obs.calldata_bool(calldata, "hooked")

def gh_title(calldata) -> str:
    return obs.calldata_string(calldata, "title")


# OBS FUNCTIONS

def script_load(settings):
    # Loading object of class holding global variables
    global globalVariables
    globalVariables = GlobalVariables()
    
    # Loading in Signals
    file_changed_sh()  # Respond to splitting the recording (ex. automatic recording split)

    # Loading in Frontend events
    obs.obs_frontend_add_event_callback(start_recording_handler)
    obs.obs_frontend_add_event_callback(recording_stop_handler)
    obs.obs_frontend_add_event_callback(start_buffer_handler)
    obs.obs_frontend_add_event_callback(replay_buffer_handler)
    obs.obs_frontend_add_event_callback(replay_buffer_stop_handler)
    obs.obs_frontend_add_event_callback(screenshot_handler_event)
    obs.obs_frontend_add_event_callback(scenecollection_changing_event)

def script_defaults(settings):
    obs.obs_data_set_default_string(settings, "outputdir", osPath.normpath(Path.home()))
    obs.obs_data_set_default_string(settings, "extension", "mkv")
    obs.obs_data_set_default_string(settings, "ss_extension", "png")

def script_update(settings):
    global globalVariables
    
    # Loading in settings
    global sett
    sett = settings
    
    # Fetching the Settings
    titleBool = obs.obs_data_get_bool(settings, "title_before_bool")
    rcrdExt=obs.obs_data_get_string(settings, "extension")
    scrnstExt=obs.obs_data_get_string(settings, "ss_extension")
    outDir = osPath.normpath(obs.obs_data_get_string(settings, "outputdir"))
    globalVariables.load_func(titleBool, rcrdExt, scrnstExt, outDir)

    print("(script_update) Updated the settings!\n")

def script_description():
    desc = (
        "<h3>OBS RecORDER </h3>"
        "<hr>"
        "Renames and organizes recordings/replays into subfolders similar to NVIDIA ShadowPlay (<i>NVIDIA GeForce Experience</i>).<br><br>"
        "<small>Created by:</small> <b>padii</b><br><br>"
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
        osPath.normpath(Path.home()),
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
    obs.obs_frontend_remove_event_callback(start_recording_handler)
    obs.obs_frontend_remove_event_callback(recording_stop_handler)
    obs.obs_frontend_remove_event_callback(start_buffer_handler)
    obs.obs_frontend_remove_event_callback(replay_buffer_handler)
    obs.obs_frontend_remove_event_callback(replay_buffer_stop_handler)
    obs.obs_frontend_remove_event_callback(screenshot_handler_event)
    obs.obs_frontend_remove_event_callback(scenecollection_changing_event)
    
    # Clear global variables
    globalVariables.unload_func()
    
    # Clear Settings class
    file_changed_sh_ref = None

    # Clear cached settings and important global values
    sett = None