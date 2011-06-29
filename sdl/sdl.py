#!/usr/bin/env python

# Copyright 2011 Jante LLC and University of Kansas
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__author__ = "Aaron Steele, Dave Vieglais, and John Wieczorek"

"""
This module includes classes and a command line interface for bulkloading 
WorldClim environment variables to CouchDB using the Rectangular Mesh Grid (RMG).
"""

import csv
import couchdb
import logging
import math
from optparse import OptionParser
import os
import random
import shapefile
import shlex
import subprocess
import rmg

#CELLS_PER_DEGREE = 120
#TILE_WIDTH_DEGREES = 30
#
#DEGREE_DIGITS = 7
#FORMAT = """.%sf"""
#
#def lng180(lng):
#    '''Given a longitude in degrees, returns a longitude in degrees between {-180, 180].'''
#    newlng = float(lng)
#    if newlng <= -180:
#        newlng = newlng + 360
#    elif newlng > 180:
#        newlng = newlng - 360
#    return float(truncate(newlng, DEGREE_DIGITS))
#
#def truncate(x, digits):
#    '''Set the representational precision of x to digits places to the right of the decimal.'''
#    format_x = FORMAT % digits
#    return format(x,format_x)
#
#def getpolygon(lng, lat, cells_per_degree = CELLS_PER_DEGREE):
#    '''Returns list of points in lng, lat order for a cell whose center is 
#    given by lng, lat on a grid with resolution defined in the same degrees.
#    Assumes math.fabs(lat) < 90
#    Example: 30 sec grid has 120 cells per degree and resolution = 0.0083333'''
#    resolution = 1.0/cells_per_degree
#    nw = [lng180(lng-resolution/2), lat+resolution/2]
#    ne = [lng180(lng+resolution/2), lat+resolution/2]
#    se = [lng180(lng+resolution/2), lat-resolution/2]
#    sw = [lng180(lng-resolution/2), lat-resolution/2]
#    return [nw, ne, se, sw]

class Variable(object):
    """An environmental variable backed by a .bil and a .hdr file."""

    def __init__(self, bilfile, hdrfile):
        """Constructs a Variable.

        Arguments:
            bilfile - The .bil file path.
            hdrfile - The .hdr file path.
        """
        self.bilfile = bilfile
        self.hdrfile = hdrfile
        
        # Loads xmin, xmax, ymin, and ymax values from the .hdr file:
        for line in open(hdrfile, 'r'):
            if line.startswith('MaxX'):
                self.xmax = int(line.split()[1].strip())
            elif line.startswith('MinX'):
                self.xmin = int(line.split()[1].strip())
            elif line.startswith('MaxY'):
                self.ymax = int(line.split()[1].strip())
            elif line.startswith('MinY'):
                self.ymin = int(line.split()[1].strip())


class TileCell(object):
    """A cell for a Tile described by a polygon with geographic coordinates."""

    def __init__(self, key, polygon, cells_per_degree = CELLS_PER_DEGREE):
        """Constructs a TileCell.

        Arguments:
        """
        self.cells_per_degree
        self.key = key
        self.polygon = polygon
        
    def __str__(self):
        return str(self.__dict__)
    
class Tile(object):
    """A geographic tile defined by a geographic coordinate bounding box."""

    def __init__(self, nwcorner, secorner, filename=None):
        """Tile constructor.

        Arguments:
            nwcorner - the starting Point in the northwest corner of the Tile.
            secorner - the ending Point in the southeast corner of the Tile.
            filename - The name of the input Shapefile for the Tile.
        """
        self.nwcorner = nwcorncer
        self.secorner = secorner
        self.filename = filename
        self.north = nwcorner.lat
        self.south = secorner.lat
        self.west = nwcorner.lng
        self.east = secorner.lng

#    def _getcellkey(self, tilerow, tilecol, cells_per_degree = CELLS_PER_DEGREE):
#        """Gets the global cell key."""
#        x = self.col * self.width * cells_per_degree + tilecol
#        y = self.row * self.width * cells_per_degree + tilerow
#        return '%s-%s' % (x, y)

