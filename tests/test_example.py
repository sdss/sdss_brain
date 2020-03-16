# !/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Filename: test_example.py
# Project: tests
# Author: Brian Cherinka
# Created: Monday, 16th March 2020 11:41:57 am
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Monday, 16th March 2020 1:33:21 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import
import pytest
from sdss_brain.core import Brain
from sdssdb.sqlalchemy.mangadb import database
from sdss_brain.helpers import get_mapped_version


class Cube(Brain):
    _db = database
    mapped_version = 'manga'

    def _parse_input(self, value):
        self.plateifu = value
        self.plate, self.ifu = value.split('-')
        return {'objectid': value}

    def _set_access_path_params(self):
        self.path_name = 'mangacube'
        drpver = get_mapped_version(self.mapped_version, release=self.release, key='drpver')
        self.path_params = {'plate': self.plate, 'ifu': self.ifu, 'drpver': drpver}

    def _load_object_from_file(self, data=None):
        pass

    def _load_object_from_db(self, data=None):
        pass

    def _load_object_from_api(self, data=None):
        pass


@pytest.fixture(scope='module')
def cube():
    cube = Cube('8485-1901')
    yield cube
    cube = None


class TestCube(object):
    @pytest.mark.parametrize('mode, db, origin',
                            [('local', False, 'db'),
                             ('local', True, 'file'),
                             ('remote', False, 'api')])
    def test_cube_mma(self, mode, db, origin):
        cube = Cube('8485-1901', mode=mode, ignore_db=db)
        if cube._db.connected is False:
            pytest.skip('skipping test when no db present')
        assert cube.data_origin == origin
        assert cube.mode == mode

    @pytest.mark.parametrize('url', [(False), (True)], ids=['nourl', 'url'])
    def test_get_full_path(self, cube, url):
        path = cube.get_full_path(url=url)
        assert '8485/stack/manga-8485-1901-LOGCUBE.fits.gz' in path
        if url:
            assert path.startswith('https://data.sdss.org')
        else:
            assert not path.startswith('https://data.sdss.org')
