#!usr/bin/env python
# encoding: utf-8
#
# conftest.py

import pytest
from sdss_access import Access

import sdss_brain.mma as mma


class MockMMA(mma.MMAMixIn):
    ''' mock MMA mixin to allow additions of fake sdss_access template paths '''
    mock_template = None

    @property
    @mma.set_access
    def access(self):
        self._access.templates['toy'] = self.mock_template
        return self._access


@pytest.fixture(autouse=True)
def mock_mma(tmp_path):
    ''' fixture that updates the mock_template path '''
    path = tmp_path / "files"
    MockMMA.mock_template = str(path / 'toy_object_{object}.txt')


class Toy(MockMMA):
    ''' toy object to utilize in tests '''
    def __init__(self, data_input=None, filename=None, objectid=None, mode=None, 
                 release=None):
        MockMMA.__init__(self, data_input=data_input, filename=filename,
                         objectid=objectid, mode=mode, release=release)

    def _parse_input(self, value):
        if len(value) == 1 and value.isalpha():
            self.objectid = value
        else:
            self.filename = value

    def _set_access_path_params(self):
        self.path_name = 'toy'
        self.path_params = {'object': self.objectid}

    def _load_object_from_file(self, data=None):
        pass

    def _load_object_from_db(self, data=None):
        pass

    def _load_object_from_api(self, data=None):
        pass


@pytest.fixture()
def make_file(tmp_path):
    ''' fixture to create a fake file '''
    path = tmp_path / "files"
    path.mkdir()
    toyfile = path / "toy_object_A.txt"
    toyfile.write_text('this is a toy file')
    yield toyfile


def make_badtoy(bad):
    ''' creates a bad version of the Toy object '''
    class BadToy(Toy):
        def _set_access_path_params(self):
            self.path_name = 'toy'
            self.path_params = {'object': self.objectid}
            if bad == 'noname':
                self.path_name = None
            elif bad == 'noparam':
                self.path_params = None
            elif bad == 'notdict':
                self.path_params = 'badparams'

        def _parse_input(self, value):
            if bad == 'none':
                return         

            if len(value) == 1 and value.isalpha():
                self.objectid = value
            else:
                self.filename = value

    return BadToy('A')
