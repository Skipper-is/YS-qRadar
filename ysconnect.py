import socket
import time
import struct
import select
import math
from datetime import timedelta
import FieldParser as fp
messageTypes = [
	"FSNETCMD_NULL",                   #   0
	"FSNETCMD_LOGON",                  #   1 Cli ->Svr",  (Svr->Cli for log-on complete acknowledgement.)
	"FSNETCMD_LOGOFF",                 #   2
	"FSNETCMD_ERROR",                  #   3
	"FSNETCMD_LOADFIELD",              #   4 Svr ->Cli",   Cli->Svr for read back
	"FSNETCMD_ADDOBJECT",              #   5 Svr ->Cli
	"FSNETCMD_READBACK",               #   6 Svr<->Cli
	"FSNETCMD_SMOKECOLOR",             #   7 Svr<->Cli
	"FSNETCMD_JOINREQUEST",            #   8 Svr<- Cli
	"FSNETCMD_JOINAPPROVAL",           #   9 Svr ->Cli
	"FSNETCMD_REJECTJOINREQ",          #  10
	"FSNETCMD_AIRPLANESTATE",          #  11 Svr<->Cli   # Be careful in FsDeleteOldStatePacket when modify
	"FSNETCMD_UNJOIN",                 #  12 Svr<- Cli
	"FSNETCMD_REMOVEAIRPLANE",         #  13 Svr<->Cli
	"FSNETCMD_REQUESTTESTAIRPLANE",    #  14
	"FSNETCMD_KILLSERVER",             #  15 Svr<- Cli
	"FSNETCMD_PREPARESIMULATION",      #  16 Svr ->Cli
	"FSNETCMD_TESTPACKET",             #  17
	"FSNETCMD_LOCKON",                 #  18 Svr<->Cli
	"FSNETCMD_REMOVEGROUND",           #  19 Svr<->Cli
	"FSNETCMD_MISSILELAUNCH",          #  20 Svr<->Cli   # fsweapon.cpp is responsible for encoding/decoding
	"FSNETCMD_GROUNDSTATE",            #  21 Svr<->Cli   # Be careful in FsDeleteOldStatePacket when modify
	"FSNETCMD_GETDAMAGE",              #  22 Svr<->Cli
	"FSNETCMD_GNDTURRETSTATE",         #  23 Svr<->Cli
	"FSNETCMD_SETTESTAUTOPILOT",       #  24 Svr ->Cli
	"FSNETCMD_REQTOBESIDEWINDOWOFSVR", #  25 Svr<- Cli
	"FSNETCMD_ASSIGNSIDEWINDOW",       #  26 Svr ->Cli
	"FSNETCMD_RESENDAIRREQUEST",       #  27 Svr<- Cli
	"FSNETCMD_RESENDGNDREQUEST",       #  28 Svr<- Cli
	"FSNETCMD_VERSIONNOTIFY",          #  29 Svr ->Cli
	"FSNETCMD_AIRCMD",                 #  30 Svr<->Cli   # After 2001/06/24
	"FSNETCMD_USEMISSILE",             #  31 Svr ->Cli   # After 2001/06/24
	"FSNETCMD_TEXTMESSAGE",            #  32 Svr<->Cli
	"FSNETCMD_ENVIRONMENT",            #  33 Svr<->Cli  (*1)
	"FSNETCMD_NEEDRESENDJOINAPPROVAL", #  34 Svr<- Cli
	"FSNETCMD_REVIVEGROUND",           #  35 Svr ->Cli   # After 2004
	"FSNETCMD_WEAPONCONFIG",           #  36 Svr<->Cli   # After 20040618
	"FSNETCMD_LISTUSER",               #  37 Svr<->Cli   # After 20040726
	"FSNETCMD_QUERYAIRSTATE",          #  38 Cli ->Svr   # After 20050207
	"FSNETCMD_USEUNGUIDEDWEAPON",      #  39 Svr ->Cli   # After 20050323
	"FSNETCMD_AIRTURRETSTATE",         #  40 Svr<->Cli   # After 20050701
	"FSNETCMD_CTRLSHOWUSERNAME",       #  41 Svr ->Cli   # After 20050914
	"FSNETCMD_CONFIRMEXISTENCE",       #  42 Not Used
	"FSNETCMD_CONFIGSTRING",           #  43 Svr ->Cli   # After 20060514    Cli->Svr for read back
	"FSNETCMD_LIST",                   #  44 Svr ->Cli   # After 20060514    Cli->Svr for read back
	"FSNETCMD_GNDCMD",                 #  45 Svr<->Cli
	"FSNETCMD_REPORTSCORE",            #  46 Svr -> Cli  # After 20100630    (Older version will ignore)
	"FSNETCMD_SERVER_FORCE_JOIN",      #  47 Svr -> Cli
	"FSNETCMD_FOGCOLOR",               #  48 Svr -> Cli
	"FSNETCMD_SKYCOLOR",               #  49 Svr -> Cli
	"FSNETCMD_GNDCOLOR",               #  50 Svr -> Cli
	"FSNETCMD_RESERVED_FOR_LIGHTCOLOR",#  51 Svr -> Cli
	"FSNETCMD_RESERVED21",             #  52
	"FSNETCMD_RESERVED22",             #  53
	"FSNETCMD_RESERVED23",             #  54
	"FSNETCMD_RESERVED24",             #  55
	"FSNETCMD_RESERVED25",             #  56
	"FSNETCMD_RESERVED26",             #  57
	"FSNETCMD_RESERVED27",             #  58
	"FSNETCMD_RESERVED28",             #  59
	"FSNETCMD_RESERVED29",             #  60
	"FSNETCMD_RESERVED30",             #  61
	"FSNETCMD_RESERVED31",             #  62
	"FSNETCMD_RESERVED32",             #  63
	"FSNETCMD_OPENYSF_RESERVED33",     #  64 Reserved for OpenYSF
	"FSNETCMD_OPENYSF_RESERVED34",     #  65 Reserved for OpenYSF
	"FSNETCMD_OPENYSF_RESERVED35",     #  66 Reserved for OpenYSF
	"FSNETCMD_OPENYSF_RESERVED36",     #  67 Reserved for OpenYSF
	"FSNETCMD_OPENYSF_RESERVED37",     #  68 Reserved for OpenYSF
	"FSNETCMD_OPENYSF_RESERVED38",     #  69 Reserved for OpenYSF
	"FSNETCMD_OPENYSF_RESERVED39",     #  70 Reserved for OpenYSF
	"FSNETCMD_OPENYSF_RESERVED40",     #  71 Reserved for OpenYSF
	"FSNETCMD_OPENYSF_RESERVED41",     #  72 Reserved for OpenYSF
	"FSNETCMD_OPENYSF_RESERVED42",     #  73 Reserved for OpenYSF
	"FSNETCMD_RESERVED43",             #  74
	"FSNETCMD_RESERVED44",             #  75
	"FSNETCMD_RESERVED45",             #  76
	"FSNETCMD_RESERVED46",             #  77
	"FSNETCMD_RESERVED47",             #  78
	"FSNETCMD_RESERVED48",             #  79
	"FSNETCMD_RESERVED49",             #  80
	"FSNETCMD_NOP"
]

