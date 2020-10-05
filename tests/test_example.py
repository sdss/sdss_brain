# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: test_example.py
# Project: tests
# Author: Brian Cherinka
# Created: Monday, 16th March 2020 11:41:57 am
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Friday, 20th March 2020 4:03:12 pm
# Modified By: Brian Cherinka


from __future__ import absolute_import, division, print_function

import os
import re

import pytest
from astropy.io import fits
from sdssdb.sqlalchemy.mangadb import database

from sdss_brain.core import Brain
from sdss_brain.helpers import get_mapped_version, load_fits_file


class Cube(Brain):
    _db = database
    mapped_version = 'manga'
    path_name = 'mangacube'

    def _parse_input(self, value):
        plateifu_pattern = re.compile(r'([0-9]{4,5})-([0-9]{4,9})')
        plateifu_match = re.match(plateifu_pattern, value)
        if plateifu_match is not None:
            self.objectid = value
            self.plateifu = plateifu_match.group(0)
            self.plate, self.ifu = plateifu_match.groups(0)
        else:
            self.filename = value

    def _set_access_path_params(self):
        drpver = get_mapped_version(self.mapped_version, release=self.release, key='drpver')
        self.path_params = {'plate': self.plate, 'ifu': self.ifu, 'drpver': drpver, 'wave': 'LOG'}

    def _load_object_from_file(self, data=None):
        self.data = load_fits_file(self.filename)

    def _load_object_from_db(self, data=None):
        pass

    def _load_object_from_api(self, data=None):
        pass


def from_cube():
    ''' function to generate a new cube

    This function form, "from_xxxx", is needed to pass
    objects to the datasource marker.
    '''
    cube = Cube('8485-1901', release='DR16')
    return cube


@pytest.fixture(scope='module')
def cube():
    ''' create module level cube fixture '''
    cube = from_cube()
    yield cube
    cube = None


@pytest.fixture(scope='function')
def fxncube():
    ''' create function level cube fixture '''
    cube = from_cube()
    yield cube
    cube = None


class TestCube(object):
    release = 'DR15'

    @pytest.mark.parametrize('mode, db, origin',
                             [pytest.param('local', False, 'db',
                                           marks=pytest.mark.datasource(from_cube, db=True)),
                              pytest.param('local', True, 'file',
                                           marks=pytest.mark.datasource(from_cube, data=True)),
                              ('remote', False, 'api')])
    def test_cube_mma(self, mode, db, origin):
        ''' test the various mma modes for cube '''
        cube = Cube('8485-1901', mode=mode, ignore_db=db, release=self.release)
        assert cube.data_origin == origin
        assert cube.mode == mode

    @pytest.mark.parametrize('url', [(False), (True)], ids=['nourl', 'url'])
    def test_get_full_path(self, cube, url):
        ''' test to generate correct paths '''
        path = cube.get_full_path(url=url)
        assert '8485/stack/manga-8485-1901-LOGCUBE.fits.gz' in path
        if url:
            base = 'rsync' if cube.download is True else 'https'
            assert path.startswith(f'{base}://data.sdss.org')
        else:
            assert not path.startswith('https://data.sdss.org')

    @pytest.mark.datasource(from_cube, data=True)
    def test_load_from_file(self):
        ''' test to load data from local file '''
        cube = Cube('8485-1901', ignore_db=True, release='DR16')
        assert cube.data is not None
        assert isinstance(cube.data, fits.HDUList)

    @pytest.mark.remote_data
    def test_download_file(self, mock_sas, fxncube):
        ''' test for downloading a remote file

        sets a temporary SDSS sas (sas_base_dir) and downloads into a clean
        directory
        '''
        assert not os.path.exists(fxncube.get_full_path())
        assert fxncube.data is None
        cube = Cube('8485-1901', ignore_db=True, release='DR16', download=True)
        assert cube.data is not None
        assert isinstance(cube.data, fits.HDUList)


def test_bad_brain():
    ''' test that abstract class can't be instantiated '''
    with pytest.raises(TypeError) as cm:
        Brain('A')
    assert "Can't instantiate abstract class Brain with abstract methods" in str(cm.value)
