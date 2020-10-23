# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: test_netrc.py
# Project: auth
# Author: Brian Cherinka
# Created: Friday, 23rd October 2020 9:46:52 am
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Friday, 23rd October 2020 9:46:52 am
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import

import os
import pytest

from sdss_brain import cfg_params
from sdss_brain.auth import Netrc
from sdss_brain.exceptions import BrainError


@pytest.fixture()
def netrc(monkeypatch, tmpdir):
    tmpnet = tmpdir.mkdir('netrc').join('.netrc')
    monkeypatch.setitem(cfg_params, 'netrc_path', str(tmpnet))
    yield tmpnet


@pytest.fixture()
def goodnet(netrc):
    netrc.write('')
    os.chmod(str(netrc), 0o600)
    yield netrc


@pytest.fixture()
def bestnet(goodnet):
    goodnet.write(write('data.sdss.org'), mode='a')
    goodnet.write(write('api.sdss.org'), mode='a')
    yield goodnet


def write(host):
    netstr = 'machine {0}\n'.format(host)
    netstr += '    login test\n'
    netstr += '    password test\n'
    netstr += '\n'
    return netstr


class TestNetrc(object):
    ''' test the netrc access '''

    @pytest.mark.parametrize('host, msg',
                             [('data.sdss.org', 'api.sdss.org not found in netrc.'),
                              ('api.sdss.org', 'data.sdss.org not found in netrc.')],
                             ids=['noapi', 'nodata'])
    def test_only_one_host(self, goodnet, host, msg):
        goodnet.write(write(host))
        with pytest.warns(UserWarning, match=msg):
            Netrc()

    def test_valid_netrc(self, bestnet):
        n = Netrc()
        assert n.is_valid is True
        assert n.valid_hosts == ['data.sdss.org', 'api.sdss.org']


class TestNetrcFails(object):

    def test_no_netrc(self, netrc):
        with pytest.raises(BrainError, match='No .netrc file found at *'):
            Netrc()

    def test_badpermissions(self, netrc):
        netrc.write('')
        with pytest.raises(BrainError, match='Your .netrc file does not have 600 permissions.'):
            Netrc()

    def test_badparse(self, goodnet):
        goodnet.write('hello\n', mode='a')
        with pytest.raises(BrainError, match='Your netrc file was not parsed correctly.'):
            Netrc()