readbacks = ["FSNETREADBACK_ADDAIRPLANE",
	"FSNETREADBACK_ADDGROUND",
	"FSNETREADBACK_REMOVEAIRPLANE",
	"FSNETREADBACK_REMOVEGROUND",
	"FSNETREADBACK_ENVIRONMENT",
	"FSNETREADBACK_JOINREQUEST",
	"FSNETREADBACK_JOINAPPROVAL",
	"FSNETREADBACK_PREPARE",
	"FSNETREADBACK____UNUSED____",
	"FSNETREADBACK_USEMISSILE",
	"FSNETREADBACK_USEUNGUIDEDWEAPON",
	"FSNETREADBACK_CTRLSHOWUSERNAME"]

navTypes = ["ILS", "VORDME","NDB"]

def returnYSMessage(connection):
    try:
        size = struct.unpack("I", connection.recv(4))[0]
        typ = struct.unpack("I", connection.recv(4))[0]
    except:
        return (0,0,'')
    
    if size >4:
        data = connection.recv(size-4)
        return (size, typ, data)
    else:
        return (size, typ,'')

def acknowledge(connection,int_1=9, int_2=0):
    ack = struct.pack("IIiI",12,6,int_1,int_2)

    connection.send(ack)
    
def sendMessage(connection,typ,message,struct_pattern):
    if type(message) == str:
        length = len(message) + 4
        struct_pattern = struct_pattern.replace("s",str(len(message)+"s"))
    elif type(message)== int:
        length = 8
    else:
        length = len(message)+4
    if message == "": # If it is a message with no data, such as the environment send, we just create an empty message with length 4, and the type
        length = 4
        msg = struct.pack('II',length, typ)
    else:
        msg = struct.pack(struct_pattern,length, typ,message)
    connection.send(msg)

