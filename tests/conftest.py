#!usr/bin/env python
# encoding: utf-8
#
# conftest.py


import pytest
from sdss_brain.mma import MMAMixIn
from sdss_access import Access
from sdss_brain.config import config


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


class Toy(MockMMA):

    def __init__(self, data_input=None, filename=None, objectid=None, mode=None):
        MockMMA.__init__(self, data_input=data_input, filename=filename,
                         objectid=objectid, mode=mode)

    def _parse_input(self, value):
        obj = {"objectid": None}
        if len(value) == 1 and value.isalpha():
            obj['objectid'] = value
        return obj

    def _set_access_path_params(self):
        self.path_name = 'toy'
        self.path_params = {'object': self.objectid}
