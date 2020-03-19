# !/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Filename: core.py
# Project: sdss_brain
# Author: Brian Cherinka
# Created: Sunday, 15th March 2020 4:53:35 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Wednesday, 18th March 2020 4:08:26 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import
import abc
from sdss_brain.mma import MMAMixIn
from astropy.io import fits


class Base(abc.ABC):
    ''' abstract base class for tools '''
    
    @abc.abstractmethod
    def _load_object_from_file(self, data=None):
        pass

    @abc.abstractmethod
    def _load_object_from_db(self, data=None):
        pass

    @abc.abstractmethod
    def _load_object_from_api(self, data=None):
        pass


class Brain(Base, MMAMixIn):
    ''' Convenience class for utilizing the MMA mixin

    This is a convenience class with the ``MMAMixIn`` already implemented.
    This class initializes the ``MMAMixIn`` and provides logic to load data based
    on the data_origin.  It also provides a simple ``repr``.
    
    This class contains three abstractmethods you must override when subclassing.
        - **_load_object_from_file**: defines data load/handling from a local file
        - **_load_object_from_db**: defines data load/handling from a local database
        - **_load_object_from_api**: defines data load/handling from a remote API

    Parameters:
        data_input (str):
            The file or name of target data to load
        filename (str):
            The absolute filepath to data to load
        objectid (str):
            The object identifier of the data to load
        mode (str):
            The operating mode: auto, local, or remote
        release (str):
            The data release of the object, e.g. "DR16"
        data (object):
            Optional data to instantiate the object with
        download (bool):
            If True, downloads the object locally with sdss_access
        ignore_db (bool):
            If True, ignores any database connection for local access
        use_db (sdssdb.DatabaseConnection):
            a database connection to override the default with

    Attributes:
        _db (sdssdb.DatabaseConnection):
            A relevant sdssdb database connection for the object
        mapped_version (str):
            The name of survey/category in the mapped_versions dictionary
    '''
    _db = None
    mapped_version = None

    def __init__(self, data_input=None, filename=None,
                 objectid=None, mode=None, data=None,
                 release=None, download=None,
                 ignore_db=None, use_db=None):

        self.data = data

        MMAMixIn.__init__(self, data_input=data_input, filename=filename,
                          objectid=objectid, mode=mode,
                          release=release, download=download,
                          ignore_db=ignore_db, use_db=use_db or self._db)

        if self.data_origin == 'file':
            self._load_object_from_file(data=data)
        elif self.data_origin == 'db':
            self._load_object_from_db(data=data)
        elif self.data_origin == 'api':
            self._load_object_from_api()

    def __repr__(self):
        objname = f"objectid='{self.objectid}'" if self.objectid else f"filename='{self.filename}'"
        return (f"<{self.__class__.__name__} {objname}, mode='{self.mode}', "
                f"data_origin='{self.data_origin}'>")

    def __del__(self):
        ''' Destructor for closing FITS files. '''
        if self.data_origin == 'file' and isinstance(self.data, fits.HDUList):
            self.data.close()

