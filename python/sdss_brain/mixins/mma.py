# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: mma.py
# Project: mixins
# Author: Brian Cherinka
# Created: Thursday, 8th October 2020 11:23:28 am
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Thursday, 8th October 2020 11:23:28 am
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import

import abc
import six
import pathlib
import os

from sdss_brain import log
from sdss_brain.mixins.access import AccessMixIn
from sdss_brain.config import config
from sdss_brain.exceptions import BrainError


__all__ = ['MMAMixIn', 'MMAccess']


class MMAMixIn(abc.ABC):
    ''' Mixin for implementing multi-modal data access

    This is a mixin class that adds multi-modal data access to any class
    that subclasses from this one.  The MMA allows toggling between local
    and remote data access modes, or leaving it on automatic.  Local mode
    access tries to load data via a database, if one exists, otherwise it loads
    data via a local filepath.  Remote mode will try to load data over an API.
    When the mode is set to "auto", it automatically tries to first load things
    locally, and then remotely.  Depending on the mode and logic, the MMA will
    set data_origin to either `file`, `db`, or `api`.

    Note that this class does not provide the logic for loading data from a db, over an API,
    or from a file.  The user must provide that logic in a subclass.

    This mixin contains three abstractmethods you must override when subclassing.

    - **_parse_inputs**: provides logic to parse ``data_input`` into either filename or objectid
    - **download**: a method for downloading a data file to a local disk
    - **get_full_path**: a method for generating the absolute file path on disk to a file

    Parameters
    ----------
        data_input : str
            The file or name of target data to load
        filename : str
            The absolute filepath to data to load
        objectid : str
            The object identifier of the data to load
        mode : str
            The operating mode: auto, local, or remote
        release : str
            The data release of the object, e.g. "DR16"
        download : bool
            If True, downloads the object locally with sdss_access
        ignore_db : bool
            If True, ignores any database connection for local access
        use_db : `~sdssdb.connection.DatabaseConnection`
            a database connection to override the default with

    Attributes
    ----------
        release : str
            The current data release loaded

    '''

    def __init__(self, data_input=None, filename=None, objectid=None, mode=None,
                 release=None, download=None, ignore_db=False, use_db=None):
        # data attributes
        self._db = use_db
        self.filename = filename
        self.objectid = objectid
        self.data_origin = None

        # inputs or config variables
        self.mode = mode or config.mode
        self._release = release or config.release
        self._forcedownload = download or config.download
        self._ignore_db = ignore_db or config.ignore_db

        # determine the input
        self._determine_inputs(data_input)

        assert self.mode in ['auto', 'local', 'remote']
        assert self.filename is not None or self.objectid is not None, 'no inputs set.'

        # perform the multi-modal data access
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
                    log.debug('local mode failed. Trying remote now.')
                    self._do_remote()

        # Sanity check to make sure data_origin has been properly set.
        assert self.data_origin in ['file', 'db', 'api'], 'data_origin is not properly set.'

    @property
    def release(self):
        """ Returns the release. """

        return self._release

    @release.setter
    def release(self, value):
        """Fails when trying to set the release after instantiation."""
        raise BrainError('the release cannot be changed once the object has been instantiated.')

    def _do_local(self):
        """ Check if it's possible to load the data locally."""

        if self.filename:

            # check if the file exists locally
            if self.filename.exists():
                self.mode = 'local'
                self.data_origin = 'file'
            else:
                raise BrainError('input file {0} not found'.format(self.filename))

        elif self.objectid:

            # prioritize a database unless explicitly set to ignore
            if self._db and self._db.connected and not self._ignore_db:
                self.mode = 'local'
                self.data_origin = 'db'
            else:

                # retrieve the full local sdss_access path
                fullpath = self.get_full_path()

                if fullpath and os.path.exists(fullpath):
                    self.mode = 'local'
                    self.filename = fullpath
                    self.data_origin = 'file'
                else:
                    # optionally download the file
                    if self._forcedownload:
                        self.download()
                        self.data_origin = 'file'
                    else:
                        raise BrainError('failed to retrieve data using '
                                         'input parameters.')

    def _do_remote(self):
        """ Check if remote connection is possible."""

        if self.filename:
            raise BrainError('filename not allowed in remote mode.')
        else:
            self.mode = 'remote'
            self.data_origin = 'api'

    def _determine_inputs(self, data_input):
        """ Determines what inputs to use in the decision tree. """

        if data_input:
            assert self.filename is None and self.objectid is None, \
                'if input is set, filename and objectid cannot be set.'

            assert isinstance(data_input, (six.string_types, pathlib.Path)), \
                'input must be a string or pathlib.Path'

            # parse the input data into either a filename or objectid
            parsed_input = self._parse_input(data_input)
            if not parsed_input:
                self.filename = data_input
            else:
                assert isinstance(
                    parsed_input, dict), 'return value of _parse_input must be a dict'
                self.filename = parsed_input.get('filename', None)
                self.objectid = parsed_input.get('objectid', None)

        # ensure either filename or objectid is specified
        if self.filename is None and self.objectid is None:
            raise BrainError('no inputs defined. filename and objectid are both None')

        # convert filename to a pathlib.Path and resolve a relative name
        if self.filename:
            self.filename = pathlib.Path(self.filename).resolve()

        # attempt to update the access path parameters from the filename or parsed data input
        self._update_access_params()

        # check for any misaligments and misassignments
        if self.filename:
            self.objectid = None

            if self.mode == 'remote':
                raise BrainError('filename not allowed in remote mode.')

            assert self.filename.exists, \
                'filename {} does not exist.'.format(str(self.filename))

        elif self.objectid:
            assert not self.filename, 'invalid set of inputs.'

    @abc.abstractmethod
    def _parse_input(self, value):
        ''' Parses the input value to determine the kind of input

        This method must be overridden by each subclass and contains the logic
        to determine the kind of input passed into it, i.e. either a filename or an
        object identification string.  This method accepts a single argument which is the
        string `data_input` and must return a dictionary containing at least keys
        for "filename" and "objectid".
        '''

    @abc.abstractmethod
    def download(self):
        ''' Abstract method to download a file '''
        pass

    @abc.abstractmethod
    def get_full_path(self):
        ''' Abstract method to return a full local file path '''
        pass

    @property
    def is_access_mixedin(self):
        ''' Checks if the `~sdss_brain.mixins.access.AccessMixIn` is included '''
        return hasattr(self, 'path_name') and hasattr(self, 'access')

    def _update_access_params(self):
        ''' Updates the path_params attribute with extracted parameters '''
        if self.is_access_mixedin and self.path_name:
            if self.filename:
                params = self.access.extract(self.path_name, self.filename)
                if params:
                    self._setup_access(params)
            elif self.objectid:
                self._set_access_path_params()
                self._setup_access(self.path_params)


