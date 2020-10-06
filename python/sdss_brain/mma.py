# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: mma.py
# Project: python
# Author: Brian Cherinka
# Created: Friday, 14th February 2020 2:23:01 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Wednesday, 18th March 2020 4:40:58 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import
from sdss_brain.helpers import get_mapped_version
import abc
import os
import time
import warnings

import six
from functools import wraps
from sdss_brain import log
from sdss_brain.config import config
from sdss_brain.exceptions import BrainError, BrainMissingDependency, BrainUserWarning

try:
    from sdss_access import Access
except ImportError:
    Access = None

__all__ = ['MMAMixIn']


def create_new_access(release):
    ''' create a new sdss_access instance

    Parameters
    ----------
        release : str
            The sdss data release
    '''
    # check for public release
    is_public = 'DR' in release
    rsync_release = release.lower() if is_public else None

    if not Access:
        raise BrainMissingDependency('sdss_access is not installed')

    return Access(public=is_public, release=rsync_release)


def set_access(func):
    ''' Decorator that sets the _access attribute

    Creates a new sdss_access instance if either the _access
    attribute is None or the object release differs from the access
    release.  Ensures that a new sdss_access.Access is instantiated
    when we change releases, e.g. between public DRs or work releases.

    '''
    @wraps(func)
    def wrapper(*args, **kwargs):
        inst = args[0]
        isset = inst._access is not None
        diffrelease = inst.release.lower() != inst._access.release if isset else None
        if not isset or diffrelease:
            inst._access = create_new_access(inst.release)
        return func(*args, **kwargs)
    return wrapper


def check_access_params(func):
    '''Decorator that checks for correct output from set_access_path_params '''

    @wraps(func)
    def wrapper(*args, **kwargs):
        inst = args[0]
        assert hasattr(inst, 'path_name'), f'{inst.__class__.__name__} must have a "path_name" class attribute'
        assert hasattr(inst, 'path_params'), 'set_access_path_params must set a "path_params" attribute'
        assert getattr(inst, 'path_name'), 'the path_name attribute cannot be None'
        assert getattr(inst, 'path_params'), 'the path_params attribute cannot be None'
        assert type(inst.path_params) == dict, 'the path_params attribute must be a dictionary'
        return func(*args, **kwargs)
    return wrapper


def _set_access_path_params(self):
    ''' Default set_access_path_params applied with the decorator'''
    keys = self.access.lookup_keys(self.path_name)
    self.path_params = {k: getattr(self, k) for k in keys}


def create_mapped_properties(kls, mapped_version):
    ''' Create new read-only properties on a given class

    Creates new read-only properties that extracts a specific version id to an input
    release.  This allows the version id to be updated when the global "release" is
    changed.  See `~sdss_brain.helpers.get_mapped_version` for more details.
    ``mapped_version`` is a mapping key, "[mapping]:[property,]", where [mapping]
    is the name of the key in the "mapped_version" attribute in the brain configuration yaml file,
    and [property,] is a list of version ids to become properties.

    For example a key of "manga:drpver" creates a new read-only property called "drpver" and uses
    `get_mapped_version` to extract the correct version number for a given release from the
    "mapped_version['manga']" key in ~sdss_brain.yaml.

    Parameters
    ----------
        kls : Type
            The class object
        mapped_version : str
            The mapping key to map a specific version onto a release
    '''
    mapkey, attrkey = mapped_version.split(':')
    # set the mapped_version class attribute
    kls.mapped_version = mapkey
    if attrkey:
        # loop over all named values found
        for attr in attrkey.split(','):
            # create read-only property that extracts the correct version number
            # for a given release
            setattr(kls, attr, property(lambda self: get_mapped_version(
                kls.mapped_version, release=self.release, key=attr)))


