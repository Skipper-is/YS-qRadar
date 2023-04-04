import numpy as np
import geojson
import json
from math import floor
import os
#These are the various geometries that can be found in the FLD files.
#PST = Points - Each vertex is a point
#PLL = Polyline - Each vertex is a point
#LSQ = Line sequence - paired points make a line. 
#PLG = Polygon - 3+ vertexes make a polygon
#PLG with 4 vertecies = rectangle
#APL = Approach light = Each point is a light, taken as points
#GQS = Graduated quadstrip - can't figure them out...
#QST = Quadstrip - Two triangles per 4, (1,2,3) (2,3,4) (3,4,5) as a formula is x-1, x, x+1, 
#TRI = Triangles, same as quadrangles, but with 3.
#QDR  = Quadrangles - split into 4 vertexes each. 4 vertexes = 1 polygon - Used for centre lines as well.



class Field():
    """.FLD object. Contains all the data for a field, and all the child fields, and all the child pc2s.
    :param name: The name of the field
    :param data: The data of the field
    :param position: The position of the field
    :param childFlds: The child fields of the field
    :param childPcs: The child pc2s of the field
    :param regions: The regions of the field
    :param parent: The parent of the field
    
    Initialised with None for all values, and then parsed with the parse function. parse(data) will return the object, and set all the values.
    The data is a list of strings, where each string is a line from the FLD file.
    
    The getRegions function will return a list of all the regions in the field, and all the child fields, and all the child pc2s."""
    def __init__(self):
        self.file = None
        self.name = None
        self.data = None
        self.position = (0,0,0,0,0,0)
        self.highestPck = 0
        self.childFlds = []
        self.childPcs = []
        self.regions = []
        self.positions = []
        self.parent = None

    def parse(self, data):
        data = [s.strip() for s in data]
        
        self.data = data
        self.getPositions(data)
        #Iterate through each row, and find the packages
        for row, line in enumerate(data):
            #Check for packages
            if line.startswith("PCK"):
                #It's a Package
                
                #Get the children of the parent first, they'll go off to be their own thing, and whatever is left will be regions and pc2s for this field. 
                if row > self.highestPck:
                    #It's outside of the previous package, so it must be a child of this parent, not a sub-child.
                    #Therefore, we'll get all the details for this package, and then move on to the next one.

                    package_name = line.split(" ")[1].replace('"', '')
                    if package_name != None:
                        #Get the position from the list of positions:
                        position = next((x for x in self.positions if x["name"] == package_name), None)
                    package_lenght = int(line.split(" ")[2])
                    package_end = row + package_lenght
                    
                    if ".FLD" in line.upper():
                        #Its a child field
                        
                        childField = Field().parse(data[row+1:package_end])
                        childField.name = package_name
                        childField.parent = self
                        if position != None:
                            childField.position = position['position']
                        self.childFlds.append(childField)
                        self.highestPck = package_end # Set the end package as the end of this FLD, so the next one will not be a child of this child. Too many children! Need another name for them!
                        
                    if ".PC2" in line.upper():
                        #Its a child pc

                        childPc = Pc2()
                        childPc.parse(data[row+1:package_end])
                        childPc.name = package_name
                        if position != None:
                            childPc.position = position['position']
                        self.childPcs.append(childPc) # We're adding all the pc2s, but at the end we need to filter out the ones that are also in child FLDs. 
                    if "TER" in line.upper():
                        pass 
                        #It's a terrain file - not going to process them at the moment.

                    
        #Iterate through the bits left after the packages are taken off, and find the regions that belong to this field
        for row, line in enumerate(data[self.highestPck:]):
            if line.startswith("RGN"):
                #It's a region
                #Get the next END from that point:
                try:
                    endIndex = data[self.highestPck+row:].index("END")
                except ValueError:
                    endIndex = len(data)-1
                #Get the data between the start, and the END
                regionData = data[self.highestPck+row:self.highestPck+row+endIndex]
                # Create a new region from the data
                region = Region().parse(regionData)
                self.regions.append(region)
        
        
        return self
    
    def getRegions(self):
        returnRegions = self.regions
        for children in self.childFlds:
            tempRegions = children.getRegions()
            if self.name != None:
                print("Parent: " +self.name)
            print("Child: " +children.name)
            print(len(tempRegions))
            for number in range(len(tempRegions)):
                tempRegions[number] = transformGeometry(tempRegions[number], children.position)
                if self.position != None:
                    tempRegions[number] = transformGeometry(tempRegions[number], self.position)
            if tempRegions != []: # This is probably defunct, as it'll just add an empty list to the list.
                returnRegions = returnRegions + tempRegions
        return returnRegions
            

    def getPositions(self,data):
        for row, line in enumerate(data):
            if line.startswith("FIL"):
                #FIL "00000006.pc2"
                # POS -593.03 0.00 384.90 0.00 0.00 0.00
                # ID 0
                # END
                #File position definition
                #Get the next END from that point:
                fileName = line.split(" ")[1].replace('"', '')

                try:
                    endIndex = data[row:].index("END")
                except ValueError:
                    endIndex = len(data)-1
                #Get the data between the start, and the END
                fileData = data[row:row+endIndex]
                #Get the file name
                
                #Get the position
                position = None
                for fil in fileData:

                    if fil.startswith("POS"):
                        position = getPosition(fil)
                #Check to see if the filename is in the data as a package, otherwise, it's an auxilary file, so we'll need to add that in as a childfld, but load the file.
                filenamePackage = 'PCK "' + fileName + '"'
                if filenamePackage in data:
                    pass # It's all good, the package is within the data, so we can move on. 
                else:
                    #It's an auxilary file, so we'll need to add it to the childFlds or childPcs (or it could be under a child fld. If it is, this won't add anything on, so all good in the hood.)
                    #Check to see if it's a pc2 or a fld
                    if fileName.endswith(".pc2"):
                        #It's a child pc
                        childScenery = Pc2()
                        childScenery.name = fileName
                        childScenery.position = position
                        
                    else:
                        #It's a child field
                        childScenery = Field()
                        childScenery.name = fileName
                        childScenery.position = position
                    if self.file:
                        try:
                            filePath = os.path.dirname(self.file)
                            file = open(filePath + '/'+fileName, "r")
                            childScenery.parse(file.readlines())
                            file.close()
                            
                        except:
                            pass
                    
                    if type(childScenery) == Field:
                        self.childFlds.append(childScenery)
                    if type(childScenery) == Pc2:
                        self.childPcs.append(childScenery)
                #Add the position to the list of positions
                self.positions.append({"name": fileName, "position": position})


    def getChildNames(self, type):
        #Gets all the names of the children of this object
        returnNames = {}
        if type == "pc2":
            for id, children in enumerate(self.childPcs):
                returnNames[id] = children
        if type == "fld":
            for id, children in enumerate(self.childFlds):
                returnNames[id] = children
        return returnNames
    
    def getAllChildNames(self, type):
        #This will cascade down through the FLDs or PC2s, and get all the names of the children. Useful for showing the heirarchy of the objects.
        returnNames = {}
        if type == "pc2":
            for children in self.childPcs:
                #returnNames.append(children.name) # We'll leave off own name, as we'll be checking for duplicates in the parent.
                childrensChildren = children.getAllChildNames(type)
                if childrensChildren != {}:
                    returnNames[children.name] = childrensChildren
                else:
                    returnNames[children.name]= children.getChildNames(type)
        
        if type == "fld":
            for children in self.childFlds:
                childrensChildren = children.getAllChildNames(type)
                if childrensChildren != {}:
                    returnNames[children] = childrensChildren
                else:
                    returnNames[children]= children.getChildNames(type)
        return returnNames



