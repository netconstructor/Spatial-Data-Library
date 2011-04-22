#!/usr/bin/env python
#
# Copyright 2011 Jante LLC and University of Kansas
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import logging
import math
from optparse import OptionParser

'''Set CELL_COUNT to the desired number of cells on each edge of the rhomboids.'''
CELL_COUNT = 3

'''
DEGREE_DIGITS is the number of significant digits to the right of the decimal
to use in latitude and longitude equality determination and representation. This 
should be set to 7 to preserve reversible transformations between coordinate systems 
down to a resolution of roughly 1 m.
''' 
DEGREE_DIGITS = 7

'''
SEMI_MAJOR_AXIS is the radius of the sphere at the equator for the WGS84 datum. 
Cell construction and lookup are based on projection of the geographic coordinates 
onto a sphere of this radius. As a result, edge lengths and areas of cells projected
onto the WGS84 ellipsoid will vary slightly by latitude.
'''
SEMI_MAJOR_AXIS = 6378137.0

'''
EDGE_LENGTH is the length of the edge of any face of the icosahedron inscribed on the 
sphere whose radius is SEMI_MAJOR_AXIS.
'''
EDGE_LENGTH = 6706370.116516389

'''
MID_EDGE_RADIUS is the distance from the center of the sphere to the midpoint of any
edge of any face of the icosahedron inscribed on the sphere whose radius is SEMI_MAJOR_AXIS.
'''
MID_EDGE_RADIUS = 5425567.394830056

'''
SURFACE_DISTANCE_BETWEEN_VERTEXES is the great circle distance between any two 
adjacent rhomboid vertexes on the sphere whose radius is SEMI_MAJOR_AXIS.
'''
SURFACE_DISTANCE_BETWEEN_VERTEXES = 7061546.20147
# SURFACE_DISTANCE_BETWEEN_VERTEXES = VERTEX_ANGLE*(2 * math.pi * SEMI_MAJOR_AXIS) / 360.0

'''
CELL_SIDE_LENGTH is the great circle distance between any two 
adjacent cell vertexes on the sphere whose radius is SEMI_MAJOR_AXIS.
'''
CELL_SIDE_LENGTH = SURFACE_DISTANCE_BETWEEN_VERTEXES / CELL_COUNT 

'''
RADIANS is constant representing the number by which to multiply a value in degrees
to get the equivalent value in radians.
'''
RADIANS = 0.017453292519943295

'''
PHI = (1+SQRT(5))/2 - the golden ratio. The vertices of an icosahedron of side length 
2 can be placed at the coordinates: 
(0, +-1, +-PHI)
(+-1, +-PHI, 0)
(+-PHI, 0, +-1)
'''
PHI = 1.618033988749895

'''
VERTEX_LAT is the latitude in degrees north or south of the equator for all
vertexes that are not at one of the poles.
'''
VERTEX_LAT = 26.565051177077997

'''
VERTEX_ANGLE is the angle in degrees from the center of the sphere between any two
adjacent vertexes.
''' 
VERTEX_ANGLE = 63.434948822922

#FACE_CENTER_LAT = 52.622631859350314
#CENTER_ANGLE = 41.810314895778575

# Precalculated useful sines and cosines.
COS_72 = 0.30901699437494734
SIN_72 = -0.9510565162951536
COS_VERTEX_LAT = 0.8944271909999159
SIN_VERTEX_LAT = -0.4472135954999581

PLACEMARK_1 = u"""                                                                                                                                          
    <Placemark>                                                                                                                                               
        <name>Cell</name>                                                                                                                              
        <visibility>1</visibility>                                                                                                                            
        <styleUrl>#transGreenPoly</styleUrl>                                                                                                                  
        <description><![CDATA[%s %s]]></description>                                                                                                             
        <Polygon id="%s">                                                                                                                                     
            <outerBoundaryIs>                                                                                                                                 
                <LinearRing>                                                                                                                                  
                    <coordinates>
"""                                                                                                                             
PLACEMARK_2 = u"""
                    </coordinates>                                                                                                                            
                </LinearRing>                                                                                                                                 
            </outerBoundaryIs>                                                                                                                                
        </Polygon>                                                                                                                                            
    </Placemark>"""
    
KML = u'''<?xml version="1.0" encoding="UTF-8"?>                                                                                                          
<kml xmlns="http://www.opengis.net/kml/2.2">                                                                                                                  
    <Document>                                                                                                                                                
        <name>KmlFile</name>                                                                                                                                  
        <Style id="transGreenPoly">                                                                                                                           
            <LineStyle>                                                                                                                                       
                <width>1.5</width>                                                                                                                            
                <color>11111111</color>                                                                                                                       
            </LineStyle>                                                                                                                                      
            <PolyStyle>                                                                                                                                       
                <color>7d00ff00</color>                                                                                                                       
            </PolyStyle>                                                                                                                                      
        </Style>                                                                                                                                              
        <Folder>                                                                                                                                              
            <name>Triangular Mesh Grid</name>                                                                                                                 
            <visibility>1</visibility>                                                                                                                        
            <description>Global triangular mesh grid coverage.</description>                                                                                  
            %s                                                                                                                                                
        </Folder>                                                                                                                                             
    </Document>                                                                                                                                               
</kml>'''

FORMAT = """.%sf"""

def flip(p):
    '''Swap latitude and longitude order in the tuple. KML requires longitude first.'''
    return (p[1], p[0])

def sqr(x):
    '''Square of x.'''
    return x * x

def signum(x):
    '''Sign of x.'''
    if x > 0:
        return 1.0
    if x < 0:
        return -1.0
    return 0

def truncate_lat_lng(p):
    '''Set the precision of a lat long in degrees to DEGREE_DIGITS.'''    
    return (truncate(p[0],DEGREE_DIGITS),truncate(p[1],DEGREE_DIGITS))

def truncate(x, digits):
    '''Set the representational precision of x to digits places to the right of the decimal.'''
    format_x = FORMAT % digits
    return format(x,format_x)

def equal_within_tolerance(a, b, digits):
    '''Determine if two floats are equal within the accuracy given by digits places to the right of the decimal.'''
    if math.fabs(a-b) <= math.pow(10,-digits):
        return True
    return False

def equal_lat_lng(p0, p1):
    '''Determine if two degree lat longs are the same within the tolerance given by digits places to the right of the decimal.'''
    return (equal_within_tolerance(p0[0], p1[0], DEGREE_DIGITS) and equal_within_tolerance(lng180(p0[1]), lng180(p1[1]), DEGREE_DIGITS)) 

def lng180(lng):
    '''Given a longitude in degrees, returns a longitude in degrees between {-180, 180].'''
    newlng = float(lng)
    if newlng <= -180:
        newlng = lng + 360
    elif newlng > 180:
        newlng = newlng - 360
    return float(truncate(newlng, DEGREE_DIGITS))

def lng360(lng):
    '''Given a longitude in degrees, returns a longitude in degrees between [0, 360}.'''
    if float(lng) < 0:
        return float(truncate(lng + 360, DEGREE_DIGITS))
    if float(lng) > 360:
        return float(truncate(lng - 360, DEGREE_DIGITS))
    return float(truncate(lng, DEGREE_DIGITS))

def xyz_from_lat_lng((lat, lng)):
    '''Returns the Cartesian coordinates of a lat long on a unit sphere.'''
    x = math.cos(lat * RADIANS) * math.cos(lng * RADIANS)
    y = math.cos(lat * RADIANS) * math.sin(lng * RADIANS)
    z = math.sin(lat * RADIANS)
    return (x, y, z)

def lat_lng_from_xyz((x, y, z)):
    '''Returns the lat long (in degrees) of Cartesian coordinates on a unit sphere.'''
    R=math.sqrt(x*x+y*y+z*z)
    znorm = z/R
    ynorm = y/R
    xnorm = x/R
    lng = math.atan2(ynorm,xnorm) / RADIANS
    lat = math.asin(znorm) / RADIANS
    return (lat, lng)

def great_circle_distance(start_lat_lng, end_lat_lng):
    '''
    Returns the distance along a great circle between two lat longs on the surface of a
    sphere of radius SEMI_MAJOR_AXIS using the Haversine formula.
    '''
    dLat = (end_lat_lng[0] - start_lat_lng[0]) * RADIANS
    dLon = (end_lat_lng[1] - start_lat_lng[1]) * RADIANS 
    '''a is the square of half the chord length between the points.'''
    a = math.sin(dLat/2) * math.sin(dLat/2) + math.cos(start_lat_lng[0] * RADIANS) * math.cos(end_lat_lng[0] * RADIANS) * math.sin(dLon/2) * math.sin(dLon/2)
    if a>1:
        out = 'great_circle_distance(): start_lat_lng = %s end_lat_lng = %s a = %s' % (start_lat_lng, end_lat_lng, a)
        logging.debug(out)
        if start_lat_lng[0] == 23.465334500000001:
            out = 'great_circle_distance(): start_lat_lng = %s end_lat_lng = %s a = %s' % (start_lat_lng, end_lat_lng, a)
            logging.debug(out)
    '''c is the angular distance in radians between the points.'''
    test1 = math.sqrt(1-a)
    test2 = math.sqrt(a)
    test3 = math.atan2(test2, test1)

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return SEMI_MAJOR_AXIS * c 

def great_circle_intersection_xyz(p0, p1, p2, p3):
    '''
    Returns one of the two points on the sphere where two great circles, each defined by two Cartesian points,
    intersect. Result should be checked against expectation for hemisphere, and if not correct, take the 
    antipode.
    '''
    r = SEMI_MAJOR_AXIS
    x0 = p0[0]
    y0 = p0[1]
    z0 = p0[2]
    x1 = p1[0]
    y1 = p1[1]
    z1 = p1[2]
    x2 = p2[0]
    y2 = p2[1]
    z2 = p2[2]
    x3 = p3[0]
    y3 = p3[1]
    z3 = p3[2]
    a = (y0*z1 - y1*z0)
    b = -(x0*z1 - x1*z0)
    c = (x0*y1 - x1*y0)
    d = (y2*z3 - y3*z2)
    e = -(x2*z3 - x3*z2)
    f =  (x2*y3 - x3*y2)
    h = (d*c-f*a)/(e*a-d*b)
    g = ((-b*h - c)/a)
    k = math.sqrt(r*r/(g*g + h*h + 1))
    lat = math.asin(k/r)
    lng = math.atan2(h*k,g*k)
    return (float(truncate(lat/RADIANS, DEGREE_DIGITS)),float(truncate(lng/RADIANS, DEGREE_DIGITS)))

