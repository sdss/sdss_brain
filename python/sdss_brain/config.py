# !/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Filename: config.py
# Project: sdss_brain
# Author: Brian Cherinka
# Created: Friday, 14th February 2020 1:41:34 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Monday, 16th March 2020 10:00:24 am
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import
from sdss_brain import cfg_params, log
from sdss_brain.exceptions import BrainError


class Config(object):
    ''' Main configuration class for SDSS '''
    
    def __init__(self):
        self._mode = 'auto'
        self._release = None
        self.download = False
        self.ignore_db = False

        # TODO replace with a tree access method
        self._allowed_releases = [f'DR{i}' for i in range(8, 17)]
        # set latest release
        self.release = self._get_latest_release()

        # load default config parameters
        self._load_defaults()

    def __repr__(self):
        return f'<Config(release={self.release}, mode={self.mode})>'
    
    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value):
        assert value in ['local', 'remote', 'auto'], ('config.mode must be "local",'
                                                      '"remote", or "auto".')
        self._mode = value

    @property
    def release(self):
        return self._release

    @release.setter
    def release(self, value):
        value = value.upper()
        if value not in self._allowed_releases:
            raise BrainError('trying to set an invalid release version. Valid releases are: {0}'
                             .format(', '.join(self._allowed_releases)))

        self._release = value

    def set_release(self, version=None):
        if not version:
            version = self._get_latest_release()
            log.info(f'Setting release to latest: {version}')
        self.release = version

    def _get_latest_release(self):
        return max(self._allowed_releases, key=lambda t: int(t.rsplit('DR', 1)[-1]))

    def _load_defaults(self):
        ''' Load the Brain config yaml file and update any parameters '''

        # update any matching Config values
        for key, value in cfg_params.items():
            if hasattr(self, key):
                self.__setattr__(key, value)

        self._custom_config = cfg_params


config = Config()