class Pc2():
    def __init__(self):
        self.name = None
        self.data = None
        self.position = None
        self.children = []

    def parse(self, data):
        #Get the geometry from the pc2, and add to the children
        self.data = data
        for row, line in enumerate(data):
            #Get the geometry type
            if line.startswith("PST") or line.startswith("APL"):
                #It's a point, now we need to find the next ENDO
                endIndex = data[row:].index("ENDO")
                #Get the data between the start, and the ENDO
                pointData = data[row:row+endIndex]
                # Create a new point from the data
                point = Point().parse(pointData)
                self.children.append(point)
            
            if line.startswith("PLL"):
                #It's a line, now we need to find the next ENDO
                endIndex = data[row:].index("ENDO")
                #Get the data between the start, and the ENDO
                lineData = data[row:row+endIndex]
                # Create a new line from the data
                lineObj = Line().parse(lineData, False)
                self.children.append(lineObj)
            
            if line.startswith("PLG"):
                #It's a polygon, now we need to find the next ENDO
                
                endIndex = data[row:].index("ENDO")
                
                #Get the data between the start, and the ENDO
                polygonData = data[row:row+endIndex]
                # Create a new polygon from the data
                polygon = Polygon().parse(polygonData)
                # Add it to the list
                self.children.append(polygon)
            
            if line.startswith("LSQ"):
                #It's a line sequence, haven't implemented this yet
                endIndex = data[row:].index("ENDO")
                #Get the data between the start, and the ENDO
                lineSequenceData = data[row:row+endIndex]
                lineSequence = Line().parse(lineSequenceData, "LSQ")
                self.children.append(lineSequence)

            if line.startswith("QST") or line.startswith("GQS"):
                #Oh quad strips, you're so complicated
                #Find the next endo...
                endIndex = data[row:].index("ENDO")
                #Get the data between the start, and the ENDO
                quadStripData = data[row:row+endIndex]
                #Create a polygon, and add it to the children
                polygon = Polygon().parse(quadStripData, "QST")
                #Quads are converted to polygons, so we pass the polygon/qst and the parent to the function, and it'll add it as a child
                quadStripToPolygon(polygon, self)
                
            
            if line.startswith("TRI"):
                #It's a triangle
                endIndex = data[row:].index("ENDO")
                #Get the data between the start, and the ENDO
                triangleData = data[row:row+endIndex]
                #Create a polygon, and add it to the children
                polygon = Polygon().parse(triangleData,"TRI")
                #Same as QSTs really
                triangleToPolygon(polygon,self)
                
            
            if line.startswith("QDR"):
                #It's a quadrangle
                endIndex = data[row:].index("ENDO")
                #Get the data between the start, and the ENDO
                quadrangleData = data[row:row+endIndex]
                #Create a polygon, and add it to the children
                polygon = Polygon().parse(quadrangleData,"QDR")
                #Same as QSTs really
                quadrilateralToPolygon(polygon,self)
                
            
            else:
                
                pass
        return self
    