def great_circle_intersection_lat_lngs(p0, p1, p2, p3):
    '''
    Returns the lat long of the point within the same hemisphere where two great circles, defined by 
    two lat longs each, intersect.
    '''
    if p0[0] == -90.0:
        corrected_p0 = p1
        corrected_p1 = p0
    else:
        corrected_p0 = p0
        corrected_p1 = p1
    p = great_circle_intersection_xyz(xyz_from_lat_lng(corrected_p0), xyz_from_lat_lng(corrected_p1), xyz_from_lat_lng(p2), xyz_from_lat_lng(p3))
    corrected_lat = p[0]
    corrected_lng = p[1]
    # If the calculated intersection is in the opposite hemisphere, return the antipode instead 
    if not same_hemisphere(p,p0):
        corrected_lng = lng180(p[1] + 180)
        if p[0] != 90.0:
            corrected_lat = -1.0 * p[0] 
    return (corrected_lat,corrected_lng)

def same_hemisphere(p0, p1):    
    '''Document this!!!'''
    if great_circle_distance(p0,p1) > math.pi*SEMI_MAJOR_AXIS/2:
        return False
    return True
    
class Cell(object):
    '''
    Cell is the rhomboidal grid cell of a Triangular Mesh Grid over a sphere. The cell is 
    identified by the rhomboid within which it lies and the x and y offset indexes from the 
    southern vertex.
    ''' 
    
    @staticmethod
    def rotate(lat_lng, axis_lat_lng, rotation_angle):
        '''
        Return the lat long in degrees of the point determined by right-handed rotating an input
        point lat_lng through an angle rotation_angle about the axis axis_lat_lng.
        '''
        x = math.cos(lat_lng[0] * RADIANS) * math.cos(lat_lng[1] * RADIANS)
        y = math.cos(lat_lng[0] * RADIANS) * math.sin(lat_lng[1] * RADIANS)
        z = math.sin(lat_lng[0] * RADIANS)

        c1 = math.cos(axis_lat_lng[0] * RADIANS) * math.cos(axis_lat_lng[1] * RADIANS)
        c2 = math.cos(axis_lat_lng[0] * RADIANS) * math.sin(axis_lat_lng[1] * RADIANS)
        c3 = math.sin(axis_lat_lng[0] * RADIANS)
        cosa = math.cos(rotation_angle * RADIANS)
        sina = math.sin(rotation_angle * RADIANS)

        x1 = x * cosa
        y1 = y * cosa
        z1 = z * cosa

        x1 = x1 + ((1 - cosa) * (c1 * c1 * x + c1 * c2 * y + c1 * c3 * z))
        y1 = y1 + ((1 - cosa) * (c2 * c1 * x + c2 * c2 * y + c2 * c3 * z))
        z1 = z1 + ((1 - cosa) * (c3 * c1 * x + c3 * c2 * y + c3 * c3 * z))

        x1 = x1 + (c2 * z - c3 * y) * sina
        y1 = y1 + (c3 * x - c1 * z) * sina
        z1 = z1 + (c1 * y - c2 * x) * sina

        newlat = math.asin(z1) / RADIANS
        newlng = math.atan2(y1, x1) / RADIANS
        return (newlat, newlng)
           
    @staticmethod
    def polygon(rhomboid_num, x_index, y_index, cell_count = None):
        '''
        Return a list of points (lng, lat pairs in degrees) as strings for the vertexes of a cell
        given by the rhomboid index number and x, y offset indexes from the southern vertex 
        of the rhomboid.
        '''
        if cell_count == None:
            cell_count=CELL_COUNT

        s = Rhomboid.south_lat_lng(rhomboid_num)
        e = Rhomboid.east_lat_lng(rhomboid_num)
        w = Rhomboid.west_lat_lng(rhomboid_num)
        n = Rhomboid.north_lat_lng(rhomboid_num)
#        out = 'Cell.polygon(): rhomboid_num = %s s = %s e = %s w = %s n = %s' % (rhomboid_num, s, e, w, n)
#        logging.debug(out)

        bearing_we0 = Rhomboid.get_bearing(w,e)
        distance_we0 = CELL_SIDE_LENGTH*x_index
        distance_we1 = CELL_SIDE_LENGTH*(x_index+1)
        we0 = Rhomboid.get_point_from_distance_at_bearing(w, distance_we0, bearing_we0)
        we1 = Rhomboid.get_point_from_distance_at_bearing(w, distance_we1, bearing_we0)
#        out = 'dist_we0=%s bearing_we0=%s we0=%s' % (distance_we0, bearing_we0, we0)
#        logging.debug(out)
#        out = 'dist_we1=%s bearing_we0=%s we1=%s' % (distance_we1, bearing_we0, we1)
#        logging.debug(out)

        bearing_ew0 = Rhomboid.get_bearing(e,w)
        distance_ew0 = CELL_SIDE_LENGTH*y_index
        distance_ew1 = CELL_SIDE_LENGTH*(y_index+1)
        ew0 = Rhomboid.get_point_from_distance_at_bearing(e, distance_ew0, bearing_ew0)
        ew1 = Rhomboid.get_point_from_distance_at_bearing(e, distance_ew1, bearing_ew0)
#        out = 'dist_ew0=%s bearing_ew0=%s ew0=%s' % (distance_ew0, bearing_ew0, ew0)
#        logging.debug(out)
#        out = 'dist_ew1=%s bearing_ew0=%s ew1=%s' % (distance_ew1, bearing_ew0, ew1)
#        logging.debug(out)

        bearing_se0 = Rhomboid.get_bearing(s,e)
        distance_se0 = CELL_SIDE_LENGTH*x_index
        se0 = Rhomboid.get_point_from_distance_at_bearing(s, distance_se0, bearing_se0)
#        out = 'dist_se0=%s bearing_se0=%s se0=%s' % (distance_se0, bearing_se0, se0)
#        logging.debug(out)

        bearing_sw0 = Rhomboid.get_bearing(s,w)
        distance_sw0 = CELL_SIDE_LENGTH*y_index
        if s[0] == -90.0:
            sw0 = Rhomboid.get_point_from_distance_at_bearing((-90.0,w[1]), distance_sw0, bearing_sw0)
        else:
            sw0 = Rhomboid.get_point_from_distance_at_bearing(s, distance_sw0, bearing_sw0)
#        out = 'dist_sw0=%s bearing_sw0=%s sw0=%s' % (distance_sw0, bearing_sw0, sw0)
#        logging.debug(out)

        distance_se1 = CELL_SIDE_LENGTH*(x_index+1)
        se1 = Rhomboid.get_point_from_distance_at_bearing(s, distance_se1, bearing_se0)
#        out = 'dist_se1=%s bearing_se0=%s se1=%s' % (distance_se1, bearing_se0, se1)
#        logging.debug(out)
        
        distance_sw1 = CELL_SIDE_LENGTH*(y_index+1)
        if s[0] == -90.0:
            sw1 = Rhomboid.get_point_from_distance_at_bearing((-90.0,w[1]), distance_sw1, bearing_sw0)
        else:
            sw1 = Rhomboid.get_point_from_distance_at_bearing(s, distance_sw1, bearing_sw0)
#        out = 'dist_sw1=%s bearing_sw0=%s sw1=%s' % (distance_sw1, bearing_sw0, sw1)
#        logging.debug(out)
        
        bearing_en0 = Rhomboid.get_bearing(e,n)
        distance_en0 = CELL_SIDE_LENGTH*y_index
        en0 = Rhomboid.get_point_from_distance_at_bearing(e, distance_en0, bearing_en0)
#        out = 'dist_en0=%s bearing_en0=%s en0=%s' % (distance_en0, bearing_en0, en0)
#        logging.debug(out)

        distance_en1 = CELL_SIDE_LENGTH*(y_index+1)
        en1 = Rhomboid.get_point_from_distance_at_bearing(e, distance_en1, bearing_en0)
#        out = 'dist_en1=%s bearing_en0=%s en1=%s' % (distance_en1, bearing_en0, en1)
#        logging.debug(out)
        
        bearing_wn0 = Rhomboid.get_bearing(w,n)
        distance_wn0 = CELL_SIDE_LENGTH*x_index
        wn0 = Rhomboid.get_point_from_distance_at_bearing(w, distance_wn0, bearing_wn0)
#        out = 'dist_wn0=%s bearing_wn0=%s wn0=%s' % (distance_wn0, bearing_wn0, wn0)
#        logging.debug(out)

        distance_wn1 = CELL_SIDE_LENGTH*(x_index+1)
        pre_wn1 = Rhomboid.get_point_from_distance_at_bearing(w, distance_wn1, bearing_wn0)
        if pre_wn1[0] == 90.0:
            wn1 = (90.0, wn0[1])
        else:
            wn1 = pre_wn1
#        out = 'dist_wn1=%s bearing_wn0=%s wn1=%s' % (distance_wn1, bearing_wn0, wn1)
#        logging.debug(out)
                
        if x_index + y_index == 0 and rhomboid_num >= 5:
            # S vertex on S pole
            s_vertex = (-90.0,e[1])
            e_vertex = se1
            w_vertex = sw1
#            out = '0a) S cell vertex on S pole e_vertex=%s w_vertex=%s' % (e_vertex, w_vertex)
#            logging.debug(out)
            if x_index + y_index < CELL_COUNT-1:
                # N cell vertex in or on S triangle also
                n_vertex = great_circle_intersection_lat_lngs(se1,we1, sw1,ew1)
#                out = '0b) N cell vertex in or on S triangle n_vertex=%s' % (str(n_vertex))
#                logging.debug(out)
            else:
                # N cell vertex in N triangle
                if equal_lat_lng(en1,wn1):
                    n_vertex = en1
                else:
                    n_vertex = great_circle_intersection_lat_lngs(we1,wn1, ew1,en1)
#                out = '0c) N cell vertex in N triangle n_vertex=%s' % (str(n_vertex))
#                logging.debug(out)
                
        elif x_index + y_index <= CELL_COUNT:
            # S cell vertex in or on S triangle
            if equal_lat_lng(se0,sw0):
                s_vertex = se0
#                out = '1a) S cell vertex in or on S triangle s_vertex=%s' % (str(s_vertex))
#                logging.debug(out)
            else:
                # S cell vertex in N triangle
                s_vertex = great_circle_intersection_lat_lngs(se0,we0, sw0,ew0)
#                out = '1b) S cell vertex in S triangle s_vertex=%s' % (str(s_vertex))
#                logging.debug(out)
            if x_index + y_index < CELL_COUNT:
                # E, W cell vertexes in or on S triangle   
                if equal_lat_lng(se1,we1):
                    e_vertex = se1
#                    out = '2a) E,W cell vertexes in or on S triangle e_vertex=%s' % (str(e_vertex))
#                    logging.debug(out)
                else:
                    e_vertex = great_circle_intersection_lat_lngs(se1,we1, sw0,ew0)
