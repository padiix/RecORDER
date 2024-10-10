![Logo](https://github.com/user-attachments/assets/273b1b70-aa5a-43c3-a669-2cf8704adf18)

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)

> Script was tested only on Windows 11, but it allegedly works on other OSes as well

**‼️Script only works with OBS in version 29.0.0 or higher‼️**

## What does this script does?
To put it simply, it tries to mimic the recordings organization of NVIDIA Shadow Play.

Once configured - you don't have to worry about anything. From now on your recordings/replays/screenshots will be automatically sorted for you.


> Tested only on **3.11.4**, but it might work on other versions as long as there are no big changes!

## Features of the script
In case of fullscreen applications/ hooked windows (mentioned as **it** below):
- Moves recordings to a folder named after it
- Moves replay buffer recordings to folders named after it
- Moves screenshots to folders named after it
- When automatic splitting is enabled, it will also actively move all of the split recordings to relevant folder as in recordings case

Other features:
- Verbose logs of the script - you should be able to see the important information on the go when viewing `Script Logs`

If the Game Capture or Window Capture is not hooked to any app, it will organize saved recording/replay buffer in a folder called **"Manual Recording"**


## What do I need to do to make it work?
First things first!
1. You need Python - a version [3.11](https://www.python.org/downloads/release/python-3110/) will probably work the best, but you can use newer.
   > You might need the version within 3.11 for best compatibility
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
   > - "Recordings folder"
   >     - Select a directory where OBS saves your recordings to, it will allow the script to organize them for you ;)
   > - "Recording extension"
   >     - Write here extension of your **recordings** (the "mkv" is set default to showcase how to write the extension and because it's recommended one for now)
   >     - [Usefull discussion to understand why use MKV instead of other containers for now](https://www.reddit.com/r/letsplay/comments/7xtssw/mkv_vs_mp4_container_in_obs_deep_discussion/)  
   > - "Screenshot extension"
   >     - Write here extension of your **screenshots** saved by OBS as (the "png" is set default to showcase how to write the extension and it's a default for non-HDR screenshots) 


## FAQ

   - #### RecORDER doesn't see my Game Capture/Window Capture source and shows "Nothing was found... Did you name your source in different way than in the 'sourceNames' array?" in script log
      - It's probably happening because you **changed the Game Capture/Window Capture source default name to something else**. <br> 
      The message shows only when the script checked the names in **"sourceNames"** and found no match with the sources in your scene.<br>
      **Check if you have put your sources into the array before resetting the script using refresh button and trying again!**

   - #### How should I edit the "sourceNames" when I have no idea how should I put it in the script?
      - No worries about that, it's not really hard to do because you have the example already in the script and here below<br><br>
      EXAMPLE:<br>
      You have a source that you use for recording game **"Voices of the Void"**, so you called the Game Capture source **"votv"**, where you have all the filters you need to make your recording look as good as it can for you.<br>
      ***Because you called it different from the "Game Capture", the script does not recognizes it!***
      <br><br><br>
      All you need to do is go to the **Scripts** menu
      ![image](https://github.com/user-attachments/assets/dd309752-52df-4971-a5b4-40b00a31c850) <br><br><br>

      Then, after clicking the **"Edit Script"** button, you will have to find this part of code
      ![image](https://github.com/user-attachments/assets/7e77834f-54f1-457a-913b-00d444130c51) <br><br><br>

      In here you can put how many source names that you are actually using in your workflow<br>
      ***Be aware that the script might need to take longer to find the right source the more source names you add, so do try to keep the difference to the neccesary minimum***
      <br><br>
      #### Example of the sourceNames array:<br>
      **sourceNames = ["votv", "jc", "sc"]**

      Make sure it's matching with whatever you have in this little window of your main OBS window:
      ![image](https://github.com/user-attachments/assets/006c3b41-53c3-468b-ab1c-77586664fadd)
     ### IMPORTANT:
     IF YOU HAVE MORE THAN ONE GAME CAPTURE/ WINDOW CAPTURE SOURCE,<br> MAKE THE CURRENT ONE YOU ARE USING THE HIGHEST ON THE LIST!