#    def _getcellpolygon(self, lat, lng, cells_per_degree = CELLS_PER_DEGREE):
#        """Gets the cell polygon given the cells per degree and the lat, lng of the NW corner."""
#        cellres = 1.0/cells_per_degree
#        return [
#                 [lng, lat],                       
#                 [lng + cellres, lat],
#                 [lng + cellres, lat - cellres],
#                 [lng, lat - cellres],
#                 [lng, lat]
#               ]

    def __str__(self):
        return str(self.__dict__)

    def _clip2intersect2couchdb(self, cells, options, batchnum):
        logging.info(self.filename)
        filename = os.path.join(os.path.splitext(self.filename)[0], '%s' % batchnum)
        logging.info(filename)
        w = shapefile.Writer(shapefile.POLYGON)
        w.field('CellKey','C','255')
        for cell in cells:
            w.poly(parts=[cell.polygon])
            w.record(CellKey=cell.key)
        w.save(filename)        
        clippedfile = Tile.clip2cell('%s.shp' % filename, self.filename)
        csvfile = Tile.intersect(clippedfile, options)
        server = couchdb.Server(options.couchurl)
        cdb = server['sdl-dev']    
        cells_per_degree = float(options.cells_per_degree)
        Tile.csv2couch(csvfile, cdb, cells_per_degree)

    @classmethod
    def csv2couch(cls, csvfile, cdb, cells_per_degree = CELLS_PER_DEGREE):
        logging.info('Bulkloading csv file ' + csvfile)
        dr = csv.DictReader(open(csvfile, 'r'))
        cells = {}
        
        #dr.next() # Skip header
        for row in dr:
            cellkey = row.get('CellKey')
            x = float(row.get('x'))
            y = float(row.get('y'))
            if not cells.has_key(cellkey):
                cells[cellkey] = {
                    '_id': cellkey, 
                    'coords': getpolygon(x, y, cells_per_degree),
                    'vars': {}
                    }            
            varname = row.get('RID').split('_')[0]
            varval = row.get('Band1')
            cells.get(cellkey).get('vars')[varname] = varval
        logging.info('Bulkloading %s documents' % len(cells))
        cdb.update(cells.values())

    @classmethod
    def intersect(cls, shapefile, options):      
        """Intesects features in a shapefile with variables via starspan."""
        variables = [os.path.join(options.vardir, x) \
                         for x in os.listdir(options.vardir) \
                         if x.endswith('.bil')]
        variables = reduce(lambda x,y: '%s %s' % (x, y), variables)
        csvfile = shapefile.replace('.shp', '.csv')
        command = 'starspan --vector %s --raster %s --csv %s' \
            % (shapefile, variables, csvfile)
        logging.info(command)
        args = shlex.split(command)
        subprocess.call(args)
        return csvfile
        
    @classmethod
    def clip2cell(cls, src, shapefile):
        """Clips src by shapefile and returns clipped shapefile name."""
        ogr2ogr = '/usr/local/bin/ogr2ogr'
        clipped = src.replace('.shp', '-clipped.shp')
        command = '%s -clipsrc %s %s %s' % (ogr2ogr, shapefile, clipped, src)
        logging.info(command)
        args = shlex.split(command)
        subprocess.call(args)
        return clipped
                
    def bulkload2couchdb(self, options):
        """Bulkloads the tile to CouchDB using command line options."""
        batchsize = int(options.batchsize)
        batchnum = 0
        cells_per_degree = float(options.cells_per_degree)
        cells = []
        count = 0
        for cell in self.getcells(cells_per_degree):
            if count >= batchsize:
                self._clip2intersect2couchdb(cells, options, batchnum)
                count = 0
                cells = []
                batchnum += 1
                continue
            cells.append(cell)
            count += 1
        if count > 0:
            self._clip2intersect2couchdb(cells, options, batchnum)
    
    def clip(self, shapefile, workspace):
        """Clips shapefile against tile and returns clipped Tile object."""
        ogr2ogr = '/usr/local/bin/ogr2ogr'
        this = self.writeshapefile(workspace)
        clipped = this.replace('.shp', '-clipped.shp')
        command = '%s -clipsrc %s %s %s' % (ogr2ogr, this, clipped, shapefile)
        logging.info(command)
        args = shlex.split(command)
        subprocess.call(args)
        return Tile(self.row, self.col, clipped)

    def writeshapefile(self, workspace):
        """Writes tile shapefile in workspace directory and returns filename."""
        cell = self.getcells(30.0).next()            
        fout = os.path.join(workspace, cell.key)
        w = shapefile.Writer(shapefile.POLYGON)
        w.field('CellKey','C','255')
        w.poly(parts=[cell.polygon])
        w.record(CellKey=cell.key)
        w.save(fout)        
        return '%s.shp' % fout

    def writemultishapefiles(self):
        pass

    @staticmethod
    def tile(nwcorner, secorner, cells_per_degree=CELLS_PER_DEGREE, digits=DEGREE_DIGITS, a=SEMI_MAJOR_AXIS, inverse_flattening=INVERSE_FLATTENING):
        """Returns a set of polygons for cells intersecting a bounding box.

        Arguments:
            nwcorner - the starting Point in the northwest corner of the bounding box
            secorner - the ending Point in the southeast corner of the bounding box
            cells_per_degree - the desired resolution of the grid
            digits - the number of digits of precision to retain in the coordinates
            a - the semi-major axis of the ellipsoid for the coordinate reference system
            inverse_flattening - the inverse of the ellipsoid's flattening parameter 
                (298.257223563 for WGS84)
        """ 
        north = nwcorner.lat
        west = nwcorner.lng
        south = secorner.lat
        east = secorner.lng
        lng = west
        lat = north
        # key for the NW corner of the tile
        key = RMGCell.key(lng, lat, cells_per_degree, a, inverse_flattening)
        indexes = key.split('-')
        x_index = int(indexes[0])
        y_index = int(indexes[1])

        while lat >= south:
            while lng <= east:
                polygon = [ [float(x[0]), float(x[1])] for x in RMGCell.polygon(key, cells_per_degree, digits, a, inverse_flattening) ]
                yield TileCell(key, polygon, cells_per_degree)
                x_index += 1
            lng = west
            y_index += 1

