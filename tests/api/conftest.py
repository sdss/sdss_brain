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
from sdss_brain.auth.user import User
from sdss_brain.auth.netrc import Netrc

api_prof = {'marvin': {'description': 'API for accessing MaNGA data via Marvin',
                       'docs': 'https://sdss-marvin.readthedocs.io/en/stable/reference/web.html',
                       'base': 'marvin',
                       'domains': ['sas', 'lore', 'dr15', 'dr16', 'dr17'],
                       'mirrors': ['magrathea'],
                       'stems': {'test': 'test', 'public': 'public', 'affix': 'prefix'},
                       'api': True,
                       'routemap': 'general/getroutemap/',
                       'auth': {'type': 'token', 'route': 'general/login/', 'refresh': '/general/refresh/'}}
            }


@pytest.fixture()
def mock_api(monkeypatch):
    """ fixture to mock the apis dictionary """
    monkeypatch.setattr(sdss_brain.api.manager, 'apis', api_prof)

@pytest.fixture
def mock_netrc():
    """ fixture to create a new mocked netrc object """
    n = Netrc()
    n.check_netrc = lambda: True
    n.read_netrc = lambda x : ("sdss", "test")
    yield n
    n = None


@pytest.fixture()
def mock_user(mock_netrc):
    """ fixture to create a new mocked sdss user """
    user = User('sdss')
    user.netrc = mock_netrc
    user._valid_netrc = True
    yield user
    user = None


@pytest.fixture()
def mock_profile(mock_api, mock_user):
    """ fixture to create a new mocked API profile """
    from sdss_brain.api.manager import ApiProfile
    profile = ApiProfile('marvin')
    profile.check_for_token = lambda: 'xyz123'
    profile.check_for_refresh_token = lambda: 'abc123'
    yield profile
    profile = None
