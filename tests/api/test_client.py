# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: test_client.py
# Project: api
# Author: Brian Cherinka
# Created: Wednesday, 4th November 2020 3:55:16 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Wednesday, 4th November 2020 3:55:16 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import

import httpx
import io
import pytest
from sdss_brain.api.client import SDSSClient, SDSSAsyncClient, apim
from sdss_brain.exceptions import BrainError


class TestClient(object):
    url = 'https://dr15.sdss.org/marvin/api/general/getroutemap/'

    def test_use_api(self):
        s = SDSSClient(use_api='icdb')
        assert str(s.api) == 'icdb'

    def test_inputs(self):
        s = SDSSClient('general/getroutemap', use_api='marvin', domain='dr15', test=True)
        assert str(s.api) == 'marvin'
        assert s.url == 'https://dr15.sdss.org/test/marvin/api/general/getroutemap'

    def test_set_api(self):
        s = SDSSClient(self.url)
        assert s.api is None
        assert s.url == self.url

        s.set_api('marvin')
        assert s.api == apim.apis['marvin']

    def test_set_user(self):
        s = SDSSClient(self.url)
        assert str(s.user) == 'sdss'

        s.set_user('test')
        assert str(s.user) == 'test'

    @pytest.mark.parametrize('url, method, err',
                             [(None, 'get', 'No url set.  Cannot make a request.'),
                              (None, 'stuff', 'http request method type can only be "get", "post", "head", or "stream"')],
                             ids=['nourl', 'badmethod'])
    def test_request_inputfails(self, url, method, err):
        s = SDSSClient(use_api='marvin')
        with pytest.raises(ValueError, match=err):
            s.request(url, method=method)

    def test_request_unresolvedurl(self):
        s = SDSSClient('cubes/{plateifu}', use_api='marvin')
        with pytest.raises(BrainError, match='Request url contains bracket arguments: "plateifu".'):
            s.request()

    def test_bad_status(self):
        s = SDSSClient('https://httpbin.org/status/500')
        with pytest.raises(BrainError, match='500 INTERNAL SERVER ERROR'):
            s.request()

    @pytest.mark.parametrize('method', ['get', 'post'])
    def test_context(self, method):
        url = f'https://httpbin.org/{method}'
        vals = {'value': 'stuff', 'release': 'DR15'}
        with SDSSClient(url) as client:
            client.request(method=method, data=vals)
            data = client.data
            assert not client.response.is_error
        if method == 'post':
            assert data['form'] == vals
            assert data['url'] == url
        elif method == 'get':
            assert data['args'] == vals
            assert data['url'] == url + '?value=stuff&release=DR15'

    @pytest.mark.parametrize('method, exp', [('get', bytes), ('stream', io.BytesIO)])
    @pytest.mark.parametrize('noprogress', [False, True], ids=['pbar', 'nopbar'])
    def test_stream_bytes(self, method, exp, noprogress):
        with SDSSClient('https://httpbin.org/range/10', no_progress=noprogress) as client:
            client.request(method=method)
            data = client.data
        assert type(data) == exp

    @pytest.mark.parametrize('option, err',
                             [('user', 'No user specified'),
                              ('api', 'No API profile specified'),
                              ('test', 'User test is not properly validated with netrc')])
    def test_invalid_token(self, option, err):
        s = SDSSClient('/general/getroutemap', use_api='marvin')

        if option == 'user':
            s.user = None
        elif option == 'api':
            s.api = None
        elif option == 'test':
            s.set_user('test')

        with pytest.raises(ValueError, match=err):
            s.get_token()

    def test_get_auth_header(self, mock_profile):
        assert mock_profile.token == 'xyz123'
        s = SDSSClient('/general/getroutemap', use_api=mock_profile)
        header = s._create_token_auth_header()
        assert header == {'Authorization': f'Bearer {mock_profile.token}'}

    def test_notoken(self, mock_profile):
        mock_profile.auth_type = 'netrc'
        s = SDSSClient('/general/getroutemap', use_api=mock_profile)
        header = s._create_token_auth_header()
        assert header == {}

    def test_token_fails_noapi(self, mock_profile):
        s = SDSSClient('/general/getroutemap', use_api=mock_profile)
        s.api = None
        with pytest.raises(BrainError, match='No API profile set. Cannot created token auth header.'):
            s._create_token_auth_header()

    def test_token_fails_to_get(self, mock_profile, mock_user):
        s = SDSSClient('/general/getroutemap', use_api=mock_profile)
        s.user = mock_user
        mock_profile.check_for_token = lambda: None
        mock_profile.get_token = lambda x: None
        with pytest.raises(ValueError, match='No token retrieved for API marvin.  Check for a valid user'):
            s._create_token_auth_header()


class TestAsync(object):

    @pytest.mark.asyncio
    @pytest.mark.parametrize('method, exp', [('get', bytes), ('stream', io.BytesIO)])
    @pytest.mark.parametrize('noprogress', [False, True], ids=['pbar', 'nopbar'])
    async def test_stream_bytes(self, method, exp, noprogress):
        async with SDSSAsyncClient('https://httpbin.org/range/10', no_progress=noprogress) as client:
            await client.request(method=method)
            data = client.data
        assert type(data) == exp
