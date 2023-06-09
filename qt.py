from PyQt5.QtWidgets import (QApplication, QDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
                             QPushButton, QSizePolicy, QSplitter, QTabWidget, QToolButton, QVBoxLayout, QWidget,
                             QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsPolygonItem,
                             QCheckBox, QStatusBar, QFrame, QGraphicsLineItem, QGraphicsItem, QGraphicsItemGroup,
                             QGraphicsTextItem, QTableWidget, QHeaderView, QTableWidgetItem, QFileDialog, QSpacerItem,
                             QMessageBox, QScrollArea, QComboBox, QAction, )

from PyQt5.QtGui import (QIcon, QColor, QPalette, QBrush, QPen, QFont, QTransform, QPainterPath, QPolygonF, QPainter,
                         QMouseEvent, QWheelEvent,)

from PyQt5.QtCore import (Qt, QSize, QRectF, QTimer, QPointF, QPoint, QEvent)

from PyQt5.QtSvg import QSvgRenderer, QGraphicsSvgItem

from PyQt5 import uic
import sys, _thread, json, configparser, os, math, threading
from queue import Queue
import ysconnect as ys
from FieldParser import FieldParser as fp
import resources
import qdarktheme

navigationPoints = {}
aircrafts = {}
userList = {}
notFlyingList = [] # Got 2 userlists, one for flying, and one for not.... It's annoying, but id is the sorting index for planes, so I need to keep track of it
serverMessage = ""
basemapPolygons = []
basemapLines = []
basemapRegions = []
basemapPoints = []
serverWeather = None


version = "0.0.14"


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setWindowTitle("YS QRadar")
        
        #Flight director, he's vital
        self.flightDirector = FlightDirector(self)
        
        #Layout
        self.layout = QSplitter(Qt.Horizontal)

        #Sub windows        
        self.mapWindow = MapWindow(self)
        self.menuWindow = MenuWindow(self)
        self.config = Config(self)
        self.login = LoginForm(self)

        #Get references to the widgets in the sub windows
        self.tableWidget = self.menuWindow.aircraftList
        self.userTable = self.menuWindow.userTable
        self.messageLog = self.menuWindow.messageLog
        self.mapScene = self.mapWindow.scene
        self.mapView = self.mapWindow.view
        self.mapWidth = self.mapWindow.view.geometry().width()
        self.mapHeight = self.mapWindow.geometry().height()


        #Get references to the groups in the map window
        self.basemapGroup = self.mapWindow.basemapGroup
        self.taxiwayGroup = self.mapWindow.taxiwayGroup
        self.navGroup = self.mapWindow.navGroup
        self.userWaypointsGroup = self.mapWindow.userWaypoints
        self.userLinesGroup = self.mapWindow.userLines

        #Add the sub windows to the layout
        self.layout.addWidget(self.mapWindow)
        self.layout.addWidget(self.menuWindow)
        self.layout.setSizes([500, 100])
        self.setCentralWidget(self.layout)

        #Main menu buttons
        connect_button = QAction( "Connect", self)
        connect_button.setStatusTip("Connect to server")
        connect_button.triggered.connect(self.loginForm)

        disconnect_button = QAction( "Disconnect", self)
        disconnect_button.setStatusTip("Disconnect from server")
        disconnect_button.triggered.connect(self.disconnect)

        load_field = QAction( "Load Map", self)
        load_field.setStatusTip("Load a basemap for the radar")
        load_field.triggered.connect(self.loadMap)
        process_field = QAction( "Export GeoJSON", self)
        process_field.setStatusTip("This will convert a FLD into a format that you can open in a GIS program")
        process_field.triggered.connect(self.saveGeoJSON)

        importWaypoints = QAction( "Import Waypoints", self)
        importWaypoints.setStatusTip("Import waypoints from a geojson file")
        importWaypoints.triggered.connect(self.importWaypoints)

        importLines = QAction( "Import Lines", self)
        importLines.setStatusTip("Import lines from a geojson file")
        importLines.triggered.connect(self.importLines)
        
        #Menu bar
        menu = self.menuBar()
        
        connection_menu = menu.addMenu("Connection")
        connection_menu.addAction(connect_button)
        connection_menu.addAction(disconnect_button)

        utilities_menu = menu.addMenu("Utilities")
        utilities_menu.addAction(load_field)
        utilities_menu.addAction(process_field)
        utilities_menu.addAction(importWaypoints)
        utilities_menu.addAction(importLines)

        about_menu = menu.addMenu("About")
        about_menu.addAction("Info", self.about)
        about_menu.addAction("Help", self.help)

        #Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.flightDirector.subscribeToMessage(self.statusBarUpdate)

        
        #Coordinates display on status bar
        self.coordinatesLabel = QLabel("Coordinates: N/A")
        self.statusBar.addPermanentWidget(self.coordinatesLabel)

        #Map display on status bar
        self.mapLabel = QLabel("Map: N/A")
        self.statusBar.addPermanentWidget(self.mapLabel)

        self.statusBar.addPermanentWidget(QLabel("Version: "+version))

        self.fieldParser = fp()

        self.show()

        #Add the ground object list to the flight director's ysconnect.
        self.flightDirector.updateNavTypes(self.config.groundFeatures)


    def statusBarUpdate(self, message):
        if type(message)== list:
            msgType = message[0]
            if msgType == "MAP":
                self.mapLabel.setText("Map: " + message[1])
        if type(message) == str:
            self.statusBar.showMessage(message)

        

    def closeEvent(self, event):
        self.flightDirector.disconnect()
        self.mapWindow.close()

    def loginForm(self):
        self.login.show()
    
    def disconnect(self):
        self.flightDirector.disconnect()

    def loadMap(self):
        options = QFileDialog.Options()
        files, _ = QFileDialog.getOpenFileName(self,"Select the Scenery File", "","Scenery Files (*.fld)", options=options)
        if files:
            
            self.file = files
            threading.Thread(target=self.fieldParser.Load, args=(self.file, self.mapLoadedCallback)).start()
            self.flightDirector.incomingMessage("Loading map...")

    def saveGeoJSON(self):
        if not self.fieldParser.processed:
            self.flightDirector.incomingMessage("You need to load a map first!")
            print("You need to load a map first!")
            return
        else:
            options = QFileDialog.Options()
            files, _ = QFileDialog.getSaveFileName(self,"Where would you like to save it?", "","GeoJSON Files (*.geojson)", options=options)
            if files:
                with open(files, 'w') as outfile:
                    json.dump(getGeoJSON("Polygon"), outfile)
                self.flightDirector.incomingMessage("GeoJSON saved!")


    def mapLoadedCallback(self):

        self.flightDirector.mapLoaded = True

    def importWaypoints(self):
        options = QFileDialog.Options()
        files, _ = QFileDialog.getOpenFileName(self,"Select the GeoJSON File", "","GeoJSON Files (*.geojson)", options=options)
        if files:
            with open(files) as f:
                data = json.load(f)
                for feature in data["features"]:
                    if feature["geometry"]["type"] == "Point":
                        waypoint = WaypointSymbol()
                        waypoint.setPos(feature["geometry"]["coordinates"][0], -feature["geometry"]["coordinates"][1])
                        waypoint.name = feature["properties"]["name"]
                        waypoint.setParentItem(self.userWaypointsGroup)
                        self.mapScene.addItem(waypoint)

    def importLines(self):
        options = QFileDialog.Options()
        files, _ = QFileDialog.getOpenFileName(self,"Select the GeoJSON File", "","GeoJSON Files (*.geojson)", options=options)
        if files:
            with open(files) as f:
                data = json.load(f)
                for feature in data["features"]:
                    if feature["geometry"]["type"] == "LineString":
                        coords = []
                        for coordinates in feature["geometry"]["coordinates"]:
                            x,y = coordinates[0], -coordinates[1]
                            coords.append(QPointF(x,y))
                        line = LineSymbol()
                        line.setPos(0,0)
                        line.coordinates = coords
                        if "colour" in feature['properties']:
                            line.colour=feature['properties']['colour']
                            line.colour = line.colour.split(",")
                            line.colour = (int(line.colour[0]), int(line.colour[1]), int(line.colour[2]))
                        else:
                            line.colour = (255,255,255)
                        line.colour = QColor(line.colour[0], line.colour[1], line.colour[2])
                        if "width" in feature:
                            try:
                                line.width = int(feature['width'])
                            except:
                                line.width = 1
                        else:
                            line.width = 1
                        
                        line.setParentItem(self.userLinesGroup)
                        self.mapScene.addItem(line)
                        
    def about(self):
        about = QMessageBox()
        about.setWindowTitle("About")
        about.setText("This program was created by Skipper\n"
                        "It is a radar/map for YSFLIGHT\n"
                        "It is still in development, so expect bugs\n"
                        "If you find any bugs, please report them to either via discord or on the forum\n"
                        "Current Version:" + version+ "\n"
                        "Various icons made by Yusuke Kamiyamane, Licenced under CC BY 3.0\n"
                        "Others by Ionicons")
        about.exec_()

    def help(self):
        help = QMessageBox()
        help.setWindowTitle("Help")
        help.setText("This program is still in development, so expect bugs\n"
                        "If you find any bugs, please report them to either via discord or on the forum\n"
                        "For any help, please contact me on discord or on the forum\n"
                        "Current Version:" + version)
        help.exec_()


