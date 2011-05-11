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
from datetime import datetime
from google.appengine.api import mail, memcache, urlfetch
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from sdl import tmg
import logging
import os
import simplejson

COUCHDB_HOST = 'http://ec2-184-73-71-48.compute-1.amazonaws.com'
COUCHDB_PORT = 5984
COUCHDB_DATABASE = 'sdl'
COUCHDB_DESIGN = 'api'
COUCHDB_VIEW = 'cell-values'
COUCHDB_URL = '%s:%s/%s/_design/%s/_view/%s' % (
    COUCHDB_HOST, COUCHDB_PORT, COUCHDB_DATABASE, COUCHDB_DESIGN, COUCHDB_VIEW)

class CouchDbCell(db.Model):
    """Models a CouchDB cell document.

    key_name - The cell key (e.g., 1-2).
    """
    rev = db.StringProperty(required=True, indexed=False)
    coords = db.StringProperty(required=True, indexed=False)
    varvals = db.TextProperty(required=True)

    def __eq__(self, other):
        if isinstance(other, CouchDbCell):
            return self.key() == other.key()
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __hash__(self):
        return hash(self.key().name())

    def __cmp__(self, other):
        return self.key().__cmp__(other.key())

class Variable(db.Expando):
    """Variable metadata."""
    name = db.StringProperty()

class CellValuesHandler(webapp.RequestHandler):
    """Handler for cell value requests."""

    @classmethod
    def fromds(cls, cell_keys):
        """Returns CouchDBCell entities from a datastore query on cell keys.

        Arguments:
            cell_keys - A set of cell key strings (e.g., 9-15).

        Returns:
            A dictionary of cell key to CouchDBCell.
        """
        entities = CouchDbCell.get_by_key_name(cell_keys)
        cells = {}
        for x in entities:
            if x:
                cells[x.key().name()] = x
        return cells

    @classmethod
    def fromcouchdb(cls, cell_keys):
        """Returns CouchDBCell entities from a CouchDB query on cell keys.
        
        Arguments:
            cell_keys - A set of cell key strings (e.g., 9-15).

        Returns:
            A dictionary of cell key to CouchDBCell.
        """
        response = urlfetch.fetch(
            url=COUCHDB_URL,
            payload=simplejson.dumps({'keys': list(cell_keys)}),
            method=urlfetch.POST,
            headers={"Content-Type":"application/json"})
        if response.status_code != 200:
            return {}
        cells = {}        
        for row in simplejson.loads(response.content).get('rows'):            
            key = row.get('key')
            value = row.get('value')
            cells[key] = CouchDbCell(
                key_name=key,
                rev=value.get('rev'),
                coords=simplejson.dumps(value.get('coords')),
                varvals=simplejson.dumps(value.get('varvals')))
        return cells

    @classmethod
    def getcells(cls, cell_keys):
        """Gets CouchDBCell entities corresponding to a set of cell keys.
        
        Arguments:
            cell_keys - A set of cell key strings (e.g., 9-15).

        Returns:
            A dictionary of cell key to CouchDBCell.
        """
        cells = {}
        
        # Checks cache:
        cached = memcache.get_multi(cell_keys)
        cells.update(cached)
        cell_keys = cell_keys.difference(cached.keys())

        cachecells = False

        # Checks datastore:
        if len(cell_keys) > 0:
            cachecells = True
            stored = cls.fromds(cell_keys)
            cells.update(stored)
            cell_keys = cell_keys.difference(stored.keys())
            
        # Checks CouchDB:
        if len(cell_keys) > 0:
            cachecells = True
            couched = cls.fromcouchdb(cell_keys)
            cells.update(couched)
            db.put(couched.values())
            
        if cachecells:
            memcache.set_multi(cells)                        

        return cells

    def get(self):
        return self.post()
    
    def post(self):
        k = self.request.get('k', None) 
        v = self.request.get('v', None)
        c = 'true' == self.request.get('c')
        if not k or not v:
            self.error(404)
            return

        cell_keys = set([x.strip() for x in k.split(',')])
        variable_names = set([x.strip() for x in v.split(',')])
        if not cell_keys or not variable_names:
            self.error(404)
            return
        
        cells = CellValuesHandler.getcells(cell_keys)        
        results = []
        for cellkey in cells.keys():
            cell = cells.get(cellkey)
            requested_varvals = {}
            varvals = simplejson.loads(cell.varvals)
            for name in variable_names:
                requested_varvals[name] = varvals.get(name)
                result = {'cell-key': cellkey, 
                          'cell-values': requested_varvals}
                if c:
                    result['cell-coords'] = simplejson.loads(cell.coords)
            results.append(result)
        json = simplejson.dumps(results)
        self.response.headers["Content-Type"] = "application/json"
        self.response.out.write(json)

application = webapp.WSGIApplication(
    [('/api/cells/values', CellValuesHandler),], debug=True)    

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
