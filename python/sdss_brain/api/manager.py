# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: manager.py
# Project: api
# Author: Brian Cherinka
# Created: Friday, 23rd October 2020 3:08:17 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Friday, 23rd October 2020 3:08:18 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import

import pathlib
import warnings
import yaml
from pydantic import BaseModel, validator, parse_obj_as
from typing import List, Dict
from urllib.parse import urlparse, urlunparse
from sdss_brain import log
from functools import wraps


__all__ = ['Domain', 'ApiProfileModel', 'ApiProfile', 'ApiManager', 'apim']


def urljoin(url1: str, url2: str) -> str:
    """ Custom function to join two url paths

    Uses `~python.urllib.parse.urlparse` and `~python.urllib.parse.urlunparse`
    to join relevant segments of two urls.

    Parameters
    ----------
    url1 : str
        The base url to join to
    url2 : str
        The url segment to join to url1

    Returns
    -------
    str
        A joined url
    """

    e = urlparse(url1)
    t = urlparse(url2)
    final = urlunparse(tuple(strjoin(*z) for z in zip(e, t)))
    return final


def strjoin(str1: str, str2: str) -> str:
    """ Joins two url strings ignoring a leading / """
    if not str2.startswith(str1):
        f = (pathlib.Path(str1) / str2.lstrip('/')).as_posix() if str2 else str1
    else:
        f = str2
    return f


# read in the available domains / apis
with open((pathlib.Path(__file__).parent.parent / 'etc/api_profiles.yml').resolve(), 'r') as f:
    profiles = yaml.load(f.read(), Loader=yaml.SafeLoader)
    domains = profiles['domains']
    apis = profiles['apis']


class Domain(BaseModel):
    """ Pydantic class handling validation for SDSS domains """
    name: str
    public: bool = False

    @validator('name')
    def check_domain_name(cls, value):
        if value != 'localhost' and not value.endswith('sdss.org') and not value.endswith('sdss.utah.edu'):
            raise ValueError(f'Domain name {value} does not fit format of "xxx.sdss.org" or "xxx.sdss.utah.edu"')

        return value


# validate and process the domains yaml section
domains = dict(zip(domains.keys(), parse_obj_as(List[Domain], list(domains.values()))))