class Config():
    def __init__(self, parent=None):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        #Check if the defaults are set, if not, set them.
        if 'QRadar' not in self.config.sections():
            self.config['QRadar'] = {
                'Version': json.dumps([20181124, 20180930, 20150425, 20130817, 20130805, 20120701, 20110207]),
                'DefaultVersion': '20180930',
                'Port': '7915',
                'Host': 'localhost',
                'Username': 'radar',
                'GroundFeatures': json.dumps({'ILS[CJAP]':'ILS', 'ILS2[CJAP]':'ILS', 'LDA[CJAP]':'NDB'}),
            }
            self.config.write(open('config.ini', 'w'))
        
        self.config.read('config.ini')
        self.ysflightVersions = json.loads(self.config['QRadar']['Version'])
        self.defaultVersion = self.config['QRadar']['DefaultVersion']
        self.port = self.config['QRadar']['Port']
        self.host = self.config['QRadar']['Host']
        self.username = self.config['QRadar']['Username']
        self.groundFeatures = json.loads(self.config['QRadar']['GroundFeatures'])
        
        

    def getVersions(self):
        return self.ysflightVersions
    
    def getDefaultVersion(self):
        return self.defaultVersion

    def getPort(self):
        return self.port
    
    def getHost(self):
        return self.host
    
    def getUsername(self):
        return self.username
    
    def setDefaultVersion(self, version):
        self.config['QRadar']['DefaultVersion'] = version
        self.config.write(open('config.ini', 'w'))
    
    def setPort(self, port):
        self.config['QRadar']['Port'] = port
        self.config.write(open('config.ini', 'w'))

    def setHost(self, host):
        self.config['QRadar']['Host'] = host
        self.config.write(open('config.ini', 'w'))

    def setUsername(self, username):
        self.config['QRadar']['Username'] = username
        self.config.write(open('config.ini', 'w'))
    
    def getGroundFeatures(self):
        return self.groundFeatures
        