#                    out = '2b) E,W cell vertexes in or on S triangle e_vertex=%s' % (str(e_vertex))
#                    logging.debug(out)
#                    out = '2b) se1=%s we1=%s sw0=%s ew0=%s' % (se1, we1, sw0, ew0)
#                    logging.debug(out)
                if equal_lat_lng(sw1,we0):
                    w_vertex = sw1
                else:
                    w_vertex = great_circle_intersection_lat_lngs(se0,we0, sw1,ew1)
#                out = '2) E,W cell vertexes in or on S triangle e_vertex=%s w_vertex=%s' % (e_vertex, w_vertex)
#                logging.debug(out)
            else:
                e_vertex = great_circle_intersection_lat_lngs(ew0,en0, we1,wn1)
                w_vertex = great_circle_intersection_lat_lngs(we0,wn0, ew1,en1)
#                out = '3) E,W cell vertexes in N triangle e_vertex=%s w_vertex=%s' % (e_vertex, w_vertex)
#                logging.debug(out)
            if x_index + y_index < CELL_COUNT-1:
                # N cell vertex in or on S triangle also
                n_vertex = great_circle_intersection_lat_lngs(se1,we1, sw1,ew1)
#                out = '4) N cell vertex in or on S triangle also n_vertex=%s' % (str(n_vertex))
#                logging.debug(out)
            else:
                # N cell vertex in N triangle
                if equal_lat_lng(en1,wn1):
                    n_vertex = en1
#                    out = '5a)'
#                    logging.debug(out)
                else:
                    n_vertex = great_circle_intersection_lat_lngs(we1,wn1, ew1,en1)
#                    out = '5d)'
#                    logging.debug(out)
#                out = '5) N cell vertex in N triangle n_vertex=%s' % (str(n_vertex))
#                logging.debug(out)
        else:
            # Whole cell in N triangle
            e_vertex = great_circle_intersection_lat_lngs(ew0,en0, we1,wn1)
            w_vertex = great_circle_intersection_lat_lngs(we0,wn0, ew1,en1)
            n_vertex = great_circle_intersection_lat_lngs(we1,wn1, ew1,en1)
            s_vertex = great_circle_intersection_lat_lngs(ew0,en0, we0,wn0)
#            out = '6) Whole cell in N triangle n_vertex=%s' % (str(n_vertex))
#            logging.debug(out)

#        out = 's_vertex=%s n_vertex=%s e_vertex=%s w_vertex=%s' % (s_vertex, n_vertex, e_vertex, w_vertex)
#        logging.debug(out)
                 
        if s_vertex[0] == -90:
            p0 = (s_vertex[0],e_vertex[1])
            p1 = (s_vertex[0],w_vertex[1])
#            out = 'S half sv=-90 p0=%s p1=%s' % (p0, p1)
#            logging.debug(out)
            '''S-out, E, N, W, S-in'''
            return [flip(truncate_lat_lng(p0)), flip(truncate_lat_lng(e_vertex)), flip(truncate_lat_lng(n_vertex)), flip(truncate_lat_lng(w_vertex)), flip(truncate_lat_lng(p1))]
        elif n_vertex[0] == 90:
            p2 = (90.0,e_vertex[1])
            p3 = (90.0,w_vertex[1])
#            out = 'S half nv=+90: p2=%s p3=%s' % (p2, p3)
#            logging.debug(out)
            '''S, E, N-in, N-out, W, S'''
            return [flip(truncate_lat_lng(s_vertex)), flip(truncate_lat_lng(e_vertex)), flip(truncate_lat_lng(p2)), flip(truncate_lat_lng(p3)), flip(truncate_lat_lng(w_vertex)), flip(truncate_lat_lng(s_vertex))]
#        out = 'S half sv<>-90 nv<>90 s_vertex=%s' % (str(s_vertex))
#        logging.debug(out)
        '''S, E, N, W, S'''
        return [flip(truncate_lat_lng(s_vertex)), flip(truncate_lat_lng(e_vertex)), flip(truncate_lat_lng(n_vertex)), flip(truncate_lat_lng(w_vertex)), flip(truncate_lat_lng(s_vertex))]
        
    @staticmethod
    def createPlacemark(key, polygon):
        '''Render a KML placemark for a polygon.''' 
        data = (key, polygon, key)
        placemark = PLACEMARK_1 % data
        for c in polygon:
            point = '                        %s,%s,1\n' % (c[0], c[1])
            placemark = placemark + point
        placemark = placemark + PLACEMARK_2
        return placemark
    
    @staticmethod
    def createBBAsKmlMesh(from_ll, to_ll, orientation, cell_count):
        '''
        Render a triangular mesh in KML of TMG cells overlapping the given oriented bounding box defined
        by the corners from_ll and to_ll using (lat,lng) convention.
        ''' 
        out = 'createBBAsKmlMesh() from_ll = %s to_ll = %s orientation = %s cell_count = %s' % (from_ll, to_ll, orientation, cell_count)
        logging.debug(out)

        placemarks = []
        key_list = get_tile(from_ll, to_ll, orientation, cell_count)
        out = 'createBBAsKmlMesh() key_list: %s ' % (key_list)
        logging.debug(out)
        for key in key_list:
            '''Get the rhomboid_num, x, and y from the cell_key'''
            rhomboid_num, x, y = get_cell_attributes(cell_key)
            polygon = Cell.polygon(rhomboid_num, x, y, cell_count)                                        
            p=Cell.createPlacemark(key, polygon)
            placemarks.append(p)
        return KML % ' '.join(placemarks)

    @staticmethod
    def createKmlMesh(rhomboid_num, cell_count):
        '''Render a triangular mesh of cells in KML.''' 
        out = 'createKmlMesh() rhombopid_num = %s cell_count = %s' % (rhomboid_num, cell_count)
        logging.debug(out)

        placemarks = []
        for x in range(cell_count):
            for y in range(cell_count):
                polygon = Cell.polygon(rhomboid_num, x, y, cell_count)                                        
                key = get_cell_key( (rhomboid_num, x, y) )
                p=Cell.createPlacemark(key, polygon)
                placemarks.append(p)
        return KML % ' '.join(placemarks)

    @staticmethod
    def get_canonical_south_point(x_index, y_index, cell_count=None):
        '''Document this!!!'''
        # This isn't correct. Rotations depend on the index.
        if not cell_count:
            cell_count = CELL_COUNT
        # Canonical rhomboid 0 has origin at -VERTEX_LAT, 0
        lat_lng0 = (-VERTEX_LAT, 0)
        axis_lat_lng = (VERTEX_LAT, -108)

        # Rotate NE from the origin by x_index cell widths
        lat_lng = Cell.rotate(lat_lng0, axis_lat_lng, 72 * x_index / cell_count)
            
        # Rotate NW from there by y_index cell widths
        lat_lng = Cell.rotate(lat_lng, (-VERTEX_LAT, -108), 72 * y_index / cell_count)
        return (lat_lng)

    @staticmethod
    def get_canonical_east_point(x_index, y_index, cell_count=None):
        '''Document this!!!'''
        if not cell_count:
            cell_count = CELL_COUNT
        # Start at canonical south point
        lat_lng0 = Cell.get_canonical_south_point(x_index, y_index)

        newlat = lat_lng0[0] + (90 + VERTEX_LAT) / (2 * cell_count)
        newlng = lat_lng0[1] + 36 / cell_count
        lat_lng = (newlat, newlng)
        return (lat_lng)

    @staticmethod
    def get_canonical_west_point(x_index, y_index, cell_count = None):
        '''Document this!!!'''
        if not cell_count:
            cell_count = CELL_COUNT
#        # Start at canonical south point
        lat_lng0 = Cell.get_canonical_south_point(x_index, y_index)
#        # Rotate NW from there by one cell width
        newlat = lat_lng0[0] + (90 + VERTEX_LAT) / (2 * cell_count)
        newlng = lat_lng0[1] - 36 / cell_count
        lat_lng = (newlat, newlng)
        return (lat_lng)

    @staticmethod
    def get_canonical_north_point(x_index, y_index, cell_count = None):
        '''Document this!!!'''
        if not cell_count:
            cell_count = CELL_COUNT

        # Start at canonical south point
        lat_lng0 = Cell.get_canonical_south_point(x_index, y_index)

        # Rotate N from there by one cell diagonal width
        newlat = lat_lng0[0] + (90 + VERTEX_LAT) / cell_count
        lat_lng = (newlat, lat_lng0[1])
        return (lat_lng)

    def __init__(self, rhomboid_num, x_index, y_index):
        self.rhomboid_num = rhomboid_num
        self.x_index = x_index
        self.y_index = y_index
    
class Face(object):
    '''
    Return a face, which is one of the sides of an icosahedron inscribed within
    a sphere. Convention is to number faces consecutively from 0 beginning with the 
    northernmost face having its center at longitude = 0.
    '''
        
    @staticmethod
    def get_northern(lng):
        '''One of the northern five faces: 0=[-36,36}, 1=[36,108}, 2=[108,180},
            3=[180,-108}, 4=[-108,-36}.
        '''
        clng = lng180(lng)
        face = int(math.floor((clng + 360 + 36) / 72))
        if clng >= -36:
            face = face - 5
        return face

    @staticmethod
    def get_southern(lng):
        '''One of the southern five faces: 15=[0,72}, 16=[72,144}, 17=[144,-144},
        18=[-144,-72}, 19=[-72,0}.
        '''
        clng = lng180(lng)
        face = int(math.floor((clng + 360) / 72) + 15)
        if clng >= 0:
            face = face - 5
        return face

    @staticmethod
    def get_equatorial(lat, lng):
        ''' lat and lng are somewhere in the equatorial zone, between the northern 
        and southern faces. Find which of ten equal sections around the equator 
        lng falls into by rotating lng to equivalent longitude at lat=0.
        '''
        clng = lng180(lng)
        section = 0
        if clng >= -18:
            section = int(math.floor((18 + clng + (18 * (lat / VERTEX_LAT))) / 36))
        else:
            section = int(math.floor((18 + 360 + clng + (18 * (lat / VERTEX_LAT))) / 36))
        # Even numbered sections are northern facets [5,9]:
        if section % 2 == 0:
            face = 5 + (section / 2)
        # Odd numbered sections are get_southern facets [10,14]:
        else:
            face = 10 + ((section - 1) / 2)
        return face

    @staticmethod
    def get_face_number(lat, lng):
        '''Return the face of the icosahedron onto which the lat lng projects.'''
        if lat >= VERTEX_LAT:
            face = Face.get_northern(lng)
        elif lat < -(VERTEX_LAT):
            face = Face.get_southern(lng)
        else:
            face = Face.get_equatorial(lat, lng)
        return face

    def __init__(self, lat, lng):
        self.lat = lat
        self.lng = lng
        self.num = self.get_face_number(lat, lng)

