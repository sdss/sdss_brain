# !/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Filename: test_mma.py
# Project: tests
# Author: Brian Cherinka
# Created: Saturday, 14th March 2020 3:21:52 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Sunday, 15th March 2020 12:10:16 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import
import pytest
from sdss_brain.config import config
from sdss_brain.mma import MMAMixIn
from sdss_access import Access


@pytest.fixture()
def make_file(tmp_path):
    ''' fixture to create a fake file '''
    path = tmp_path / "files"
    path.mkdir()
    toyfile = path / "toy_object_A.txt"
    toyfile.write_text('this is a toy file')
    yield toyfile


class MockMMA(MMAMixIn):
    ''' mock MMA mixin to allow additions of fake sdss_access template paths '''
    mock_template = None

    @property
    def access(self):
        access = Access(public='DR' in config.release, release=config.release.lower())
        access.templates['toy'] = self.mock_template
        return access


@pytest.fixture(autouse=True)
def mock_mma(tmp_path):
    ''' fixture that updates the mock_template path '''
    path = tmp_path / "files"
    MockMMA.mock_template = str(path / 'toy_object_{object}.txt')


class Toy(MockMMA, object):
    
    def __init__(self, data_input=None, filename=None, objectid=None):
        MockMMA.__init__(self, data_input=data_input, filename=filename, objectid=objectid)

    def _parse_input(self, value):
        obj = {"objectid": None}
        if len(value) == 1 and value.isalpha():
            obj['objectid'] = value
        return obj

    def _get_full_path(self):
        params = {'object': self.objectid}
        return super(Toy, self)._get_full_path('toy', **params)


class TestMMA(object):
    objectid = 'A'

    def test_local_input(self, make_file):
        toy = Toy(self.objectid)
        assert toy.mode == 'local'
        assert toy.objectid == self.objectid

    def test_local_input_file(self, make_file):
        filename = str(make_file)
        toy = Toy(filename)
        assert toy.mode == 'local'
        assert toy.filename == filename

    def test_remote(self):
        toy = Toy(self.objectid)
        assert toy.mode == 'remote'
        assert toy.objectid == self.objectid
        
    def test_explicit_filename(self, make_file):
        filename = str(make_file)
        toy = Toy(filename=filename)
        assert toy.mode == 'local'
        assert toy.filename == filename

    def test_explicit_object(self, make_file):
        toy = Toy(objectid=self.objectid)
        assert toy.mode == 'local'
        assert toy.objectid == self.objectid
