# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: test_manager.py
# Project: api
# Author: Brian Cherinka
# Created: Tuesday, 3rd November 2020 3:46:09 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Tuesday, 3rd November 2020 3:46:09 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import

import pytest
import pydantic
from httpx import Response
from astropy.table import Table
from sdss_brain.api.manager import ApiProfile, ApiProfileModel, Domain, apim


class TestDomain(object):

    def test_good_domain(self):
        data = {'name': 'test.sdss.org', 'public': False, 'description': 'test domain'}
        domain = Domain.parse_obj(data)
        assert domain.name == data['name']
        assert domain.public == data['public']
        assert domain.description == data['description']

        assert str(domain) == data['name']
        assert data['name'] == domain

    def test_invalid_domain(self):
        with pytest.raises(pydantic.ValidationError, match='Domain name bad.domain does not '
                           'fit format of "xxx.sdss.org"'):
            Domain.parse_obj({'name': 'bad.domain', 'description': 'bad domain'})


class TestProfileModel(object):
    def test_good_profile(self):
        data = {'base': 'good', 'description': 'a good API profile', 'domains': ['data', 'sas'],
                'stems': {'test': 'dev', 'affix': 'prefix'}, 'api': True}
        profile = ApiProfileModel.parse_obj(data)
        assert profile.base == data['base']
        assert profile.domains == data['domains']
        assert profile.api is True
        assert profile.stems == data['stems']
        assert profile.auth['type'] == 'netrc'
        assert profile.mirrors is None
        assert profile.routemap is None

    @pytest.mark.parametrize('baddata, msg',
                             [({'domains': ['data']}, r'base\s* field required'),
                              ({'base': 'good'}, r'domains\s* field required'),
                              ({'base': 'good', 'domains': ['baddomain']}, 'Not all of the input domains/mirrors are in the list of domains.yml'),
                              ({'stems': {}}, 'stems dictionary must contain at least "test" and "affix" key'),
                              ({'stems': {'test': 'test', 'affix': 'badfix'}}, 'affix value can only be "prefix" or "suffix"')],
                             ids=['noname', 'nodomain', 'baddomain', 'missingaffix', 'badaffix'])
    def test_invalid_profile(self, baddata, msg):
        with pytest.raises(pydantic.ValidationError, match=msg):
            ApiProfileModel.parse_obj(baddata)