def check_domain(func):
    """ Decorator that checks for correct the domain

    Checks that a given input domain is in the list of valid domains for the given
    API profile.  Aso checks for the appropriate inputs when the domain is localhost, i.e.
    for an additional valid port or ngrokid input.  Raises ValueErrors.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        inst, domain = args
        port = kwargs.get('port', None)
        ngrokid = kwargs.get('ngrokid', None)

        if domain not in inst._all_domains:
            raise ValueError(
                f'Input domain "{domain}" not a valid domain/mirror for API profile {inst.name}')

        if (port or ngrokid) and domain != 'local':
            raise ValueError('Domain must be local if a port or ngrokid is set!')

        if domain == 'local' and not (port or ngrokid):
            raise ValueError('A port or ngrokid must be specified when domain is local')

        return func(*args, **kwargs)
    return wrapper


class ApiProfileModel(BaseModel):
    """ Pydantic class handling validation for SDSS API profiles """
    domains: List[str]
    base: str
    mirrors: List[str] = None
    public: bool = False
    stems: Dict[str, str] = {'test': 'test', 'public': 'public', 'affix': 'prefix'}
    api: bool = False
    routemap: str = None

    @validator('domains', 'mirrors')
    def domains_in_list(cls, values):
        if not set(values).issubset(set(domains)):
            raise ValueError(f'Not all of the input domains/mirrors are in the list of domains.yml!')
        return values

    @validator('stems')
    def allowed_affixes(cls, values):
        if {'test', 'affix'} - set(values.keys()):
            raise ValueError('stems dictionary must contain at least "test" and "affix" keys!')

        if values['affix'] not in ['prefix', 'suffix']:
            raise ValueError('affix value can only be "prefix" or "suffix"!')
        return values


class ApiProfile(object):
    """ Class representing an API profile

    This class provides an interface for a given SDSS API profile.  It provides
    convenience methods for easily switching domain hosts for a given API, switching
    between production and development paths, and constructing full url route paths.
    It uses the `~urllib.parse.urlparse` URL scheme,
    "scheme://netloc/path;parameters?query#fragment".

    Parameters
    ----------
    name : str
        The name of the API profile
    domain : str, optional
        The name of the domain to use, by default None
    port : int, optional
        The port used for localhost domains, by default None
    ngrokid : int, optional
        The ngrok id used for localhost domains, by default None
    test: bool, optional
        If True, use the development url, by default None

    Raises
    ------
    ValueError
        when input name does not match a valid API profile
    """
    def __init__(self, name: str, domain: str = None, port: int = None, ngrokid: int = None,
                 release: str = None, test: bool = None) -> None:

        self.name = name
        # load and validate the name from the list of API profiles
        if name not in apis:
            raise ValueError(f'API Profile {name} not in the apis.yml file. Consider adding it.')
        else:
            self._validated_model = ApiProfileModel.parse_obj(apis[name])
            self.info = self._validated_model.dict()

        # load the domains and mirrors
        self.domains = self._get_domains()
        self.mirrors = self._get_domains(mirror=True)
        self._all_domains = {**self.domains} if not self.mirrors else {**self.domains, **self.mirrors}

        # select the current domain
        domain = next(iter(self.domains)) if not domain else domain
        self._select_current_domain(domain, port=port, ngrokid=ngrokid)

        # construct the API url
        self.url = self.construct_url(test=test)

    def __repr__(self) -> str:
        return f'<ApiProfile("{self.name}", current_domain="{self.current_domain}", url="{self.url}")>'

    def __str__(self) -> str:
        return self.name.lower()

    @check_domain
    def _select_current_domain(self, domain: str, port: int = None, ngrokid: int = None) -> None:
        if len(self._all_domains) == 1:
            warnings.warn(f'Only one domain available for API profile {self.name}. '
                          'Selecting that one.')
            self.current_domain = list(self._all_domains.values())[0]
            return

        if domain == 'local':
            self.current_domain = self._create_local_domain(port, ngrokid)
        else:
            self.current_domain = self._all_domains.get(domain, None)

    def _get_domains(self, mirror: bool = None) -> dict:
        # get the API profile domains ; add localhost automatically
        key = 'mirrors' if mirror else 'domains'
        profile_domains = self.info.get(key, None)
        if key == 'domains':
            profile_domains.append('local')

        if not mirror and not profile_domains:
            raise ValueError(f'Profile {self.name} has no "domains" entry set!')
        elif mirror and not profile_domains:
            return None
        return {i: domains[i].name for i in profile_domains}

    def construct_url(self, test: bool = None, public: bool = None) -> str:
        """ Constructs a new base url

        Constructs a new url given the currently set domain name and the API
        base name.  Can optionally specify a development base using the test or
        public keywords.

        Parameters
        ----------
        test : bool, optional
            If True, add the "test" stem for the development path, by default None
        public : bool, optional
            If True, adds the "public" stem for the deveopment path, by default None

        Returns
        -------
        str
            [description]
        """
        scheme = 'http' if 'local' in self.current_domain else 'https'
        netloc = self.current_domain
        path = self._create_base_stem(test, public)
        return urlunparse((scheme, netloc, path, '', '', ''))

    def construct_route(self, route: str) -> str:
        """ Construct a full url to an input route

        Constructs a full url path to the input route.

        Parameters
        ----------
        route : str
            The route component url path

        Returns
        -------
        str
            The full route url

        Example
        -------
        >>> p = ApiProfile('marvin')
        >>> p.url
        'https://sas.sdss.org/marvin/api'
        >>> p.construct_route('general/getroutemap')
        'https://sas.sdss.org/marvin/api/general/getroutemap'
        """
        return urljoin(self.url, route)

    def _create_local_domain(self, port: int, ngrokid: int) -> str:
        if ngrokid:
            domain = f'{ngrokid}.ngrok.io'
        else:
            domain = f'{self.domains["local"]}:{port}'
        return domain

    @check_domain
    def change_domain(self, domain: str, port: int = None, ngrokid: int = None) -> None:
        """ Change the url domain

        Updates the url "netloc" segment to use the domain name provided.  If the domain is
        "local", also needs either a port number or ngrok id to fully construct a local
        domain name.

        Parameters
        ----------
        domain : str
            The name of the domain to use
        port : int, optional
            The port used for localhost domains, by default None
        ngrokid : int, optional
            The ngrok id used for localhost domains, by default None

        Example
        -------
        >>> p = ApiProfile('marvin')
        >>> p.url
        'https://sas.sdss.org/marvin/api'
        >>> p.change_domains('dr15')
        >>> p.url
        'https://dr15.sdss.org/marvin/api'
        """
        parsed_url = urlparse(self.url)
        params = dict(zip(['scheme', 'netloc', 'path', 'params', 'query', 'fragment'],
                          tuple(parsed_url)))
        if domain == 'local':
            params['scheme'] = 'http'
            params['netloc'] = self._create_local_domain(port, ngrokid)
        else:
            params['netloc'] = self._all_domains[domain]
        self.url = urlunparse(params.values())

    def _create_base_stem(self, test: bool, public: bool) -> str:
        base = self.info['base']
        api = self.info.get('api', False)
        path = f'{base}'

        if test or public:
            stems = self.info.get('stems', None)
            affix = stems.get('affix', 'prefix')
            testfix = stems.get('test', 'test')
            publicfix = stems.get('public', 'public')
            if test:
                path = f'{testfix}/{path}' if affix == 'prefix' else f'{path}/{testfix}'
            if public:
                path = f'{publicfix}/{path}' if affix == 'prefix' else f'{path}/{publicfix}'

        if api:
            path = f'{path}/api'

        return path

    def change_path(self, test: bool = None, public: bool = None) -> None:
        """ Change the url path

        Updates the url "path" segment.  Called without arguments, with update the path
        to the production base.  If either "test" or "public" is set will update the path
        with the corresponding stems, used to switch to development urls.

        Parameters
        ----------
        test : bool, optional
            If True, add the "test" stem for the development path, by default None
        public : bool, optional
            If True, adds the "public" stem for the deveopment path, by default None

        Example
        -------
        >>> p = ApiProfile('marvin')
        >>> p.url
        'https://sas.sdss.org/marvin/api'
        >>> p.change_path(test=True)
        >>> p.url
        'https://sas.sdss.org/test/marvin/api'
        """
        path = self._create_base_stem(test, public)
        parsed_url = urlparse(self.url)
        params = dict(zip(['scheme', 'netloc', 'path', 'params', 'query', 'fragment'],
                          tuple(parsed_url)))
        params['path'] = path
        self.url = urlunparse(params.values())


class ApiManager(object):
    """ Class for managing SDSS APIs

    This class provides an interface for handling and managing the selection of various
    SDSS APIs.  It allows toggling of the current API to use for all remote
    requests.

    Attributes
    ----------
    domains : dict
        A dictionary of available SDSS domains
    apis : dict
        A dictionary of available SDSS APIs
    profile : Type[ApiProfile]
        The currently selected API to use
    """
    def __init__(self) -> None:
        self.domains = domains
        self.apis = {a: ApiProfile(a) for a in apis.keys()}
        self.profile = None

    def __repr__(self) -> str:
        return (f'<ApiManager(current_api="{str(self.profile)}", n_domains="{len(self.domains)}", '
                f'n_apis="{len(self.apis)}")>')

    def list_apis(self) -> list:
        """ List the available SDSS APIs

        Displays the complete list of available SDSS APIs.

        Returns
        -------
        list
            The list of available SDSS APIs
        """
        return list(self.apis.values())

    def list_domains(self) -> list:
        """ List the available SDSS domains

        Displays the complete list of available SDSS domain names.

        Returns
        -------
        list
            The list of available SDSS domains
        """
        return list(self.domains.values())

    def set_profile(self, name: str, domain: str = None, test: bool = None) -> None:
        """ Set the current API profile

        Sets the current API to the named profile

        Parameters
        ----------
        name : str
            The name of the API
        domain: str, optional
            The name of the domain to switch to, by default None
        test: bool, optional
            If True, sets the API profile to development, by default None
        """

        if name not in self.apis:
            raise ValueError(f'Input profile {name} not an available SDSS API.')

        self.profile = self.apis.get(name, None)

        if domain:
            self.profile.change_domain(domain)

        if test:
            self.profile.change_path(test=test)


apim = ApiManager()