#The main geometry types we're going to use
class Polygon():
    def __init__(self):
        self.data = None
        self.type = None
    
    def parse(self, data, type = "POLY"):
        self.data = data
        self.type = type
        self.colour = colToColourTuple(data[1])
        self.points = getGeometryfromFeature(data)
        return self

    def getGeoJSON(self):
        #Returns an uncorrected geojson object. The position of this object is relative to the field it is in, not the world.
        #This can be called once everything has been reprojected using the returnFields function.
        polygon = geojson.Polygon([self.points])
        feature = geojson.Feature(geometry=polygon, properties={"type": self.type, "colour": self.colour})
        return feature

class Line():
    def __init__(self):
        self.data = None
        self.type = None
    
    def parse(self, data, type = "LIN"):
        self.data = data
        self.type = type
        self.colour = colToColourTuple(data[1])
        self.points = getGeometryfromFeature(data)
        return self
    
    def getGeoJSON(self):
        #Returns an uncorrected geojson object. The position of this object is relative to the field it is in, not the world.
        line = geojson.LineString([self.points])
        feature = geojson.Feature(geometry=line, properties={"type": self.type, "colour": self.colour})
        return feature

class Point():
    def __init__(self):
        self.data = None
        self.points = []

    def parse(self, data):
        self.data = data
        
        self.colour = colToColourTuple(data[1])
        self.points = getGeometryfromFeature(data)
        return self
    
    def getGeoJSON(self):
        #Returns an uncorrected geojson object. The position of this object is relative to the field it is in, not the world.
        point = geojson.MultiPoint(self.points)
        feature = geojson.Feature(geometry=point, properties={"colour": self.colour})
        return feature