def access_loader(kls=None, *, name=None, defaults={}, mapped_version='manga:drpver'):
    """ Decorator to reduce boilerplate around setting of sdss_access parameters

    Parameters
    ----------
        name : str
        defaults : dict
        mapped_version : str

    Returns
    -------
        The decorated class
    """
    def wrap(kls):
        # add the path_name class attribute and add defaults for path_params
        kls.path_name = name
        kls._path_defaults = defaults

        # create new properties for mapped versions
        if mapped_version:
            create_mapped_properties(kls, mapped_version)

        # attach the default set_access_path_params
        setattr(kls, '_set_access_path_params', _set_access_path_params)

        # update the __abstractmethod__ with the boilerplate set
        method_set = ['_set_access_path_params']
        kls.__abstractmethods__ = kls.__abstractmethods__.symmetric_difference(method_set)
        return kls

    if not kls:
        return wrap
    return wrap(kls)


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
        use_db : sdssdb.DatabaseConnection
            a database connection to override the default with

    Attributes
    ----------
        release : str
            The current data release loaded
        access : sdss_access.Access
            An instance of `sdss_access` using for all path creation and file downloads

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

        # sdss_access attributes
        self._access = None
        self.path_params = None
        self._setup_access()

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

    @property
    @set_access
    def access(self):
        ''' Returns an instance of `sdss_access.Access` '''
        return self._access

    def _do_local(self):
        """ Check if it's possible to load the data locally."""

        if self.filename:

            # check if the file exists locally
            if os.path.exists(self.filename):
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
                # retrieve the full local access path
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

            assert isinstance(data_input, six.string_types), 'input must be a string.'

            # parse the input data
            self._parse_input(data_input)

        # ensure either filename or objectid is specified
        if self.filename is None and self.objectid is None:
            raise BrainError('no inputs defined. filename and objectid are both None')

        # attempt to extract access path parameters from the filename
        if hasattr(self, 'path_name') and self.path_name:
            if self.filename:
                params = self.access.extract(self.path_name, self.filename)
                if params:
                    self._setup_access(params)
            elif self.objectid:
                self._set_access_path_params()
                self._setup_access(self.path_params)

        # check for any misaligments and misassignments
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
        ''' Parses the input value to determine the kind of input

        This method must be overridden by each subclass and contains the logic
        to determine the kind of input passed into it, i.e. either a filename or an
        object identification string.
        '''

    @check_access_params
    def get_full_path(self, url=None):
        """ Returns the full path of the file in the tree.

        Parameters
        ----------
            url : bool
                If True, specifies the url location rather than the local file location

        Returns
        -------
            The full path as built by sdss_access
        """

        try:
            if url:
                fullpath = self.access.url(self.path_name, **self.path_params)
            else:
                fullpath = self.access.full(self.path_name, **self.path_params)
        except Exception as ee:
            warnings.warn('sdss_access was not able to retrieve the full path of the file. '
                          'Error message is: {0}'.format(str(ee)), BrainUserWarning)
            fullpath = None
        return fullpath

    @abc.abstractmethod
    def _set_access_path_params(self):
        ''' Return the sdss_access path parameters

        This method must be overridden by each subclass and must set at least two
        parameters, "path_name", and "path_params", which specify parameters to be passed
        to sdss_access.

        Attributes
        ----------
            path_name : str
                Required. The sdss_access template path key name.
            path_params : dict
                Required. The keywords needed to fill out the sdss_access template path
        '''

    def _setup_access(self, params=None):
        ''' Set up the initial access parameters

        Sets up an initial default path_params dictionary.  Given a provided `path_name`
        class attribute, looks up the path keyword arguments and creates instance properties,
        as well as a default `path_params` dictionary.  If "params" is specified then properties
        and `path_params` is updated from that input.

        Parameters
        ----------
            params : dict
                A dictionary of access path params
        '''

        # do nothing if no path_name set
        if not hasattr(self, 'path_name') or not self.path_name:
            return

        # look up the access keys and create attributes
        keys = self.access.lookup_keys(self.path_name)
        for k in keys:
            # skip if a class attribute already exists
            if hasattr(self.__class__, k):
                continue

            # look for a default value
            default = self._path_defaults.get(k, None) if hasattr(
                self, '_path_defaults') else None
            if params:
                assert type(params) == dict, 'the path_params attribute must be a dictionary'
                setattr(self, k, params.get(k, default))
            else:
                setattr(self, k, default)

        # create a default path params dictionary
        self.path_params = {k: getattr(self, k) for k in keys}

    @check_access_params
    def download(self):
        """ Download the file using sdss_access """

        self.access.remote()
        self.access.add(self.path_name, **self.path_params)
        self.access.set_stream()
        self.access.commit()
        paths = self.access.get_paths()
        # adding a millisecond pause for download to finish and file existence to register
        time.sleep(0.001)

        self.filename = paths[0]  # doing this for single files, may need to change

