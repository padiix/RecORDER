# RecORDER

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)

> Script was tested only on Windows 11

## What does this script does?
To put it simply, it tries to be the NVIDIA Shadowplay and organize your recordings.

Once you configure it you don't have to worry about anything else, because from now on your recordings as well as replays will be sorted for you.


> Tested only on **3.11.4**, but it might work on earlier minor versions, though you can try it at your own risk!

## Features of the script
In case of fullscreen applications:
- Moves recordings to a folder named after it
- Moves replay buffer recordings to folders named after it
- When automatic splitting is enabled, it will also move actively move all of the recordings to folder named after it

Other features:
- Verbose output of the script in the logs - you should be able to see the most important stuff on the go when available

If not recording a fullscreen app, it will move any recording/replay buffer to a folder named "Manual Recording"


## What do I need to do to make it work?
First things first!
####
1. You need Python - a version [3.11](https://www.python.org/downloads/release/python-3110/) will probably work the best, can be newer.
   > You still need the version within 3.11 for best compatibility
2. Next you need to configure the Python - it's located under `Tools > Scripts > Python Settings` inside of OBS.
   > Select the root folder of where the Python resides, it should be called something like `Python311`
3. You are half way there, next you need to add the script in the `Tools > Scripts`
   > Click the "+" button and select the Python script I created.
   > 
   > For simplicity you can place the script in location where you installed your OBS, here's the relative path: `obs-studio\data\obs-plugins\frontend-tools\scripts`
4. Configure the script in a way you see fit
   > Explaination for parts of the settings:
   > - "Add name of the game as a recording prefix" checkbox - if you want your recordings to look like this:
   >     - Voices of The Void - %Filename Formatting%
   >     - Filename Formatting is configured in `Settings > Advanced > Recording`
   > - "Scene for recording"
   >     - Pick whatever Scene you fancy right now for recording (if you have more than one)
   > - "Source name"
   >     - Select the source that will be the one you use for Window/Application capture
   >     - It will only work on sources of below type (because it utilizes a string named "title" which is unavailable in others for now):
   >         - Window Capture (Windows)
   >         - Game Capture (Windows)
   >         - Application Audio Output Capture (Windows)
   > - "Recordings folder"
   >     - Select a directory where all of your recordings go by default, it will let the script organize the place for you ;)
   > - "Recording extension"
   >     - Write here whatever extension you use for your recordings, the "mkv" is put here by default to both show how you should write the extension and also because I believe it's one of the best ones to use at the moment  
   > - "Screenshot extension"
   >     - Write here whatever extension you have your screenshots saved by OBS as, the "png" is put here by default to both show how you should write the extension and also because it's a default one for non-HDR screenshots 