class Rhomboid(object):
    '''Document this!!!'''
    @staticmethod
    def canonical_lat(face):
        '''Document this!!!'''
        if face.num < 10:
            return face.lat
        clng = Rhomboid.canonical_lng(face)
        x = math.cos(face.lat * RADIANS) * math.cos(clng * RADIANS)
        y = math.cos(face.lat * RADIANS) * math.sin(clng * RADIANS)
        z = math.sin(face.lat * RADIANS)
        c1 = COS_VERTEX_LAT * COS_72
        c2 = COS_VERTEX_LAT * SIN_72
        c3 = SIN_VERTEX_LAT
        cosa = COS_72
        sina = -(SIN_72)
        z1 = z * cosa
        z1 = z1 + ((1 - cosa) * (c3 * c1 * x + c3 * c2 * y + c3 * c3 * z))
        z1 = z1 + (((c1 * y) - (c2 * x)) * sina)
        newlat = math.asin(z1) / RADIANS
#        out = 'canonical_lat(face.num=%s) x=%s, y=%s, z=%s z1=%s face.lat=%s clng=%s' % (face.num, x, y, z, z1, face.lat, clng)
#        logging.debug(out)
        return newlat
    
    @staticmethod
    def get_bearing(start_lat_lng, end_lat_lng):
        '''Document this!!!'''
        if start_lat_lng[0] == -90.0:
            return 0
        y = math.sin((end_lat_lng[1] - start_lat_lng[1]) * RADIANS) * math.cos(end_lat_lng[0] * RADIANS)
        x = math.cos(start_lat_lng[0] * RADIANS) * math.sin(end_lat_lng[0] * RADIANS) - math.sin(start_lat_lng[0] * RADIANS) * math.cos(end_lat_lng[0] * RADIANS) * math.cos((end_lat_lng[1] - start_lat_lng[1]) * RADIANS)
        b = math.atan2(y, x) / RADIANS
        return float(truncate(b, DEGREE_DIGITS))
    
    @staticmethod
    def get_point_from_distance_at_bearing(start_lat_lng, distance, bearing):
        '''Document this!!!'''
        ad = distance/SEMI_MAJOR_AXIS
        lat1 = start_lat_lng[0] * RADIANS
        lng1 = start_lat_lng[1] * RADIANS
        b = bearing * RADIANS
        lat2 = math.asin( math.sin(lat1) * math.cos(ad) + \
                          math.cos(lat1)*math.sin(ad)*math.cos(b) )
        lng2 = lng1 + math.atan2( math.sin(b)*math.sin(ad)*math.cos(lat1), \
                                  math.cos(ad)-math.sin(lat1)*math.sin(lat2))
        return (float(truncate(lat2/RADIANS,DEGREE_DIGITS)), float(truncate(lng2/RADIANS,DEGREE_DIGITS)))
                                 
    @staticmethod
    def rotation_axis_xyz(start_lat_lng, end_lat_lng):
        '''Document this!!!'''
        
#        In 2- or 3-dimensional Euclidean space, two vectors are orthogonal if their dot product is zero.
        
        start_xyz = xyz_from_lat_lng(start_lat_lng)
        end_xyz = xyz_from_lat_lng(end_lat_lng)

#        out = 'ROTATION_AXIS_XYZ: start_xyz=%s end_xyz=%s' % (start_xyz, end_xyz)
#        logging.debug(out)

        a1 = start_xyz[0]
        a2 = start_xyz[1]
        a3 = start_xyz[2]
        b1 = end_xyz[0]
        b2 = end_xyz[1]
        b3 = end_xyz[2]
    
        c1 = a2*b3 - a3*b2
        c2 = a3*b1 - a1*b3
        c3 = a1*b2 - a2*b1
        
        # test orthogonality by dot products
#        R = math.sqrt(c1*c1 + c2*c2 + c3*c3)
#        a.c = a1c1+a2c2+a3c3 = 0
#        b.c = b1c1+b2c2+b3c3 = 0
#        c1(a1-b1) + c2(a2-b2) + c3(a3-b3) = 0

#        c1 = c1/R
#        c2 = c2/R
#        c3 = c3/R
#        adotc = a1*c1 + a2*c2 + a3*c3
#        bdotc = b1*c1 + b2*c2 + b3*c3
#
#        out = ' adotc=%s bdotc=%s' % (adotc, bdotc)
#        logging.debug(out)

        return (c1, c2, c3)

    @staticmethod
    def get_bearing_ne(rhomboid_num):
        '''Document this!!!'''
        start_lat_lng = Rhomboid.south_lat_lng(rhomboid_num)
        end_lat_lng = Rhomboid.east_lat_lng(rhomboid_num)
        return Rhomboid.get_bearing(start_lat_lng, end_lat_lng, rhomboid_num)

    @staticmethod
    def get_bearing_nw(rhomboid_num):
        '''Document this!!!'''
        start_lat_lng = Rhomboid.south_lat_lng(rhomboid_num)
        end_lat_lng = Rhomboid.west_lat_lng(rhomboid_num)
        return Rhomboid.get_bearing(start_lat_lng, end_lat_lng, rhomboid_num)

    @staticmethod
    def south_lat_lng(rhomboid_num):
        '''Document this!!!'''
        lat = -VERTEX_LAT
        lng = 0
        if rhomboid_num < 5:
            # Latitude is correct already.
            lng = lng180(72 * (rhomboid_num % 5))
        else:
            lat = -90
            lng = lng180(72 + 72 * (rhomboid_num % 5))
        # Longitude might as well be zero for the pole.
        # But note that polygon construction from vertices at the poles may 
        # be sensitive to the longitude when connecting to an adjacent vertex.
        return (lat, lng)

    @staticmethod
    def east_lat_lng(rhomboid_num):
        '''Document this!!!'''
        lat = VERTEX_LAT
        lng = 0
        if rhomboid_num < 5:
            # Latitude is correct already.
            lng = lng180(36 + 72 * (rhomboid_num % 5))
        else:
            lat = -VERTEX_LAT
            lng = lng180(72 + 72 * (rhomboid_num % 5))
        return (lat, lng)

    @staticmethod
    def west_lat_lng(rhomboid_num):
        '''Document this!!!'''
        lat = VERTEX_LAT
        lng = 0
        if rhomboid_num < 5:
            # Latitude is correct already
            lng = lng180(-36 + 72 * (rhomboid_num % 5))
        else:
            lat = -VERTEX_LAT
            lng = lng180(72 * (rhomboid_num % 5))
        return (lat, lng)

    @staticmethod
    def north_lat_lng(rhomboid_num):
        '''Document this!!!'''
        lat = 90
        lng = 0
        # For rhomboid_num < 5:
        # Latitude is correct already.
        # Longitude might as well be zero for the pole.
        # But note that polygon construction from vertices at the poles may 
        # be sensitive to the longitude when connecting to an adjacent vertex.
        if rhomboid_num >= 5:
            lat = VERTEX_LAT
            lng = lng180(36 + 72 * (rhomboid_num % 5))
        return (lat, lng)

    @staticmethod
    def south_xyz(rhomboid_num):
        '''Document this!!!'''
        return xyz_from_lat_lng(Rhomboid.south_lat_lng(rhomboid_num))

    @staticmethod
    def east_xyz(rhomboid_num):
        '''Document this!!!'''
        return xyz_from_lat_lng(Rhomboid.east_lat_lng(rhomboid_num))

    @staticmethod
    def west_xyz(rhomboid_num):
        '''Document this!!!'''
        return xyz_from_lat_lng(Rhomboid.west_lat_lng(rhomboid_num))

    @staticmethod
    def north_xyz(rhomboid_num):
        '''Document this!!!'''
        return xyz_from_lat_lng(Rhomboid.north_lat_lng(rhomboid_num))

    @staticmethod
    def canonical_lng(face):
        '''Document this!!!'''
        clng = lng360(face.lng)
        if face.num >= 10 and face.num < 15:
            clng = clng - 36 - (face.num % 5) * 72;
        else:
            clng = clng - (face.num % 5) * 72;
#        out = 'canonical_lng(face.num=%s), clng=%s' % (face.num, clng)
#        logging.debug(out)
        return lng360(clng)
    
    @staticmethod
    def cartesian_dist(fromlat, fromlng, tolat, tolng, radius):
        '''Document this!!!'''
        from_x = radius * math.cos(fromlat * RADIANS) * math.cos(fromlng * RADIANS)
        from_y = radius * math.cos(fromlat * RADIANS) * math.sin(fromlng * RADIANS)
        from_z = radius * math.sin(fromlat * RADIANS)
        to_x = radius * math.cos(tolat * RADIANS) * math.cos(tolng * RADIANS)
        to_y = radius * math.cos(tolat * RADIANS) * math.sin(tolng * RADIANS)
        to_z = radius * math.sin(tolat * RADIANS)
        dist = sqr(from_x - to_x)
        dist = dist + sqr(from_y - to_y)
        dist = dist + sqr(from_z - to_z)
        dist = math.sqrt(dist)
#        out = 'fromlat = %s fromlng = %s \ntolat = %s tolng = %s' % (fromlat, fromlng, tolat, tolng)
#        logging.debug(out)
#        out = 'dist = %s \n  from_x = %s, from_y = %s from_z = %s \n  to_x = %s to_y = %s to_z = %s' % (dist, from_x, from_y, from_z, to_x, to_y, to_z)
#        logging.debug(out)
        return dist
    
    @staticmethod
    def calc_num(face):
        '''Return the rhomboid number given a face.'''
        if face.num < 10:
            facet = face.num % 5
        else:
            facet = (face.num % 5) + 5
        return facet

    @staticmethod
    def get_x_dist(clat, clng):
        '''Document this!!!'''
        cface = Face.get_face_number(clat, clng)