def sendRaw(connection,message):
    connection.send(message)

def replySame(connection, message):
    length = message[0]
    typ = message[1]
    data = message[2]
    msg = struct.pack("I",length)+struct.pack("I",typ)+data
    sendRaw(connection,msg)

def parseFlightData(message):
    try:
        timer = struct.unpack("I",message[0:4])[0]
        id = struct.unpack("I",message[4:8])[0]
        info1 = struct.unpack("h",message[8:10])[0]
        if info1 == 3:
            #2 octets of padding after info1, remove these
            message = message[:8] + message[10:]
            
        x = struct.unpack("f",message[10:14])[0]
        y = struct.unpack("f",message[14:18])[0]
        z = -struct.unpack("f",message[18:22])[0]
        yaw = struct.unpack("h",message[22:24])[0]
        
        pitch = struct.unpack("h",message[24:26])[0]
        roll = struct.unpack("h",message[26:28])[0]
        xspeed = struct.unpack("h",message[28:30])[0]
        ySpeed = struct.unpack("h",message[30:32])[0]
        zSpeed = struct.unpack("h",message[32:34])[0]
        fuel = struct.unpack("h",message[50:52])[0]
        return {"timer":timer,"id":id,"info1":info1,"x":x,"z":z,"y":y,"yaw":-yaw,"pitch":pitch,"roll":roll,"xspeed":xspeed,"ySpeed":ySpeed,"zSpeed":zSpeed,"fuel":fuel}
    except:
        return {"timer":0,"id":0,"info1":0,"x":0,"z":0,"y":0,"yaw":0,"pitch":0,"roll":0,"xspeed":0,"ySpeed":0,"zSpeed":0,"fuel":0}

def parseUser(message):
    try:
        length = str(len(message)-12)+"c"
        if len(message) < 8:
            return None
        type = struct.unpack("h",message[0:2])[0]
        iff = struct.unpack("h",message[2:4])[0]
        id = struct.unpack("i",message[4:8])[0]
        name = message[12:-1].decode()
        return {"name":name,"id":id,"type":type,"iff":iff}
    except:
        return {"name":None,"id":0,"type":0,"iff":0}

def parseGroundObject(message):
    if len(message) < 36:
        return None
    type = struct.unpack("i",message[0:4])[0] # Type of object, 65537 is ground objects
    id = struct.unpack("i",message[4:8])[0] # ID of the object
    iff = struct.unpack("i",message[8:12])[0] # IFF of the object
    x = struct.unpack("f",message[12:16])[0] # X position of the object
    y = struct.unpack("f",message[16:20])[0] # Y position of the object
    z = struct.unpack("f",message[20:24])[0] # Z position of the object
    yaw = struct.unpack("f",message[24:28])[0] # Yaw of the object
    pitch = struct.unpack("f",message[28:32])[0] # Pitch of the object
    roll = struct.unpack("f",message[32:36])[0] # Roll of the object
    try:
        name = struct.unpack("64s",message[36:100])[0] # Name of the object (This is the name from the .dat)
        name = name.replace(b'\x00', b'')   # Remove the null bytes from the string
        name= name.decode()
    except:
        name = 'unknown'
    
    length = len(message)
    try:
        name2 = struct.unpack("56s",message[length-57:-1])[0] # Name of the object (This is the name set in scenery editor, of the nav point for example)
        name2 = name2.replace(b'\x00', b'')
        name2 = name2.decode()
    except:
        name2 = 'unknown'
    return {"type":type,"id":id,"iff":iff,"x":x,"y":y,"z":z,"yaw":yaw,"pitch":pitch,"roll":roll,"name":name,"name2":name2}

def createRadarPoints(ground_object):
    radarPoint = {}
    if type(ground_object) == type(None):
        return None #If it's empty, return nothing
    if ground_object["type"] == 65537: #Check it is actually a ground object
        if ground_object["name"] in navTypes: #It is a type of nav point, you can add more at the top in the declaration
            radarPoint['id'] = ground_object["id"] # Set the ID of the point
            radarPoint["type"] = ground_object["name"] # Set the type of point as the original name, so ILS, VORDME etc
            radarPoint["name"] = ground_object["name2"] # The name is then set to the name of the nav point - eg HILO
            radarPoint["x"] = ground_object["x"] #Positions....
            radarPoint["y"] = ground_object["y"]
            radarPoint["z"] = -ground_object["z"]
            rawRotation = ground_object["yaw"]*180/math.pi # It's in radians, so convert to degrees (we may regret this when it comes time to plot it out on the screen.... we'll see)
            radarPoint["rotation"] = 180 +- rawRotation # The rotation in heading degrees. 
            return radarPoint
    else:
        return None # If it's not a ground object, don't return anything

