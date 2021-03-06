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
WorldClim environment variables to CouchDB.
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

CELLS_PER_DEGREE = 120
TILE_WIDTH_DEGREES = 30

DEGREE_DIGITS = 7
FORMAT = """.%sf"""

def lng180(lng):
    '''Given a longitude in degrees, returns a longitude in degrees between {-180, 180].'''
    newlng = float(lng)
    if newlng <= -180:
        newlng = newlng + 360
    elif newlng > 180:
        newlng = newlng - 360
    return float(truncate(newlng, DEGREE_DIGITS))

def truncate(x, digits):
    '''Set the representational precision of x to digits places to the right of the decimal.'''
    format_x = FORMAT % digits
    return format(x,format_x)

def getpolygon(lng, lat, cpd = CPD):
    '''Returns list of points in lng, lat order for a cell whose center is 
    given by lng, lat on a grid with resolution defined in the same degrees.
    Assumes math.fabs(lat) < 90
    Example: 30 sec grid has 120 cells per degree and resolution = 0.0083333'''
    resolution = 1.0/cpd
    nw = [lng180(lng-resolution/2), lat+resolution/2]
    ne = [lng180(lng+resolution/2), lat+resolution/2]
    se = [lng180(lng+resolution/2), lat-resolution/2]
    sw = [lng180(lng-resolution/2), lat-resolution/2]
    return [nw, ne, se, sw]

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
    """A tile cell described by a polygon with geographic coordinates."""

    def __init__(self, cpd = CELLS_PER_DEGREE, key, polygon):
        """Constructs a TileCell.

        Arguments:
        """
        self.cpd
        self.key = key
        self.polygon = polygon
        
    def __str__(self):
        return str(self.__dict__)
    
class Tile(object):
    """A 30 arc-second geographic tile (http://www.worldclim.org/tiles.php)."""

    def __init__(self, row, col, width=TILE_WIDTH_DEGREES, filename=None):
        """Tile constructor.

        Arguments:
            row - The global tile row number.
            col - The global tile column number.
            width - The width of the tile, in degrees.
            filename - The name of the input Shapefile.
        """
        self.width = width
        self.row = row
        self.col = col
        self.filename = filename
        self.north = 90.0 - self.width * row
        self.south = self.north - self.width
        self.west = -180.0 + self.width * col
        self.east = self.west + self.width

    def _getcellkey(self, tilerow, tilecol, cpd = CELLS_PER_DEGREE):
        """Gets the global cell key."""
        x = self.col * self.width * cpd + tilecol
        y = self.row * self.width * cpd + tilerow
        return '%s-%s' % (x, y)

    def _getcellpolygon(self, lat, lng, cpd = CELLS_PER_DEGREE):
        """Gets the cell polygon given the cells per degree and the lat, lng of the NW corner."""
        cellres = 1.0/cpd
        return [
                 [lng, lat],                       
                 [lng + cellres, lat],
                 [lng + cellres, lat - cellres],
                 [lng, lat - cellres],
                 [lng, lat]
               ]

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
        cpd = float(options.cpd)
        Tile.csv2couch(csvfile, cdb, cpd)

    @classmethod
    def csv2couch(cls, csvfile, cdb, cpd = CELLS_PER_DEGREE):
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
                    'coords': getpolygon(x, y, cpd),
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
        cpd = float(options.cpd)
        cells = []
        count = 0
        for cell in self.getcells(cpd):
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
                                            
    def getcells(self, cpd = CELLS_PER_DEGREE):
        """Iterates over all cells in the tile at the given cell resolution.

        Arguments:
            cpd - The number of cells in one degree of lat or lng.
        """
        cellres = 1.0/cpd
        lng = self.west
        lat = self.north        
        row = 0
        col = 0
        while lng < self.east:
            row = 0
            while lat > self.south:
                yield TileCell(
                    cpd,
                    self._getcellkey(row, col, cpd), 
                    self._getcellpolygon(lat, lng, cpd))
                lat -= cellres
                row += 1
            lat = self.north
            lng += cellres
            col += 1

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
                      dest="cpd",
                      help="The number of cells in a degree",
                      default=CELLS_PER_DEGREE)

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
