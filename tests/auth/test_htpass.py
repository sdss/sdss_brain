# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: test_htpass.py
# Project: auth
# Author: Brian Cherinka
# Created: Friday, 23rd October 2020 11:01:38 am
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Friday, 23rd October 2020 11:01:38 am
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import
import pytest
from sdss_brain import cfg_params
from sdss_brain.auth import Htpass
from sdss_brain.exceptions import BrainError

try:
    import passlib
except ImportError:
    passlib = None
else:
    from passlib.apache import HtpasswdFile


@pytest.fixture()
def htpass(monkeypatch, tmpdir):
    tmphtp = tmpdir.mkdir('htpass').join('.htpasswd')
    monkeypatch.setitem(cfg_params, 'htpass_path', str(tmphtp))
    yield tmphtp


@pytest.fixture()
def goodhtp(htpass):
    htpass.write('')
    yield htpass


@pytest.fixture()
def realhtp(goodhtp):
    goodhtp.write('')
    if not passlib:
        pytest.skip('passlib not installed.')

    ht = HtpasswdFile(str(goodhtp), new=True)
    ht.set_password("testuser", "test secret password")
    ht.save()
    yield goodhtp


class TestHtpass(object):

    def test_valid_htpass(self, goodhtp):
        h = Htpass()
        assert h.is_valid is True
        assert h.list_users() == []

    def test_real_htpass(self, realhtp):
        h = Htpass()
        assert h.is_valid is True
        assert h.list_users() == ['testuser']

    @pytest.mark.parametrize('user, passwd, exp',
                             [('baduser', 'stuff', None),
                              ('testuser', 'badpass', False),
                              ('testuser', 'test secret password', True)],
                             ids=['baduser', 'badpass', 'gooduser'])
    def test_validate_user(self, realhtp, user, passwd, exp):
        h = Htpass()
        vv = h.validate_user(user, passwd)
        assert vv == exp

    def test_no_htpass(self, htpass):
        with pytest.raises(BrainError, match='No .htpasswd file found at *'):
            Htpass()
