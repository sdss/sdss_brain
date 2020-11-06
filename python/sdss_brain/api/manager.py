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

import os
import pathlib
import warnings
import yaml
from astropy.table import Table
from functools import wraps
from pydantic import BaseModel, validator, parse_obj_as
from typing import List, Dict
from urllib.parse import urlparse, urlunparse
from sdss_brain import log, cfg_params
from sdss_brain.auth import User
from sdss_brain.api.io import send_post_request
from sdss_brain.exceptions import BrainError

try:
    from tabulate import tabulate
except ImportError:
    tabulate = None


__all__ = ['Domain', 'ApiProfileModel', 'ApiProfile', 'ApiManager', 'apim']


def urljoin(url1: str, url2: str) -> str:
    """ Custom function to join two url paths

    Uses `~urllib.parse.urlparse` and `~urllib.parse.urlunparse`
    to join relevant segments of two urls.  Does not use `~urllib.parse.urljoin`
    as that replaces existing url path with a new path.

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
        # use os.path instead of pathlib since it does not trim trailing slashes
        f = os.path.join(str1, str2.lstrip('/')) if str2 else str1
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
    description: str = None

    @validator('name')
    def check_domain_name(cls, value):
        if value != 'localhost' and not value.endswith('sdss.org') and not value.endswith('sdss.utah.edu'):
            raise ValueError(f'Domain name {value} does not fit format of "xxx.sdss.org" or "xxx.sdss.utah.edu"')

        return value

    def __str__(self):
        return str(self.name)

    def __eq__(self, value):
        if type(value) is str:
            return value == self.name
        elif isinstance(value, Domain):
            return value is self


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
    stems: Dict[str, str] = {'test': 'test', 'public': 'public', 'affix': 'prefix'}
    api: bool = False
    routemap: str = None
    auth: Dict[str, str] = {'type': 'netrc', 'route': None}
    description: str = ''
    docs: str = None

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

    Attributes
    ----------
        description : str
            A description of the API
        documentation : str
            A url link to any documentation of the API
        auth_type : str
            The type of authentication needed for the API
        domains : dict
            The available domains this API can be accessed on
        mirrors : dict
            The available domains acting as mirrors
        url : str
            The current constructed base API url
        current_domain : str
            The current domain the API it set to use
        name : str
            The name of the API profile
        token: str
            The authenticated token, if any
        info : dict
            A dictionary of information extracted from Pydantic datamodel

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

        self.description = self.info.get('description', '')
        self.documentation = self.info.get('docs', '')

        # load the domains and mirrors
        self.domains = self._get_domains()
        self.mirrors = self._get_domains(mirror=True)
        self._all_domains = {**self.domains} if not self.mirrors else {**self.domains, **self.mirrors}

        # select the current domain
        domain = next(iter(self.domains)) if not domain else domain
        self._select_current_domain(domain, port=port, ngrokid=ngrokid)

        # construct the API url
        self.url = self.construct_url(test=test)

        # set auth type
        self._set_auth_type()

    def __repr__(self) -> str:
        return f'<ApiProfile("{self.name}", current_domain="{self.current_domain}", url="{self.url}")>'

    def __str__(self) -> str:
        return self.name.lower()

    def _set_auth_type(self) -> None:
        """ Sets the API authentication type """
        if self.is_domain_public is True or 'local' in str(self.current_domain):
            self.auth_type = None
        else:
            self.auth_type = self.info['auth'].get('type', 'netrc')

    @property
    def token(self) -> str:
        """ Returns an authentication token """
        return self.check_for_token()

    def check_for_token(self) -> str:
        """ Checks for a proper auth token set as a envvar or in custom config """
        token = f'{self.name.upper()}_API_TOKEN'
        return os.getenv(token) or cfg_params.get(token.lower(), None)

    def construct_token_url(self) -> str:
        """ Construct a login url for requesting tokens """
        # check the API auth_type
        auth = self.info.get('auth', None)
        if auth['type'] != 'token':
            log.info(f'Auth type for API {self.name} is not "token".  No token needed.')
            return

        # get the token route for the given API
        token_route = auth.get('route', None)
        if not token_route:
            raise ValueError(f'No token route specified for API profile {self.name}. '
                             'I do not where to request a token from.')

        return self.construct_route(token_route)

    def get_token(self, user: str) -> str:
        """ Request and receive a valid API auth token

        Requests an auth token for the specified user.  This uses found netrc
        authentication to attempt to request and retrieve a valid token.  The
        token should be saved in an "XXX_API_TOKEN" environment variable or in
        the custom sdss_brain.yml configuration file as "xxx_api_token", where
        "XXX" is the API profile name.

        Parameters
        ----------
        user : str
            The name of the SDSS user

        Returns
        -------
        str
            A valid API auth token

        Raises
        ------
        BrainError
            when the user is not netrc validated
        BrainError
            when a token cannot be extracted from the http response
        """
        if self.token:
            return self.token

        auth = self.info.get('auth', None)
        if auth['type'] != 'token':
            log.info(f'Auth type for API {self.name} is not "token".  No token needed.')
            return

        if type(user) == str:
            user = User(user)
        if not user.validated and not user.is_netrc_valid:
            raise BrainError(f'User {user.name} is not netrc validated!  Cannot access credentials.')

        username, password = user.netrc.read_netrc('api.sdss.org')
        token_url = self.construct_token_url()
        data = send_post_request(token_url, data={'username': username, 'password': password})
        token = data.get('token',
                         data.get('access_token',
                                  data.get('user_token',
                                           data.get('sdss_token', None))))
        if not token:
            raise BrainError('Token request successful but could not extract token '
                             'from response data. Check the returned json response '
                             'for prope key name')
        else:
            tok_name = f'{self.name.upper()}_API_TOKEN'
            log.info(f'Save this token as either a "{tok_name}" environment variable in your '
                     f'.bashrc or as "{tok_name.lower()}" in your custom sdss_brain.yml config file.')
            return token

    @property
    def is_domain_public(self) -> bool:
        """ Checks if current domain is a public one """
        return self.current_domain.public

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
        """ Get the subset of domains valid for the given API

        Set the domains subsets for the specific API.  Sets the
        ``domains`` attribute and the ``mirrors`` attribute.

        Parameters
        ----------
        mirror : bool, optional
            If True, looks for and sets any mirror domains, by default None

        Returns
        -------
        dict
            The set of valid domains for the given API

        Raises
        ------
        ValueError
            when the API profile has no domains entry set
        """
        # get the API profile domains ; add localhost automatically
        key = 'mirrors' if mirror else 'domains'
        profile_domains = self.info.get(key, None)
        if key == 'domains':
            profile_domains.append('local')

        if not mirror and not profile_domains:
            raise ValueError(f'Profile {self.name} has no "domains" entry set!')
        elif mirror and not profile_domains:
            return None
        return {i: domains[i] for i in profile_domains}

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
        netloc = self.current_domain.name
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
        """ Create a local domain name """
        if ngrokid:
            domain = f'{ngrokid}.ngrok.io'
        else:
            domain = f'{self.domains["local"].name}:{port}'
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
            params['scheme'] = 'https'
            params['netloc'] = self._all_domains[domain].name
        self.url = urlunparse(params.values())

        # reset current domain and auth_type
        self.current_domain = self._all_domains[domain]
        self._set_auth_type()

    def _create_base_stem(self, test: bool, public: bool) -> str:
        """ Create a new path stem """
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

    def identify_api_from_url(self, url: str) -> tuple:
        """ Identify and extract an API and domain type from a URL.

        Identifies the type of API and domain name the input URL
        is using.  Loops over all available API and domain profiles in the
        ApiManager checks against extracted url parts from `~urllib.parse.urlparse`.

        Parameters
        ----------
        url : str
            The full url string

        Returns
        -------
        tuple
            The identified API profile and domain name

        Raises
        ------
        ValueError
            when the url does not start with http
        """
        if not url.startswith('http'):
            raise ValueError('Input url does not start with http.')

        api = domain = None
        # extract url parts
        parts = urlparse(url)
        # identify the API
        for v in self.apis.values():
            if v.info['base'] in parts.path:
                api = v.name

        # identify the domain
        for k, d in self.domains.items():
            if d.name == parts.netloc:
                domain = k

        return api, domain

    def display(self, value: str, pprint: bool = False, show_docs: bool = True,
                show_desc: bool = True, **kwargs) -> Table:
        """ Display the APIs or domains as an Astropy Table

        Display the list of available SDSS APIs or domains as an
        Astropy Table.

        Parameters
        ----------
        value : str
            Either "api(s)" or "domain(s)"
        pprint : bool, optional
            If True, pretty print the Astropy Table, by default False
        show_docs : bool, optional
            If True, include the "docs" column in the API table, by default True
        show_desc : bool, optional
            If True, include the "description" column in the API table, by default True
        kwargs: Any
            Other kwargs for Table.pprint (pretty print) method

        Returns
        -------
        `~astropy.table.Table`
            An Astropy Table of information

        Raises
        ------
        TypeError
            when the input value is not a string
        ValueError
            when the input value is not either "apis" or "domains"
        """
        if type(value) != str:
            raise TypeError('Value can only be a string')

        value = value.lower()
        if value not in ['apis', 'api', 'domains', 'domain']:
            raise ValueError('Value can only be "apis" or "domains"!')

        rows = []
        cols = []
        if 'domain' in value:
            # create display columns
            cols = ['key', 'name', 'public', 'description']

            # create table rows
            for k, v in self.domains.items():
                row = v.dict()
                row['key'] = k
                rows.append(row)
        elif 'api' in value:
            # create display columns
            cols = ['key', 'base', 'description', 'domains', 'mirrors', 'auth', 'docs']
            if not show_docs:
                cols.remove('docs')
            if not show_desc:
                cols.remove('description')

            # create table rows
            for k, v in self.apis.items():
                row = {kk: vv for kk, vv in v.info.items() if kk in cols}
                row['domains'] = ', '.join(row['domains'])
                row['mirrors'] = ', '.join(row['mirrors']) if row['mirrors'] else ''
                row['auth'] = row['auth']['type']
                row['key'] = k
                rows.append(row)

        table = Table(rows, names=cols)

        if pprint:
            table.pprint(**kwargs)
            return

        return table

    def generate_rst_table(self, value: str, show_docs: bool = True,
                           show_desc: bool = True, **kwargs) -> str:
        """ Generate a rst-formatted table

        Generates an rst-formatted table of the available domains or APIs
        using the `tabulate <https://github.com/astanin/python-tabulate>`_
        python package.  This method is good for dropping tables into Sphinx
        documentation.

        Parameters
        ----------
        value : str
            Either "api(s)" or "domain(s)"
        show_docs : bool, optional
            If True, include the "docs" column in the API table, by default True
        show_desc : bool, optional
            If True, include the "description" column in the API table, by default True
        kwargs: Any
            Other kwargs for the tabulate method

        Returns
        -------
        str
            The rst formatted table as a string

        Raises
        ------
        ImportError
            when the tabulate package is not installed.
        """
        if not tabulate:
            raise ImportError('package tabulate not found.  Cannot generate rst table.')

        # create the table as a numpy array of data
        table = self.display(value, show_docs=show_docs, show_desc=show_desc).as_array()

        # convert the table into an rst table using tabulate
        rst = tabulate(table, headers='keys', tablefmt='rst', disable_numparse=True, **kwargs)

        return rst


apim = ApiManager()
