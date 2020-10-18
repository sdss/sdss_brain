# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: test_apogee.py
# Project: tools
# Author: Brian Cherinka
# Created: Thursday, 15th October 2020 10:25:18 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Thursday, 15th October 2020 10:25:18 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import
import pytest
from sdss_brain.tools.spectra import ApStar, ApVisit, AspcapStar
from .conftest import WorkTests, get_mocked
from tests.conftest import object_data


releases = object_data.get('apstar').keys()


@pytest.fixture(scope='class', params=releases)
def release(request):
    yield request.param


@pytest.mark.use_test_data('apstar', fake_missing=True)
class TestApStarWorkVersions(WorkTests):
    mock = get_mocked(ApStar)
    version = 'apred'


@pytest.mark.use_test_data('apvisit', fake_missing=True)
class TestApVisitWorkVersions(WorkTests):
    mock = get_mocked(ApVisit)
    version = 'apred'


@pytest.mark.use_test_data('aspcap', fake_missing=True)
class TestAspcapStarWorkVersions(WorkTests):
    mock = get_mocked(AspcapStar)
    version = 'apred'