#    def getcells(self, cells_per_degree = CELLS_PER_DEGREE):
#        """Iterates over all cells in the tile at the given cell resolution.
#
#        Arguments:
#            cells_per_degree - The number of cells in one degree of lat or lng.
#        """
#        cellres = 1.0/cells_per_degree
#        lng = self.west
#        lat = self.north        
#        row = 0
#        col = 0
#        while lng < self.east:
#            row = 0
#            while lat > self.south:
#                yield TileCell(
#                    self._getcellkey(row, col, cells_per_degree), 
#                    self._getcellpolygon(lat, lng, cells_per_degree),
#                    cells_per_degree)
#                lat -= cellres
#                row += 1
#            lat = self.north
#            lng += cellres
#            col += 1

def _getoptions():
    """Parses command line options and returns them."""
    parser = OptionParser()    
    parser.add_option("-v", 
                      "--vardir", 
                      dest="vardir",
                      help="The directory of variable files.",
                      default=None)
    parser.add_option("-w", 
                      "--workspace", 
                      dest="workspace",
                      help="The workspace directory for temporary files.",
                      default=None)
    parser.add_option("-c", 
                      "--couchurl", 
                      dest="couchurl",
                      help="The CouchDB URL.",
                      default=None)
    parser.add_option("-g", 
                      "--gadm", 
                      dest="gadm",
                      help="The GADM shapefile.",
                      default=None)
    parser.add_option("-t", 
                      "--tile", 
                      dest="tile",
                      help="The Worldclim tile number (rowcol).",
                      default=None)
    parser.add_option("-b", 
                      "--batchsize", 
                      dest="batchsize",
                      help="The batch size (default 25,000)",
                      default=None)
    parser.add_option("-n", 
                      "--cells-per-degree", 
                      dest="cells_per_degree",
                      help="The number of cells in a degree",
                      default=CELLS_PER_DEGREE)
    parser.add_option("-d", 
                      "--dry-run", 
                      dest="dry_run",
                      help="Boolean to run without couchdb.",
                      default=False)

    return parser.parse_args()[0]

def load(options):    
    row = int(options.tile.split(',')[0])
    col = int(options.tile.split(',')[1])
    tile = Tile(row, col)
    clipped = tile.clip(options.gadm, options.workspace)
    logging.info('Clipped: %s' % str(clipped))
    clipped.bulkload2couchdb(options)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    options = _getoptions()
    load(options)    