class LoginForm(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("YS QRadar - Login")
        self.parent = parent
        self.setMaximumSize(300, 200)
        #Get defaults from config
        ysflightVersions = self.parent.config.getVersions()
        port = self.parent.config.getPort()
        host = self.parent.config.getHost()
        username = self.parent.config.getUsername()
        defaultVersion = self.parent.config.getDefaultVersion()

        #Buttons and textedit
        #Username box
        self.hostHbox = QHBoxLayout()
        self.host = QLineEdit(host)
        self.hostlabel = QLabel("Host:")
        self.hostHbox.addWidget(self.hostlabel)
        self.hostHbox.addWidget(self.host)

        #Port box
        self.portHbox = QHBoxLayout()
        self.port= QLineEdit(port)
        self.portlabel = QLabel("Port:")
        self.portHbox.addWidget(self.portlabel)
        self.portHbox.addWidget(self.port)

        #Version box
        self.versionHbox = QHBoxLayout()
        self.versionlabel = QLabel("Version:")
        self.version = QComboBox()
        self.versionHbox.addWidget(self.versionlabel)
        self.versionHbox.addWidget(self.version)



        for version in ysflightVersions:
            self.version.addItem(str(version))
        self.version.setCurrentIndex(ysflightVersions.index(int(defaultVersion)))
        #Button box
        self.buttonHbox = QHBoxLayout()
        self.login = QPushButton("Login")
        self.login.clicked.connect(self.loginClicked)
        self.buttonHbox.addWidget(self.login)


        #Layout

        layout = QVBoxLayout()
        layout.addLayout(self.hostHbox)
        layout.addLayout(self.portHbox)
        layout.addLayout(self.versionHbox)
        layout.addLayout(self.buttonHbox)
        self.setLayout(layout)

    def loginClicked(self):
        
        #Save the configs
        self.parent.config.setHost(self.host.text())
        self.parent.config.setPort(self.port.text())
        self.parent.config.setDefaultVersion(self.version.currentText())


        if self.port.text() == "":
            self.port.setText("7915")
        try :
            int(self.port.text())
        except ValueError:
            self.port.setText("7915")
        global ysf
        
        self.connectingWidget = ConnectingWidget(self.parent, self.host.text(), self.port.text(), self.version.currentText())
        self.connectingWidget.show()
        self.accept()


class ConnectingWidget(QDialog):
    def __init__(self, parent=None, host=None, port=None, version=20181124):
        super().__init__(parent)
        self.setWindowTitle("YS QRadar - Connecting")
        self.parent = parent
        self.host = host
        self.port = port
        self.parent.flightDirector.connect(self.host, self.port, 'radar', int(version))
        self.messageCount = 0
        #Buttons and textedit
        self.connectingLabel = QLabel("Connecting to " + self.host + ":" + self.port)
        self.connectingLabel.setAlignment(Qt.AlignCenter)
        self.message = QLabel("Please wait...")
        self.subscription = self.parent.flightDirector.subscribeToMessage(self.getMessageUpdate)

        

        #Layout

        layout = QGridLayout()
        layout.addWidget(self.connectingLabel, 0, 0)
        layout.addWidget(self.message, 1, 0)
        self.setLayout(layout)

    def getMessageUpdate(self, label):
        if type(label) == str:
            self.messageCount += 1
            self.message.setText(str(self.messageCount)+": " + label)
        if self.parent.flightDirector.connected:
            self.parent.flightDirector.unsubscribeToMessage(self.subscription)
            self.accept()


class MapWindow(QWidget):
    def __init__(self, parent=None):
        super(MapWindow, self).__init__(parent)
        self.setAutoFillBackground(True)
        self.setMinimumSize(640,480)
        self._zoom = 1
        self.currentSceneScale = 1
        self.setParent(parent)
        self.mainWindow = parent
        #Set a graphics scene
        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QBrush(QColor(0,0,68)))
        self.view = QGraphicsView(self.scene)
        self.view.setParent(self)
        self.view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.view.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        
        self.view.setFrameShape(QFrame.NoFrame)
        self.view.viewport().installEventFilter(self)
        self.view.viewport().setCursor(Qt.CrossCursor)

        #Add a layout
        hbox = QHBoxLayout(self)
        hbox.addWidget(self.view)
        self.setLayout(hbox)

        self.resizeScene()

        self.view.wheelEvent = self.wheelEvent
        self.view.mouseReleaseEvent = self.mouseReleaseEvent
        self.setMouseTracking(True)
        self.lastPos = None
        self.lastPosItem = None
        
        #Add zoom buttons
        self.zoomInButton = QPushButton("+")
        self.zoomOutButton = QPushButton("-")
        self.zoomResetButton = QPushButton("Reset")
        
        self.zoomInButton.setStyleSheet("QPushButton {background-color: #202124; color: #FFFFFF; border-radius: 5px;}")
        self.zoomOutButton.setStyleSheet("QPushButton {background-color: #202124; color: #FFFFFF; border-radius: 5px;}")
        self.zoomResetButton.setStyleSheet("QPushButton {background-color: #202124; color: #FFFFFF; border-radius: 5px;}")

        

        self.zoomInButton.setMaximumSize(50,30)
        self.zoomOutButton.setMaximumSize(50,30)
        self.zoomResetButton.setMaximumSize(50,30)

        self.zoomInButton.setMinimumSize(50,30)
        self.zoomOutButton.setMinimumSize(50,30)
        self.zoomResetButton.setMinimumSize(50,30)

        self.zoomInButton.clicked.connect(self.zoomIn)
        self.zoomOutButton.clicked.connect(self.zoomOut)
        self.zoomResetButton.clicked.connect(self.zoomReset)

        self.zoomInButton.move(10,10)
        self.zoomOutButton.move(10,40)
        self.zoomResetButton.move(10,70)

        self.zoomInButton.setParent(self)
        self.zoomOutButton.setParent(self)
        self.zoomResetButton.setParent(self)


        #Basemap and click counters - for drawing lines etc

        self.clickCount = 0
        self.basemapGroup = Basemap()
        self.taxiwayGroup = Basemap()
        self.navGroup = Basemap()
        self.userWaypoints = Basemap()
        self.userLines = Basemap()
        self.scene.addItem(self.basemapGroup)
        self.scene.addItem(self.taxiwayGroup)
        self.scene.addItem(self.navGroup)
        self.scene.addItem(self.userWaypoints)
        self.scene.addItem(self.userLines)


        self.mapHighlightedObject = None



        # #Basemap buttons
        self.toggleLabel = QLabel("Toggle map elements:")
        self.toggleLabel.setStyleSheet("QLabel { color: white; }")
        
        self.toggleBasemapButton = QCheckBox("Basemap")
        self.toggleTaxiwayButton = QCheckBox("Taxiways")
        self.toggleNavButton = QCheckBox("Navs")
        self.toggleUserWaypointsButton = QCheckBox("User Waypoints")
        self.toggleUserLinesButton = QCheckBox("User Lines")
        self.currentScenewidth = self.view.width()
        self.toggleBasemapButton.setStyleSheet("QCheckBox { color: white; }")
        self.toggleTaxiwayButton.setStyleSheet("QCheckBox { color: white; }")
        self.toggleNavButton.setStyleSheet("QCheckBox { color: white; }")
        self.toggleUserWaypointsButton.setStyleSheet("QCheckBox { color: white; }")
        self.toggleUserLinesButton.setStyleSheet("QCheckBox { color: white; }")

        self.toggleBasemapButton.setChecked(True)
        self.toggleTaxiwayButton.setChecked(True)
        self.toggleNavButton.setChecked(True)
        self.toggleUserWaypointsButton.setChecked(True)
        self.toggleUserLinesButton.setChecked(True)

        self.toggleLabel.move(self.currentScenewidth-120,0)
        self.toggleBasemapButton.move(self.currentScenewidth-120,20)
        self.toggleTaxiwayButton.move(self.currentScenewidth-120,40)
        self.toggleNavButton.move(self.currentScenewidth-120,60)
        self.toggleUserWaypointsButton.move(self.currentScenewidth-120,80)
        self.toggleUserLinesButton.move(self.currentScenewidth-120,100)

        self.toggleLabel.setParent(self.view)
        self.toggleBasemapButton.setParent(self.view)
        self.toggleTaxiwayButton.setParent(self.view)
        self.toggleNavButton.setParent(self.view)
        self.toggleUserWaypointsButton.setParent(self.view)
        self.toggleUserLinesButton.setParent(self.view)

        self.toggleBasemapButton.stateChanged.connect(lambda:self.toggleBasemap(self.toggleBasemapButton,'basemap'))
        self.toggleTaxiwayButton.stateChanged.connect(lambda:self.toggleBasemap(self.toggleTaxiwayButton,'taxiway'))
        self.toggleNavButton.stateChanged.connect(lambda:self.toggleBasemap(self.toggleNavButton, 'navs'))
        self.toggleUserWaypointsButton.stateChanged.connect(lambda:self.toggleBasemap(self.toggleUserWaypointsButton, 'userwaypoints'))
        self.toggleUserLinesButton.stateChanged.connect(lambda:self.toggleBasemap(self.toggleUserLinesButton, 'userlines'))
        pen = QPen(QColor(255,0,0,125), 1, Qt.SolidLine)
        pen.setCosmetic(True)
        self.bearingLine = self.scene.addPath(QPainterPath(), pen)
        self.bearingText = self.scene.addText("", QFont("Arial", 10))
        self.bearingText.setFlags(QGraphicsItem.ItemIgnoresTransformations)
        self.bearingText.hide()
    
    def resizeEvent(self, event):
        self.currentScenewidth = self.view.width()
        self.toggleLabel.move(self.currentScenewidth-120,0)
        self.toggleBasemapButton.move(self.currentScenewidth-120,20)
        self.toggleTaxiwayButton.move(self.currentScenewidth-120,40)
        self.toggleNavButton.move(self.currentScenewidth-120,60)
        self.toggleUserWaypointsButton.move(self.currentScenewidth-120,80)
        self.toggleUserLinesButton.move(self.currentScenewidth-120,100)

        self.resizeScene()
    
    def resizeScene(self):
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatioByExpanding) #KeepAspectRatioByExpanding
    
    def getCentre(self):
       
        return self.scene.sceneRect().center()
    
    def fitInView(self, scale=True):
        rect = QRectF()
        if self.scene.items():
            rect = self.scene.itemsBoundingRect()
            rect.setX(rect.x() -1000)
            rect.setY(rect.y() -1000)
            rect.setWidth(rect.width() + 2000)
            rect.setHeight(rect.height() + 2000)
        if rect.width() == 0 or rect.height() == 0:
            rect = QRectF(0, 0, 1, 1)
        self.scene.setSceneRect(rect)
        if not self.scene.views():
            return
        view = self.scene.views()[0]
        current = view.transform().mapRect(rect)
        if not scale:
            current.reset()
        self._zoom = 1


    def zoomIn(self):
        factor = 1.25
        self._zoom *= factor
        self.view.scale(factor, factor)

        self.currentSceneScale = self._zoom


    def zoomOut(self):
        factor = 0.8
        self._zoom *= factor

        self.currentSceneScale = self._zoom
        self.view.scale(factor, factor)
    
    def zoomReset(self):
        factor = 1/self._zoom
        self.view.scale(factor, factor)
        self._zoom = 1
        self.currentSceneScale = self._zoom
        
    
    def toggleBasemap(self, state, mapType):
        if mapType == 'basemap':
            basemap = self.basemapGroup
        elif mapType == 'taxiway':
            basemap = self.taxiwayGroup
        elif mapType == 'navs':
            basemap = self.navGroup
        elif mapType == 'userwaypoints':
            basemap = self.userWaypoints
        elif mapType == 'userlines':
            basemap = self.userLines
        

        if state.isChecked():
            basemap.setVisible(True)
        else:
            basemap.setVisible(False)

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.zoomIn()
        else:
            self.zoomOut()

    def mousePressEvent(self, event):
        item = self.view.itemAt(event.pos())
        if event.button() == Qt.LeftButton:
        
            if type(item) == PlaneSymbol:
                self.selectPlaneOnMap(item)

        if event.button() == Qt.RightButton:
            
            if self.clickCount == 0:
                if type(item) == PlaneSymbol or type(item) == WaypointSymbol or type(item) == GroundSymbol:
                    self.lastPos = item.pos()
                    self.lastPosItem = item
                else:
                    eventPos = event.pos()
                    eventPos = QPoint(eventPos.x()-10, eventPos.y()-10)
                    self.lastPos = self.view.mapToScene(eventPos).toPoint() # For some reason this is adding 5...
                self.clickCount = 1
            elif self.clickCount == 1:
                self.clickCount = 2
            elif self.clickCount == 2:
                self.clickCount = 0
                self.lastPos = None
                self.newPos = None
                self.lastPosItem = None
                self.bearingText.hide()
                self.bearingLine.setPath(QPainterPath())    #Clear the line

        super(MapWindow, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.view.setDragMode(QGraphicsView.NoDrag)
            
            self.view.setDragMode(QGraphicsView.ScrollHandDrag)
            self.view.viewport().setCursor(Qt.CrossCursor)

    def eventFilter(self, source, event):
        if (event.type() == QEvent.MouseMove and source is self.view.viewport()):
            position = event.pos()
            localPosition = self.view.mapToScene(position)
            self.mainWindow.coordinatesLabel.setText("x: " + str(int(localPosition.x())) + " y: " + str(-int(localPosition.y())))
            #That updates the position in the bottom status bar.

            if self.clickCount == 1:
                self.newpos = self.view.mapToScene(event.pos()).toPoint()
                self.updatePath()
        else:
            pass
        return super(MapWindow, self).eventFilter(source, event)
    
    def selectPlaneOnMap(self, plane):
        '''Selects a plane on the map, and updates the aircraft details tab'''
        if self.mapHighlightedObject: # Clear anything that was previously selected
            self.mapHighlightedObject.clicked = False
            self.mapHighlightedObject.update()

        if self.mapHighlightedObject == plane: #If it's the same one, clear it from the list.
            self.mapHighlightedObject = None
        else:
            self.mapHighlightedObject = plane #Otherwise, set the current plane as the highlighted one
            plane.clicked = not plane.clicked
            plane.update()
            updateAircraftOnMap(self.mainWindow, plane.parent)

    def updatePath(self):
        if not self.lastPos.isNull() and not self.newpos.isNull():
            if self.lastPosItem:
                self.lastPos = self.lastPosItem.pos()
            path = QPainterPath(self.lastPos)
            angle, distance, midpoint = bearingFromPoints(self.lastPos, self.newpos)
            distance = mToNm(distance)
            self.bearingText.setPos(midpoint)
            self.bearingText.setPlainText(str(int(angle)) + u"\N{DEGREE SIGN}\n" + str(int(distance)) + "nm")
            self.bearingText.show()
            path.lineTo(self.newpos)
            self.bearingLine.setPath(path)
            

class MenuWindow(QWidget):
    def __init__(self, parent=None):
        super(MenuWindow, self).__init__(parent)
        self.parent = parent
        #Set up window tabs
        self.tabs = QTabWidget()
        #self.mapControlsTab = QWidget()
        self.userList =[]
        self.timerEvent = QTimer()
        self.timerEvent.timeout.connect(self.receiveMessages)
        self.timerEvent.start(1000)

        #uic.loadUi("mapControlsMenu.ui", self.mapControlsTab)
        self.aircraftListTab = QWidget()
        self.aircraftList = QTableWidget()
        self.aircraftList.setEditTriggers(self.aircraftList.NoEditTriggers)
        self.aircraftInfoBox = QWidget()
        self.userlistTab = QWidget()
        self.messageLogTab = QWidget()
        self.tabs.resize(300,200)
        
        self.flightDirector = self.parent.flightDirector
        self.flightDirector.subscribeToMessage(self.receiveFDMessages)

        self.weatherTab = QWidget()

        #Add tabs
        
        self.tabs.addTab(self.aircraftListTab,"Aircraft List")
        self.tabs.addTab(self.userlistTab,"User List")
        self.tabs.addTab(self.messageLogTab,"Message Log")
        self.tabs.addTab(self.weatherTab,"Weather")
        


        self.aircraftListTab.layout = QVBoxLayout()
        self.aircraftListTab.setLayout(self.aircraftListTab.layout)
        self.aircraftList.setColumnCount(5)
        self.aircraftList.setHorizontalHeaderLabels(["Callsign", "Altitude", "Speed (kts)", "Heading","ID"])
        id_column = self.aircraftList.columnCount() -1
        self.aircraftList.setColumnHidden(id_column, True)
        self.aircraftListTab.layout.addWidget(self.aircraftList)
        self.aircraftList.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.aircraftList.cellClicked.connect(self.aircraftListClicked)

        self.aircraftListTab.layout.addWidget(QLabel("Aircraft Info:", styleSheet='font-weight: bold;'))
        self.aircraftListTab.layout.addWidget(self.aircraftInfoBox)
        


        
        self.userlistTab.layout = QGridLayout()
        self.userlistTab.setLayout(self.userlistTab.layout)
        self.userTable = QTableWidget()
        self.userTable.setColumnCount(4)
        self.userTable.setHorizontalHeaderLabels(["Name", "Situation","Flight Time","IFF"])
        self.userlistTab.layout.addWidget(self.userTable, 0, 0)
        self.userTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)




        
        #Set up aircraft info tab:
        self.aircraftInfoBox.layout = QGridLayout()
        self.aircraftInfoBox.setLayout(self.aircraftInfoBox.layout)
        self.aircraftInfoBox.layout.addWidget(QLabel("Callsign:", styleSheet='font-weight: bold;'), 0, 0)
        self.callsignLabel = QLabel("N/A")
        self.aircraftInfoBox.layout.addWidget(self.callsignLabel, 0, 1)
        self.callSignEditButton = QPushButton(QIcon(":icons/pencil-button.png"), "Edit Callsign", self)
        self.callSignEditButton.clicked.connect(self.editCallsign)
        self.aircraftInfoBox.layout.addWidget(self.callSignEditButton, 0, 2)
        self.aircraftInfoBox.layout.addWidget(QLabel("Username:", styleSheet='font-weight: bold;'), 1, 0)
        self.usernameLabel = QLabel("N/A")
        self.aircraftInfoBox.layout.addWidget(self.usernameLabel, 1, 1)
        self.aircraftInfoBox.layout.addWidget(QLabel("Altitude:", styleSheet='font-weight: bold;'), 2, 0)
        self.altitudeLabel = QLabel("N/A")
        self.aircraftInfoBox.layout.addWidget(self.altitudeLabel, 2, 1)
        self.aircraftInfoBox.layout.addWidget(QLabel("Speed:", styleSheet='font-weight: bold;'), 3, 0)
        self.speedLabel = QLabel("N/A")
        self.aircraftInfoBox.layout.addWidget(self.speedLabel, 3, 1)
        self.aircraftInfoBox.layout.addWidget(QLabel("Heading:", styleSheet='font-weight: bold;'), 4, 0)
        self.headingLabel = QLabel("N/A")
        self.aircraftInfoBox.layout.addWidget(self.headingLabel, 4, 1)

        #Set up message log tab
        self.messageLogTab.layout = QVBoxLayout()
        self.messageLogTab.setLayout(self.messageLogTab.layout)
        self.messageLogScroll = QScrollArea()
        self.messageLogScroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.messageLogScroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.messageLogScroll.setWidgetResizable(True)
        self.messageLogTab.layout.addWidget(self.messageLogScroll)
        self.messageLogScrollContent = QWidget()
        self.messageLogScroll.setWidget(self.messageLogScrollContent)
        self.messageLog = QVBoxLayout()
        self.messageLog.addStretch()
        self.messageLog.setAlignment(Qt.AlignTop)
        self.messageLogScrollContent.setLayout(self.messageLog)

        self.sendLayout = QHBoxLayout()
        
        self.messageLogTab.layout.addLayout(self.sendLayout)
        self.messageInput = QLineEdit()
        self.messageInput.returnPressed.connect(self.sendMessage)
        self.sendLayout.addWidget(self.messageInput)
        self.sendButton = QPushButton("Send")
        self.sendLayout.addWidget(self.sendButton)
        self.sendButton.clicked.connect(self.sendMessage)

        #Set up weather tab
        self.weatherTab.layout = QVBoxLayout()
        self.weatherTab.setLayout(self.weatherTab.layout)
        self.weatherTab.layout.addWidget(QLabel("Wind:", styleSheet='font-weight: bold;'))
        self.weather = None
        self.windView = QGraphicsView()
        self.weatherTab.layout.addWidget(self.windView)
        self.windScene = QGraphicsScene()
        self.windView.setScene(self.windScene)
        self.windView.setMinimumHeight(100)
        self.windView.setMaximumHeight(400)

        #Add the compass to the scenepyqt5 add 
        compass = QGraphicsSvgItem(":icons/compass.svg")
        self.windScene.addItem(compass)
        compass.setPos(0, 0)
        compass.setScale(2)
        
        centrePoint = compass.boundingRect().center()*2
        
        self.compassArrow = QGraphicsSvgItem(":icons/compassArrow.svg")
        compassArrowcentre = self.compassArrow.boundingRect().center()
        self.compassArrow.setTransformOriginPoint(compassArrowcentre)
        self.compassArrow.setPos(centrePoint+QPointF(-compassArrowcentre.x(), -compassArrowcentre.y()))
        self.compassArrow.setRotation(-90)
        self.windScene.addItem(self.compassArrow)     
        self.windScene.update()
        self.windValue = QLabel("N/A")
        self.weatherDetailsLayout = QGridLayout()
        self.weatherTab.layout.addLayout(self.weatherDetailsLayout)
        self.weatherDetailsLayout.addWidget(QLabel("Wind Speed:", styleSheet='font-weight: bold;'), 0, 0)
        self.weatherDetailsLayout.addWidget(self.windValue, 0, 1)

        self.weatherDetailsLayout.addWidget(QLabel("Time of day: ", styleSheet='font-weight: bold;'), 1, 0)
        self.timeDetails = QLabel("N/A")
        self.weatherDetailsLayout.addWidget(self.timeDetails, 1, 1)
        self.visibilityDetails = QLabel("N/A")
        self.weatherDetailsLayout.addWidget(QLabel("Visibility: ", styleSheet='font-weight: bold;'), 2, 0)
        self.weatherDetailsLayout.addWidget(self.visibilityDetails, 2, 1)


        self.weatherTab.layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))


        layout = QHBoxLayout()

        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def editCallsign(self):
        if self.parent.mapWindow.mapHighlightedObject:

            self.editCallsignDialog = EditCallsignDialog(self.parent.mapWindow.mapHighlightedObject)
            self.editCallsignDialog.show()

    def aircraftListClicked(self, row, column):
        #Get the id from the table
        id = self.aircraftList.item(row, 4).text()
        #Get the aircraft associated with the id

        aircaft = aircrafts[int(id)]
        self.parent.mapWindow.selectPlaneOnMap(aircaft.symbol)
        self.parent.mapWindow.view.centerOn(aircaft.symbol)

    def sendMessage(self):
        message = self.messageInput.text()
        if message != "":
            message = '(' + self.flightDirector.username + ") " + message
            self.flightDirector.sendMessage(message)
            self.messageInput.setText("")

    def receiveMessages(self): # This is receiving chat messages
        messages = self.flightDirector.messageList
        for message in messages:
            self.receiveMessage(message)
        self.flightDirector.messageList = []
        self.updateWeather(self.weather)

    def receiveMessage(self, message):
        messageContainer = QLabel(message)
        messageContainer.setWordWrap(True)
        self.messageLog.addWidget(messageContainer)
        #Check that the message log isn't over 50 messages long, otherwise delete the first one
        rowCount = self.messageLog.count()
        if rowCount > 50:
            self.messageLog.itemAt(1).widget().setParent(None)
            self.messageLog.itemAt(1).widget().deleteLater()
    
    def receiveFDMessages(self, message):
        if type(message)== list:
            #Should be a weather message:
            if message[0] == "weather":
              self.weather = message[1]

    
    def updateWeather(self,weather):
        #Weather dict contains: {"windDirection": windDirection, "windSpeed": windSpeed, "time": time, "visibility": visibility}
        if weather is None:
            self.windValue.setText("N/A")
            self.timeDetails.setText("N/A")
            self.visibilityDetails.setText("N/A")
        else:
            self.windValue.setText(str(weather["windSpeed"]) + " knots")
            self.timeDetails.setText(str(weather["time"]))
            self.visibilityDetails.setText(str(round(weather["visibility"]/1852,2)) + "nm / "+ str(round(weather["visibility"]/1000,2)) + "km")
            self.compassArrow.setRotation(weather["windDirection"]-90)
            self.windScene.update()