def createLogin(username, conversion):
    username=username+"\x00"*(15-len(username))
    if len(username)>15:
        print("Too Long!")
    user_struct = struct.pack("16sI",username.encode(),conversion)
    mesg_type = 1
    length = len(user_struct)+4
    login = struct.pack("II16sI",length,mesg_type,username.encode(),conversion)
    return login

def ysRotationToDegreesFromNorth(rotation):
    #Rotation in YS starts at 0 for north, but goes 180 for south, 90 for east, and -90 for west.
    #This function converts the YS rotation to degrees from north.
    try:
        rotation = int(rotation)
    except:
        rotation = 0

    if rotation < 0:
        return 360- abs(rotation)
    else:
        return rotation

class YSConnect:
    def __init__(self, callback=None):
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.inputs = [self.sock]
        self.outputs = [self.sock]
        self.message_queues = {}
        self.navPoints = {}
        self.userList = UserList()
        self.planeList = {}
        self.connected = False
        self.lastStayAlive = time.time()
        self.callback = callback
        self.map = None
    
    def connect(self, host, port=7915, username="radar", version=20180930):
        self.username = createLogin(username, version)
        self.host = host
        self.port = port
        try: 
            self.sock.connect((self.host, self.port))
        except socket.error as msg:
            print("Connection Failed")
            self.callback("Connection Failed, have you used the correct address?")
            return False
        except:
            print("Connection Failed")
            self.callback("Connection Failed, have you used the correct port?")
            return False
        self.connection()
        return True

    def connection(self):

        self.sock.send(self.username)
        
        while self.inputs:
            readable, writable, exceptional = select.select(self.inputs, self.outputs, self.inputs)
            for s in readable:
                if s is self.sock:
                    s = self.sock
                    if self.connected:
                        currentTime = time.time()
                        if currentTime - self.lastStayAlive > 5:
                            self.stayAlive()
                            self.lastStayAlive = currentTime
                    else:
                        pass
                    try:
                        message = returnYSMessage(s)
                        mesgType = messageTypes[message[1]]
                    except:
                        mesgType = "NULL"
                    if mesgType == "FSNETCMD_VERSIONNOTIFY":
                        acknowledge(s,9)
                        self.callback("Verifying version")

                    elif mesgType == "FSNETCMD_USEMISSILE":
                        acknowledge(s,readbacks.index("FSNETREADBACK_USEMISSILE"))
                        self.callback("Verifying missile usage")

                    elif mesgType == "FSNETCMD_CTRLSHOWUSERNAME":
                        acknowledge(s,readbacks.index("FSNETREADBACK_CTRLSHOWUSERNAME"))
                        self.callback("Verifying username display")

                    elif mesgType == "FSNETCMD_USEUNGUIDEDWEAPON":
                        acknowledge(s,readbacks.index("FSNETREADBACK_USEUNGUIDEDWEAPON"))
                        self.callback("Verifying unguided weapon usage")
                        
                    elif mesgType == "FSNETCMD_LOADFIELD":
                        replySame(s,message)
                        length = 4
                        typ = messageTypes.index("FSNETCMD_ENVIRONMENT")

                        try:
                            self.map = message[2].split(b'\x00')[0].decode()
                        except:
                            self.map = "Unknown"
                        self.callback("Verifying map")
                        self.callback(["MAP",self.map])
                    
                    elif mesgType == "FSNETCMD_CONFIGSTRING":
                        msg_length = len(message[2])
                        sendMessage(s,message[1],message[2],"II"+ str(msg_length) + "s")
                        self.callback("Verifying config")

                    elif mesgType == "FSNETCMD_LIST":
                        msg_length = len(message[2])
                        sendMessage(s,message[1],message[2],"iI"+str(msg_length) + "s")
                        self.callback("Verifying aircraft list")
                        
                    elif mesgType == "FSNETCMD_PREPARESIMULATION":
                        acknowledge(s,readbacks.index("FSNETREADBACK_PREPARE"))
                        sendMessage(s,messageTypes.index("FSNETCMD_QUERYAIRSTATE"),0,"III")
                        self.connected = True
                        sendMessage(self.sock,37,0,"III") # Get users
                        self.callback("Logged in!")
                        
                    elif mesgType == "FSNETCMD_ENVIRONMENT":
                        acknowledge(s,readbacks.index("FSNETREADBACK_ENVIRONMENT"))
                        self.callback("Verifying environment")
                    
                    elif mesgType == "FSNETCMD_LOGON":
                        #Sometimes this is called, sometimes not... Very weird.
                        # Seems to be mainly not called on OpenYS, and ocasionally on 2015xxxx. Have moved the code to prepare, as
                        sendMessage(s,messageTypes.index("FSNETCMD_QUERYAIRSTATE"),0,"III")
                        self.connected = True
                        sendMessage(self.sock,37,0,"III") # Get users
                        self.callback("Logged in!")
                    
                    elif mesgType == "FSNETCMD_LISTUSER":
                        user = parseUser(message[2])
                        if user['name'] != None:
                            if type(user['name']) != str : #Could be encoded... Had one or two that were, not all. Weird. maybe if they've got non ascii chars?
                                user['name'] = user['name'].decode()
                            tempUser = User(user)
                            #If it's a valid user, check it's on the list:
                            if self.userList.getUserByName(user['name']):
                                if not self.userList.updateUser(tempUser): # Update it, and if it failed, add it
                                    self.userList.addUser(tempUser)
                            else: # If it's not on the list, add it.
                                self.userList.addUser(tempUser)
                    
                    elif mesgType == "FSNETCMD_ADDOBJECT":
                        groundObject = parseGroundObject(message[2])
                        radarPoint = createRadarPoints(groundObject)
                        if radarPoint != None:
                            self.navPoints[radarPoint["id"]] = NavPoint(radarPoint)

                    elif mesgType == "FSNETCMD_AIRPLANESTATE":
                        data = parseFlightData(message[2])
                        userid = data['id']
                        user = self.userList.getUserByID(userid)
                        if user:
                            username = user.name
                        else:
                            username = "AI"
                            user = User()

                        velocity = math.sqrt((data['xspeed']/10)**2 + (data['ySpeed']/10)**2 + (data['zSpeed']/10)**2)*1.94384
                        horizontal_velocity = math.sqrt((data['xspeed']/10)**2 + (data['zSpeed']/10)**2)*1.94384
                        if data['zSpeed'] == 0 or data['xspeed'] == 0:
                            heading = 0
                        else:

                            heading = math.atan2(data['xspeed']/10,data['zSpeed']/10)*180/math.pi
                        data['heading'] = heading
                        data['velocity'] = velocity
                        data['horizontal_velocity'] = horizontal_velocity
                        data['username'] = username
                        
                        flight = FlightData(data,user)
                        
                        if flight.id != 0:
                            self.planeList[flight.id] = flight
                    
                    elif mesgType == "FSNETCMD_REMOVEAIRPLANE":
                        id = struct.unpack("I",message[2][0:4])[0]
                        
                        try:
                            del self.planeList[id]
                            del self.userList[id]
                        except:
                            pass

                    elif mesgType == "FSNETCMD_REJECTJOINREQ":
                        print("Rejected")
                    
                    elif mesgType == "FSNETCMD_TEXTMESSAGE":
                        self.callback("Chat: " + message[2].decode())

    def disconnect(self):
        self.sock.close()
        self.connected = False
        print("Disconnected")

    def getPlanes(self):
        return self.planeList
    
    def getNavPoints(self):
        return self.navPoints
    
    def stayAlive(self):
        message =struct.pack("II",4,messageTypes.index("FSNETCMD_LISTUSER"))
        self.notFlyingUsers = [] # Clear the userlist, as we'll get a new one in a second
        self.sock.send(message)

    def getUsers(self):
        return self.userList
    
    def sendMessage(self,message):
        if self.connected:
            message = message.encode()
            message = struct.pack("II",len(message)+13,messageTypes.index("FSNETCMD_TEXTMESSAGE")) + struct.pack("II",0,0) + message + b'\x00'
            self.sock.send(message)