class Region():
    def __init__(self):
        self.data = None
        self.id = 0
        self.points = []
    
    def parse(self, data):
        #Empty list to hold all the point tuples
        pointList = []
        for line in data:
            if line.startswith("ARE"):
                point = line.split(" ")[1:]
                point[:] = [x for x in point if x != ''] #Remove any empty strings, sometimes there is a 3 space gap between points, and I have no idea why...
                point[-1] = point[-1].strip("\n") # If there are any new lines left, there shouldn't be!
                #Append all the points to the list as tuple pairs
                pointList.append((float(point[0]), float(point[1])))
                pointList.append((float(point[-2]), float(point[1])))
                pointList.append((float(point[-2]), float(point[-1])))
                pointList.append((float(point[0]), float(point[-1])))

            #Get the region position 
            if line.startswith("POS"):
                ownposition = getPosition(line)
            if line.startswith("ID"):
                self.id = int(line.split(" ")[1])
        
        #After getting the details from the data, we need to reproject it using the position given:
        for count, point in enumerate(pointList):
            point = rotatePoint(point, (0,0), ownposition[3])
            
            point = translatePoint(point, ownposition[0], ownposition[2])
            pointList[count] = point
        self.points = pointList
        return self

    def getPoints(self):
        # Returns a list of point tuples
        return self.points

    def getGeoJSON(self):
        #Returns an uncorrected geojson object. The position of this object is relative to the field it is in, not the world.
        polygon = geojson.Polygon([self.points])
        feature = geojson.Feature(geometry=polygon, properties={"type": self.id})
        return feature


    
#Helper functions

def colToColourTuple(colour):
    """Converts the colour string to a tuple of RGB integers
    :param colour: The colour string, in the format \"COL r g b\""""
    colour = colour.split(" ")[1:]
    colour = tuple(colour)

    return colour

def getPosition(position):
    #split the text up, Format is: POS x y z yaw pitch roll
    """Returns a tuple of the position of the object, in the format (x, y, z, yaw, pitch, roll). Input format is \"POS x y z yaw pitch roll\
    :param position: The position string, in the format \"POS x y z yaw pitch roll\""""
    position = position.split(" ")[1:]
    #Convert all values to integers
    for i in range(len(position)):
        position[i] = int(float(position[i]))
    
    #Convert uu to degrees - All are converted, but only yaw will be used.
    position[3] = uuToDegrees(position[3])
    position[4] = uuToDegrees(position[4])
    position[5] = uuToDegrees(position[5])
    position = tuple(position)
    return position

def uuToDegrees(uu):
    """Converts the uu value to degrees. This is the rotation value in YS"""
    #Converts the uu value to degrees
    #360 degrees = 65536 uu
    #1 degree = 65536/360 = 182.04 uu
    #1 uu = 360/65536 = 0.0054931640625 degrees
    degrees = (uu * 0.0054931640625)
    return degrees

