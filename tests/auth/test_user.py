# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: test_user.py
# Project: auth
# Author: Brian Cherinka
# Created: Friday, 23rd October 2020 11:23:48 am
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Friday, 23rd October 2020 11:23:49 am
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import

import os
import pytest
import respx
from sdss_brain import cfg_params
from sdss_brain.config import config
from sdss_brain.auth import User
from sdss_brain.exceptions import BrainError


@pytest.fixture(autouse=True)
def setup_paths(monkeypatch, tmpdir):
    tmpnet = tmpdir.mkdir('netrc').join('.netrc')
    monkeypatch.setitem(cfg_params, 'netrc_path', str(tmpnet))
    tmphtp = tmpdir.mkdir('htpass').join('.htpasswd')
    monkeypatch.setitem(cfg_params, 'htpass_path', str(tmphtp))
    yield tmpnet, tmphtp


@pytest.fixture()
def goodnet(setup_paths):
    tmpnet, tmphtpass = setup_paths  # pylint: disable=unused-variable
    tmpnet.write('')
    os.chmod(str(tmpnet), 0o600)
    tmpnet.write(write('data.sdss.org'), mode='a')
    tmpnet.write(write('api.sdss.org'), mode='a')
    yield tmpnet


def write(host):
    netstr = 'machine {0}\n'.format(host)
    netstr += '    login test\n'
    netstr += '    password test\n'
    netstr += '\n'
    return netstr


@pytest.fixture()
def user():
    u = User('test')
    yield u
    u = None


user_data = {'authenticated': 'True',
             'member': {'sdss4': {'email': 'test@email.edu',
                                  'fullname': 'Test User',
                                  'has_sdss_access': True,
                                  'username': 'test'},
                        'sdss5': {'email': 'test@email.edu',
                                  'fullname': 'Test User',
                                  'has_sdss_access': True,
                                  'username': 'test'}},
             'message': 'Welcome Back!',
             'username': 'test'}


class TestUser(object):

    def test_blank_user(self, user):
        assert user.user == 'test'
        assert user.validated is False

    def test_user_valid_netrc(self, goodnet, user):
        assert user.user == 'test'
        assert user.validated is True
        user.is_netrc_valid is True

    @respx.mock
    def test_validate_user(self, goodnet, user):
        url = 'https://internal.sdss.org/dev/collaboration/api/login'
        request = respx.post(url, content=user_data, status_code=200)

        user.validate_user('test')
        assert user.is_sdss_cred_valid is True
        assert user.in_sdss == {'sdss4': True, 'sdss5': True}
        assert user.member == user_data['member']





