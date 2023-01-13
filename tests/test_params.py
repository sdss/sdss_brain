# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: test_params.py
# Project: tests
# Author: Brian Cherinka
# Created: Sunday, 11th October 2020 11:52:28 am
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Sunday, 11th October 2020 11:52:29 am
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import
import os
import re

import pytest
from tests.conftest import get_path

from astropy.io import fits

from sdss_brain.core import Brain, BrainNoAccess
from sdss_brain.helpers import parse_data_input, parser_loader
from sdss_brain.datamodel import get_mapped_version


#
# These tests for proper parameter extraction and instance attribute application
# for different definitions of the _parse_input method
#

cube_file = '/Users/Brian/Work/sdss/sas/dr15/manga/spectro/redux/v2_4_3/8485/stack/manga-8485-1901-LOGCUBE.fits.gz'
params = {'plate': '8485', 'ifu': '1901', 'wave': 'LOG', 'drpver': 'v2_4_3'}


class BaseCube(Brain):
    path_name = 'mangacube'

    def _set_access_path_params(self):
        drpver = get_mapped_version('drpver', release=self.release)
        self.path_params = {'plate': self.plate, 'ifu': self.ifu, 'drpver': drpver, 'wave': 'LOG'}

    def _load_object_from_file(self):
        pass

    def _load_object_from_db(self):
        pass

    def _load_object_from_api(self):
        pass


class BaseCubeNoAccess(BrainNoAccess):
    def _load_object_from_file(self):
        pass

    def _load_object_from_db(self):
        pass

    def _load_object_from_api(self):
        pass

    def download(self):
        pass

    def get_full_path(self):
        return self.filename


def manual_unnamed(self, value):
    pattern = re.compile(r'(\d{4,5})-(\d{3,5})')
    match = re.match(pattern, value)
    data = dict.fromkeys(['filename', 'objectid'])
    if match is not None:
        data['objectid'] = value
        self.plateifu = match.group(0)
        self.plate, self.ifu = match.groups(0)
    else:
        data['filename'] = value
    return data


def manual_named(self, value):
    pattern = re.compile(r'(?P<plate>\d{4,5})-(?P<ifu>\d{3,5})')
    match = re.match(pattern, value)
    data = dict.fromkeys(['filename', 'objectid'])
    if match is not None:
        dd = match.groupdict()
        data['objectid'] = value
        self.plate, self.ifu = dd['plate'], dd['ifu']
    else:
        data['filename'] = value
    return data


def parse_data_pattern_explicit_add(self, value):
    pattern = re.compile(r'(?P<plate>\d{4,5})-(?P<ifu>\d{3,5})')
    data = parse_data_input(value, regex=pattern)
    self.plate = data['plate']
    self.ifu = data['ifu']
    return data


def parse_data_pattern(self, value):
    pattern = re.compile(r'(?P<plate>\d{4,5})-(?P<ifu>\d{3,5})')
    data = parse_data_input(value, regex=pattern)
    return data


def parse_data_keys(self, value):
    keys = self.access.lookup_keys(self.path_name)
    data = parse_data_input(value, keys=keys, order=['plate', 'ifu'])
    return data


def parse_file(self, value):
    data = dict.fromkeys(['filename', 'objectid'])
    data['filename'] = value
    return data


def create_cube(name, noaccess=None, path=None):
    if noaccess:
        Cube = type("Cube", (BaseCubeNoAccess,), {})
    else:
        Cube = type("Cube", (BaseCube,), {})

    if name == 'manual_unnamed':
        Cube._parse_input = manual_unnamed
    elif name == 'manual_named':
        Cube._parse_input = manual_named
    elif name == 'parse_explicit':
        Cube._parse_input = parse_data_pattern_explicit_add
    elif name == 'parse_pattern':
        Cube._parse_input = parse_data_pattern
    elif name == 'parse_keys':
        Cube._parse_input = parse_data_keys
    elif name == 'parse_file':
        Cube._parse_input = parse_file
    elif name == 'by_file':
        Cube._parse_input = parse_file
    elif name == 'loader':
        Cube = parser_loader(kls=Cube, order=['plate', 'ifu'])
        return Cube('8485-1901', release='DR15')
    elif name == 'loader_pattern':
        Cube = parser_loader(kls=Cube, pattern=r'(?P<plate>\d{4,5})-(?P<ifu>\d{3,5})')
        return Cube('8485-1901', release='DR15')

    Cube.__abstractmethods__ = Cube.__abstractmethods__.symmetric_difference({'_parse_input'})
    if name == 'parse_file':
        return Cube(path, release='DR15')
    elif name == 'by_file':
        return Cube(filename=path, release='DR15')
    else:
        return Cube('8485-1901', release='DR15')


def asserts(cube):
    assert hasattr(cube, 'plate') and cube.plate == params['plate']
    assert hasattr(cube, 'ifu') and cube.ifu == params['ifu']
    assert hasattr(cube, 'wave') and cube.wave == params['wave']
    assert hasattr(cube, 'drpver') and cube.drpver == params['drpver']
    assert hasattr(cube, 'path_params') and cube.path_params == params
    assert getattr(cube, 'drpver') == cube.path_params['drpver']


@pytest.mark.parametrize('name',
                         [('manual_unnamed'), ('manual_named'), ('parse_explicit'),
                          ('parse_pattern'), ('parse_keys'),
                          pytest.param('parse_file',
                                       marks=pytest.mark.datasource(
                                           get_path('cube'), data=True)),
                          pytest.param('by_file',
                                       marks=pytest.mark.datasource(
                                           get_path('cube'), data=True)),
                          ('loader'), ('loader_pattern')])
@pytest.mark.parametrize('make_path', ['cube'], indirect=True)
def test_correct_set_params(make_path, name):
    cube = create_cube(name, path=make_path)
    asserts(cube)

