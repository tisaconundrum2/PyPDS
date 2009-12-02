The tableextractor module
=========================

This module extracts data from a PDS table.  At the moment it supports:

* FIXED_LENGTH  

.. note::
    ASCII_FILE.

This is an example on how to use the code:

>>> from pds.tableextractor import TableExtractor
>>> extractor = TableExtractor(log='options.log')
>>> table, labels = extractor.extract('../../test_data/110kmin.lbl')
>>> print table.fieldnames
['ORBIT NUMBER', 'UTC TIME OF PERIAPSIS', 'LONGITUDE OF THE SUN', 'AREODETIC ALTITUDE', 'PERIAPSIS AREODETIC ALTITUDE', 'LATITUDE', 'EAST LONGITUDE', 'LOCAL SOLAR TIME', 'SOLAR ZENITH ANGLE', 'DENSITY', 'SIGMA DENSITY', 'TEMPERATURE', 'SCALE HEIGHT', 'SIGMA SCALE HEIGHT', 'RMS']
>>> for row in table:
...     print row['ORBIT NUMBER']
... 
6.0000
7.0000
8.0000
...


.. automodule:: pds.tableextractor
   :members:
