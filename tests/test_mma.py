# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: test_mma.py
# Project: tests
# Author: Brian Cherinka
# Created: Saturday, 14th March 2020 3:21:52 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Tuesday, 17th March 2020 5:36:17 pm
# Modified By: Brian Cherinka


from __future__ import absolute_import, division, print_function

import pytest
from sdss_brain.exceptions import BrainError
from .conftest import Toy, make_badtoy


class TestMMA(object):
    objectid = 'A'

    def assert_paths(self, toy):
        assert toy.path_name == 'toy'
        assert toy.path_params is not None
        assert 'object' in toy.path_params
        assert toy.path_params['object'] == 'A'
        assert hasattr(toy, 'object')
        assert toy.object == 'A'

    @pytest.mark.parametrize('data', [('filename'), ('objectid')])
    def test_local_input(self, make_file, data):
        if data == 'filename':
            exp = make_file
        else:
            exp = self.objectid
        toy = Toy(exp)
        assert toy.mode == 'local'
        assert getattr(toy, data) == exp
        self.assert_paths(toy)

    def test_remote(self):
        toy = Toy(self.objectid)
        assert toy.mode == 'remote'
        assert toy.objectid == self.objectid
        assert toy.data_origin == 'api'

    @pytest.mark.parametrize('data', [('filename'), ('objectid')])
    def test_explicit_input(self, make_file, data):
        if data == 'filename':
            filename = make_file
            toy = Toy(filename=filename)
            exp = filename
        else:
            toy = Toy(objectid=self.objectid)
            exp = self.objectid
        assert toy.mode == 'local'
        assert getattr(toy, data) == exp
        assert toy.data_origin == 'file'
        self.assert_paths(toy)

    def test_get_full_path(self, make_file):
        toy = Toy(self.objectid)
        path = toy.get_full_path()
        assert f'files/toy_object_{self.objectid}.txt' in path

    def test_access_switch(self, make_file):
        old = 'DR16'
        new = 'DR15'
        toy = Toy(self.objectid, release=old)
        assert toy.release == old
        assert toy.access.release == old.lower()
        toy = Toy(self.objectid, release=new)
        assert toy.release == new
        assert toy.access.release == new.lower()


class TestMMAFails(object):
    objectid = 'A'

    def test_fail_remote_filename(self):
        with pytest.raises(BrainError) as cm:
            Toy(filename='A', mode='remote')
        assert 'filename not allowed in remote mode' in str(cm.value)

    @pytest.mark.parametrize('bad, exp',
                             [('noname', 'must have a "path_name" class attribute'),
                              ('nonename', 'path_name attribute cannot be None'),
                              ('badpath', 'must be defined in the path templates'),
                              ('notdict', 'path_params attribute must be a dictionary')])
    def test_bad_access_params(self, bad, exp):
        with pytest.raises(AssertionError) as cm:
            make_badtoy(bad)
        assert exp in str(cm.value)

    @pytest.mark.parametrize('bad, exp',
                             [('empty', 'no inputs defined. filename and objectid are both None'),
                              ('none', 'input file not found')])
    def test_bad_parse_inputs(self, bad, exp):
        with pytest.raises(BrainError) as cm:
            make_badtoy(bad)
        assert exp in str(cm.value) or set(exp).issubset(set(str(cm.value)))