class EditCallsignDialog(QDialog):
    def __init__(self, currentPlane, parent=None):
        super(EditCallsignDialog, self).__init__(parent)
        self.currentPlane = currentPlane
        self.callsign = currentPlane.callsign
        self.setWindowTitle("Edit Callsign")
        self.layout = QGridLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(QLabel("Callsign:"), 0, 0)
        self.layout.addWidget(QLineEdit(self.callsign), 0, 1)
        saveButton = QPushButton("Save")
        saveButton.clicked.connect(self.saveEdit)
        self.layout.addWidget(saveButton, 1, 0)
        cancelButton = QPushButton("Cancel")
        cancelButton.clicked.connect(self.close)
        self.layout.addWidget(cancelButton, 1, 1)

    def saveEdit(self):
        self.currentPlane.callsign = self.layout.itemAtPosition(0, 1).widget().text()
        self.currentPlane.update()
        self.close()


class PlaneSymbol(QGraphicsItem):
    """
    A class representing a plane symbol in a radar display.
    """

    def __init__(self, parent=None):
        super(PlaneSymbol, self).__init__(parent)
        self.speed = 0
        self.heading = 0
        self.altitude = 0
        self.callsign = ""
        
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations,True)
        self.clicked = False
        self.change = 0
        self.parent = parent

    def boundingRect(self):
        if self.clicked:
            rectangle = QRectF(-100, -100, 200, 200)
        else:
            rectangle = QRectF(-25, -25, 50, 50)
        return rectangle

    def paint(self, painter, option, widget):

        if self.clicked:
            painter.setPen(QPen(Qt.red))
        else:
            painter.setPen(QPen(Qt.white))

        painter.rotate((self.heading - 90))
        painter.drawRect(-3, -3, 6, 6)

        if self.clicked:
            dashedPen = QPen(Qt.red)
        else:
            dashedPen = QPen(Qt.white)

        dashedPen.setWidth(1)
        dashedPen.setStyle(Qt.DashLine)
        painter.setPen(dashedPen)
        painter.drawLine(5, 0, 10, 0)
        painter.rotate(-(self.heading - 90))

        painter.setFont(QFont("Arial", 8))
        painter.drawText(6, 10, self.callsign)
        painter.drawText(6, 25, 'FL' + mToFL(self.altitude))
        painter.setPen(QPen(Qt.white))

        arrowsvg = QSvgRenderer(":icons/arrow.svg")

        if self.change > 0:  # climbing
            arrowsvg.render(painter, QRectF(0, 8, 8, 16))
        elif self.change < 0:  # descending
            painter.rotate(180)
            arrowsvg.render(painter, QRectF(-8, -24, 8, 16))
            painter.rotate(-180)

        painter.drawText(6, 40, str(int(self.speed * 1.94384)) + 'kts')

        if self.clicked:
            painter.setPen(QPen(Qt.white))
            svg = QSvgRenderer(":icons/compass.svg")
            svg.render(painter, QRectF(-100, -100, 200, 200))


