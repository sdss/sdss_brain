# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: client.py
# Project: api
# Author: Brian Cherinka
# Created: Friday, 23rd October 2020 3:08:00 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Friday, 23rd October 2020 3:08:00 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import
import httpx
import re
import warnings
from io import BytesIO
from typing import Union, Type
from sdss_brain import log
from sdss_brain.auth import User
from sdss_brain.api.manager import ApiManager, ApiProfile
from sdss_brain.config import config
from sdss_brain.exceptions import BrainError

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None


apim = ApiManager()


class BaseClient(object):
    """ Base class for creating a client for sending http requests

    This class provides a client for submitting http requests using
    `httpx <https://www.python-httpx.org/>`_.  It provides support for SDSS user
    validation and profile switching between different SDSS APIs.  It provides a
    basic synchronous client, ``SDSSClient``, using
    `httpx Client <https://www.python-httpx.org/advanced/#usage>`_ and asynchronous
    client, ``SDSSAsyncClient``, using `httpx AsyncClient <https://www.python-httpx.org/async/>`_.

    Parameters
    ----------
    route : str, optional
        A full url or route segment, by default None
    user : Union[str, Type[User]], optional
        The name of a valid SDSS user, by default None
    use_api : Union[str, Type[ApiProfile]], optional
        The name of a valid SDSS API profile, by default None
    test : bool, optional
        If True, uses the development API, by default None
    domain : str, optional
        The name of the domain to use for the given API, by default None
    headers : dict, optional
        Any httpx request headers to attach to the client, by default None
    no_progress : bool, optional
        If True, turns off the tqdm progress bar for streaming responses, by default None
    release : str, optional
        The data release to use for the request

    Attributes
    ----------
    user : `~sdss_brain.auth.user.User`
        an SDSS User instance
    api : `~sdss_brain.api.manager.ApiProfile`
        an SDSS API Profile instance
    url: str
        The request url
    client : Union[`httpx.Client`, `httpx.AsyncClient`]
        The underling httpx request client
    response: `httpx.Response`
        The underlying httpx response instance
    data: Union[dict, str, bytes]
        The extracted response content
    """
    _kls: Union[Type[httpx.Client], Type[httpx.AsyncClient]] = None

    def __init__(self, route: str = None, user: Union[str, Type[User]] = None,
                 use_api: Union[str, Type[ApiProfile]] = None, test: bool = None,
                 domain: str = None, headers: dict = None, no_progress: bool = None,
                 release: str = None, **kwargs):
        self.user = None
        self.api = None
        self.url = None
        self.response = None
        self.data = None
        self.no_progress = no_progress
        self.release = release or config.release

        # set the user
        self.set_user(user)

        # set the api when no route or partial route is provided; otherwise use the full url.
        if not route or (route and not route.startswith('http')):
            self.set_api(use_api, domain=domain, test=test)

        # set the URL
        self.set_url(route)

        # set the httpx.Client or httpx.AsyncClient
        self.client = self._kls(headers=headers, **kwargs)  # pylint: disable=not-callable

    def __repr__(self) -> str:
        client = self._kls.__name__
        return (f'<SDSS{client}(api="{str(self.api)}", user="{str(self.user)}")>')

    def set_user(self, user: Union[str, Type[User]]) -> None:
        """ Set the user for the http client

        Sets the SDSS user to use for all remote http requests.

        Parameters
        ----------
        user : Union[str, Type[User]]
            An SDSS username or `~sdss_brain.auth.user.User`

        Raises
        ------
        BrainError
            when the user is not validated
        """
        self.user = User(user) if type(user) == str else user if isinstance(user, User) \
            else config.user
        if not self.user.validated:
            warnings.warn(f"User {user} is not a validated user. Some requests may not work.")

    def set_api(self, use_api: Union[str, Type[ApiProfile]], domain: str = None,
                test: bool = None) -> None:
        """ Set the API profile to use in the http client

        Sets the API profile to use for all remote http requests.

        Parameters
        ----------
        use_api : Union[str, Type[ApiProfile]]
            A API name or `~sdss_brain.api.manager.ApiProfile`
        domain : str, optional
            The domain name to use for the API, by default None
        test : bool, optional
            If True, toggles the development API, by default None

        Raises
        ------
        BrainError
            when no API profile is set
        """
        api = use_api or config.apis.profile
        if isinstance(api, ApiProfile):
            self.api = api
        elif type(api) == str:
            apim.set_profile(api, test=test, domain=domain)
            self.api = apim.profile
        else:
            self.api = None

        if not self.api:
            raise BrainError('No API is set. Set one either by specifying "use_api" on input or '
                             'setting one on the global config.')

    def set_url(self, route: str) -> None:
        """ Sets the url route to use on the http client

        Sets the url to use in the http client for remote requests.  When the input route
        is a full url starting with "http", uses the url as specified.  When the input
        route is a segment, will construct a full url using the base url of the preset SDSS
        API profile.

        Parameters
        ----------
        route : str
            A url or route segment

        Raises
        ------
        BrainError
            when no API profile is set
        """
        if not route:
            return
        elif route.startswith('http'):
            self.url = route
            log.debug(f'Using fully qualified url {route}.')
        else:
            if not self.api:
                raise BrainError(f'No API is set.  Cannot construct a full url for {route}')
            self.url = self.api.construct_route(route)
            log.debug(f'Building url from input route {route} and selected API {self.api}.')

    def _validate_request(self, url: str, method: str) -> None:
        """ Validates some inputs to the request wrapper

        Validates the wrapper request method for a proper url and input
        method type.

        Parameters
        ----------
        url : str
            The request url
        method : str
            The type of http request

        Raises
        ------
        ValueError
            when an invalid method is passed
        ValueError
            when no url is set
        """
        if url:
            self.set_url(url)

        if method not in ['get', 'post', 'stream', 'head']:
            raise ValueError('http request method type can only be "get", "post", '
                             '"head", or "stream".')

        if not self.url:
            raise ValueError('No url set.  Cannot make a request. Please specify a '
                             'url or route segment.')

        # look for any bracketed named arguments in the url
        parts = re.findall(r'{(.*?)}', self.url)
        if parts:
            raise BrainError(f'Request url contains bracket arguments: "{", ".join(parts)}". '
                             'Cannot send request until these are properly replaced.')

    def prepare_data(self, data: dict = None):
        """ Add the SDSS release to input request data

        Automatically adds the client SDSS data release to the input request data
        for cases where the API web server needs it.

        Parameters
        ----------
        data : dict, optional
            any input request data, by default None

        Returns
        -------
        dict
            The request data with release added

        Raises
        ------
        TypeError
            when the input data is not a dict
        """

        # set the release dict and return it when no input data
        release = {'release': self.release}
        if not data:
            return release

        # otherwise check the data type
        if type(data) != dict:
            raise TypeError('input request data is not of type dict')

        # add the release to the request data
        if data and 'release' not in data:
            data.update(release)
        return data

    def _check_response(self, resp: Type[httpx.Response]) -> None:
        """ Checks the returned httpx response

        Checks the httpx response, raises exception for any problem status code,
        and attempts to extract the response content.

        Parameters
        ----------
        resp : Type[httpx.Response]
            The returned httpx response instance

        Raises
        ------
        BrainError
            when the response is not ok
        """
        resp.raise_for_status()
        if resp.is_error:
            raise BrainError('There was an error in the response!')

        self.response = resp
        self._return_data()

    def _return_data(self) -> None:
        """ Extracts the data from a httpx response

        Extracts the relevant httpx response content based on the "content-type"
        from the response header, and sets the data attribute.

        """
        encoding = self.response.headers.get('content-encoding')
        contentype = self.response.headers.get('content-type')

        if 'json' in contentype:
            self.data = self.response.json()
        elif 'text' in contentype:
            self.data = self.response.text
        elif 'octet-stream' in contentype and self.data is None:
            self.data = self.response.content
        else:
            self.data = self.data

    def _create_token_auth_header(self) -> dict:
        """ Create a new request authorization header

        Creates a new http request header containing valid
        Bearer token authorization.

        Returns
        -------
        dict
            A new http request header to be added to the outgoing request

        Raises
        ------
        BrainError
            when no API profile has been set
        ValueError
            when a token cannot be retrieved
        """
        if not self.api:
            raise BrainError("No API profile set. Cannot created token auth header.")

        if self.api.auth_type != 'token':
            return {}

        token = self.api.token
        if not token:
            log.info('No token found.  Attempting to retreive one.')
            token = self.get_token()
            if not token:
                raise ValueError(f'No token retrieved for API {self.api.name}.  Check for a valid '
                                 'user, try self.get_token again, and save your token!')
            else:
                log.info("This token is temporary.  To permanently set one, run self.api.get_token "
                         "and save it in your config file or as an environment variable.")

        return {'Authorization': f'Bearer {token}'}

    def get_token(self) -> str:
        """ Get an API auth token for the specified API

        Retrieves an API auth token for the given API profile, if
        the auth_type for this API is set to "token".  For APIs that only
        use "netrc" authentication, this method is unnecessary.

        Returns
        -------
        str
            A valid API auth token

        Raises
        ------
        ValueError
            when no user is set
        ValueError
            when no API profile is set
        ValueError
            when the user is not properly validated
        """
        if not self.user:
            raise ValueError("No user specified.")

        if not self.api:
            raise ValueError("No API profile specified.")

        if not self.user.validated and not self.user.is_netrc_valid:
            raise ValueError(f'User {self.user} is not properly validated with netrc.  '
                             'Cannot get a token.  Check self.user for proper netrc validation.')

        return self.api.get_token(self.user)


