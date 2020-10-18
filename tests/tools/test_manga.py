# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: test_manga.py
# Project: tools
# Author: Brian Cherinka
# Created: Thursday, 15th October 2020 5:07:11 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Thursday, 15th October 2020 5:07:11 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import
import pytest
from sdss_brain.tools.cubes import MangaCube
from .conftest import WorkTests, get_mocked
from tests.conftest import object_data


releases = object_data.get('cube').keys()


@pytest.fixture(scope='class', params=releases)
def release(request):
    yield request.param


@pytest.mark.use_test_data('cube', fake_missing=True)
class TestMangaWorkVerions(WorkTests):
    mock = get_mocked(MangaCube)
    version = 'drpver'