class GroundSymbol(QGraphicsItem):
    """
    A class representing a ground nav symbol in a radar display.
    """
    def __init__(self, parent=None):
        super(GroundSymbol, self).__init__(parent)
        self.id = 0
        self.type = ""
        self.name = ""
        self.rotation = 0
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations)
    
    def boundingRect(self):
        rectangle = QRectF(-10,-25,50,50)
        t = QTransform()
        t.rotate(self.rotation)
        rectangle = t.mapRect(rectangle)
        return rectangle

    def paint(self, painter, option, widget):
        painter.setPen(QPen(Qt.white))
        painter.setFont(QFont("Arial",8))
        painter.drawText(6,10,self.name)
        painter.drawText(0,30,self.type)
        pen = QPen(Qt.white)
        pen.setWidth(1)
        painter.setPen(pen)
        if self.type == 'ILS':
            triangle = QPainterPath()
            triangle.moveTo(4,0)
            triangle.lineTo(0,8)
            triangle.lineTo(8,8)
            triangle.lineTo(4,0)
            painter.drawPath(triangle)
        else:
            if(self.type == 'VORDME'):
                painter.drawRect(-4,-4,8,8)
                painter.drawPolygon(QPolygonF([QPointF(-2,-4),QPointF(2,-4),QPointF(4,0), QPointF(2,4), QPointF(-2,4), QPointF(-4,0)]))

            if (self.type == 'NDB'):
                painter.drawEllipse(-4,-4,8,8)
                painter.drawEllipse(-2,-2,4,4)