#        out = 'get_x_dist(clat = %s clng = %s) VERTEX_LAT = %s diff = %s' % (clat, clng, VERTEX_LAT, VERTEX_LAT-clat)
#        logging.debug(out)
        if cface == 5:
            d3 = Rhomboid.cartesian_dist(clat, clng, VERTEX_LAT, 36, SEMI_MAJOR_AXIS)
            d0 = Rhomboid.cartesian_dist(clat, clng, -(VERTEX_LAT), 0, SEMI_MAJOR_AXIS)
        else:
            d0 = Rhomboid.cartesian_dist(clat, clng, VERTEX_LAT, -36, SEMI_MAJOR_AXIS)
            d3 = Rhomboid.cartesian_dist(clat, clng, 90, 0, SEMI_MAJOR_AXIS)
        return (d0, d3)

    @staticmethod
    def get_y_dist(clat, clng):
        '''Document this!!!'''
        cface = Face.get_face_number(clat, clng)
        if cface == 5:
            d0 = Rhomboid.cartesian_dist(clat, clng, -(VERTEX_LAT), 0, SEMI_MAJOR_AXIS)
            d0 = math.floor(d0)
            d1 = Rhomboid.cartesian_dist(clat, clng, VERTEX_LAT, -36, SEMI_MAJOR_AXIS)
            d1 = math.floor(d1)
        else:
            d0 = Rhomboid.cartesian_dist(clat, clng, VERTEX_LAT, 36, SEMI_MAJOR_AXIS)
            d0 = math.floor(d0)
            d1 = Rhomboid.cartesian_dist(clat, clng, 90, 0, SEMI_MAJOR_AXIS)
            d1 = math.floor(d1)
        return (d0, d1)

    @staticmethod
    def get_x_edge_fraction(d0, d3):
        '''Document this!!!'''
        dist_from_d0 = (EDGE_LENGTH * EDGE_LENGTH - d3 * d3 + d0 * d0) / (2 * EDGE_LENGTH)
        edge_fraction = dist_from_d0 / EDGE_LENGTH

#        dist_from_d0 = (EDGE_LENGTH * EDGE_LENGTH - d3 * d3 + d0 * d0) / (2 * EDGE_LENGTH)
#        h = math.sqrt(d0 * d0 - dist_from_d0 * dist_from_d0)
#        dp = h * math.tan(30 * RADIANS)        
#        dist_from_d0 = dist_from_d0 + dp
#        if dist_from_d0 > (d0 / 2):
#            edge_angle = VERTEX_ANGLE / 2
#            edge_angle = edge_angle + math.atan((dist_from_d0 - (d0 / 2)) / MID_EDGE_RADIUS) / RADIANS
#        else:
#            edge_angle = VERTEX_ANGLE / 2
#            edge_angle = edge_angle - math.atan(((d0 / 2) - dist_from_d0) / MID_EDGE_RADIUS) / RADIANS
#        edge_fraction = edge_angle / VERTEX_ANGLE
        return edge_fraction

    @staticmethod
    def get_y_edge_fraction(d0, d1):
        '''Document this!!!'''
        dist_from_d0 = (EDGE_LENGTH * EDGE_LENGTH - d1 * d1 + d0 * d0) / (EDGE_LENGTH * 2)
        edge_fraction = dist_from_d0 / EDGE_LENGTH
        
#        dist_from_d0 = (EDGE_LENGTH * EDGE_LENGTH - d1 * d1 + d0 * d0) / (EDGE_LENGTH * 2)
#        h = math.sqrt(d0 * d0 - dist_from_d0 * dist_from_d0)        
#        dp = h * math.tan(30 * RADIANS) 
#        dist_from_d0 = dist_from_d0 + dp       
#        dist_from_d0 = math.floor(dist_from_d0)
#        if dist_from_d0 > (d0 / 2):
#            edge_angle = VERTEX_ANGLE / 2
#            edge_angle = edge_angle + math.atan((dist_from_d0 - (d0 / 2)) / MID_EDGE_RADIUS) / RADIANS
#        else:
#            edge_angle = VERTEX_ANGLE / 2
#            edge_angle = edge_angle - math.atan(((d0 / 2) - dist_from_d0) / MID_EDGE_RADIUS) / RADIANS
#        edge_fraction = edge_angle / VERTEX_ANGLE
        return edge_fraction
        
    @staticmethod
    def calc_x_index(clat, clng, cell_count = None):
        '''Document this!!! Include conventions for points that lie on boundaries.'''
        if cell_count == None:
            cell_count = CELL_COUNT
            
        d0, d3 = Rhomboid.get_x_dist(clat, clng)
#        out = 'd0=%s, d3=%s' % (d0, d3)
#        logging.debug(out)
        if d3 < 1:
            return cell_count - 1;
        if d0 < 1:
            return 0;        
        edge_fraction = Rhomboid.get_x_edge_fraction(d0, d3)
        cell_index = int(cell_count * edge_fraction)
        return cell_index
        
    @staticmethod
    def calc_y_index(clat, clng, cell_count = None):
        '''Document this!!! Include conventions for points that lie on boundaries.'''
        if cell_count == None:
            cell_count = CELL_COUNT

        d0, d1 = Rhomboid.get_y_dist(clat, clng)
#        out = 'd0=%s, d1=%s' % (d0, d1)
#        logging.debug(out)
        if d0 < 1:
            return 0
        if d1 < 1:
            return cell_count - 1
        edge_fraction = Rhomboid.get_y_edge_fraction(d0, d1)
        cell_index = int(cell_count * edge_fraction)
        return cell_index
        
    def __init__(self, lat, lng, cell_count = None):
        self.face = Face(lat, lng)
        self.clat = self.canonical_lat(self.face)
        self.clng = self.canonical_lng(self.face)
        self.num = self.calc_num(self.face)
        self.x = self.calc_x_index(self.clat, self.clng, cell_count)
        self.y = self.calc_y_index(self.clat, self.clng, cell_count)
        self.key = get_cell_key( (self.num, self.x, self.y) )

def get_cell_polygon(cell_key, cell_count = None):
    '''Return the polygon for a given cell_key and cell_count. Polygon vertexes are in lng, lat pairs.'''
#    out = 'get_cell_polygon(): cell_key = %s' % (str(cell_key))
#    logging.debug(out)
    rhomboid_num, x, y = cell_key.split('-')
#    out = 'r = %s x = %s y = %s cell_key = %s' % (rhomboid_num, x, y, cell_key)
#    logging.debug(out)
    return Cell.polygon(int(rhomboid_num), int(x), int(y), cell_count)

def get_cell_key_from_lat_lng(lat, lng, cell_count = None):
    '''Return the key for the cell in which the geographic latitude and longitude lie.'''
    return Rhomboid(lat,lng, cell_count).key

def is_point_in_bounding_box(lat, lng, bb):
    '''
    Returns true if the point given by lat, lng is within the confines of the NW to SE-oriented bounding box
    given by bb.
    ''' 
    bb_n = bb[0][0]
    bb_w = bb[0][1]
    bb_s = bb[1][0]
    bb_e = bb[1][1]
    if float(lat) > float(bb_n):
        return False
    if float(lat) < float(bb_s):
        return False
    if is_lng_between(lng, bb_w, bb_e):
        return True
    return False
    
def get_oriented_bounding_box(from_ll, to_ll, orientation = 0):
    '''
    Return the latitude/longitude of the NW corner and SE corner of a bounding box
    that begins in the NW corner and goes E and S from there to the SE corner using 
    the orientation (non-negative means west to east) to determine the global extent.
    For example; 
    from_ll (-1,-1) to_ll (1,1) orientation >= 0 is a 2 by 2 degree bounding box with NW corner
    (1,-1) and SE corner (-1,1)
    
    while
    from_ll (-1,-1) to_ll (1,1) orientation < 0 is a 2 by 358 degree bounding box with NW corner
    (1,1) and SE corner (-1,-1)
    
    while
    from_ll (1,1) to_ll (-1,-1) orientation >= 0 is a 2 by 358 degree bounding box with NW corner
    (1,1) and SE corner (-1,-1)
    
    and
    from_ll (1,1) to_ll (-1,-1) orientation < 0 is a 2 by 2 degree bounding box with NW corner
    (1,-1) and SE corner (-1,1)    
    '''  
#    out = 'ENTER get_oriented_bounding_box(): from_ll = %s to_ll = %s orientation = %s' % (from_ll, to_ll, orientation)
#    logging.debug(out)
    
    from_lat = float(from_ll[0])
    from_lng = float(from_ll[1])
    to_lat = float(to_ll[0])
    to_lng = float(to_ll[1])
    
#    out = 'get_oriented_bounding_box(): from_ll: %s to_ll: %s orientation: %s' % (from_ll, to_ll, orientation)
#    logging.debug(out)
#    out = 'get_oriented_bounding_box(): from_lat: %s from_lng: %s to_lat: %s to_lng: %s' % (from_lat, from_lng, to_lat, to_lng)
#    logging.debug(out)

    '''Set north and south limits of the bounding box from the input corners.'''
    if from_lat >= to_lat:
        bb_n = from_lat
        bb_s = to_lat
#        out = 'get_oriented_bounding_box() 1: from_lat: %s >= to_lat: %s' % (from_lat, to_lat)
#        logging.debug(out)
    else:
        bb_n = to_lat
        bb_s = from_lat
#        out = 'get_oriented_bounding_box() 2: from_lat: %s < to_lat: %s' % (from_lat, to_lat)
#        logging.debug(out)

    '''Set east and west limits of the bounding box from the input corners respecting orientation.'''
    if orientation >= 0:
        bb_w = lng180(from_lng)
        bb_e = lng180(to_lng)
#        out = 'get_oriented_bounding_box() 3: orientation %s >= 0 bb_w: %s bb_e: %s' % (orientation, bb_w, bb_e)
#        logging.debug(out)
    else:
        bb_e = lng180(from_lng)
        bb_w = lng180(to_lng)
#        out = 'get_oriented_bounding_box() 4: orientation %s < 0 bb_w: %s bb_e: %s' % (orientation, bb_w, bb_e)
#        logging.debug(out)
        
    '''Bounding box defined by vertexes (bb_n, bb_w) and (bb_s, bb_e).'''
    bb = ((bb_n, bb_w), (bb_s, bb_e))
#    out = 'get_oriented_bounding_box() 5: bb: %s' % (str(bb))
#    logging.debug(out)
    return bb
    
def get_tile(from_ll, to_ll, orientation, cell_count = None):
    '''
    Return a list of TMG keys given a direction-sensitive geographic coordinate bounding box. 
    Orientation of the bounding box matters, as this function is meant to support bounding 
    boxes that span more than 180 degrees of longitude. The tile will be defined from the 
    corner given by from_ll to the corner given by to_ll in the direction given by orientation. 
    Then tile determinations will be done from NW corner of the bounding box to the SE corner.
    '''
#    out = 'ENTER get_tile(): from_ll = %s to_ll = %s orientation = %s cell_count = %s' % (from_ll, to_ll, orientation, cell_count)
#    logging.debug(out)

    '''If no cell_count is provided, use the default constant CELL_COUNT.'''
    if cell_count == None:
        cell_count = CELL_COUNT


    '''Bounding box defined by vertexes (bb_n, bb_w) and (bb_s, bb_e).'''
    bb = get_oriented_bounding_box(from_ll, to_ll, orientation)
    bb_n = bb[0][0]
    bb_w = bb[0][1]
    bb_s = bb[1][0]
    bb_e = bb[1][1]
    
