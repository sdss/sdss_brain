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
import warnings
from sdss_brain.config import config
from sdss_brain.exceptions import BrainError
from sdss_brain.helpers import db_type
from sdss_brain.api.handler import api_type, ApiHandler
from sdss_brain.mixins.mma import MMAccess, MMAMixIn
from astropy.io import fits


class Base(abc.ABC):
    ''' abstract base class for tools '''

    def __new__(cls, *args, **kwargs):
        # set the correct MMA class
        if MMAccess in cls.mro():
            cls._mma = MMAccess
        else:
            cls._mma = MMAMixIn

        return super().__new__(cls)

    @abc.abstractmethod
    def _load_object_from_file(self) -> None:
        pass

    @abc.abstractmethod
    def _load_object_from_db(self) -> None:
        pass

    @abc.abstractmethod
    def _load_object_from_api(self) -> None:
        pass


class HindBrain(Base):
    ''' Base class for utilizing the MMA mixin

    This is a convenience class with the `~sdss_brain.mixins.mma.MMAccess` already implemented.
    This class initializes the ``MMAccess`` and provides logic to load data based
    on the data_origin.  It also provides a simple ``repr``.

    In addition to any abstractmethod from the MMA, this class contains three abstractmethods you
    must override when subclassing.

    - **_load_object_from_file**: defines data load/handling from a local file
    - **_load_object_from_db**: defines data load/handling from a local database
    - **_load_object_from_api**: defines data load/handling from a remote API

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
        use_db : db_type, see `~sdss_brain.helpers.database.DatabaseHandler`
            a database ORM or connection to override the default with
        use_api : api_type, see `~sdss_brain.api.handler.ApiHandler`
            An API or URL route to use for remote access to the object
        async_client : bool
            If True, sets the remote http client to `~sdss_brain.api.client.SDSSAsyncClient`
    Attributes
    ----------
        db : `~sdss_brain.helpers.database.DatabaseHandler`
            A db handler for any loaded sdssdb ORM or db connection for the object
        mapped_version : str
            The name of survey/category in the mapped_versions dictionary
        remote : `~sdss_brain.api.handler.ApiHandler`
            An api handler for loaded APIs or urls, and sending http requests
    '''
    _db = None
    mapped_version = None
    data_origin = None
    _api = None
    async_client = False

    def __new__(cls, *args, **kwargs):
        # set any work versions
        cls.set_work_version(config.work_versions)
        return super().__new__(cls)

    def __init__(self, data_input: str = None, filename: str = None,
                 objectid: str = None, mode: str = None,
                 release: str = None, download: bool = None,
                 ignore_db: bool = None, use_db: db_type = None, version: str = None,
                 use_api: api_type = None, async_client: bool = None) -> None:

        # set a version for sdsswork data
        checked_release = release or config.release
        if version:
            self.set_work_version(version)
            if checked_release.lower() != 'work':
                raise BrainError('version is only used for "work" data. '
                                 'Please set the input or config release to "WORK"')
        else:
            if not self._version and checked_release.lower() == 'work':
                raise BrainError('You are using a "work" release but have no work versions set! '
                                 'Try setting a global "work_version" dict or specify a "version" '
                                 'input!')

        # initialize the MMA
        self._mma.__init__(self, data_input=data_input, filename=filename,
                           objectid=objectid, mode=mode,
                           release=release, download=download,
                           ignore_db=ignore_db, use_db=use_db or self._db)

        # set up any ApiHandler
        remote = use_api or self._api or config.apis.profile
        async_client = async_client or self.async_client
        if remote:
            self._api = ApiHandler(remote, async_client=async_client)
            self._check_remote_url()

        # load the data
        if self.data_origin == 'file':
            self._load_object_from_file()
        elif self.data_origin == 'db':
            self._load_object_from_db()
        elif self.data_origin == 'api':
            self._load_object_from_api()

    def __repr__(self):
        objname = f"objectid='{self.objectid}'" if self.objectid else f"filename='{self.filename}'"
        return (f"<{self.__class__.__name__} {objname}, mode='{self.mode}', "
                f"data_origin='{self.data_origin}'>")

    @property
    def remote(self):
        """ An instance of an ApiHandler """
        return self._api

    def resolve_remote_url(self):
        """ Resolve the remote url using instance attributes

        Attempts to resolve the remote url and match the named arguments
        in the url to any instance attributes that are set.  Otherwise issues a warning
        for the user to resolve manually.
        """
        if not self.remote or (self.remote and not self.remote.url):
            return

        names = self.remote.extract_url_brackets()
        if names:
            params = {}
            for name in names:
                if hasattr(self, name):
                    params[name] = getattr(self, name)
            try:
                self.remote.resolve_url(params)
            except KeyError as exc:
                raise BrainError(f'Cannot resolve remote url. Missing keys {exc} found.')from exc
            else:
                if not self.remote.has_valid_url:
                    raise BrainError('Still invalid url')

    def _check_remote_url(self):
        """ Check for a valid remote url and issue warning otherwise """
        if self._api and self._api.has_valid_url is False:
            try:
                self.resolve_remote_url()
            except BrainError as exc:
                warnings.warn('API url contains bracket arguments. Http request will not send '
                              'correctly.  Consider resolving the url with '
                              f'self.remote.resolve_url. {exc}')

    def __del__(self):
        ''' Destructor for closing open objects '''
        self._close()

    def _close(self):
        ''' close open object for each data_origin '''
        # close open FITS files
        if self.data_origin == 'file' and isinstance(self.data, fits.HDUList):
            self.data.close()
        elif self.data_origin == 'db':
            if hasattr(self, 'db'):
                self.db.close()
            self.data = None
        elif self.data_origin == 'api':
            if hasattr(self, 'remote'):
                self.remote.close()

    def __enter__(self):
        ''' constructor for context manager '''
        return self

    def __exit__(self, type, value, traceback):
        ''' destructor for context manager '''
        self._close()
        return True

    @classmethod
    def set_work_version(cls, value: dict) -> None:
        """ Set the work version for the given class

        Sets the versions used by sdswork on the given class.  This takes
        precendence over any versions set in the global config. Input is a valid
        dictionary containing version names and numbers as key value pairs, e.g.
        `{'drpver':'v2_4_3', 'run2d':'v1_1_1', 'apred':'r12'}`.

        The input dictionary is merged with any values specified on the config class.

        Parameters
        ----------
        values : dict, optional
            Dictionary of version names:numbers needed in paths, by default {}

        Raises
        ------
        ValueError
            when input value is not a dictionary
        """
        if type(value) != dict:
            raise ValueError(f'input verion must be a dictionary')

        # update any existing work versions with the new values
        wv = config.work_versions.copy()
        wv.update(value)
        cls._version = wv

    @classmethod
    def set_database_object(cls, value: db_type) -> None:
        """ Sets up the MMA to create a new db handler

        Sets up the MMA to create a new `~sdss_brain.helpers.database.DatabaseHandler`
        on the given class.  Valid input can be any sdssdb ORM Model,
        DatabaseConnection, or schema module.

        Parameters
        ----------
        value : db_type
            The type of ``sdssdb`` database input
        """
        # set this straight to the value since the MMA converts it into a DatabaseHandler
        cls._db = value

    @classmethod
    def set_api_object(cls, value: api_type) -> None:
        """ Sets up the tool to create a new API handler

        Sets up the tool to create a new `~sdss_brain.api.handler.ApiHandler` on the
        given class.  Valid input can be any explicit url, a string API profile name,
        or a tuple containing (API profile name, url route segment, optional domain name).

        Parameters
        ----------
        value : api_type
            The type of remote API input
        """
        cls._api = value


class Brain(HindBrain, MMAccess):
    """ The hind Brain with support for ``sdss_access``

    See `~HindBrain`, `~sdss_brain.mixins.mma.MMAccess`, and `~sdss_brain.mixins.access.AccessMixIn`
    for detailed information.

    """


class BrainNoAccess(HindBrain, MMAMixIn):
    """ A version of `~Brain` without support for ``sdss_access``

    See `~HindBrain` and `~sdss_brain.mixins.mma.MMAMixIn` for detailed
    information.

    """
