# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: test_io.py
# Project: api
# Author: Brian Cherinka
# Created: Tuesday, 3rd November 2020 3:18:33 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Tuesday, 3rd November 2020 3:18:33 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import

import httpx
import pytest
from sdss_brain.api.io import send_post_request


def test_send_post_request():
    expdata = {'value': '555'}
    url = 'https://httpbin.org/post'
    data = send_post_request(url, data=expdata)
    assert data['form'] == expdata


def test_send_failure():
    with pytest.raises(httpx.HTTPStatusError, match='500 INTERNAL SERVER ERROR'):
        send_post_request('https://httpbin.org/status/500')
