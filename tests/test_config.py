# !/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Filename: test_config.py
# Project: tests
# Author: Brian Cherinka
# Created: Tuesday, 17th March 2020 4:22:15 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Tuesday, 17th March 2020 5:30:03 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import
import pytest
from sdss_brain import cfg_params
from sdss_brain.config import config, tree, Config
from sdss_brain.exceptions import BrainError

# set release to DR16
config.set_release("DR16")


@pytest.fixture()
def mockedcfg(monkeypatch):
    ''' fixture to return a mocked Config with modified cfg_params '''
    monkeypatch.setitem(cfg_params, 'ignore_db', True)
    monkeypatch.setitem(cfg_params, 'download', True)
    config = Config()
    yield config
    config = None


class TestConfig(object):
    
    def test_release_fail(self):
        with pytest.raises(BrainError) as cm:
            config.release = 'DR4'
        assert 'trying to set an invalid release version.' in str(cm.value)
    
    def test_set_release_fail(self):
        with pytest.raises(BrainError) as cm:
            config.set_release('DR4')
        assert 'trying to set an invalid release version.' in str(cm.value)

    def test_set_release(self):
        old = 'DR16'
        new = 'DR15'
        assert config.release == old
        assert tree.config_name == old.lower()
        config.release = new
        assert config.release == new
        assert tree.config_name == new.lower()
        config.set_release(old)
        assert config.release == old

    def test_read_cfg(self):
        assert hasattr(config, '_custom_config')
        assert isinstance(config._custom_config, dict)
        assert 'mapped_versions' in config._custom_config

    def test_update_cfg(self, mockedcfg):
        assert config.ignore_db is False
        assert mockedcfg.ignore_db is True
        
        assert config.download is False
        assert mockedcfg.download is True
