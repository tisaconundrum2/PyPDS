#!/usr/bin/env python
# encoding: utf-8
"""
tableextractor.py

Created by Alessandro Frigeri on 2009-12-2.

Copyright (c) 2009 Ryan Matthew Balfanz & Alessandro Frigeri. All rights reserved.
"""


import logging
import os
import sys
import unittest
import re

import csv

from core.common import open_pds
from core.parser import Parser, ParserNode
from core.extractorbase import ExtractorBase
from core.reader import Reader

def getPdsFileName(filename,datadir):
     """An helper function that returns the real pds filename

     In PDS all filename are UPPERCASE, at least for CD/DVD archives.
     This function returns the full path of the real file (that can be mixes case) 
     specified by the filename (e.g. obtained from parsing a label - thus uppercase), 
     and the datadir path.
     """
     for f in os.listdir(datadir):                          
         if re.match(filename, f, re.IGNORECASE):
             realfilename = f 
     return os.path.join(datadir,realfilename)

class ParserRootColumn(ParserNode):
	"""A tree-like node structure to maintain structure within PDS labels.
        
        Case of multiple groups with the same name, we store all in a list
        """
	def __init__(self, children=None, parent=None):
		super(ParserRootColumn, self).__init__()
		if not children:
			children = []
			
		self.children = children
		self.parent = parent

class ColumnParser(Parser):
       """ Parse a column format 
 
       The Parse class returns a dictionary of the labels within a PDS file.  In the case of a column 
       format file, we have multiple ('COLUMN') objects with the same name, thus overwriting the 
       same 'COLUMN' key in the dictionary.
  
       This class returns a list of keys. 
       """

       def _parse_header(self, source):
		"""Parse the PDS header.
		
		For grouped data, supported containers belong to {'OBJECT', 'GROUP'}.
		Unidentified containers will be parsed as simple labels and will not create a child dictionary.
		"""
		if self.log: self.log.debug('Parsing header')
		CONTAINERS = {'OBJECT':'END_OBJECT', 'GROUP':'END_GROUP'}
		CONTAINERS_START = CONTAINERS.keys()
		CONTAINERS_END = CONTAINERS.values()
		
		root = ParserRootColumn([], None)
		currentNode = root
		expectedEndQueue = []
		for record in self._reader.read(source):
			k, v = record[0], record[1]
			assert k == k.strip() and v == v.strip(), ('Found extraneous whitespace near %s and %s') % (k, v)
			if k in CONTAINERS_START:
				expectedEndQueue.append((CONTAINERS[k], v))
				currentNode = ParserNode({}, currentNode)
				#print expectedEndQueue,k,v                                
			elif k in CONTAINERS_END:                                
				try:
					expectedEnd = expectedEndQueue.pop()
					newParent = currentNode.parent                  
                                        # Add the node to the node list 
                                        # (so multiple object with the same name are possible)
                                        newParent.children.append({v:currentNode.children})
					currentNode = newParent
				except IndexError:
					# Verifiy that we are back at the root.
					assert currentNode.parent is None, ('Parent node is not None.')
			else:
				assert not k.startswith('END_'), ('Detected a possible uncaught nesting %s.') % (k,)
                               
				currentNode.children[k] = v
                               
		assert not expectedEndQueue, ('Detected hanging chads, very gory... %s') % (expectedEndQueue,)

		assert currentNode.parent is None, ('Parent is not None, did not make it back up the tree')                
		return root.children       
       