class TestProfile(object):
    profile = apim.apis['marvin']

    def test_make_profile(self, mock_profile):
        from sdss_brain.api.manager import apis
        assert {'marvin'} == set(apis)
        assert isinstance(mock_profile, ApiProfile)

    def test_change_domains(self, mock_profile):
        assert 'sas.sdss.org' == mock_profile.current_domain
        assert mock_profile.is_domain_public is False
        mock_profile.change_domain('dr15')
        assert 'dr15.sdss.org' == mock_profile.current_domain
        assert 'dr15.sdss.org' in mock_profile.url
        assert mock_profile.is_domain_public is True
        assert mock_profile.url.startswith('https://')

    @pytest.mark.parametrize('local, value, url',
                             [('port', 5000, "localhost:5000"),
                              ('ngrok', 12345, "12345.ngrok.io")],
                             ids=['port', 'ngrokid'])
    def test_localhost(self, mock_profile, local, value, url):
        if local == 'port':
            mock_profile.change_domain('local', port=value)
        elif local == 'ngrok':
            mock_profile.change_domain('local', ngrokid=value)
        assert url in mock_profile.url
        assert mock_profile.url.startswith('http://')

    def test_localhost_failures(self, mock_profile):
        with pytest.raises(ValueError, match='A port or ngrokid must be specified when domain is local'):
            mock_profile.change_domain('local')

    @pytest.mark.parametrize('option', [('test'), ('public')])
    def test_change_paths(self, mock_profile, option):
        assert 'sas.sdss.org/marvin/api' in mock_profile.url
        mock_profile.change_path(test=option == 'test', public=option == 'public')
        assert f'sas.sdss.org/{option}/marvin/api' in mock_profile.url
        mock_profile.change_path()
        assert 'test' not in mock_profile.url and 'public' not in mock_profile.url
        assert mock_profile.url.startswith('https://')

    def test_construct_route(self, mock_profile):
        assert 'sas.sdss.org/marvin/api' in mock_profile.url
        url = mock_profile.construct_route('general/getroutemap/')
        assert url == 'https://sas.sdss.org/marvin/api/general/getroutemap/'

    def test_construct_url(self, mock_profile):
        url = mock_profile.construct_url()
        assert url == 'https://sas.sdss.org/marvin/api'
        url = mock_profile.construct_url(test=True)
        assert url == 'https://sas.sdss.org/test/marvin/api'

    def test_construct_token_url(self, mock_profile):
        url = mock_profile.construct_token_url()
        assert url == 'https://sas.sdss.org/marvin/api/general/login/'
        assert mock_profile.auth_type == 'token'

        url = mock_profile.construct_token_url(refresh=True)
        assert url == 'https://sas.sdss.org/marvin/api/general/refresh/'

    def test_check_tokens(self, mock_profile):
        assert mock_profile.check_for_token() == 'xyz123'
        assert mock_profile.check_for_refresh_token() == 'abc123'

    def test_get_token(self, respx_mock, mock_profile, monkeypatch):
        monkeypatch.setattr(mock_profile, 'check_for_token', lambda: None)

        url = 'https://sas.sdss.org/marvin/api/general/login/'
        respx_mock.post(url).mock(return_value=Response(200, json={'access_token': 'xyz123', 'refresh_token': 'abc123'}))

        tokens = mock_profile.get_token('sdss')
        assert tokens['access'] == 'xyz123'
        assert tokens['refresh'] == 'abc123'

    def test_refresh_token(self, respx_mock, mock_profile):
        url = 'https://sas.sdss.org/marvin/api/general/refresh/'
        respx_mock.post(url).mock(return_value=Response(200, json={'access_token': '123xyz'}))

        tokens = mock_profile.refresh_auth_token()
        assert tokens['access'] == '123xyz'

class TestManager(object):

    @pytest.mark.parametrize('domain', ['data.sdss.org', 'dr15.sdss.org'])
    def test_list_domains(self, domain):
        domains = apim.list_domains()
        d = Domain(name=domain)
        assert str(d) in domains
        assert isinstance(domains[0], Domain)

    def test_identify_api(self):
        (api, domain) = apim.identify_api_from_url('https://dr15.sdss.org/marvin/api/cubes')
        assert (api, domain) == ('marvin', 'dr15')

    def test_set_profile(self):
        assert apim.profile is None
        apim.set_profile('marvin')
        assert apim.profile == apim.apis['marvin']

    def test_list_apis(self, mock_profile):
        apis = apim.list_apis()
        assert str(mock_profile) in [str(a) for a in apis]

    def test_display_domains(self):
        table = apim.display('domains')
        assert isinstance(table, Table)
        assert set(['data', 'dr15', 'sas', 'api']).issubset(set(table['key']))
        assert table[table['key'] == 'dr15']['description'][0] == 'public domain for DR15 data access'

    @pytest.mark.parametrize('option',
                             [('full'),
                              ('nodocs'),
                              ('nodesc')])
    def test_display_apis(self, option):
        table = apim.display('apis', show_docs=option != 'nodocs', show_desc=option != 'nodesc')
        assert isinstance(table, Table)
        assert set(['marvin']).issubset(set(table['key']))
        if option == 'nodocs':
            assert 'docs' not in table.colnames
        elif option == 'nodesc':
            assert 'description' not in table.colnames
        else:
            assert table[table['key'] == 'marvin']['description'][0] == 'API for accessing MaNGA data via Marvin'

