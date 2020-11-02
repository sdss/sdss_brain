# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: handler.py
# Project: api
# Author: Brian Cherinka
# Created: Friday, 30th October 2020 4:16:04 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Friday, 30th October 2020 4:16:04 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import

from typing import Type, Union
from sdss_brain.api.client import SDSSClient, SDSSAsyncClient
from sdss_brain.api.manager import apim, ApiProfile


api_type = Union[str, list, tuple, Type[ApiProfile]]


class ApiHandler(object):
    """ Convenience class for handling an API profile, and SDSS remote http client

    A convenience class to provide a simple API to the client for sending remote http requests
    using the ``SDSSClient``, with access to the underlying SDSS API profile.
    Accepts as input any string URL, API profile name or instance of ``ApiProfile``, as well as
    a tuple or list of valid "(api profile name, url route segment, optional domain name)", e.g.
    "('marvin', '/general/getroutemap').  Given valid input will attempt to determine, which URL,
    API profile, and SDSS remote client.

    Parameters
    ----------
    api_input : api_type, optional
        The type of API input, by default None
    async_client : bool, optional
        If True, instructs to use the `~sdss_brain.api.client.SDSSAsyncClient`, by default False

    Attributes
    ----------
    url : str
        The url or route segment
    api : `~sdss_brain.api.manager.ApiProfile`
        The SDSS API profile instance
    client: `~sdss_brain.api.client.SDSSClient`
        The client for sending http requests
    """

    def __init__(self, api_input: api_type = None, async_client=False):
        self.api = None
        self.url = None
        self.client = None
        self._kls = SDSSAsyncClient if async_client else SDSSClient

        self._determine_input(api_input)

    def __repr__(self) -> str:
        return f'<ApiHandler(api="{str(self.api)}", url="{self.url}")>'

    def _determine_input(self, value: api_type = None) -> None:
        """ Determine the type of API input

        Determine the type of API input.  Valid input can be either a valid
        URL string or API profile name, a tuple of (API profile name, route segment)
        or a valid SDSS ApiProfile instance.  Attempts to set the ``url``, ``api``, and
        ``client`` attributes.

        Parameters
        ----------
        value : api_type, optional
            The type of API input, by default None.
        """
        # if nothing, do nothing
        if not value:
            return

        if type(value) == str:
            self._check_url(value)
        elif isinstance(value, (list, tuple)):
            self._check_api(value)
        elif isinstance(value, ApiProfile):
            self._check_profile(value)

    def _check_url(self, value: str) -> None:
        """ Check a URL string or API name

        Check if the input string is a URL starting with http
        or the name of an available SDSS API profile.  If able, sets
        a valid URL, API, and SDSS remote client.

        Parameters
        ----------
        value : str
            the input URL string or API profile name
        """
        # check if the input is a URL starting with http
        if value.startswith('http'):
            self.url = value
            # extract the API and domain names and set the API accordingly
            api, domain = apim.identify_api_from_url(value)
            if api:
                self.api = apim.apis[api]
                if domain:
                    self.api.change_domain(domain)
        else:
            # set the API profile
            self.api = apim.apis.get(value, None)

        # set the SDSS client
        self.client = self._kls(self.url, use_api=self.api)
        if self.api and not self.client.api:
            self.client.set_api(self.api)

    def _check_api(self, value: Union[tuple, list]) -> None:
        """ Check the API/route tuple

        Check the input tuple or list for a valid API profile name and
        URL route.  Can optionally include a domain name as the third element in the list.
        Input syntax must be "(api name, URL route, domain name)".  If able, sets
        a valid API, the route segment as URL, and SDSS remote client.

        Parameters
        ----------
        value : Union[tuple, list]
            A valid API name and URL route segment.  Optionally include a domain name.

        Raises
        ------
        ValueError
            when the input list is not 2+ elements in length
        ValueError
            when the domain name is not in the available domain list
        """
        if len(value) < 2:
            raise ValueError('Input tuple/list must have at least two parts.')

        name, route, *extra = value
        self.api = apim.apis.get(name, None)
        if extra:
            domain = extra[0]
            if domain not in apim.domains:
                raise ValueError(f'Domain {domain} is not an available SDSS domain.')
            else:
                self.api.change_domain(domain)
        self.url = route
        self.client = self._kls(self.url, use_api=self.api)

    def _check_profile(self, value: Type[ApiProfile]) -> None:
        """ Check the API Profile

        Check the input API Profile, sets it as the api and
        sets the SDSS remote client.

        Parameters
        ----------
        value : Type[ApiProfile]
            A valid SDSS ApiProfile
        """
        self.api = value
        self.client = self._kls(use_api=self.api)

