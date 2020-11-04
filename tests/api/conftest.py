# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: conftest.py
# Project: api
# Author: Brian Cherinka
# Created: Wednesday, 4th November 2020 5:51:18 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Wednesday, 4th November 2020 5:51:19 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import
import pytest

import sdss_brain.api.manager


api_prof = {'marvin': {'description': 'API for accessing MaNGA data via Marvin',
                       'docs': 'https://sdss-marvin.readthedocs.io/en/stable/reference/web.html',
                       'base': 'marvin',
                       'domains': ['sas', 'lore', 'dr15', 'dr16'],
                       'mirrors': ['magrathea'],
                       'stems': {'test': 'test', 'public': 'public', 'affix': 'prefix'},
                       'api': True,
                       'routemap': 'general/getroutemap/',
                       'auth': {'type': 'token', 'route': 'general/login/'}}
            }


@pytest.fixture()
def mock_api(monkeypatch):
    """ fixture to mock the apis dictionary """
    monkeypatch.setattr(sdss_brain.api.manager, 'apis', api_prof)


@pytest.fixture()
def mock_profile(mock_api):
    """ fixture to create a new mocked API profile """
    from sdss_brain.api.manager import ApiProfile
    profile = ApiProfile('marvin')
    profile.check_for_token = lambda: 'xyz123'
    yield profile
    profile = None
