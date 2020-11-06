# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: config.py
# Project: sdss_brain
# Author: Brian Cherinka
# Created: Friday, 14th February 2020 1:41:34 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Tuesday, 17th March 2020 4:20:37 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import
from sdss_brain import cfg_params, log, tree
from sdss_brain.auth import User
from sdss_brain.api.manager import ApiManager
from sdss_brain.exceptions import BrainError


class Config(object):
    """ Main configuration class for SDSS Brain

    This class helps set up global configurations for the ``Brain`` to use.

    Attributes
    ----------
    download : bool
        When True, automatically downloads all data
    ignore_db : bool
        When True, automatically ignores all database connections
    work_versions: dict
        A dictionary containing the survey version numbers to work with non-released data
    user: type[User]
        A validated SDSS user
    """

    def __init__(self):
        self._mode = 'auto'
        self._release = None
        self.download = False
        self.ignore_db = False
        self.work_versions = None

        # load default config parameters
        self._load_defaults()

        # get allowed releases from the Tree
        self._allowed_releases = tree.get_available_releases()

        # set a default release or get the latest one
        default_release = self._custom_config.get('default_release', None)
        self.release = default_release or self._get_latest_release()

        # set any work versions from the config
        self.set_work_versions()

        # set default sdss user
        self.set_user()

        # set default API
        self.set_api()

    def __repr__(self):
        return f'<SDSSConfig(release={self.release}, mode={self.mode})>'

    @property
    def mode(self) -> str:
        """ The mode of operation for the Brain """
        return self._mode

    @mode.setter
    def mode(self, value: str):
        assert value in ['local', 'remote', 'auto'], ('config.mode must be "local",'
                                                      '"remote", or "auto".')
        self._mode = value

    @property
    def release(self) -> str:
        """ The SDSS public, internal, or "work" release """
        return self._release

    @release.setter
    def release(self, value: str) -> None:
        value = value.upper()
        if value not in self._allowed_releases:
            raise BrainError(f'trying to set an invalid release version {value}. '
                             f'Valid releases are: {", ".join(self._allowed_releases)}')

        # replant the tree
        if value.lower() == 'work':
            tree.replant_tree('sdsswork')
        else:
            tree.replant_tree(value.lower())

        self._release = value

    def set_release(self, version: str = None) -> None:
        """ Set a new release

        Set a new global data release to use.  Can be either
        a public, internal SDSS data release, or can use non-released data
        by setting release to "WORK".

        Parameters
        ----------
        version : str, optional
            The new data release to set, by default uses the latest public DR
        """
        if not version:
            version = self._get_latest_release()
            log.info(f'Setting release to latest: {version}')
        self.release = version

    def _get_latest_release(self) -> str:
        """ Get the latest public DR release """
        drsonly = [i for i in self._allowed_releases if 'DR' in i]
        return max(drsonly, key=lambda t: int(t.rsplit('DR', 1)[-1]))

    def list_allowed_releases(self) -> list:
        """ List the allowed releases based on the available tree environment configurations """
        return self._allowed_releases

    def _load_defaults(self) -> None:
        """ Load the Brain config yaml file and update any parameters """

        # update any matching Config values
        for key, value in cfg_params.items():
            if hasattr(self, key):
                self.__setattr__(key, value)

        self._custom_config = cfg_params

    def set_work_versions(self, values: dict = {}) -> None:
        """ Set the versions used for sdsswork

        Sets the versions used by sdswork globally into the config.
        Input is a valid dictionary containing version names and numbers as
        key value pairs, e.g. `{'drpver':'v2_4_3', 'run2d':'v1_1_1', 'apred':'r12'}`.
        Optionally can set them permanently in the custom configuration YAML file.

        The input dictionary is merged with any values specified from the custom config.

        Parameters
        ----------
        values : dict, optional
            Dictionary of version names:numbers needed in paths, by default {}

        Raises
        ------
        ValueError
            when the input is not a dictionary
        """

        if type(values) != dict:
            raise ValueError('input versions must be a dict')

        cfg_work = self._custom_config.get('work_versions', {})
        cfg_work.update(values)
        self.work_versions = cfg_work

    def set_user(self, user: str = 'sdss', password: str = None) -> None:
        """ Set a new global user

        Sets a new global `~sdss_brain.auth.user.User`.  By default with be
        set to the generic "sdss" user.  Can override the default by setting
        the "default_username" and "default_userpass" keywords in the custom
        YAML configuration file.

        Parameters
        ----------
        user : str, optional
            The username to use, by default 'sdss'
        password : str, optional
            The password to use to validate the user, by default None.

        Raises
        ------
        BrainError
            when a user cannot be validated
        """

        default_user = self._custom_config.get('default_username', None)
        default_pass = self._custom_config.get('default_userpass', None)
        user = default_user or user
        password = default_pass or password
        log.debug(f'Setting user {user}. '
                  '{"No password specified." if not password else "Password specified."}')
        self.user = User(user)
        if not self.user.validated and user and password:
            self.user.validate_user(password)

            if not self.user.validated:
                raise BrainError(f'Could not validate default user {user}!')
            else:
                log.debug(f'Validated user {user}')

        if not self.user.validated:
            log.warning(f'User {user} is not validated.  Check your netrc credentials '
                        'or validate your user with config.set_user(username, password)')

    def set_api(self, name: str = None, domain: str = None, test: bool = None) -> None:
        """ Set a new global API to use

        Sets the `~sdss_brain.api.manager.ApiManager` and a new global
        `~sdss_brain.api.manager.ApiProfile`.  Can set permanently by setting
        the "default_api" keywords in the custom YAML configuration file.

        Parameters
        ----------
        name : str, optional
            The name of a valid SDSS API, by default None
        domain : str, optional
            The name of the domain to set on the API profile, by default None
        test : bool, optional
            If True, uses the development API, by default None
        """
        default_api = self._custom_config.get('default_api', None)
        name = name or default_api
        self.apis = ApiManager()
        if name:
            self.apis.set_profile(name, domain=domain, test=test)


config = Config()