#    out = 'get_tile(): From Lat/Lng: %s To Lat/Lng: %s Orientation: %s Bounding Box bb = %s' % (from_ll, to_ll, orientation, bb)
#    logging.debug(out)

    '''Begin cell iteration in the northwest corner of the bounding box.'''
    start_cell_key = get_cell_key_from_lat_lng(bb_n, bb_w, cell_count)
#    out = 'get_tile(): start_cell_key: %s bb_n = %s bb_w = %s' % (start_cell_key, bb_n, bb_w)
#    logging.debug(out)

    '''The tile will be stored as a list of keys.'''
    key_list = []
    last_cell_key = start_cell_key

    '''
    Start in the NW corner of the bounding box, but look to see if the cell to the 
    SW of this intersects the bounding box as well. If it does, start there instead.
    Add whichever is the starting cell to the list of keys, then iterate NE adding cells 
    until they no longer intersect the bounding box. 
    Then go one cell south from the one that started the iteration in the NE direction. If that's
    in the bounding box, iterate NE again from there as above. 
    '''
    while start_cell_key != None and cell_in_bb(start_cell_key, bb, cell_count):
        cell_key_sw = get_cell_key(next_cell_sw(start_cell_key, cell_count))
        if cell_key_sw != None and cell_in_bb(cell_key_sw, bb, cell_count):
            start_cell_key = cell_key_sw
        cursor = start_cell_key
        while cell_in_bb(cursor, bb, cell_count):
            key_list.append(cursor)
#            out = 'get_tile(): key_list = %s' % (key_list)
#            logging.debug(out)
            cursor = get_cell_key(next_cell_ne(cursor, cell_count))
        last_cell_key = start_cell_key
        start_cell_key = get_cell_key(next_cell_south(bb_w, start_cell_key, cell_count))
    next_key_ne = get_cell_key(next_cell_ne(last_cell_key, cell_count))
#    out = 'get_tile(): last_cell_key = %s' % (last_cell_key)
#    logging.debug(out)
#    out = 'get_tile(): next_key_ne = %s' % (next_key_ne)
#    logging.debug(out)
    '''
    Up to this point the cells intersecting the west edge of the bounding box 
    have been included in the list along with all of the ones NE from these that
    are also within the bounding box.
    The next step is to iterate along the cells intersecting the southern edge of the 
    bounding box and those NE from these that are also within the bounding box.
    ''' 
    next_e = get_cell_key(next_cell_east(bb_s, last_cell_key, cell_count))
    if next_e == next_key_ne:
#        out = 'get_tile(): next_key_ne = %s' % (next_key_ne)
#        logging.debug(out)
        next_e = next_cell_east(bb_s, next_key_ne, cell_count)
#        out = 'get_tile(): next_e = %s' % (str(next_e))
#        logging.debug(out)
        start_cell_key = get_cell_key(next_e)
    else:
        start_cell_key = get_cell_key(next_cell_east(bb_s, last_cell_key, cell_count))
    cursor = start_cell_key
    while cell_in_bb(cursor, bb, cell_count):
        key_list.append(cursor)
        cursor = get_cell_key(next_cell_ne(cursor, cell_count))
        start_cell_key = get_cell_key(next_cell_east(bb_s, start_cell_key, cell_count))
    return key_list

def lng_distance(west_lng, east_lng):
    '''Returns the number of degrees from west_lng going eastward to east_lng.'''
    w = lng180(west_lng)
    e = lng180(east_lng)
    if equal_within_tolerance(w, e, DEGREE_DIGITS):
        '''
        Convention: If west and east are the same, the whole circumference is meant 
        rather than no difference.
        '''
        return 360
    if e <= 0:
        if w <= 0:
            if w > e:
                '''w and e both in western hemisphere with w east of e.'''
                return 360 + e - w
            '''w and e in western hemisphere with w west of e.'''
            return e - w
        '''w in eastern hemisphere and e in western hemisphere.'''
        return 360 + e - w
    if w <= 0:
        '''w in western hemisphere and e in eastern hemisphere.'''
        return e - w
    if w > e:
        '''w and e both in eastern hemisphere with w east of e.''' 
        return 360 + e - w
    '''w and e both in eastern hemisphere with w west or e.'''
    return e - w
            
def is_lng_between(lng, west_lng, east_lng):
    '''
    Returns true if the given lng is between the longitudes west_lng and east_lng
    proceeding east from west_lng to east_lng.
    '''
    if equal_within_tolerance( float(lng), float(west_lng), DEGREE_DIGITS) or equal_within_tolerance( float(lng), float(east_lng), DEGREE_DIGITS):
        return True
    west_to_east = lng_distance(west_lng, east_lng)
    lng_to_east = lng_distance(lng, east_lng)
    if west_to_east >= lng_to_east:
        return True
    return False
    
def cell_in_bb(cell_key, bb, cell_count = None):
    '''
    Return True if any part of the cell referred to by cell_key overlaps the NW to SE-oriented 
    bounding box bb, False otherwise.
    '''
    '''If no cell_count is provided, use the default constant CELL_COUNT.'''
    if cell_count == None:
        cell_count = CELL_COUNT

    '''Cell polygon returns vertexes as strings in lng, lat order.'''
    p = get_cell_polygon(cell_key, cell_count)
    '''
    For South vertex at -90 latitude:
        S-out, E, N, W, S-in
    For North vertex at 90 latitude:
        S, E, N-in, N-out, W, S
    For all other cells:
        S, E, N, W, S
    '''
    s = float(p[0][1])
    e = lng180(float(p[1][0]))
    n = float(p[2][1])
    w = lng180(float(p[len(p)-2][0]))

    '''Bounding box is expected to be oriented NW to SE with points in lat,lng order.'''
    bb_s = bb[1][0]
    bb_e = bb[1][1]
    bb_n = bb[0][0]
    bb_w = bb[0][1]

    '''First test: if southern vertex is north of the bounding box, there is no overlap.'''
    if s > bb_n:
        return False
    '''Second test: if northern vertex is south of the bounding box, there is no overlap.'''
    if n < bb_s:
        return False
    
    '''Third set of tests: If any cell vertex is in the bounding box, there is overlap.'''
    '''Is S vertex in bounding box?'''
    if is_point_in_bounding_box(float(p[0][1]), lng180(float(p[0][0])), bb):
        return True
    '''Is E vertex in bounding box?'''
    if is_point_in_bounding_box(p[1][1], p[1][0], bb):
        return True
    '''Is N vertex in bounding box?'''
    if is_point_in_bounding_box(p[2][1], p[2][0], bb):
        return True
    '''Is W vertex in bounding box?'''
    if is_point_in_bounding_box(p[len(p)-2][1], p[len(p)-2][0], bb):
        return True

    '''Fourth set of tests: If any bounding box corner is within the cell, there is overlap.'''
    test_key = get_cell_key_from_lat_lng( bb_n, bb_w, cell_count )
    if test_key == cell_key:
        '''NW corner is in the cell.'''
        return True
    test_key = get_cell_key_from_lat_lng( bb_n, bb_e, cell_count )
    if test_key == cell_key:
        '''NE corner is in the cell.'''
        return True
    test_key = get_cell_key_from_lat_lng( bb_s, bb_w, cell_count )
    if test_key == cell_key:
        '''SW corner is in the cell.'''
        return True
    test_key = get_cell_key_from_lat_lng( bb_s, bb_e, cell_count )
    if test_key == cell_key:
        '''SE corner is in the cell.'''
        return True
    
    '''It is still possible that there is overlap.'''
    '''
    Fifth set of tests: If a meridian or parallel crosses a cell edge.
    Note that only one meridian and one parallel need to be tested, because if one
    crosses, both must cross, otherwise the cell vertex 
    would be in the bounding box, and that has already been tested.
    Also, only one of each pair of adjacent edges need to be tested, because if one
    is crossed, both must be crossed, otherwise the bounding box corner would
    be in the cell, and that too has already been tested.
    '''
    if is_lng_between(get_nearest_lng_where_lat_crosses_circle(bb_n, p[0], p[1]), p[0][0], p[1][0]):
        '''N edge of the bounding box crosses the edge of the cell between the south and east vertexes.'''
        return True
    if is_lng_between(get_nearest_lng_where_lat_crosses_circle(bb_n, p[len(p)-2], p[len(p)-3]), p[len(p)-2][0], p[len(p)-3][0]):
        '''N edge of the bounding box crosses the edge of the cell between the west and north vertexes.'''
        return True
    #TO DO: Test for the two possible meridians crossing p[0] to p[1] and p[len(p)-1] to p[len(p)-2].
    return False

def get_nearest_lng_where_lat_crosses_circle(lat3, p0, p1):
    '''
    Return the longitude (in degrees) of the point (if any) where a parallel (line of latitude) crosses a great
    circle defined by p0 and p1 (defined by lng, lat).  A parallel crosses a great circle in exactly zero or
    two places unless the p0 an p1 are on the equator, which, for the purposes of rhomboid edges
    never occurs. Choose the intersection that lies between the points p0 and p1 along the edge of a rhomboid.
    '''
    '''
    Suppose a great circle passes through (lat1,lon1) and (lat2,lon2). It crosses the parallel lat3 at longitudes 
    lng3_1 and lng3_2 given by:
    '''
    lat1 = float(p0[1]) * RADIANS
    lat2 = float(p1[1]) * RADIANS
    lng1 = float(p0[0]) * RADIANS
    lng2 = float(p1[0]) * RADIANS
    l12 = lng1 - lng2
    A = math.sin(lat1) * math.cos(lat2) * math.cos(lat3) * math.sin(l12)
    B = math.sin(lat1) * math.cos(lat2) * math.cos(lat3) * math.cos(l12) - math.cos(lat1) * math.sin(lat2) * math.cos(lat3)
    C = math.cos(lat1) * math.cos(lat2) * math.sin(lat3) * math.sin(l12)
    '''atan2(y,x) convention.'''
    lng = math.atan2(B,A)
    if math.fabs(C) > math.sqrt(A*A + B*B):
        '''no crossing'''
        return None
    else:
        dlng = math.acos( C / math.sqrt(A*A + B*B) )
        lng3_1 = (lng1 + dlng + lng + math.pi) % (2 * math.pi) - math.pi
        if is_lng_between(lng3_1, lng1, lng2):
            return lng3_1
        else:
            lng3_2 = (lng1 - dlng + lng + math.pi) % (2 * math.pi) - math.pi
            return lng3_2
    
