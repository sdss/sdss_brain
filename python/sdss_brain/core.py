# !/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Filename: core.py
# Project: sdss_brain
# Author: Brian Cherinka
# Created: Sunday, 15th March 2020 4:53:35 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Tuesday, 17th March 2020 5:39:55 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import
from sdss_brain.mma import MMAMixIn
from astropy.io import fits


class Brain(MMAMixIn):
    ''' Convenience class for utilizing the MMA mixin '''
    _db = None
    mapped_version = None

    def __init__(self, data_input=None, filename=None,
                 objectid=None, mode=None, data=None,
                 release=None, download=None,
                 ignore_db=None, use_db=None):

        MMAMixIn.__init__(self, data_input=data_input, filename=filename,
                          objectid=objectid, mode=mode, data=data,
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

    # def _parse_input(self, value):
    #     pass

    # def _set_access_path_params(self):
    #     pass

    # def _load_object_from_file(self, data=None):
    #     pass

    # def _load_object_from_db(self, data=None):
    #     pass

    # def _load_object_from_api(self, data=None):
    #     pass

    def __del__(self):
        ''' Destructor for closing FITS files. '''
        if self.data_origin == 'file' and isinstance(self.data, fits.HDUList):
            self.data.close()

