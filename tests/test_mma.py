# !/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Filename: test_mma.py
# Project: tests
# Author: Brian Cherinka
# Created: Saturday, 14th March 2020 3:21:52 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Sunday, 15th March 2020 11:54:22 pm
# Modified By: Brian Cherinka


from __future__ import absolute_import, division, print_function

import pytest
from sdss_brain.exceptions import BrainError
from .conftest import Toy


@pytest.fixture()
def make_file(tmp_path):
    ''' fixture to create a fake file '''
    path = tmp_path / "files"
    path.mkdir()
    toyfile = path / "toy_object_A.txt"
    toyfile.write_text('this is a toy file')
    yield toyfile


class TestMMA(object):
    objectid = 'A'

    @pytest.mark.parametrize('data', [('filename'), ('objectid')])
    def test_local_input(self, make_file, data):
        if data == 'filename':
            exp = str(make_file)
        else:
            exp = self.objectid
        toy = Toy(exp)
        assert toy.mode == 'local'
        assert getattr(toy, data) == exp
        
    def test_remote(self):
        toy = Toy(self.objectid)
        assert toy.mode == 'remote'
        assert toy.objectid == self.objectid

    @pytest.mark.parametrize('data', [('filename'), ('objectid')])
    def test_explicit_input(self, make_file, data):
        if data == 'filename':
            filename = str(make_file)
            toy = Toy(filename=filename)
            exp = filename
        else:
            toy = Toy(objectid=self.objectid)
            exp = self.objectid
        assert toy.mode == 'local'
        assert getattr(toy, data) == exp
        
    def test_fail_remote_filename(self):
        with pytest.raises(BrainError) as cm:
            Toy(filename='A', mode='remote')
        assert 'filename not allowed in remote mode' in str(cm.value)