def get_cell_attributes(cell_key):
    rhomboid_num, x, y = cell_key.split('-')
    rhomboid_num = int(rhomboid_num)
    x = int(x)
    y = int(y)
    return (rhomboid_num, x, y)
        
def get_cell_key(tuple):
    '''Given a rhomboid_num, x, y tuple, return the cell key.'''
    return '%s-%s-%s' % (tuple[0], tuple[1], tuple[2])

def next_cell_ne(cell_key, cell_count = None):        
    '''
    Return the indexes for the cell adjacent in the NE direction to the given cell.
    ''' 

    '''If no cell_count is provided, use the default constant CELL_COUNT.'''
    if cell_count == None:
        cell_count = CELL_COUNT

    '''Get the rhomboid_num, x, and y from the cell_key'''
    rhomboid_num, x, y = get_cell_attributes(cell_key)

    if x < cell_count - 1:
        '''Next cell NE is in the same rhomboid.'''
        return (rhomboid_num, x + 1, y)

    '''Next cell NE is in an adjacent rhomboid.'''
    if rhomboid_num < 5:
        '''The rhomboid is one of the 5 northern ones.'''
        if x == cell_count - 1 and y == cell_count - 1:
            '''
            The given cell is the northernmost cell in the given rhomboid.
            The one to the northeast is the northernmost cell in the next rhomboid
            to the east.
            '''
            return ((rhomboid_num + 1) % 5, cell_count - 1, cell_count - 1)
        return ((rhomboid_num + 1) % 5, 0, y)
    
    '''The rhomboid is one of the 5 southern ones.'''
    return ((rhomboid_num + 1) % 5, 0, y)

def next_cell_se(cell_key, cell_count = None):
    '''
    Return the indexes for the cell adjacent in the SE direction to the given cell.
    ''' 
    
    '''If no cell_count is provided, use the default constant CELL_COUNT.'''
    if cell_count == None:
        cell_count = CELL_COUNT
    
#    out = 'ENTER next_cell_se(): cell_key = %s' % (cell_key)
#    logging.debug(out)

    '''Get the rhomboid_num, x, and y from the cell_key'''
#    out = 'next_cell_se(): cell_key = %s' % (cell_key)
#    logging.debug(out)
    rhomboid_num, x, y = get_cell_attributes(cell_key)

    if y > 0:
        '''Next cell SE is in the same rhomboid.'''
        return (rhomboid_num, x, y - 1)

    '''Next cell SE is in an adjacent rhomboid.'''
    if rhomboid_num < 5:
        '''The rhomboid is one of the 5 northern ones.'''
        return (5 + (rhomboid_num % 5), x, cell_count - 1)

    '''The rhomboid is one of the 5 southern ones.'''
    if x == 0 and y == 0:
        '''The given cell is the southernmost cell in the given rhomboid.'''
        return None
            
    return (5 + (rhomboid_num + 1) % 5, x, cell_count - 1)

def next_cell_sw(cell_key, cell_count = None):
    '''
    Return the indexes for the cell adjacent in the SW direction to the given cell.
    ''' 
    
    '''If no cell_count is provided, use the default constant CELL_COUNT.'''
    if cell_count == None:
        cell_count = CELL_COUNT
    
    '''Get the rhomboid_num, x, and y from the cell_key'''
    rhomboid_num, x, y = get_cell_attributes(cell_key)

    if x > 0:
        '''Next cell SW is in the same rhomboid.'''
        return (rhomboid_num, x - 1, y)

    '''Next cell SW is in an adjacent rhomboid.'''
    if rhomboid_num < 5:
        '''The rhomboid is one of the 5 northern ones.'''
        return (5 + (rhomboid_num + 4) % 5, cell_count - 1, y)

    '''The rhomboid is one of the 5 southern ones.'''
    if x == 0 and y == 0:
        '''The given cell is the southernmost cell in the given rhomboid.'''
        return None
            
    return (5 + (rhomboid_num - 1) % 5, cell_count - 1, y)

def next_cell_south(lng, cell_key, cell_count = None):
    '''
    Return the indexes for the cell adjacent to the south of the given cell.
    ''' 
    
    '''If no cell_count is provided, use the default constant CELL_COUNT.'''
    if cell_count == None:
        cell_count = CELL_COUNT

    next_se = next_cell_se(cell_key, cell_count)
    if next_se == None:
        '''The given cell is the southernmost cell in a southern rhomboid.'''
        return None
    if lng_in_cell(lng, get_cell_key(next_se), cell_count):
        '''lng crosses the cell to the SE of the given cell.'''
        return next_se
    next_sw = next_cell_sw(cell_key, cell_count)
    if lng_in_cell(lng, get_cell_key(next_sw), cell_count):
        '''lng crosses the cell to the SW of the given cell.'''
        return next_cell_sw(cell_key, cell_count)
    return None

def lng_in_cell(lng, cell_key, cell_count = None):
    '''
    Return True if the longitude given by lng crosses the cell given by cell_key
    for the given cell_count.
    '''

    lng = lng180(lng)
    '''Cell polygon has vertexes in lng, lat pairs.'''
    p = get_cell_polygon(cell_key, cell_count)
    '''
    For South vertex at -90 latitude:
        S-out, E, N, W, S-in
    For North vertex at 90 latitude:
        S, E, N-in, N-out, W, S
    For all other cells:
        S, E, N, W, S
    So, the east vertex is always the second point in the cell polygon and
    the west vertex is always the penultimate point in the cell polygon. 
    '''
    
    '''get_cell_polygon returns points as strings in (lng, lat) pairs.'''
    e = lng180(float(p[1][0]))
    w = lng180(float(p[len(p)-2][0]))
    
    '''
    e_w_dist is the distance (in degrees) between the east and
    west vertexes of the given cell.
    '''
    e_w_dist = e - w
    if e_w_dist < 0:
        '''Cell crosses longitude 180.'''
        e_w_dist = e_w_dist + 360
    '''
    lng_w_dist is the distance (in degrees) between the given lng and the
    west vertex of the given cell.
    '''
    lng_w_dist = lng - w
    if lng_w_dist < 0:
        '''West vertex and lng in opposite hemispheres.'''
        lng_w_dist = lng_w_dist + 360
    if lng_w_dist > e_w_dist:
        '''lng is not between east and west vertexes'''
        return False
    
    '''lng is between east and west vertexes'''
    return True

def next_cell_east(lat, cell_key, cell_count = None):
    '''
    Return the cell (if any) due east of the given longitude and
    cell given by cell_key, cell_count.
    ''' 
    
    '''If no cell_count is provided, use the default constant CELL_COUNT.'''
    if cell_count == None:
        cell_count = CELL_COUNT

#    out = 'ENTER next_cell_east(): lat = %s cell_key = %s' % (lat, cell_key)
#    logging.debug(out)
    next_se = next_cell_se(cell_key, cell_count)
    if next_se == None:
        '''
        The given cell is the southernmost cell in a southern rhomboid.
        next_se is east of cell_key.
        '''
        '''Get the rhomboid_num, x, and y from the cell_key'''
        rhomboid_num, x, y = get_cell_attributes(cell_key)
        next_se = (5 + (rhomboid_num + 1) % 5, x, y)
        return next_se
    
    if lat_in_cell(lat, get_cell_key(next_se), cell_count):
        '''lat crosses the cell to the SE of the given cell.'''
        return next_se
    '''lat crosses the cell to the NE of the given cell.'''
    return next_cell_ne(cell_key, cell_count)

def lat_in_cell(lat, cell_key, cell_count = None):
    '''
    Return True if the latitude given by lat crosses the cell given by cell_key
    for the given cell_count.
    '''
    p = get_cell_polygon(cell_key, cell_count)
    '''
    For South vertex at -90 latitude:
        S-out, E, N, W, S-in
    For North vertex at 90 latitude:
        S, E, N-in, N-out, W, S
    For all other cells:
        S, E, N, W, S
    '''
    
    '''get_cell_polygon returns points in (lng, lat) pairs.'''
    s = float(p[0][1])
    n = float(p[2][1])

    if lat < s:
        '''lat is south of southern vertex of cell'''
        return False
    if lat > n:
        '''lat is north of northern vertex of cell'''
        return False
    return True

def lat_in_cell_test(cell_count = None):
    '''If no cell_count is provided, use the default constant CELL_COUNT.'''
    if cell_count == None:
        cell_count = CELL_COUNT
    lat = 90.0
    cell_key = get_cell_key( (0, cell_count - 1, cell_count - 1) )
    if not (lat_in_cell(lat, cell_key, cell_count)):
        out = 'FAIL: lat_in_cell_test() lat = %s not in cell_key = %s with cell_count = %s' % (lat, cell_key, cell_count)
        logging.debug(out)
        return False
    lat = -90.0
    for r in range(5,10):
        cell_key = get_cell_key( (r, 0, 0) )
        if not (lat_in_cell(lat, cell_key, cell_count)):
            out = 'FAIL: lat_in_cell_test() lat = %s not in cell_key = %s with cell_count = %s' % (lat, cell_key, cell_count)
            logging.debug(out)
            return False
    lat = -VERTEX_LAT
    for r in range(0,5):
        cell_key = get_cell_key( (r, 0, 0) )
        if not (lat_in_cell(lat, cell_key, cell_count)):
            out = 'FAIL: lat_in_cell_test() lat = %s not in cell_key = %s with cell_count = %s' % (lat, cell_key, cell_count)
            logging.debug(out)
            return False
    lat = VERTEX_LAT
    for r in range(5,10):
        cell_key = get_cell_key( (r, cell_count - 1, cell_count - 1) )
        if not (lat_in_cell(lat, cell_key, cell_count)):
            out = 'FAIL: lat_in_cell_test() lat = %s not in cell_key = %s with cell_count = %s' % (lat, cell_key, cell_count)
            logging.debug(out)
            return False
    out = 'PASS: lat_in_cell_test()'
    logging.debug(out)
    return True

def lng_in_cell_test(cell_count = None):
    '''If no cell_count is provided, use the default constant CELL_COUNT.'''
    if cell_count == None:
        cell_count = CELL_COUNT

    for r in range(5):
        lng = lng180(r * 72)
        cell_key = get_cell_key( (r, cell_count - 1, cell_count - 1) )
        if not (lng_in_cell(lng, cell_key, cell_count)):
            out = 'FAIL: lng_in_cell_test() lng = %s not in cell_key = %s with cell_count = %s' % (lng, cell_key, cell_count)
            logging.debug(out)
            return False
        cell_key = get_cell_key( (r, 0, 0) )
        if not (lng_in_cell(lng, cell_key, cell_count)):
            out = 'FAIL: lng_in_cell_test() lng = %s not in cell_key = %s with cell_count = %s' % (lng, cell_key, cell_count)
            logging.debug(out)
            return False
        lng = lng180((r * 72) + 36)
        cell_key = get_cell_key( (r, cell_count - 1, 0) )
        if not (lng_in_cell(lng, cell_key, cell_count)):
            out = 'FAIL: lng_in_cell_test() lng = %s not in cell_key = %s with cell_count = %s' % (lng, cell_key, cell_count)
            logging.debug(out)
            return False
        lng = lng180((r * 72) - 36)
        cell_key = get_cell_key( (r, 0, cell_count - 1) )
        if not (lng_in_cell(lng, cell_key, cell_count)):
            out = 'FAIL: lng_in_cell_test() lng = %s not in cell_key = %s with cell_count = %s' % (lng, cell_key, cell_count)
            logging.debug(out)
            return False
    out = 'PASS: lng_in_cell_test()'
    logging.debug(out)
    return True