def rotatePoint(point, origin=(0,0), angle=0):
    """Takes the point, rotates it around the origin by the angle, and returns the new point
    :param point: The point to rotate, in the format (x, y)
    :param origin: The origin to rotate around, in the format (x, y)
    :param angle: The angle to rotate by, in degrees"""
    #Rotate a point counterclockwise by a given angle around a given origin.
    # Angle is in degrees
    #Point is a tuple of (x,y)
    #Origin is a tuple of (x,y)
    #Returns a tuple of (x,y)

    angle = np.radians(angle)
    ox, oy = origin
    px, py = point
    qx = ox + np.cos(angle) * (px - ox) - np.sin(angle) * (py - oy)
    qy = oy + np.sin(angle) * (px - ox) + np.cos(angle) * (py - oy)
    return (qx, qy)

def translatePoint(point, x=0, y=0):
    """Translates a point by x and y, usually taken from the POS
    :param point: The point to translate, in the format (x, y)
    :param x: The x value to translate by, usually taken from the POS
    :param y: The y value to translate by, taken from the POS"""
    #Translate a point by a given x and y
    #Point is a tuple of (x,y)
    #Returns a tuple of (x,y)
    px, py = point
    qx = px + x
    qy = py + y
    return (qx, qy)

def transformGeometry(geometry, position):
    """Transforms a geometry based on the position tuple, this calls the other translate and rotate functions
    :param geometry: The geometry to transform, in the form of a list of point tuples
    :param position: The position tuple, in the format (x, y, z, yaw, pitch, roll)
    """
    #Transforms a polygon to the correct position
    points = geometry.points

    for count, point in enumerate(points):
        point = rotatePoint(point, angle=position[3])
        point = translatePoint(point, x=position[0], y=position[2])
        points[count] = point
    geometry.points = points
    return geometry

def getGeometryfromFeature(feature):
    """Helper function that takes the feature from a PC2, and returns a list of points, used for each geometry type
    :param feature: The feature from a PC2, in the form of a list of strings that make up the feature"""
    points = []
    for line in feature:
        if line.startswith("VER"):
            point = line.split(" ")[1:] # Just get the back bit (strip of VER)
            #Convert all values to floats
            for i in range(len(point)):
                    point[i] = float(point[i])
            point = tuple(point)
            points.append(point)
    return points

def quadStripToPolygon(qst,parent):
    """Converts a quad strip to a polygon, and adds it to the parent
    :param qst: The quad strip to convert, as a polygon object.
    :param parent: The parent PC2 to add the polygons created to"""
    points = qst.points # Get the point list
    points.reverse() # Flip it and reverse it
    colour = qst.colour
    type = qst.type
    for point_index in range (len(points)-2):
        list  = []
        list.append(points[point_index])
        list.append(points[point_index+1])
        list.append(points[point_index+2])
        polygon = Polygon()
        polygon.points = list
        polygon.type = type
        polygon.colour = colour
        parent.children.append(polygon)

def quadrilateralToPolygon(qdr,parent):
    """Converts a quadrilateral to a polygon, and adds it to the parent
    :param qdr: The quadrilateral to convert, as a polygon object.
    :param parent: The parent PC2 to add the polygons created to"""
    points = qdr.points
    colour = qdr.colour
    type = qdr.type
    for count in range(0,len(points),4):
        if (len(points[count:count+4]) <4 ):
            break
        list = []
        list.append(points[count])
        list.append(points[count+1])
        list.append(points[count+2])
        list.append(points[count+3])
        polygon = Polygon()
        polygon.points = list
        polygon.type = type
        polygon.colour = colour
        parent.children.append(polygon)

def triangleToPolygon(tri,parent):
    """Converts a triangle to a polygon, and adds it to the parent
    :param tri: The triangle to convert, as a polygon object.
    :param parent: The parent PC2 to add the polygons created to"""
    points = tri.points
    colour = tri.colour
    type = tri.type
    for count in range(0,len(points),3):
        if (len(points[count:count+3]) <3 ):
            break
        list = []
        list.append(points[count])
        list.append(points[count+1])
        list.append(points[count+2])
        polygon = Polygon()
        polygon.points = list
        polygon.type = type
        polygon.colour = colour
        parent.children.append(polygon)        


