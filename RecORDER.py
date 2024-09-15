import glob
import obspython as obs  # type: ignore
import re
import os
import time
from pathlib import Path

# Author: oxypatic! (61553947+padiix@users.noreply.github.com)

# TODO: Implement a way for storing the UUID and Signals that react to it's deletion, etc. (Not figured out by me yet)
# TODO: Config instead of the Classes storing the data (Need to think if it's necessary, but probably not)


# >>> ONLY PLACE WHERE MODIFICATIONS ARE SAFE FOR YOU TO DO! <<<
# Table of capturing video source names
sources = ["Game Capture", "Window Capture"]
# >>> ONLY PLACE WHERE MODIFICATIONS ARE SAFE FOR YOU TO DO! <<<


# Global variables

globalVariables = None

# Values supporting smooth working and less calls

sett = None
file_changed_sh_ref = None


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
    
    print("------------------------------")
    print("Recording automatic splitting detected!")
    print("Moving saved recording...")

    global globalVariables
    globalVariables.set_currentRecording(find_latest_file(globalVariables.get_outputDir(), globalVariables.get_recordingExtensionMask()))

    rec = Recording(customPath=globalVariables.get_currentRecording())
    rec.create_new_folder()
    rec.remember_and_move()
    
    print("Done!")
    print("------------------------------")
    print(f"Saved recording: {globalVariables.get_currentRecording()}")
    print(f"New path: {rec.get_newPath()}")
    print("------------------------------")
    
def hooked_sh():
    global sources, globalVariables
    source_obj = None
    
    print("Checking available sources for a match with source table...")
    
    current_scene_as_source = obs.obs_frontend_get_current_scene()
    scene = obs.obs_scene_from_source(current_scene_as_source)

    sceneitems = obs.obs_scene_enum_items(scene)
    for item in sceneitems:
        source_obj = obs.obs_sceneitem_get_source(item)
        name = obs.obs_source_get_name(source_obj)
        for source in sources:
            if name is source :
                globalVariables.set_sourceUUID(obs.obs_source_get_uuid(source_obj))
                print("Match found!")
                break
            else:
                print("Not found... Looking further")
                obs.obs_source_release(source_obj)

    obs.sceneitem_list_release(sceneitems)
    obs.obs_source_release(current_scene_as_source)
    
    if not source_obj:
        print ("Nothing was found... Did you name your source in different way than in the 'source' array?")
    
    obs.obs_source_release(source_obj)
    
    # print("Fetching the signal handler from the matching source...")
    source_sh_ref = obs.obs_source_get_signal_handler(source_obj)
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
        
        print("------------------------------")
        print("Recording has started...\n")
        print("Reloading the signals!")
        if not globalVariables.get_sourceUUID():
            hooked_sh()    # Respond to selected source hooking to a window
        file_changed_sh()  # Respond to splitting the recording (ex. automatic recording split)

        print("Signals reloaded!\n")
        print("Reseting the recording related values...")

        

        globalVariables.set_isRecording(True)
        globalVariables.set_currentRecording(None)
        globalVariables.set_gameTitle(globalVariables.get_defaultRecordingName())

        print("------------------------------")
        print(f"Recording started: {'Yes' if globalVariables.get_isRecording() else 'No'}")
        print(f"Current recording is {globalVariables.get_currentRecording()}")
        print(f"Current game title: {globalVariables.get_gameTitle()}")
        print("------------------------------")

def recording_stop_handler(event):
    """Event function reacting to OBS Event of recording fully stopping."""
    if event == obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED:
        print("------------------------------")
        print("Recording has stopped, moving the last file into right folder...")

        global globalVariables

        if globalVariables.get_gameTitle() is globalVariables.get_defaultRecordingName():
            print("Running get_hooked procedure to get current app title...")
            check_if_hooked_and_update_title()


        rec = Recording()
        rec.create_new_folder()
        rec.remember_and_move()
        
        print("Job's done. The file was moved.")
        print("------------------------------")
        print(f"Recording: {rec.get_filename()}")
        print(f"New path: {rec.get_newPath()}")

        globalVariables.set_currentRecording(None)
        globalVariables.set_isRecording(False)
        print("------------------------------")

def start_buffer_handler(event):
    """Event function reacting to OBS Event of starting the replay buffer."""

    if event == obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_STARTED:
        global globalVariables
        print("------------------------------")
        print("Replay buffer has started...\n")
        
        if not globalVariables.get_sourceUUID():
            print("Reloading the signals!")
            hooked_sh()    # Respond to selected source hooking to a window
            print("Signals reloaded!\n")
        
        print("Reseting the recording related values...\n")

        

        globalVariables.set_isReplayActive(True)
        globalVariables.set_currentRecording(None)
        globalVariables.set_gameTitle(globalVariables.get_defaultRecordingName())

        print("------------------------------")
        print(f"Replay active? {'Yes' if globalVariables.get_isReplayActive() else 'No'}")
        print(f"CurrentRecording is {globalVariables.get_currentRecording()}")
        print(f"Game title set to {globalVariables.get_gameTitle()}")
        print("------------------------------")