class TableExtractor(ExtractorBase):
	"""Extract a PDS table.
	
	Returned images are instances of the Python Imaging Library Image class.
	As such, this module depends on PIL.
	
	An attached image may be extracted from by 
	determining its location within the file and identifying its size.
	Not all PDS images are supported at this time.
	
	Currently this module only supports FIXED_LENGTH as the RECORD_TYPE,
	8 as the SAMPLE_BITS and either UNSIGNED_INTEGER or MSB_UNSIGNED_INTEGER as the SAMPLE_TYPE.
	Attempts to extract an image that is not supported will result in None being returned.
	
	Simple Example Usage:
	
	>>> from tableextractor import TableExtractor
	>>> te = TableExtractor()
	>>> tbl,columns,labels = te.extract('pdsFileWithATable.lbl')
	>>> if tbl:
	>>> 	print tbl.fieldnames
	>>> else:
	>>> 	print "The table was not supported."
	"""
	
	def __init__(self, log=None):
		super(TableExtractor, self).__init__()
		
		self.log = log
		if log:
			self._init_logging()	

	def _init_logging(self):
		"""Initialize logging."""
		# Set the message format.
		format = logging.Formatter("%(levelname)s:%(name)s:%(asctime)s:%(message)s")

		# Create the message handler.
		stderr_hand = logging.StreamHandler(sys.stderr)
		stderr_hand.setLevel(logging.DEBUG)
		stderr_hand.setFormatter(format)

		# Create a handler for routing to a file.
		logfile_hand = logging.FileHandler(self.log + '.log')
		logfile_hand.setLevel(logging.DEBUG)
		logfile_hand.setFormatter(format)

		# Create a top-level logger.
		self.log = logging.getLogger(self.log)
		self.log.setLevel(logging.DEBUG)
		self.log.addHandler(logfile_hand)
		self.log.addHandler(stderr_hand)

		self.log.debug('Initializing logger')
		
	def extract(self, source):
		"""Extract an image from *source*.
		
		If the image is supported an instance of PIL's Image is returned, otherwise None.
		"""
		p = Parser()
		f = open_pds(source)
                pdsdatadir, pdsfile = os.path.split(source)
		if self.log: self.log.debug("Parsing '%s'" % (source))
		self.labels = p.parse(f)
		if self.log: self.log.debug("Found %d labels" % (len(self.labels)))
		if self._check_table_is_supported():
			if self.log: self.log.debug("Table in '%s' is supported" % (source))
			dim = self._get_table_dimensions()

                        # Get the location of the table
                        location = self._get_table_location().strip().replace("\"","")
                        #location = os.path.join(pdsdatadir,location)
                                       
                        # Get the structure of the table from the pointer
			struct_fname = self._get_table_structure().strip().replace("\"","")                        
                        structurefile = getPdsFileName(struct_fname,pdsdatadir)                                                                                  
                        
                        sp = ColumnParser()                        
                        s = open_pds(structurefile)
                        slabels = sp.parse(s)
                        columns = []
                        for l in slabels:
                           columns.append(l['COLUMN']['NAME'].strip().replace("\"",""))                     
                        if self.log: self.log.debug("Found %d columns" % (len(columns)))
                        if self.labels['RECORD_TYPE'] == "FIXED_LENGTH":      
                           locationfile = getPdsFileName(location,pdsdatadir)                                             
                           tbl = csv.DictReader(open(locationfile), fieldnames=columns, delimiter=' ')                                                     
			
		else:
			if self.log: self.log.error("Table is not supported '%s'" % (source))
			tbl = None
		f.close()
				
		return tbl,self.labels
			
	def _check_table_is_supported(self):
		"""Check that the image is supported."""
		SUPPORTED = {}
		SUPPORTED['RECORD_TYPE'] = 'FIXED_LENGTH',
		#SUPPORTED['SAMPLE_BITS'] = 8,
		#SUPPORTED['SAMPLE_TYPE'] = 'UNSIGNED_INTEGER', 'MSB_UNSIGNED_INTEGER'
				
		if not self.labels.has_key('TABLE'):
			if self.log: self.log.warn("No table data found")
			return False
			
		recordType = self.labels['RECORD_TYPE']
		
		if recordType not in SUPPORTED['RECORD_TYPE']:
			errorMessage = ("RECORD_TYPE '%s' is not supported") % (recordType)
			#raise NotImplementedError(errorMessage)
			return False
			
		return True
			
	def _get_table_dimensions(self):
		"""Return the dimensions of the table as (columns, rows).
		
		The table size is expected to be defined by the labels COLUMNS and ROWS.
		"""
		tableColumns = int(self.labels['TABLE']['COLUMNS'])
		tableRows = int(self.labels['TABLE']['ROWS'])
		return tableColumns, tableRows


	def _get_table_structure(self):
		"""Return the PDS file describing the structure of the table.
		
		It is defined by the ^STRUCTURE pointer.		
		"""
		structurePointer = self.labels['TABLE']['^STRUCTURE']                
                if self.log: self.log.debug("Found Table structure: %s" % (structurePointer))
		
		return structurePointer
			
	def _get_table_location(self):
		"""Return the position of the table.
		
                It is defined by the ^TABLE pointer.		
		"""
		tablePointer = self.labels['^TABLE'].split()
                tableLocation = tablePointer[0]
		
		return tableLocation
		
		
class TableExtractorTests(unittest.TestCase):
	"""Unit tests for class TableExtractor"""
	def setUp(self):
		pass

	def test_no_exceptions(self):
		import os

		from core import open_pds

		testDataDir = '../../test_data/'
		outputDir = '../../tmp/'
		tblExtractor = TableExtractor(log="TableExtractor_Unit_Tests")
		for root, dirs, files in os.walk(testDataDir):
			for name in ['110kmin.lbl']:                                
				filename = os.path.join(root, name)		                                	
				tbl, _ = tblExtractor.extract(filename)
				try:
					if tbl:	
                                                print "Field names:"					
                                                print tbl.fieldnames
				except Exception, e:
					# Re-raise the exception, causing this test to fail.
					raise
				else:
					# The following is executed if and when control flows off the end of the try clause.
					assert True


if __name__ == '__main__':
	unittest.main()
	
