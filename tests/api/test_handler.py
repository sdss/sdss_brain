# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: test_handler.py
# Project: api
# Author: Brian Cherinka
# Created: Wednesday, 4th November 2020 3:20:01 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Wednesday, 4th November 2020 3:20:01 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import
import pytest
from sdss_brain.api.handler import ApiHandler
from sdss_brain.api.client import SDSSClient, SDSSAsyncClient


class TestHandler(object):

    @pytest.mark.parametrize('api_input',
                             [('marvin'),
                              ('https://sas.sdss.org/marvin/api/general/getroutemap/'),
                              (('marvin', 'general/getroutemap'))])
    def test_creation(self, api_input):
        a = ApiHandler(api_input)
        assert str(a.api) == 'marvin'
        assert 'sas.sdss.org' == a.api.current_domain
        if api_input == 'marvin':
            assert a.url is None
        elif type(api_input) == str and api_input.startswith('http'):
            assert a.url == api_input
        else:
            api, url = api_input
            assert str(a.api) == api
            assert a.url == url
            assert a.client.url == 'https://sas.sdss.org/marvin/api/general/getroutemap'

    def test_with_domain(self):
        a = ApiHandler(('marvin', 'general/getroutemap', 'dr15'))
        assert 'dr15.sdss.org' in a.client.url

    def test_extend_url(self):
        a = ApiHandler(('marvin', 'general/getroutemap'))
        url = a.extend_url('cubes')
        assert url == 'general/getroutemap/cubes'

    def test_resolve_url(self):
        a = ApiHandler(('marvin', 'cubes/{plateifu}'))
        assert a.has_valid_url is False

        params = a.extract_url_brackets()
        assert params == ['plateifu']

        a.resolve_url({'plateifu': '8485-1901'})

        assert a.has_valid_url is True
        assert a.url == 'cubes/8485-1901'

    @pytest.mark.parametrize('async_client, client',
                             [(True, SDSSAsyncClient),
                              (False, SDSSClient)])
    def test_client(self, async_client, client):
        a = ApiHandler('marvin', async_client=async_client)
        assert isinstance(a.client, client)