def replay_buffer_handler(event):
    """Event function reacting to OBS Event of saving the replay buffer."""
    if event == obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_SAVED:
        
        global globalVariables
        
        print("------------------------------")
        print("Saving the Replay Buffer...")
        
        if globalVariables.get_gameTitle() is globalVariables.get_defaultRecordingName():
            print("Running get_hooked procedure to get current app title...")
            check_if_hooked_and_update_title()

        rec = Recording(isReplay=globalVariables.get_isReplayActive())
        rec.create_new_folder()
        rec.remember_and_move()

        print(f"Old path: {rec.get_oldPath()}")
        print(f"New path: {rec.get_newPath()}")
        print("------------------------------")
           
def replay_buffer_stop_handler(event):
    if event == obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_STOPPED:
        global globalVariables
        globalVariables.set_isReplayActive(False)
        
        print("------------------------------")
        print(f"Replay active? {'Yes' if globalVariables.get_isReplayActive() else 'No'}")
        print("------------------------------")
        
def screenshot_handler_event(event):
    """Event function reacting to OBS Event of taking the screenshot."""
    
    if event == obs.OBS_FRONTEND_EVENT_SCREENSHOT_TAKEN:
        print("------------------------------")
        global globalVariables
        
        if not globalVariables.get_sourceUUID():
            print("Reloading the signals...")
            hooked_sh()    # Respond to selected source hooking to a window
            print("Signals reloaded.")
            
        if globalVariables.get_gameTitle() is globalVariables.get_defaultRecordingName():
            print("Running get_hooked procedure to get current app title...")
            check_if_hooked_and_update_title()
            
        print("User took the screenshot...")
        
        scrnst = Screenshot()
        scrnst.create_new_folder()
        scrnst.remember_and_move()
        
        print(f"Old path: {scrnst.get_oldPath()}")
        print(f"New path: {scrnst.get_newPath()}")
        print("------------------------------")

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
    return remove_unusable_title_characters(obs.calldata_string(calldata, "title"))


# HELPER FUNCTIONS

def remove_unusable_title_characters(title: str):
    # Remove non-alphanumeric characters (ex. ':')
    title = re.sub(r"[^A-Za-z0-9 ]+", "", title)

    # Remove whitespaces at the end
    title = "".join(title.rstrip())

    # Remove additional whitespaces
    title = " ".join(title.split())

    return title

def find_latest_file(folder_path: str, file_type: str):
    files = glob.glob(folder_path + file_type)
    if files:
        max_file = max(files, key=os.path.getctime)
        return os.path.normpath(max_file)



# CLASSES

class GlobalVariables:
    """Class that holds and allows better control over the Global variables used in this script"""
    
    def __init__(self):
        #[PROPERTIES]
        self.addTitleBool = None
        self.recordingExtension = None
        self.screenshotExtension = None
        self.ttw = 0.007
        
        #[Related to RECORDING]
        self.defaultRecordingName = "Manual Recording"
        self.isRecording = False
        self.isReplayActive = False
        self.currentRecording = None
        self.gameTitle = None
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
        self.gameTitle = value
        
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
        self.ttw = globalVariables.get_ttw()
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
        if self.isReplay:
            return os.path.join(self.dir, self.gameTitle, self.replaysFolderName)
        else:
            return os.path.join(self.dir, self.gameTitle)


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

        time.sleep(self.ttw)
        try:
            os.renames(oldPath, newPath)
        except PermissionError:
            print("Re-trying moving of the recording...")
            time.sleep(self.ttw/2)
            os.renames(oldPath, newPath)
        
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
        self.ttw = globalVariables.get_ttw()
        self.gameTitle = globalVariables.get_gameTitle()
        self.addTitleBool = globalVariables.get_addTitleBool()
        
        # Allow to specify a custom path where the file is located.
        if customPath is not None:
            self.path = customPath
        else:
            self.path = obs.obs_frontend_get_last_screenshot()

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
        return os.path.join(self.dir, self.gameTitle, self.screenshotsFolderName)

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

        time.sleep(self.ttw)
        try:
            os.renames(oldPath, newPath)
        except PermissionError:
            print("Re-trying moving of the screenshot...")
            time.sleep(self.ttw/2)
            os.renames(oldPath, newPath)


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
    obs.obs_data_set_default_string(settings, "outputdir", os.path.normpath(Path.home()))
    obs.obs_data_set_default_string(settings, "extension", "mkv")
    obs.obs_data_set_default_string(settings, "ss_extension", "png")

def script_update(settings):
    global globalVariables
    
    # Loading in settings
    global sett
    sett = settings
    
    # Reloading the signal for hooking
    hooked_sh()        # Respond to selected source hooking to a window
    
    # Fetching the Settings
    titleBool = obs.obs_data_get_bool(settings, "title_before_bool")
    rcrdExt=obs.obs_data_get_string(settings, "extension")
    scrnstExt=obs.obs_data_get_string(settings, "ss_extension")
    outDir = os.path.normpath(obs.obs_data_get_string(settings, "outputdir"))
    globalVariables.load_func(titleBool, rcrdExt, scrnstExt, outDir)

    print("Updated the settings!")

def script_description():
    desc = (
        "<h3>OBS RecORDER </h3>"
        "<hr>"
        "Renames and organizes recordings/replays into subfolders similar to NVIDIA ShadowPlay (<i>NVIDIA GeForce Experience</i>).<br><br>"
        "<small>Created by:</small> <b>padii</b><br><br>"
        ""
        "<h4>Please, make sure that your screen/game capturing source is matching the 'source' array in the script!</h4>"
        "You can view the script by pressing 'Edit script' button while RecORDER.py is selected"
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
        os.path.normpath(Path.home()),
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