class UserList:
    def __init__(self):
        self.users = []
        self.timeout = 15
    
    def __str__(self):
        return str(self.users)
    
    def addUser(self, user):
        self.users.append(user)

    
    def removeUser(self, user):
        self.users.remove(user)
    
    def getUserByID(self, id):
        for user in self.users:
            if user.id == id:
                return user
        return None
    
    def getUserByName(self, name):
        for user in self.users:
            if user.name == name:
                return user
        return None

    def getUsers(self):
        self.checkUsersAge()
        return self.users
    
    def updateUser(self, user):
        for i in range(len(self.users)):
            if self.users[i].name == user.name:
                self.users[i].setFlying(user.type) # Gets a special one
                self.users[i].iff = user.iff
                self.users[i].id = user.id
                self.users[i].seen()
                
                return True
        return False
    
    def checkUsersAge(self):
        for user in self.users:
            if time.time() - user.lastSeenTime > self.timeout:
                user.deleteFlag = True


class User:
    def __init__(self, data={"name":"AI","id":0,"type":0,"iff":0}):
        self.name = data["name"]
        self.id = data["id"]
        self.type = data["type"]
        self.iff = data["iff"]
        self.flying = False
        self.flyingStart = 0
        self.flyingTime= 0
        self.setFlying(self.type) # Do the initial setup     
        self.tableRow = None
        self.lastSeenTime = time.time()
        self.deleteFlag = False
    
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return self.name
    
    def getName(self):
        return self.name
    
    def getID(self):
        return self.id
    
    def seen(self):
        self.lastSeenTime = time.time()
    
    def userType(self):
        if self.type == 0 or self.type == 1:
            return "Client"
        else:
            return "Server"
    
    def getFlying(self):
        return self.flying
    
    def getIFF(self):
        return self.iff
    
    def setIFF(self, iff):
        self.iff = iff
    
    def setID(self, id):
        self.id = id
    
    def setName(self, name):
        self.name = name
    
    def setFlying(self, type):
        if self.type != type:
            #It's changed.
            self.type = type
            if type == 1 or type == 3: # It's changed from not flying, to flying, start the clock
                self.flyingStart = time.time()
                self.flying = True
            else:
                self.flyingTime += time.time() - self.flyingStart # It's changed from flying to not flying, stop the clock, increment the time
                self.flying = False
        else:
            if type == 1 or type == 3:
                self.flying = True
                if self.flyingStart == 0:
                    self.flyingStart = time.time()
            else:
                self.flying = False       
    
    def isFlying(self):
        if self.type == 1 or self.type == 3:
            return True
        else:
            return False
    
    def getFlyingTime(self,formatted=False):
        if self.isFlying():
            if formatted:
                return str(timedelta(seconds=int(self.flyingTime + (time.time() - self.flyingStart))))
            else:
                return self.flyingTime + (time.time() - self.flyingStart)
        else:
            if formatted:
                return str(timedelta(seconds=int(self.flyingTime)))
            else:
                return self.flyingTime


