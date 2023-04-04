# qRadar for YSFLIGHT
Welcome! This is the release, and source of qRadar for [YSFlight](ysflight.com).

[Visit the YSFHQ forum here](ysfhq.com) 

Current version - 0.0.9
![enter image description here](https://github.com/Skipper-is/YS-qRadar/blob/main/images/UI.png?raw=true)
*DISCLAIMER: I am not a programmer, my code is messy, and got messier as I got more and more tired towards the end of this project!* 
## Feature List
These are the current features of qRadar:

 - Connect to a running YSFlight server
 - Show aircraft currently flying on a chart
![enter image description here](https://github.com/Skipper-is/YS-qRadar/blob/main/images/Planeflying.png?raw=true)
 - Load .fld sceneries from YS as a background map for the chart
![enter image description here](https://github.com/Skipper-is/YS-qRadar/blob/main/images/ParsedMap.png?raw=true)
 - Export the background .fld as a geojson for use in a GIS or for creating:
 - Importing user created point and line geojson files as waypoints and flight lines/general lines
![enter image description here](https://github.com/Skipper-is/YS-qRadar/blob/main/images/UserCreatedLines.png?raw=true)
 - Vectoring tool to get bearings and distances from two mouse clicks![enter image description here](https://github.com/Skipper-is/YS-qRadar/blob/main/images/Vectoring%20tool.png?raw=true)
 - Aircraft flying list (showing who is currently in the air, their speed and altitude)
 - Aircraft info tab - allowing the setting of a custom callsign
 - User list - showing who is on the server, whether they're flying, what IFF, and how long they've flown
 - Message log and chat window.![enter image description here](https://github.com/Skipper-is/YS-qRadar/blob/main/images/Chat.png?raw=true)

Many more being added daily! (Along with the obligatory bug fixes)

## Upcoming features
(If they work....)

 - In app waypoint and line creation (without having to import a
   geojson)
 - Importing the .point and .line files from the original YSRADAR
 - PAR (Precision Approach Radar)
 - Processing of mod nav features (additional ILSs etc, currently only takes default ones)
 - Faster log-in process! Is there a way to bypass the usual YS login? I don't need all the plane lists etc!

Any others, suggest them!
## Required Python libraries for code

    PyQt5 (pip install pyqt5)
    PyQtDarkTheme (pip install pyqtdarktheme)
    geojson (pip install geojson)
    
The release under /dist/qRadar.exe is self standing and doesn't have any dependencies.

## Notices
 This code uses QT for GUI
 Some icons are from Yusuke Kamiyamane, Licenced under CC BY 3.0
 Other icons are from Ionicons.
 
> Written with [StackEdit](https://stackedit.io/).