# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: access.py
# Project: sdss_brain
# Author: Brian Cherinka
# Created: Friday, 2nd October 2020 3:24:02 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Friday, 2nd October 2020 3:24:02 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import
import abc
import time
import warnings
from functools import wraps
from typing import Type

from sdss_brain import log
from sdss_brain.exceptions import BrainError, BrainMissingDependency, BrainUserWarning
from sdss_brain.config import config

try:
    from sdss_access import Access
except ImportError:
    Access = None

__all__ = ['AccessMixIn']


def create_new_access(release: str) -> Type[Access]:
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
        # see if the instance release is different than the access release
        if 'work' in inst.release.lower():
            diffrelease = 'sdsswork' != inst._access.release if isset else None
        else:
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

        if kwargs.get('force_file', None):
            return func(*args, **kwargs)

        assert hasattr(
            inst, 'path_name'), f'{inst.__class__.__name__} must have a "path_name" class attribute'
        assert hasattr(
            inst, 'path_params'), 'set_access_path_params must set a "path_params" attribute'
        assert getattr(inst, 'path_name'), 'the path_name attribute cannot be None'
        assert getattr(inst, 'path_params'), 'the path_params attribute cannot be None'
        assert type(inst.path_params) == dict, 'the path_params attribute must be a dictionary'
        if inst.filename is None and not all(inst.path_params.values()):
            warnings.warn('Not all path_params are set.  Check how path_params are set '
                          'or for a mismatch between path_params and any extracted parameters '
                          'from _parse_input.  Ensuring any None path_params are set as strings')
            inst.path_params = dict(zip(inst.path_params.keys(), map(str, inst.path_params.values())))
        return func(*args, **kwargs)
    return wrapper


class AccessMixIn(abc.ABC):
    ''' Mixin for implementing multi-modal data access

    This is a class that adds support for dynamic path operations using
    `sdss_access`.  Given a template path name and a defined set of
    template keyword argument, provides convenience methods for constructing
    the full local or url-based pathname, downloading the file with `sdss_access`.
    Also provides the complete `~sdss_access.sync.access.Access` object as a property
    for full range of functionality.  The ``access`` property automatically reconfigures
    itself according to the specified data release on each call.

    This mixin contains one abstractmethod you must override when subclassing.

    - **_set_access_path_params**: sets the arguments needed by `sdss_access`

    Parameters
    ----------
        release : str
            The data release of the object, e.g. "DR16"

    Attributes
    ----------
        path_name : str
            The `sdss_access` template path name
        path_params : dict
            The set of `sdss_access` template path keyword arguments
        access : ~sdss_access.sync.access.Access
            An instance of `sdss_access` using for all path creation and file downloads

    '''

    path_name: str = None

    def __init__(self, *args: str, **kwargs: str):
        self._release = kwargs.get('release', None) or config.release

        # sdss_access attributes
        self._access = None
        self.path_params = None

        self._setup_access()

        super().__init__(*args, **kwargs)

    @property
    @set_access
    def access(self) -> Type[Access]:
        ''' Returns an instance of `~sdss_access.sync.access.Access` '''
        return self._access

    @abc.abstractmethod
    def _set_access_path_params(self) -> None:
        ''' Return the sdss_access path parameters

        This method must be overridden by each subclass and must set at least one
        parameter, "path_params", which specify parameters to be passed
        to sdss_access.  "path_name" must also be specified as a class attribute.

        Attributes
        ----------
            path_name : str
                Required. The sdss_access template path key name.  Must be set on the class.
            path_params : dict
                Required. The keywords needed to fill out the sdss_access template path
        '''

    @check_access_params
    def get_full_path(self, url: str = None, force_file: bool = None) -> str:
        """ Returns the full path of the file in the tree.

        Parameters
        ----------
            url : bool
                If True, specifies the url location rather than the local file location
            force_file : bool
                If True, explicitly returns any set filename attribute instead of constructing
                a path from keyword arguments.

        Returns
        -------
            fullpath : str
                The full path as built by sdss_access
        """

        if force_file:
            return self.filename

        log.debug(f'getting full path for {self.path_name} and params {self.path_params}')
        msg = 'sdss_access was not able to retrieve the full path of the file.'
        fullpath = None
        try:
            if url:
                fullpath = self.access.url(self.path_name, **self.path_params)
            else:
                fullpath = self.access.full(self.path_name, **self.path_params)
        except TypeError as ee:
            warnings.warn(msg + 'Error: {0}'.format(str(ee)), BrainUserWarning)
            raise BrainError(f'Bad input type for sdss_access: {ee}') from ee
        except Exception as ee:
            warnings.warn(msg + 'Error: {0}'.format(str(ee)), BrainUserWarning)
        return fullpath

    def _setup_access(self, params: dict = None, origin: str = None) -> None:
        ''' Set up the initial access parameters

        Sets up an initial default path_params dictionary.  Given a provided `path_name`
        class attribute, looks up the path keyword arguments and creates instance properties,
        as well as a default `path_params` dictionary.  If "params" is specified then properties
        and `path_params` is updated from that input.

        Parameters
        ----------
            params : dict
                A dictionary of access path params
            origin : str
                Indicates the origin of the content calling this method. Either "file" or "object"
        '''

        assert origin in [None, 'file', 'object'], 'origin can only be file or object'

        # do nothing if no path_name set
        if not hasattr(self, 'path_name') or not self.path_name:
            return

        # look up the access keys and create attributes
        keys = self.access.lookup_keys(self.path_name)
        log.debug(f"setting up initial access keys for {keys} for {self.path_name}")
        for k in keys:
            # look up a possible work version
            work_ver = self._version.get(k, None)
            vmsg = ('Version extracted from file is different than your preset "work" '
                    f'version for {k}. Consider updating the configured work version or '
                    'specifying an input version.')

            # look for a default value
            default = self._path_defaults.get(k, None) if hasattr(
                self, '_path_defaults') else None

            # set the work version as default if no default found
            if not default and work_ver and origin == 'object':
                default = work_ver

            # get the attribute value to set
            if params:
                if type(params) != dict:
                    raise TypeError('the path_params attribute must be a dictionary')

                # check if work_ver should supersede the path_param
                if origin == 'object' and work_ver:
                    params[k] = work_ver

                attr_value = params.get(k, default)
            else:
                attr_value = default

            # skip if a class attribute already exists
            if hasattr(self.__class__, k):
                # but first check the work version and issue a warning if there mismatch is found
                if work_ver and origin == 'file' and work_ver != attr_value:
                    warnings.warn(vmsg)
                continue

            # set attributes on the instance
            setattr(self, k, attr_value)

            # issue a warning if the preset work version mismatches from the one
            # extracted from the file
            if origin == 'file' and work_ver and work_ver != getattr(self, k, None):
                warnings.warn(vmsg)

        # create a default path params dictionary
        self.path_params = {k: getattr(self, k) for k in keys}

    @check_access_params
    def download(self) -> None:
        """ Download the file using sdss_access """

        self.access.remote()
        self.access.add(self.path_name, **self.path_params)
        self.access.set_stream()
        self.access.commit()
        paths = self.access.get_paths()
        # adding a millisecond pause for download to finish and file existence to register
        time.sleep(0.001)

        self.filename = paths[0]  # doing this for single files, may need to change
