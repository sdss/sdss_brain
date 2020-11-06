# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: io.py
# Project: api
# Author: Brian Cherinka
# Created: Friday, 30th October 2020 1:22:42 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Friday, 30th October 2020 1:22:43 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import

import httpx
from sdss_brain.exceptions import BrainError


def send_post_request(url: str, data: dict = None) -> dict:
    """ A simple httpx post request

    A simple standalone httpx post request to a specified url, and
    given an optional data payload.

    Parameters
    ----------
    url : str
        The url to send the request to
    data : dict, optional
        Input data to send along with the request, by default None

    Returns
    -------
    dict
        Extracted response data from response.json()

    Raises
    ------
    BrainError
        when an error occurs sending the request
    """
    try:
        resp = httpx.post(url, data=data)
    except httpx.RequestError as exc:
        raise BrainError(f'An error occurred requesting {exc.request.url!r}') from exc
    else:
        resp.raise_for_status()
        data = resp.json()
    return data
