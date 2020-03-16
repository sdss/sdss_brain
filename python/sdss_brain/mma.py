# !/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Filename: mma.py
# Project: python
# Author: Brian Cherinka
# Created: Friday, 14th February 2020 2:23:01 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Sunday, 15th March 2020 7:21:31 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import
import abc
import os
import re
import time
import warnings

import six
from dataclasses import dataclass, field
from functools import wraps
from sdss_brain import log
from sdss_brain.config import config
from sdss_brain.exceptions import BrainError, BrainMissingDependency, BrainUserWarning
#from marvin.utils.db import testDbConnection
#from marvin.utils.general.general import mangaid2plateifu

try:
    from sdss_access.path import Path
except ImportError:
    Path = None

try:
    from sdss_access import Access
except ImportError:
    Access = None

__all__ = ['MMAMixIn']


def check_access_params(func):
    '''Decorator that checks for correct output from set_access_path_params '''

    @wraps(func)
    def wrapper(*args, **kwargs):
        inst = args[0]
        path_params = inst._set_access_path_params()
        assert type(path_params) == dict, 'set_access_path_params must return a dictionary'
        assert 'name' in path_params, ('dictionary returned by set_access_path_params'
                                       ' must contain a "name" keyword argument')
        return func(*args, **kwargs)
    return wrapper
    

class MMAMixIn(object, six.with_metaclass(abc.ABCMeta)):

    def __init__(self, data_input=None, filename=None, objectid=None, mode=None, data=None,
                 release=None, download=None, ignore_db=False, use_db=None):
        self.data = data
        self.data_origin = None
        self._ignore_db = ignore_db
        self._db = use_db

        self.filename = filename
        self.objectid = objectid

        self.mode = mode if mode is not None else config.mode

        self._release = release if release is not None else config.release

        self._forcedownload = download if download is not None else config.download

        self._determine_inputs(data_input)

        assert self.mode in ['auto', 'local', 'remote']
        assert self.filename is not None or self.objectid is not None, 'no inputs set.'

        #self.datamodel = None
        #self._set_datamodel()

        if self.mode == 'local':
            self._do_local()
        elif self.mode == 'remote':
            self._do_remote()
        elif self.mode == 'auto':
            try:
                self._do_local()
            except BrainError as ee:

                if self.filename:
                    # If the input contains a filename we don't want to go into remote mode.
                    raise(ee)
                else:
                    log.info('local mode failed. Trying remote now.')
                    self._do_remote()

        # Sanity check to make sure data_origin has been properly set.
        assert self.data_origin in ['file', 'db', 'api'], 'data_origin is not properly set.'

    @property
    def release(self):
        """Returns the release."""

        return self._release

    @release.setter
    def release(self, value):
        """Fails when trying to set the release after instantiation."""
        raise BrainError('the release cannot be changed once the object has been instantiated.')

    @property
    def access(self):        
        # check for public release
        is_public = 'DR' in self.release
        rsync_release = self.release.lower() if is_public else None

        if not Access:
            raise BrainMissingDependency('sdss_access is not installed')

        return Access(public=is_public, release=rsync_release)

    def _do_local(self):
        """Tests if it's possible to load the data locally."""

        if self.filename:

            if os.path.exists(self.filename):
                self.mode = 'local'
                self.data_origin = 'file'
            else:
                raise BrainError('input file {0} not found'.format(self.filename))

        elif self.objectid:

            if self._db and self._db.connected and not self._ignore_db:
                self.mode = 'local'
                self.data_origin = 'db'
            else:
                fullpath = self._get_full_path()

                if fullpath and os.path.exists(fullpath):
                    self.mode = 'local'
                    self.filename = fullpath
                    self.data_origin = 'file'
                else:
                    if self._forcedownload:
                        self.download()
                        self.data_origin = 'file'
                    else:
                        raise BrainError('failed to retrieve data using '
                                         'input parameters.')

    def _do_remote(self):
        """Tests if remote connection is possible."""

        if self.filename:
            raise BrainError('filename not allowed in remote mode.')
        else:
            self.mode = 'remote'
            self.data_origin = 'api'

    def _determine_inputs(self, data_input):
        """Determines what inputs to use in the decision tree."""

        if data_input:
            assert self.filename is None and self.objectid is None, \
                'if input is set, filename and objectid cannot be set.'

            assert isinstance(data_input, six.string_types), 'input must be a string.'

            input_dict = self._parse_input(data_input)

            if input_dict['objectid'] is not None:
                self.objectid = data_input
            else:
                # Assumes the input must be a filename
                self.filename = data_input

        if self.filename is None and self.objectid is None:
            raise BrainError('no inputs defined.')

        if self.filename:
            self.objectid = None

            if self.mode == 'remote':
                raise BrainError('filename not allowed in remote mode.')

            assert os.path.exists(self.filename), \
                'filename {} does not exist.'.format(str(self.filename))

        elif self.objectid:
            assert not self.filename, 'invalid set of inputs.'

    @abc.abstractmethod
    def _parse_input(self, value):
        pass
    
    @check_access_params
    def _get_full_path(self):
        """ Returns the full path of the file in the tree. """

        path_params = self._set_access_path_params()
        url = path_params.pop('url', None)
        path_name = path_params.pop('name', None)

        try:
            if url:
                fullpath = self.access.url(path_name, **path_params)
            else:
                fullpath = self.access.full(path_name, **path_params)
        except Exception as ee:
            warnings.warn('sdss_access was not able to retrieve the full path of the file. '
                          'Error message is: {0}'.format(str(ee)), BrainUserWarning)
            fullpath = None
        return fullpath
    
    @abc.abstractmethod
    def _set_access_path_params(self):
        ''' Return the sdss_access path parameters
        
        This method must be overridden by each subclass and must return
        a dictionary of parameters to be passed to sdss_access.  The dictionary must
        contain a keyword "name", the sdss_access template path key.

        Dictionary parameters:

            - name (str): Required. The sdss_access template path key name.
            - url (bool): If True, tells sdss_access to return the url location instead of location file location
            - any additonal keywords needed to fill out the sdss_access template path

        '''
        pass

    @check_access_params
    def download(self):
        """ Download using sdss_access """

        path_params = self._set_access_path_params()
        path_name = path_params.pop('name', None)
        
        self.access.remote()
        self.access.add(path_name, **path_params)
        self.access.set_stream()
        self.access.commit()
        paths = self.access.get_paths()
        # adding a millisecond pause for download to finish and file existence to register
        time.sleep(0.001)

        self.filename = paths[0]  # doing this for single files, may need to change
