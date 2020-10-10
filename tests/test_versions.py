# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: test_versions.py
# Project: tests
# Author: Brian Cherinka
# Created: Saturday, 10th October 2020 1:12:46 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Saturday, 10th October 2020 1:12:46 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import
import pytest
from sdss_brain.helpers import get_mapped_version
from sdss_brain import cfg_params


class TestVersionMapping(object):

    def test_mapping_exists(self):
        versions = cfg_params.get('mapped_versions', None)
        assert versions is not None
        assert isinstance(versions, dict)

    @pytest.mark.parametrize('survey, release, exp',
                             [('manga', 'DR15', {'drpver': 'v2_4_3', 'dapver': '2.2.1'}),
                              ('manga', 'DR13', {'drpver': 'v1_5_4', 'dapver': None}),
                              ('manga', 'MPL5', {'drpver': 'v2_0_1', 'dapver': '2.0.2'}),
                              ('eboss', 'DR16', 'v5_13_0'),
                              ('eboss', 'DR10', 'v5_5_12'),
                              ('apogee', 'DR12', 'r5')
                              ])
    def test_get_version_from_release(self, survey, release, exp):
        version = get_mapped_version(survey, release=release)
        assert version == exp

    @pytest.mark.parametrize('survey, key, exp',
                             [('manga', None, {'drpver': 'v2_4_3', 'dapver': '2.2.1'}),
                              ('manga', 'drpver', 'v2_4_3'),
                              ('manga', 'dapver', '2.2.1'),
                              ('eboss', None, 'v5_10_0'),
                              ('eboss', 'run2d', 'v5_10_0')
                              ])
    def test_get_version_keys(self, survey, key, exp):
        version = get_mapped_version(survey, release='DR15', key=key)
        assert version == exp


class TestMappingFails(object):
    release = 'DR15'
    name = 'manga'

    def test_bad_config(self, monkeypatch):
        monkeypatch.setitem(cfg_params, 'mapped_versions', 'not a dict')

        with pytest.raises(TypeError, match='mapped_versions must be a dictionary'):
            get_mapped_version(self.name, release=self.release)

    def test_bad_name(self):
        with pytest.raises(ValueError, match='not found in mapped_versions dictionary'):
            get_mapped_version('badname', release=self.release)

    def test_name_bad_value(self, monkeypatch):
        versions = cfg_params['mapped_versions']
        monkeypatch.setitem(versions, self.name, 'not a dict')

        with pytest.raises(TypeError, match='release versions for .* must be a dictionary'):
            get_mapped_version(self.name, release=self.release)

    def test_bad_release(self):
        with pytest.raises(ValueError, match='no version found for release'):
            get_mapped_version(self.name, release='badrelease')