class FlightData:
    def __init__(self, data, user=None):
        #return {"timer":timer,"id":id,"info1":info1,"x":x,"z":z,"y":y,"yaw":yaw,"pitch":pitch,"roll":roll,"xspeed":xspeed,"ySpeed":ySpeed,"zSpeed":zSpeed,"fuel":fuel} + the extra bits added
        self.username = data["username"]
        self.id = data["id"]
        self.x = data["x"]
        self.y = data["y"] # Should be altitude
        
        self.z = data["z"]
        self.heading = data["heading"]
        self.velocity = data["velocity"]
        self.horizontal_velocity = data["horizontal_velocity"]
        self.username = data["username"]
        self.user = user
        #Don't care about the rest for now, but add them for future
        self.startTime = time.time()
        self.yaw = data["yaw"]
        self.pitch = data["pitch"]
        self.roll = data["roll"]
        self.xspeed = data["xspeed"]
        self.ySpeed = data["ySpeed"]
        self.zSpeed = data["zSpeed"]
        self.fuel = data["fuel"]
        self.callsign= None
        self.altitude = self.getAltitude()
    
    def getPosition(self):
        return (self.x,self.y,self.z)
    
    def getSpeed(self):
        return self.horizontal_velocity

    def getHeading(self):
        
        return ysRotationToDegreesFromNorth(fp.uuToDegrees(self.yaw))
    
    def getAltitude(self):
        return self.y
    
    def setCallsign(self, callsign):
        self.callsign = callsign

    def getCallsign(self):
        if self.callsign != None:
            return self.callsign
        else:
            return self.username

    def getFlightTime(self):
        return time.time() - self.startTime

class NavPoint:
    def __init__(self, data):
        self.id = data["id"]
        self.type = data["type"]
        self.name = data["name"]
        self.x = data["x"]
        self.y = data["y"]
        self.z = data["z"]
        self.rotation = data["rotation"]
    
    def getPosition(self):
        return(self.x,self.z)

        