class Basemap(QGraphicsItem):
    def __init__(self, parent=None):
        super(Basemap, self).__init__(parent)
        self.parent = parent
        

    def boundingRect(self):
        if self.childItems:
            rectangle = self.childrenBoundingRect()
        else:
            rectangle = QRectF(0,0,self.parent.mapWidth,self.parent.mapHeight)
        return rectangle
    
    def paint(self, painter, option, widget):
        pass


class WaypointSymbol(QGraphicsItem):
    def __init__(self, parent=None):
        super(WaypointSymbol, self).__init__(parent)
        self.name = ""
        self.boundingRect = QRectF(-8,-8,16,50)
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations)

    def boundingRect(self):
        return self.boundingRect
    
    def paint(self, painter, option, widget):
        painter.setPen(QPen(Qt.white))
        painter.setFont(QFont("Arial",8))
        rectangle = painter.drawText(QRectF(6,10,100,30),Qt.AlignLeft,self.name)
        painter.setPen(QPen(Qt.white))
        painter.drawEllipse(-4,-4,8,8)
        painter.drawPolygon([QPointF(-1,-3),QPointF(0,-8),QPointF(1,-3)]) #Top triangle
        painter.drawPolygon([QPointF(-1,3),QPointF(0,8),QPointF(1,3)]) #Bottom triangle
        painter.drawPolygon([QPointF(-3,-1),QPointF(-8,0),QPointF(-3,1)]) #Left triangle
        painter.drawPolygon([QPointF(3,-1),QPointF(8,0),QPointF(3,1)]) #Right triangle

        minx = -8
        miny = -8
        maxx = rectangle.width()+6
        maxy = rectangle.height()+10
        self.boundingRect = QRectF(minx,miny,maxx-minx,maxy-miny)


class LineSymbol(QGraphicsItem):
    def __init__(self, parent=None):
        super(LineSymbol, self).__init__(parent)
        self.name = ""
        self.colour = QColor(255,255,255,255)
        self.coordinates = []
        self.width = 0
        self.minimumX = 0
        self.minimumY = 0
        self.maximumX = 0
        self.maximumY = 0
        

    def boundingRect(self):

        rectangle = QRectF(self.minimumX-5,self.minimumY-5,self.maximumX-self.minimumX+5,self.maximumY-self.minimumY+5)
        return rectangle

    def paint(self, painter, option, widget):

        self.getMaxMin()

        dashedPen = QPen(self.colour)
        dashedPen.setCosmetic(True)
        dashedPen.setWidth(self.width)
        dashedPen.setStyle(Qt.DashLine)
        painter.setPen(dashedPen)           
        painter.drawPolyline(self.coordinates)
            

    def getMaxMin(self):
        for coords in self.coordinates:
            x = coords.x()
            y = coords.y()
            if x < self.minimumX:
                self.minimumX = x
            if y < self.minimumY:
                self.minimumY = y
            if x > self.maximumX:
                self.maximumX = x
            if y > self.maximumY:
                self.maximumY = y


class User():
    def __init__(self, usertype, iff,id, name):
        self.name = name
        self.id = id
        self.iff = iff
        self.type = usertype
        self.table_row = None
    
    def __str__(self):
        return self.name
    
    def setName(self, name):
        self.name = name
    
    def setID(self, id):
        self.id = id
    
    def setTableRow(self, table_row):
        self.table_row = table_row
    
    def getName(self):
        return self.name
    
    def getID(self):
        return self.id
    
    def getTableRow(self):
        return self.table_row
    

