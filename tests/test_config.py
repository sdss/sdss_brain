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
@pytest.fixture(autouse=True)
def set_default():
    config.set_release("DR16")


@pytest.fixture()
def mockedcfg(monkeypatch):
    ''' fixture to return a mocked Config with modified cfg_params '''
    monkeypatch.setitem(cfg_params, 'ignore_db', True)
    monkeypatch.setitem(cfg_params, 'download', True)
    monkeypatch.setitem(cfg_params, 'work_versions', {})
    config = Config()
    config.set_user('test')
    yield config
    config = None


class TestConfig(object):

    def test_release_fail(self):
        with pytest.raises(BrainError, match='trying to set an invalid release version'):
            config.release = 'DR4'

    def test_set_release_fail(self):
        with pytest.raises(BrainError, match='trying to set an invalid release version'):
            config.set_release('DR4')

    @pytest.mark.parametrize('release', ['work', 'MPL8'])
    def test_release_bad_user(self, mockedcfg, release):
        with pytest.raises(BrainError, match='User test is not validated.'):
            mockedcfg.set_release(release)

    def test_public_invalid_user(self, mockedcfg):
        mockedcfg.set_release('DR14')
        assert mockedcfg.release == 'DR14'
        mockedcfg.set_release('DR8')
        assert mockedcfg.release == 'DR8'

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

    def test_set_work_versions(self, mockedcfg):
        exp = {'drpver': 'v2_4_3', 'apred': 'r12'}
        config.set_work_versions(exp)
        assert config.work_versions == exp

    def test_public_release(self):
        assert config.is_release_public() == True
        assert config.is_release_public("IPL1") == False
        config.set_release('IPL1')
        assert config.is_release_public() == False
        config.set_release('DR16')