class MMAccess(AccessMixIn, MMAMixIn):
    """ Class that mixes in the sdss_access functionality with the MMA

    This is a mixin class that adds multi-modal data access to any class
    that subclasses from this one.  The MMA allows toggling between local
    and remote data access modes, or leaving it on automatic.  Local mode
    access tries to load data via a database, if one exists, otherwise it loads
    data via a local filepath.  Remote mode will try to load data over an API.
    When the mode is set to "auto", it automatically tries to first load things
    locally, and then remotely.  Depending on the mode and logic, the MMA will
    set data_origin to either `file`, `db`, or `api`.

    Note that this class does not provide the logic for loading data from a db, over an API,
    or from a file.  The user must provide that logic in a subclass.

    This mixin contains two abstractmethods you must override when subclassing.

    - **_set_access_path_params**: sets the arguments needed by `sdss_access`
    - **_parse_inputs**: provides logic to parse ``data_input`` into either filename or objectid

    Parameters
    ----------
        data_input : str
            The file or name of target data to load
        filename : str
            The absolute filepath to data to load
        objectid : str
            The object identifier of the data to load
        mode : str
            The operating mode: auto, local, or remote
        release : str
            The data release of the object, e.g. "DR16"
        download : bool
            If True, downloads the object locally with sdss_access
        ignore_db : bool
            If True, ignores any database connection for local access
        use_db : `~sdssdb.connection.DatabaseConnection`
            a database connection to override the default with

    Attributes
    ----------
        release : str
            The current data release loaded
        access : `~sdss_access.sync.Access`
            An instance of ``sdss_access`` using for all path creation and file downloads

    """
    pass
