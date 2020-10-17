# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: conftest.py
# Project: tools
# Author: Brian Cherinka
# Created: Thursday, 15th October 2020 3:31:39 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Thursday, 15th October 2020 3:31:39 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import
import pytest
import pathlib
from sdss_brain.config import config
from tests.conftest import object_data, check_path


@pytest.fixture()
def use_test_data(request):
    marker = request.node.get_closest_marker("use_test_data")

    if marker is None:
        # Handle missing marker in some way...
        name = None
    else:
        name = marker.args[0]

    data = object_data.get(name, None)

    # get keywords
    skip = marker.kwargs.get('skip_missing', None)
    fake = marker.kwargs.get('fake_missing', None)

    # construct the path
    release = request.getfixturevalue('release')
    path = pathlib.Path(data[release]['path'])
    exists = path.is_file()

    # skip the data
    if skip:
        check_path(str(path))

    # fake the data
    if fake and not exists:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('fake file')

    # Do something with the data
    yield data

    # clean up the fake file
    if fake and not exists:
        path.unlink()


@pytest.fixture()
def expdata(release, use_test_data):
    data = use_test_data.get(release, None)
    new = data.copy()
    yield new


def get_mocked(kls):
    ''' get a mocked tools class '''
    class Mocked(kls):
        def _load_spectrum(self):
            pass

        def _load_object_from_file(self, data):
            pass

        def _load_object_from_file(self, data):
            pass

        def _load_object_from_api(self):
            pass

    return Mocked


class WorkTests(object):
    """ Class that tests that the class attributes and path_params

    This class tests that a Brain sub-class sets instance attributes and path_params
    properly and that they are consistent with each other.  This works for a given release
    or for work versions.
    """
    version = None
    mock = None

    def assert_file(self, inst, path):
        assert inst.filename is not None
        assert inst.objectid is None
        assert str(inst.filename) == path

    def assert_objectid(self, inst, oid):
        assert inst.objectid is not None
        assert str(inst.objectid) == oid

    def assert_params(self, inst, data):
        assert inst.release == data['release']
        assert inst.path_params == data['params']
        assert getattr(inst, self.version) == inst.path_params[self.version]
        for param, val in inst.path_params.items():
            assert getattr(inst, param) == val

    def test_as_filename(self, monkeypatch, expdata):
        """ tests explicit filename input """
        monkeypatch.setattr(config, 'work_versions', {self.version: 'v1_1_1'})
        version = expdata['version'] if 'WORK' in expdata['release'] else None
        inst = self.mock(filename=expdata['path'], release=expdata['release'], version=version)
        self.assert_file(inst, expdata['path'])
        self.assert_params(inst, expdata)

    #@pytest.mark.parametrize('noversion', [(True), (False)], ids=['noversion', 'explicit_version'])
    def test_as_fileinput(self, monkeypatch, expdata):#, noversion):
        """ tests filename as data input """
        monkeypatch.setattr(config, 'work_versions', {self.version: 'v1_1_1'})
        version = expdata['version'] if 'WORK' in expdata['release'] else None
        #version = None if noversion else version
        inst = self.mock(expdata['path'], release=expdata['release'], version=version)
        self.assert_file(inst, expdata['path'])
        self.assert_params(inst, expdata)

    def test_fileinput_workver_warning(self, monkeypatch, expdata):
        """ temporary tests to check mismatch between filename version and work version

        When filename input is different version than work_version and no explicit version
        is set, tool loads the file correctly but path params are incorrect

        if ever fixed then update the test and above test
        """
        monkeypatch.setattr(config, 'work_versions', {self.version: 'v1_1_1'})
        if expdata['release'] != 'WORK':
            pytest.skip('skipping non-work releases')

        if 'aspcap' in expdata['params']:
            pytest.xfail('manually defined ascap fails this test due to setting correct versions')

        with pytest.warns(UserWarning) as record:
            inst = self.mock(expdata['path'], release=expdata['release'])

        assert ('Version extracted from file is different '
                'than your preset "work" version') in str(record[0].message)
        self.assert_file(inst, expdata['path'])

        assert getattr(inst, self.version) not in inst.filename.as_posix()

    def test_as_objectid(self, expdata):
        """ tests object id as data input """
        s = expdata['objectid']
        version = expdata['version'] if 'WORK' in expdata['release'] else None
        inst = self.mock(s, release=expdata['release'], version=version)
        self.assert_objectid(inst, s)
        self.assert_params(inst, expdata)