class FieldParser():
    """The main class that parses the file, and creates the geometry objects
    :param file: The file to parse (as the full path)
    returns the parser, which can then be used to get the geometries by using getGeoJSON() and stating what type of geometry you want (Point, Line or Polygon)
    """
    def __init__(self):
        self.geometries = [] # List of all the geometries
        self.regions = [] # List of all the regions
        self.callback=None
        self.field = Field() # The root field
        self.processed=  False
        
        
    
    def Load(self, file, callback=None):
        self.name = file.split("\\")[-1].split(".")[0] # Get the file name
        
        self.file = file
        with open(file, 'r') as f:
            self.lines = f.readlines()
        self.field.name = self.name
        self.field.file = self.file
        self.field.parse(self.lines)
        self.reproject()
        self.processed = True
        if callback:
            callback()


    def reproject(self):
        self.returnFields(self.field)
        self.returnRegions(self.field)

    def returnFields(self, rootFld):
        childrenList = rootFld.childFlds
        for child in childrenList:
            #print("Running again for child" + child.name)
            self.returnFields(child)
        #Get all the PC2s from this field:
        pc2s = rootFld.childPcs
        #print(len(pc2s))
        for pc2 in pc2s:
            name = pc2.name
            position = pc2.position
            parentPosition = rootFld.position
            #print(position)
            #Reproject, then add this to the parent
            for count, geometry in enumerate(pc2.children):
                    #print("Transforming "+ name+ " under " + rootFld.name +" to " + str(position))
                    geometry = transformGeometry(geometry, position)
                    geometry = transformGeometry(geometry, parentPosition)
                    pc2.children[count] = geometry
            if rootFld.parent != None:
                pc2.postion = None #Set the pc2s position to 0,0, as we're now done reprojecting it (otherwise it'll get reprojected at the next child level)
                pc2.position = (0,0,0,0,0,0)
                #print("new position is " + str(pc2.position))
                rootFld.parent.childPcs.append(pc2)
            else:
                #We're now at root level.
                self.geometries.append(pc2)

    def returnRegions(self, rootFld):
        childrenList = rootFld.childFlds
        for child in childrenList:
            
            self.returnRegions(child)
        
        regions = rootFld.regions
        
        for region in regions:
            #Don't have own position.
            parentPosition = rootFld.position
            #print(position)
            #Reproject, then add this to the parent
            geometry = transformGeometry(region, parentPosition)
            region = geometry

            if rootFld.parent != None:
                rootFld.parent.regions.append(region)
            else:
                #We're now at root level.
                self.regions.append(region)


    def getGeoJSON(self, geom_type):
        """Returns a feature collection of the geometries of a certain type
        :param geom_type: The type of geometry to return, as a string. Can be \"Point\", \"Line\" or \"Polygon\"
        :returns: A feature collection of the geometries of the specified type
        """
        #Get all the geometries of a certain type
        #Type is a string
        if geom_type == "Polygon":
            geom_type = Polygon
        elif geom_type == "Line":
            geom_type = Line
        elif geom_type == "Point":
            geom_type = Point
        else:
            return None
        geoJSON = []
        for geometry in self.geometries:
            for child in geometry.children:
                if type(child) == geom_type:
                    geoJSON.append(child.getGeoJSON())
        featureCollection = geojson.FeatureCollection(geoJSON)
        return featureCollection

    def getRegions(self):
        return self.regions

    def getGeometry(self):
        polygons = []
        lines = []
        points = []
        for geometry in self.geometries:
            for child in geometry.children:
                if type(child) == Polygon:
                    polygons.append(child)
                elif type(child) == Line:
                    lines.append(child)
                elif type(child) == Point:
                    points.append(child)
        return polygons, lines, points