class SDSSClient(BaseClient):
    """ Helper class for sending http requests using httpx.Client"""
    _kls: Type[httpx.Client] = httpx.Client

    def __del__(self):
        if hasattr(self, 'client'):
            self.client.close()

    def __enter__(self):
        ''' Constructor for client use as context manager '''
        return self

    def __exit__(self, type, value, traceback):
        ''' Destructor for client use as context manager '''
        self.client.close()
        return True

    def request(self, url: str = None, data: dict = None, method: str = 'get', files: dict = None,
                content: bytes = None, **kwargs) -> None:
        """ Submit a http request with httpx

        This is a convenience method that wraps `httpx.Client.request`.  It provides support for
        simple "get", "post", or "stream" requests.  For more custom, or complete, control over
        sending requests, use the `client` attribute, and see
        `httpx Client <https://www.python-httpx.org/advanced/#usage>`_ and
        `httpx docs <https://www.python-httpx.org/quickstart/>`_. for more.

        Parameters
        ----------
        url : str, optional
            A url or route segment to send a request to, by default None
        data : dict, optional
            Any data passed along in the request, by default None
        method : str, optional
            The type of http request method, by default 'get'
        files : dict, optional
            Input for multi-part file uploads, by default None
        content : bytes, optional
            Input for binary content, by default None
        kwargs : Any, optional
            Any other httpx request keyword arguments

        Raises
        ------
        BrainError
            when there is an error sending the request
        """

        # validate the input
        self._validate_request(url, method)

        # add any token auth to headers
        headers = None
        if self.api and self.api.auth_type == 'token':
            headers = self._create_token_auth_header()

        # prepare the data with the release
        data = self.prepare_data(data)

        try:
            # try to send the request
            if method == 'stream':
                resp = self._stream_request()
            else:
                params, data, json = (data, None, None) if method == 'get' else (None, data, data)
                resp = self.client.request(method, self.url, params=params, data=data, json=json,
                                           files=files, content=content, headers=headers, **kwargs)

        except httpx.RequestError as exc:
            raise BrainError(f'An error occurred requesting {exc.request.url!r}') from exc
        else:
            # check the response and set the data attribute
            self._check_response(resp)

    def _stream_request(self) -> Type[httpx.Response]:
        """ Stream a httpx response

        Streams response binary content, using ``iter_bytes`` into a
        BytesIO stream object.  For other types of streaming,
        see `<https://www.python-httpx.org/quickstart/#streaming-responses>`_ and use
        the `client` attribute directly.  If ``tqdm`` is installed will display a progress
        bar while streaming content.

        Returns
        -------
        httpx.Response
            The httpx response instance
        """
        # create a BytesIO object
        b = BytesIO()
        with self.client.stream("GET", self.url) as resp:
            # check the status
            resp.raise_for_status()
            # get the content-length
            total = int(resp.headers.get("Content-Length", 0))
            if not tqdm or self.no_progress or total == 0:
                # stream bytes data without progress bar
                for data in resp.iter_bytes():
                    b.write(data)
            else:
                # stream bytes data with progress bar
                with tqdm(total=total, unit_scale=True, unit_divisor=1024, unit="B") as progress:
                    num_bytes_downloaded = resp.num_bytes_downloaded
                    for data in resp.iter_bytes():
                        b.write(data)
                        progress.update(resp.num_bytes_downloaded - num_bytes_downloaded)
                        num_bytes_downloaded = resp.num_bytes_downloaded
            b.seek(0)

        self.data = b
        return resp