def next_cell_east_test(cell_count = None):
    '''If no cell_count is provided, use the default constant CELL_COUNT.'''
    if cell_count == None:
        cell_count = CELL_COUNT

    lat = 90.0
    for r in range(5):
        testkey = get_cell_key( (r, cell_count - 1, cell_count - 1) )
        resultkey = get_cell_key( ((r + 1) % 5, cell_count - 1, cell_count - 1) )
        cell_east = next_cell_east(lat, testkey, cell_count)
        cell_east_key = get_cell_key(cell_east)
        if cell_east_key != resultkey:
            out = 'FAIL: next_cell_east_test() %s not next cell east of %s at lat = %s. Should be %s' % (cell_east, testkey, lat, resultkey)
            logging.debug(out)
            return False
    lat = -90.0
    for r in range(6,10):
        testkey = get_cell_key( (r, 0, 0) )
        resultkey = get_cell_key( (5 + (r + 1) % 5, 0, 0) )
        cell_east = next_cell_east(lat, testkey, cell_count)
        cell_east_key = get_cell_key(cell_east)
        if cell_east_key != resultkey:
            out = 'FAIL: next_cell_east_test() %s not next cell east of %s at lat = %s. Should be %s' % (cell_east, testkey, lat, resultkey)
            logging.debug(out)
            return False
    lat = -VERTEX_LAT
    for r in range(5):
        testkey = get_cell_key( (r, 0, 0) )
        resultkey = get_cell_key( (5 + (r % 5), 0, cell_count - 1) )
        cell_east = next_cell_east(lat, testkey, cell_count)
        cell_east_key = get_cell_key(cell_east)
        if cell_east_key != resultkey:
            out = 'FAIL: next_cell_east_test() %s not next cell east of %s at lat = %s. Should be %s' % (cell_east, testkey, lat, resultkey)
            logging.debug(out)
            return False
    lat = VERTEX_LAT
    for r in range(6, 10):
        testkey = get_cell_key( (r, cell_count - 1, cell_count - 1) )
        resultkey = get_cell_key( ((1 + r) % 5, 0, cell_count - 1) )
        cell_east = next_cell_east(lat, testkey, cell_count)
        cell_east_key = get_cell_key(cell_east)
        if cell_east_key != resultkey:
            out = 'FAIL: next_cell_east_test() %s not next cell east of %s at lat = %s. Should be %s' % (cell_east, testkey, lat, resultkey)
            logging.debug(out)
            return False
    out = 'PASS: next_cell_east_test()'
    logging.debug(out)
    return True

def next_cell_south_test(cell_count = None):
    '''If no cell_count is provided, use the default constant CELL_COUNT.'''
    if cell_count == None:
        cell_count = CELL_COUNT

    for r in range(5):
        lng = lng180(r * 72)
        testkey = get_cell_key( (r, cell_count - 1, cell_count - 1) )
        resultkey = get_cell_key( (r, cell_count - 1, cell_count - 2) )
        cell_south = next_cell_south(lng, testkey, cell_count)
        cell_south_key = get_cell_key(cell_south)
        if cell_south_key != resultkey:
            out = 'FAIL: next_cell_south_test() %s not next cell south of %s at lng = %s. Should be %s' % (cell_south, testkey, lng, resultkey)
            logging.debug(out)
            return False
    for r in range(5,10):
        lng = lng180(r * 72)
        testkey = get_cell_key( (r, 0, cell_count - 1) )
        resultkey = get_cell_key( (r, 0, cell_count - 2) )
        cell_south = next_cell_south(lng, testkey, cell_count)
        cell_south_key = get_cell_key(cell_south)
        if cell_south_key != resultkey:
            out = 'FAIL: next_cell_south_test() %s not next cell south of %s at lng = %s. Should be %s' % (cell_south, testkey, lng, resultkey)
            logging.debug(out)
            return False
    for r in range(5):
        lng = lng180(r * 72)
        testkey = get_cell_key( (r, 0, 0) )
        resultkey = get_cell_key( (5 + (r % 5), 0, cell_count - 1) )
        cell_south = next_cell_south(lng, testkey, cell_count)
        cell_south_key = get_cell_key(cell_south)
        if cell_south_key != resultkey:
            out = 'FAIL: next_cell_south_test() %s not next cell south of %s at lng = %s. Should be %s' % (cell_south, testkey, lng, resultkey)
            logging.debug(out)
            return False
    for r in range(6,10):
        lng = lng180(36 + (r * 72))
        testkey = get_cell_key( (r, cell_count - 1, cell_count - 1) )
        resultkey = get_cell_key( (r, cell_count - 1, cell_count - 2) )
        cell_south = next_cell_south(lng, testkey, cell_count)
        cell_south_key = get_cell_key(cell_south)
        if cell_south_key != resultkey:
            out = 'FAIL: next_cell_south_test() %s not next cell south of %s at lng = %s. Should be %s' % (cell_south, testkey, lng, resultkey)
            logging.debug(out)
            return False
    out = 'PASS: next_cell_south_test()'
    logging.debug(out)
    return True

def lng_between_test():
    '''Test 1: Whole earth'''
    w = 0
    e = 0
    lng = 0
    while lng < 360:
        if not is_lng_between(lng, w, e):
            out = 'FAIL: lng_between_test() lng %s should be between %s and %s' % (lng, w, e)
            logging.debug(out)
            return False
        lng = lng + 10
    '''Test 2: Western hemisphere'''
    w = 0
    e = 180
    lng = 0
    while lng < 360:
        if lng <= 180 and not is_lng_between(lng, w, e):
            out = 'FAIL: lng_between_test() lng %s should be between %s and %s' % (lng, w, e)
            logging.debug(out)
            return False
        if lng > 180 and is_lng_between(lng, w, e):
            out = 'FAIL: lng_between_test() lng %s should not be between %s and %s' % (lng, w, e)
            logging.debug(out)
            return False
        lng = lng + 10
    '''Test 3: Eastern hemisphere'''
    w = -180
    e = 0
    lng = -180
    while lng < 180:
        if lng <= 0 and not is_lng_between(lng, w, e):
            out = 'FAIL: lng_between_test() lng %s should be between %s and %s' % (lng, w, e)
            logging.debug(out)
            return False
        if lng > 0 and is_lng_between(lng, w, e):
            out = 'FAIL: lng_between_test() lng %s should not be between %s and %s' % (lng, w, e)
            logging.debug(out)
            return False
        lng = lng + 10
    out = 'PASS: lng_between_test()'
    logging.debug(out)
    
def lng_distance_test():
    w = 0
    e = 0
    while w < 360:
        distance = lng_distance(w,e)
        if distance != 360 - w:
            out = 'FAIL: lng_distance_test() distance = %s. Should be %s' % (distance, 360 - w)
            logging.debug(out)
            return False
        w = w + 10
    w = 0
    e = 10
    while e < 360:
        distance = lng_distance(w,e)
        if distance != e:
            out = 'FAIL: lng_distance_test() distance = %s. Should be %s' % (distance, e)
            logging.debug(out)
            return False
        e = e + 10
    out = 'PASS: lng_distance_test()'
    logging.debug(out)
    return True

def get_bounding_box_test():
    ll_from = (1,1)
    ll_to = (-1,-1)
    orientation = -1
    bb = get_oriented_bounding_box(ll_from, ll_to, orientation)
    out = 'get_bounding_box_test() ll_from = %s ll_to = %s orientation = %s bb = %s.' % (ll_from, ll_to, orientation, bb)
    logging.debug(out)
    
def lat_crosses_circle_test():
    get_nearest_lng_where_lat_crosses_circle(lat3, p0, p1)
    
def test_suite():
    lat_crosses_circle_test()
#    get_bounding_box_test()
#    lng_distance_test()
#    lng_between_test()
#    lat_in_cell_test()
#    lng_in_cell_test()
#    next_cell_east_test()
#    next_cell_south_test()

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)    
    
    f = open('python.out', 'w')

#    test_suite()

#    out = '%s' % (Cell.createKmlMesh(CELL_COUNT))
#    logging.debug(out)

    f.flush()
    f.close()

    parser = OptionParser()
    parser.add_option("-c", "--command", dest="command",
                      help="TGM command",
                      default=None)
    parser.add_option("-f", "--from-ll", dest="from_ll",
                      help="From Lat/Lng",
                      default=None)
    parser.add_option("-t", "--to-ll", dest="to_ll",
                      help="To Lat/Lng",
                      default=None)
    parser.add_option("-o", "--orientation", dest="orientation",
                      help="Orientation",
                      default=None)
    parser.add_option("-n", "--cell-count", dest="cell_count",
                      help="Cell count",
                      default=None)
    parser.add_option("-r", "--rhomboid", dest="rhomboid",
                      help="Rhomboid",
                      default=None)

    (options, args) = parser.parse_args()
    command = options.command
    
    if command == 'test':
        test_suite()
    if command == 'get_tile':
        from_ll = map(float, options.from_ll.split(','))
        to_ll = map(float, options.to_ll.split(','))
        orientation = int(options.orientation)
        cell_count = int(options.cell_count)
        print get_tile(from_ll, to_ll, orientation, cell_count)
    if command == 'get_cell_key':
        from_ll = map(float, options.from_ll.split(','))
        cell_count = int(options.cell_count)
        print get_cell_key_from_lat_lng(from_ll[0], from_ll[1], cell_count)
    if command == 'get_TMG_KML':
        from_ll = map(float, options.from_ll.split(','))
        to_ll = map(float, options.to_ll.split(','))
        orientation = int(options.orientation)
        cell_count = int(options.cell_count)
        print Cell.createBBAsKmlMesh(from_ll, to_ll, orientation, cell_count)
    if command == 'get_rhomboid_KML':
        rhomboid = int(options.rhomboid)
        cell_count = int(options.cell_count)
        print Cell.createKmlMesh(rhomboid, cell_count)