class FlightDirector():
    """The MVP of the module. This guy does all the heavy lifting and directing. He's the boss, although he's quite over worked. Deals with all the incoming messages and updates the map accordingly,
    also handles the messy business of dealing with the threads, which are generally a nightmare."""
    def __init__(self, parent=None):
        self.parent = parent
        self.mainWindow = parent
        self.client = None
        self.connected = False
        self.client = ys.YSConnect(self.incomingMessage)
        self.latestMessage = None
        self.subscribedToMessages = []
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(2500)
        self.mapLoaded = False
        self.messageList = []
        self.username = "radar"

    def connect(self, ip, port, username="radar", version=20180930):
        self.username = username
        threading.Thread(target=self.client.connect, args=(ip, int(port), username, version)).start()
    
    def disconnect(self):
        self.client.disconnect()
        self.connected = False

    def incomingMessage(self, message):
        self.latestMessage = message
        if type(message) == str:
            self.messageList.append(message)            
        for listener in self.subscribedToMessages:
            listener(message)
        
        if "Logged in!" in message:
            self.connected = True

    def subscribeToMessage(self, listener):
        self.subscribedToMessages.append(listener)

    def unsubscribeToMessage(self, listener):
        try:
            self.subscribedToMessages.remove(listener)
        except:
            pass
    
    def update(self):
        #Update every 5 seconds
        if self.connected:
            updateUsers(self.mainWindow.userTable, self.client.getUsers())
            updatePlanes(self.mainWindow, self.client.getPlanes(), self.client.getNavPoints())
        if self.mapLoaded:
            updateBasemap(self.mainWindow)
            self.mapLoaded = False

    def sendMessage(self, message):
        self.client.sendMessage(message)
    
    def updateNavTypes(self,navTypes):
        self.client.updateNavTypes(navTypes)


def mToNm(m):
    return m/1852

def nmToPx(nm):
    return nm*50

def pxToNm(px):
    return px/50

def mToPx(m):
    return nmToPx(mToNm(m))

def msToKnots(ms):
    return round(ms*1.94384,2)

def mToFL(m):
    ft = m*3.28084
    fl = int(ft/100)
    if fl < 100:
        return "0"+str(fl)
    else:
        return str(fl)

def bearingFromPoints(point1, point2):
    point1x = point1.x()
    point1y = point1.y()
    point2x = point2.x()
    point2y = point2.y()
    angle = math.atan2(point2y-point1y, point2x-point1x)
    angle = math.degrees(angle)
    angle += 90
    if angle < 0:
        angle = 360 + angle
    distance = math.sqrt((point2x-point1x)**2 + (point2y-point1y)**2)

    midpoint = QPointF((point1x+point2x)/2,(point1y+point2y)/2)
    return int(angle), int(distance), midpoint

def drawGrid(scene,number,gap,origin):
    pen = QPen(QColor(255,255,255,127))
    pen.setWidthF(0.1)
    pen.setStyle(Qt.DashLine)
    
    #For horizontal lines:
    length = scene.width()
    startOffset = origin[1] - (gap*number/2)
    for i in range(0,number):
        line = QGraphicsLineItem(0,0,length,0)
        line.setPos(0,startOffset+(i*gap))
        line.setPen(pen)
        scene.addItem(line)
    
    #For vertical lines:
    length = scene.height()
    startOffset = origin[0] - (gap*number/2)
    for i in range(0,number):
        line = QGraphicsLineItem(0,0,0,length)
        line.setPos(startOffset+(i*gap),0)
        line.setPen(pen)
        scene.addItem(line)

def updateUsers(userTable, newUserList):
    
    for user in newUserList.getUsers():
        if user.deleteFlag: #Remove the user if they've been flagged as to delete. 
            if user.tableRow != None:
                userTable.removeRow(user.tableRow)
                user.tableRow = None
            newUserList.removeUser(user)
        else:
            if user.tableRow != None:
                userTable.item(user.tableRow, 0).setText(user.name)
                if user.flying:
                    userTable.item(user.tableRow, 1).setIcon(QIcon(":icons/airplane.png"))
                else:
                    userTable.item(user.tableRow, 1).setIcon(QIcon(":icons/home.png"))
                userTable.item(user.tableRow, 2).setText(str(user.getFlyingTime(True)))

                userTable.item(user.tableRow, 3).setText(str(user.iff+1))
                setTableCellColourFromIFF(userTable.item(user.tableRow, 3), user.iff)
                
            else:
                user.tableRow = userTable.rowCount()
                userTable.insertRow(user.tableRow)
                userTable.setItem(user.tableRow, 0, QTableWidgetItem(user.name))
                if user.flying:
                    userTable.setItem(user.tableRow, 1, QTableWidgetItem(QIcon(":icons/airplane.png"), ""))
                else:
                    userTable.setItem(user.tableRow, 1, QTableWidgetItem(QIcon(":icons/home.png"), ""))
                userTable.setItem(user.tableRow, 2, QTableWidgetItem(str(user.getFlyingTime(True))))
                userTable.setItem(user.tableRow, 3, QTableWidgetItem(str(user.iff+1)))
                setTableCellColourFromIFF(userTable.item(user.tableRow, 3), user.iff)

def setTableCellColourFromIFF(tableCell, iff):
    colours = [QColor(0,0,255), QColor(255,0,0), QColor(0,128,0), QColor(255,0,255)]
    tableCell.setBackground(colours[iff])

def updatePlanes(mainWindow, planes, navs):
    mapScene = mainWindow.mapScene
    tableWidget = mainWindow.tableWidget
    tempAircrafts = {}
    tempNavs = {}
    for id in planes:
        #Check if the plane is already in the list, first add the plane to a temp list
        
        tempAircrafts[id] = planes[id]

    for key in aircrafts.copy().keys():
        if key not in tempAircrafts.keys():
            #This plane has been removed from the list, so remove it from the map
            mapScene.removeItem(aircrafts[key].symbol)
            tableWidget.removeRow(aircrafts[key].tableRow)
            del aircrafts[key]
    for key in tempAircrafts.keys():
        if key not in aircrafts.keys():
            #This plane has been added to the list, so add it to the map
            aircrafts[key] = tempAircrafts[key]
            aircrafts[key].altitudeChange = 0
            plane = PlaneSymbol()
            plane.setPos(aircrafts[key].x,aircrafts[key].z)
            plane.change = 0
            plane.heading = aircrafts[key].getHeading()
            plane.speed = msToKnots(aircrafts[key].getSpeed()/3.6)
            plane.callsign = aircrafts[key].getCallsign()
            plane.altitude = round(aircrafts[key].getAltitude(),0)
            plane.username = aircrafts[key].username
            plane.parent = aircrafts[key]
            aircrafts[key].symbol = plane
            mapScene.addItem(plane)
            updateAircraftOnMap(mainWindow,aircrafts[key])
            currentRowCount = tableWidget.rowCount()
            tableWidget.insertRow(currentRowCount)
            tableWidget.setItem(currentRowCount,0,QTableWidgetItem(plane.callsign))
            tableWidget.setItem(currentRowCount,1,QTableWidgetItem("FL" +str(mToFL(plane.altitude))))
            tableWidget.setItem(currentRowCount,2,QTableWidgetItem(str(msToKnots(int(plane.speed)))))
            tableWidget.setItem(currentRowCount,3,QTableWidgetItem(str(plane.heading)))
            tableWidget.setItem(currentRowCount,4,QTableWidgetItem(str(key)))
            aircrafts[key].tableRow = currentRowCount


            

            
        else:
            #This plane is already in the list, so update it's position
            aircraft = aircrafts[key]
            aircraft.x = tempAircrafts[key].x
            aircraft.y = tempAircrafts[key].y
            aircraft.z = tempAircrafts[key].z
            
            aircraft.heading = tempAircrafts[key].getHeading()
            aircraft.horizontal_velocity = tempAircrafts[key].getSpeed()
            tempAlt = aircraft.altitude

            aircraft.altitude = round(tempAircrafts[key].getAltitude(),0)
            aircraft.altitudeChange = aircraft.altitude - tempAlt
            if aircraft.altitudeChange > 10:
                aircraft.altitudeChange = 1
            elif aircraft.altitudeChange < -10:
                aircraft.altitudeChange = -1
            else:
                aircraft.altitudeChange = 0

            #Check if the callsign has changed, if so update it
            tempCallsign = aircraft.symbol.callsign
            if tempCallsign != aircraft.callsign:
                aircraft.setCallsign(tempCallsign)

            if aircraft.callsign == "AI":
                aircraft.callsign = tempAircrafts[key].getCallsign()
            
            #Update the table:
            if tableWidget.item(aircraft.tableRow,0):
                tableWidget.item(aircraft.tableRow,0).setText(aircraft.callsign)
                tableWidget.item(aircraft.tableRow,1).setText("FL" +str(mToFL(aircraft.altitude)))
                tableWidget.item(aircraft.tableRow,2).setText(str(int(msToKnots(aircraft.horizontal_velocity/3.6))))
                tableWidget.item(aircraft.tableRow,3).setText(str(int(aircraft.heading)))
                tableWidget.item(aircraft.tableRow,4).setText(str(key))
            updateAircraftOnMap(mainWindow,aircraft)

        #Process Navs:
    for id in navs:
        #Check if the plane is already in the list, first add the plane to a temp list
        
        tempNavs[id] = navs[id]
    for key in navigationPoints.keys():
        if key not in tempNavs.keys():
            #This plane has been removed from the list, so remove it from the map
            mapScene.removeItem(navigationPoints[key]['symbol'])
            del navigationPoints[key]
    for key in tempNavs.keys():  
        if key not in navigationPoints.keys():
            #This plane has been added to the list, so add it to the map
            navigationPoints[key] = tempNavs[key]
            updateNav(mainWindow, navigationPoints[key])
            #Set the bbox from the nav points
            boundingRectangle = mapScene.itemsBoundingRect()
            boundingRectangle.setWidth(boundingRectangle.width()+100)
            boundingRectangle.setHeight(boundingRectangle.height()+100)
            mapScene.setSceneRect(boundingRectangle)
    
    mainWindow.mapWindow.fitInView()