class SDSSAsyncClient(BaseClient):
    """ Helper class for sending asynchronous http requests using httpx.AsyncClient"""
    _kls: Type[httpx.AsyncClient] = httpx.AsyncClient

    async def __aenter__(self):
        ''' Constructor for client use as context manager '''
        return self

    async def __aexit__(self, type, value, traceback):
        ''' Destructor for client use as context manager '''
        await self.client.aclose()
        return True

    async def request(self, url: str = None, data: dict = None, method: str = 'get', files: dict = None,
                      content: bytes = None, **kwargs):
        """ Submit a http request with httpx

        This is a convenience method that wraps `httpx.AsyncClient.request`.  It provides support
        for simple "get", "post", or "stream" requests.  For more custom, or complete, control over
        sending requests, use the `client` attribute, and see
        `httpx AsyncClient <https://www.python-httpx.org/async/>`_ and
        `httpx docs <https://www.python-httpx.org/quickstart/>`_. for more.

        Parameters
        ----------
        url : str, optional
            A url or route segment to send a request to, by default None
        data : dict, optional
            Any data passed along in the request, by default None
        method : str, optional
            The type of http request method, by default 'get'
        files : dict, optional
            Input for multi-part file uploads, by default None
        content : bytes, optional
            Input for binary content, by default None
        kwargs : Any, optional
            Any other httpx request keyword arguments

        Raises
        ------
        BrainError
            when there is an error sending the request
        """
        # validate the input
        self._validate_request(url, method)

        # add any token auth to headers
        headers = None
        if self.api and self.api.auth_type == 'token':
            headers = self._create_token_auth_header()

        # prepare the data with the release
        data = self.prepare_data(data)

        try:
            # try to send the request
            if method == 'stream':
                resp = await self._stream_request()
            else:
                params, data, json = (data, None, None) if method == 'get' else (None, data, data)
                resp = await self.client.request(method, self.url, params=params, data=data,
                                                 json=json, files=files, content=content,
                                                 headers=headers, **kwargs)
        except httpx.RequestError as exc:
            raise BrainError(f'An error occurred requesting {exc.request.url!r}') from exc
        else:
            # check the response and set the data attribute
            self._check_response(resp)
        finally:
            await self.client.aclose()

    async def _stream_request(self) -> Type[httpx.Response]:
        """ Stream a httpx response

        Streams response binary content, using ``iter_bytes`` into a
        BytesIO stream object.  For other types of streaming,
        see `<https://www.python-httpx.org/quickstart/#streaming-responses>`_ and use
        the `client` attribute directly.  If ``tqdm`` is installed will display a progress
        bar while streaming content.

        Returns
        -------
        httpx.Response
            The httpx response instance
        """
        # create a BytesIO object
        b = BytesIO()
        async with self.client.stream("GET", self.url) as resp:
            # check the status
            resp.raise_for_status()
            # get the content-length
            total = int(resp.headers.get("Content-Length", 0))
            if not tqdm or self.no_progress or total == 0:
                # stream bytes data without progress bar
                async for data in resp.aiter_bytes():
                    b.write(data)
            else:
                # stream bytes data with progress bar
                with tqdm(total=total, unit_scale=True, unit_divisor=1024, unit="B") as progress:
                    num_bytes_downloaded = resp.num_bytes_downloaded
                    async for data in resp.aiter_bytes():
                        b.write(data)
                        progress.update(resp.num_bytes_downloaded - num_bytes_downloaded)
                        num_bytes_downloaded = resp.num_bytes_downloaded
            b.seek(0)

        self.data = b
        return resp

