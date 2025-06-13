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
import respx
from httpx import Response

from sdss_brain.datamodel.versions import (get_mapped_version, collapse_versions,
                                           get_versions, generate_versions)
from sdss_brain import cfg_params


data = {'IPL1': {'apred_vers': '1.0', 'v_astra': '0.2.6', 'run2d': 'v6_0_9', 'run1d': 'v6_0_9'},
        'DR18': {'run2d': 'v6_0_4', 'run1d': 'v6_0_4', 'v_speccomp': 'v1.4.3', 'v_targ': '1.0.1'},
        'DR17': {'run2d': 'v5_13_2', 'apred_vers': 'dr17', 'drpver': 'v3_1_1', 'dapver': '3.1.0'},
        'DR16': {'run2d': 'v5_13_0', 'apred_vers': 'r12', 'apstar_vers': 'stars', 'drpver': 'v2_4_3', 'dapver': '2.2.1'},
        'DR15': {'run2d': 'v5_10_0', 'apstar_vers': 'stars', 'drpver': 'v2_4_3', 'dapver': '2.2.1'},
        'DR13': {'drpver': 'v1_5_4', 'dapver': 'None'},
        'DR12': {'apred_vers': 'r5', 'apstar_vers': 'stars'},
        'DR10': {'run1d': 'v5_5_12'},
        'MPL5': {'drpver': 'v2_0_1', 'dapver': '2.0.2'},
        'DR19': {'run2d': 'v6_1_3', 'apred_vers': '1.3', 'v_astra': '0.6.0', 'run1d': 'v6_1_3'},
        'IPL3': {'apred_vers': '1.3', 'v_astra': '0.6.0', 'run2d': 'v6_1_3', 'run1d': 'v6_1_3'}
        }

dmdata = {'IPL1': {'mwm': {'apred_vers': '1.0', 'v_astra': '0.2.6'},
                 'bhm': {'run2d': 'v6_0_9', 'run1d': 'v6_0_9'}},
        'DR18': {'bhm': {'run2d': 'v6_0_4', 'run1d': 'v6_0_4', 'v_speccomp': 'v1.4.3', 'v_targ': '1.0.1'}},
        'DR17': {'eboss': {'run2d': 'v5_13_2'}, 'apogee': {'apred_vers': 'dr17'}, 'manga': {'drpver': 'v3_1_1', 'dapver': '3.1.0'}},
        'DR16': {'eboss': {'run2d': 'v5_13_0'}, 'apogee': {'apred_vers': 'r12', 'apstar_vers': 'stars'}, 'manga': {'drpver': 'v2_4_3', 'dapver': '2.2.1'}},
        'DR15': {'eboss': {'run2d': 'v5_10_0'}, 'apogee': {'apstar_vers': 'stars'}, 'manga': {'drpver': 'v2_4_3', 'dapver': '2.2.1'}},
        'DR13': {'manga': {'drpver': 'v1_5_4', 'dapver': 'None'}},
        'DR12': {'apogee': {'apred_vers': 'r5', 'apstar_vers': 'stars'}},
        'DR10': {'eboss': {'run1d': 'v5_5_12'}},
        'MPL5': {'manga': {'drpver': 'v2_0_1', 'dapver': '2.0.2'}},
        'DR19': {'bhm': {'run2d': 'v6_1_3', 'run1d': 'v6_1_3'},
                 'mwm': {'apred_vers': '1.3', 'v_astra': '0.6.0'}},
        'IPL3': {'bhm': {'run2d': 'v6_1_3', 'run1d': 'v6_1_3'},
                 'mwm': {'apred_vers': '1.3', 'v_astra': '0.6.0'}}
        }

@pytest.fixture(autouse=True)
def mock_vers():
    url = 'https://api.sdss.org/valis/info/tags'
    request = respx.get(url).mock(return_value=Response(200, json={'tags': dmdata}))
    return data


@pytest.fixture()
def patch_version(mocker):
    mocker.patch('sdss_brain.datamodel.versions.get_versions', return_value=data)


@respx.mock
def test_generate_versions(mock_vers):
    vers = generate_versions()
    for key in dmdata:
        assert dmdata[key].items() <= vers[key].items()


def test_collapse_versions():
    output = {'a': {'c': 1, 'd': 2}}
    dd = collapse_versions({'a': {'b': {'c': 1, 'd': 2}}})
    assert dd == output


@pytest.fixture(params=data)
def release(request):
    yield request.param


@pytest.mark.parametrize('local', [True, False], ids=['local', 'remote'])
@respx.mock
def test_get_versions(local, mocker, release):
    if not local:
        mocker.patch('sdss_brain.datamodel.versions.SDSSDataModel', new=None)

    out = get_versions()
    assert data[release].items() <= out[release].items()

@pytest.mark.parametrize('release, key, exp',
                            [('DR18', 'run2d', 'v6_0_4'),
                            ('DR17', 'drpver', 'v3_1_1'),
                            ('DR15', 'dapver', '2.2.1'),
                            ('DR13', 'drpver', 'v1_5_4'),
                            ('DR13', 'dapver', 'None'),
                            ('MPL5', 'drpver', 'v2_0_1'),
                            ('MPL5', 'dapver', '2.0.2'),
                            ('DR16', 'run2d', 'v5_13_0'),
                            ('DR10', 'run1d', 'v5_5_12'),
                            ('DR12', 'apred', 'r5'),
                            ('DR15', 'apstar', 'stars'),
                            ('WORK', 'run2d', None),
                            ('IPL1', None, {'apred_vers': '1.0', 'v_astra': '0.2.6', 'run2d': 'v6_0_9', 'run1d': 'v6_0_9'}),
                            ('DR19', 'run2d', 'v6_1_3'),
                            ('IPL3', 'run2d', 'v6_1_3')
                            ])
def test_get_version_from_release(patch_version, release, key, exp):
    version = get_mapped_version(key, release=release)
    assert version == exp

@pytest.mark.parametrize('key, exp',
                            [('apred_vers', 'dr17'),
                            ('apred', 'dr17'),
                            ('apr', 'dr17')
                            ])
def test_alt_versions(patch_version, monkeypatch, key, exp):
    monkeypatch.setitem(cfg_params, 'version_aliases', {'apr': 'apred_vers'})

    version = get_mapped_version(key, release='DR17')
    assert version == exp



@pytest.mark.usefixtures("patch_version")
class TestMappingFails(object):
    release = 'DR15'
    key = 'run2d'

    def test_bad_config(self, monkeypatch):
        monkeypatch.setitem(cfg_params, 'version_aliases', 'not a dict')

        with pytest.raises(TypeError, match='version_aliases must be a dictionary'):
            get_mapped_version('apr', release=self.release)

    def test_bad_versions(self, mocker):
        mocker.patch('sdss_brain.datamodel.versions.get_versions', return_value={'DR15': 'baddict'})

        with pytest.raises(TypeError, match='version info for release DR15 is not a valid dict.'):
            get_mapped_version(self.key, release=self.release)

    def test_bad_release(self):
        with pytest.raises(ValueError, match='no version info found for release badrelease.'):
            get_mapped_version(self.key, release='badrelease')