def updateBasemap(mainWindow):
    fieldParser = mainWindow.fieldParser
    polygons, lines, points = fieldParser.getGeometry()
    regions = fieldParser.getRegions()
    
    for polygon in polygons:
        #First convert the points to a QPolygonF
        convertedPolygon = QPolygonF()
        for point in polygon.points:
            point = QPoint(int(point[0]), -int(point[1]))
            convertedPolygon.append(point)
        try:
            colour = QColor(int(polygon.colour[0]), int(polygon.colour[1]), int(polygon.colour[2]))
        except:
            colour = QColor(80,80,80)
        colour = colour.toHsv()
        h, s, v, a = colour.getHsv()
        colour.setHsv(int(h), int(s/3), int(v/3), int(a))
        pen = QPen(colour)
        brush = QBrush(colour)
        
        mainWindow.mapScene.addPolygon(convertedPolygon, pen, brush).setParentItem(mainWindow.basemapGroup)
        mainWindow.basemapGroup.update()
        

    #Add the lines to the map: TODO


    #Add the points to the map: TODO

    #Add the regions to the map:

    for region in regions:
        convertedPolygon = QPolygonF()
        for point in region.points:
            point = QPoint(int(point[0]), -int(point[1]))
            convertedPolygon.append(point)
            type = region.id
            if type == 1: #Runway
                colour = QBrush(QColor(255,255,255,255))        
                pen = QPen(QColor(255,255,255,255))
                pen.setWidth(5)
                pen.setStyle(Qt.SolidLine)
            elif id == 2:
                #Taxiway
                colour = QBrush(QColor(100,112,145,50))
                pen = QPen(QColor(100,112,145,50))
                pen.setWidth(1)
                pen.setStyle(Qt.SolidLine)
            else:
                colour = QBrush(QColor(0,60,60,50))
                pen = QPen(QColor(255,255,255,50))
                pen.setWidth(1)
                pen.setStyle(Qt.DashLine)
        
        mainWindow.mapScene.addPolygon(convertedPolygon, pen, colour).setParentItem(mainWindow.taxiwayGroup)
        mainWindow.taxiwayGroup.update()

    mainWindow.mapWindow.fitInView()
    mainWindow.flightDirector.incomingMessage("Map loaded")

def getGeoJSON(mainWindow, geometryType):
    fieldParser = mainWindow.fieldParser
    geoJSON = fieldParser.getGeoJSON(geometryType)
    return geoJSON

def updateAircraftOnMap(mainWindow, aircraft):
    aircraftSymbol  = aircraft.symbol
    aircraftSymbol.setPos(aircraft.x,aircraft.z)

    aircraftSymbol.heading = aircraft.heading
    aircraftSymbol.speed = msToKnots(aircraft.getSpeed()/3.6)
    aircraftSymbol.altitude = aircraft.getAltitude()
    aircraftSymbol.callsign = aircraft.getCallsign()
    aircraftSymbol.change = aircraft.altitudeChange
    aircraftSymbol.update()
    if aircraftSymbol.clicked:
        mainWindow.mapView.centerOn(aircraftSymbol)
        updateAircraftInfo(mainWindow.menuWindow,aircraftSymbol)
    mainWindow.mapScene.update()

def updateNav(mainWindow, nav):
    mapScene = mainWindow.mapScene
    navGroup = mainWindow.navGroup
    navSymbol = GroundSymbol()
    
    navSymbol.setPos(nav.x,nav.z)
    navSymbol.name = nav.name
    navSymbol.type = nav.type
    navSymbol.rotation = nav.rotation
         
    nav.symbol = navSymbol
    if nav.type == "ILS": # Classing LDAs as NDBs for now...
        if nav.type == "ILS":
            offset = -50
        else:
            offset = 0
        polygonLight = QPolygonF([QPointF(offset,0),QPointF(offset,9260),QPointF(-300,9260+100),QPointF(offset,0)])
        polygonDark = QPolygonF([QPointF(offset,0),QPointF(offset,9260),QPointF(250,9260+100),QPointF(offset,0)])
        transform = QTransform()
        transform.translate(nav.x,nav.z)
        transform.rotate(nav.rotation)
        

        polygonLight = transform.map(polygonLight)
        polygonDark = transform.map(polygonDark)

        mapScene.addPolygon(polygonLight,QPen(QColor(255,255,0,255),5)).setParentItem(navGroup)
        mapScene.addPolygon(polygonDark,QPen(QColor(255,255,0,255),5),QBrush(QColor(255,255,0,255))).setParentItem(navGroup)
    navSymbol.setParentItem(navGroup)
    #mapScene.addItem(navSymbol)
    navSymbol.update()

def updateAircraftInfo(aircraftInfoBox, aircraft):
    aircraftInfoBox.callsignLabel.setText(aircraft.callsign)
    aircraftInfoBox.usernameLabel.setText(aircraft.username)
    aircraftInfoBox.altitudeLabel.setText(str(round(aircraft.altitude,0))+ "m/ FL"+str(mToFL(aircraft.altitude)))
    aircraftInfoBox.speedLabel.setText(str(aircraft.speed)+"m/s/ "+str(msToKnots(aircraft.speed))+"kts")
    aircraftInfoBox.headingLabel.setText(str(aircraft.heading))

class QRadar(QApplication):

    def __init__(self,*args):
        super().__init__(*args)
        self.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        self.setWindowIcon(QIcon(":icons/qRadarLogo.ico"))
        qdarktheme.setup_theme()
        self.mainWindow = MainWindow()
        self.mainWindow.showMaximized()
        
        

if __name__ == "__main__":
    app = QRadar(sys.argv)
    sys.exit(app.exec_())


