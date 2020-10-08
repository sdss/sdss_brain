#!usr/bin/env python
# encoding: utf-8
#
# conftest.py

import pytest
import os
import six
import inspect
from sdss_brain import tree
from sdss_brain.config import config
import sdss_brain.mixins.mma as mma
import sdss_brain.mixins.access as access


def pytest_addoption(parser):
    """ Add new options to the pytest command-line """
    # ignore datasources
    parser.addoption('--ignore-datasources', action='store_true', default=False,
                     help='Ignore the datasource marker applied to tests')


def check_class(item):
    ''' Check if argument is a proper class mixed from mma.MMAMixIn '''
    if inspect.isfunction(item):
        # check if item is a fxn and return is correct class
        assert item.__name__.startswith('from_')
        dataobj = item()
        assert issubclass(dataobj.__class__, (mma.MMAMixIn, mma.MMAccess))
    else:
        # check if item is correct class
        assert issubclass(item.__class__, (mma.MMAMixIn, mma.MMAccess))
        dataobj = item
    return dataobj


def check_path(item):
    ''' checks if data exists locally '''
    if isinstance(item, six.string_types):
        # check if item is string; assume filepath
        path = item
    else:
        dataobj = check_class(item)
        path = dataobj.get_full_path()

    if not os.path.exists(path):
        pytest.skip('No local file found.')
    return path


def check_db(item):
    ''' checks if db exists locally

    Paramter:
        item (fxn|object):
            A function o
    '''
    dataobj = check_class(item)
    if not dataobj._db or dataobj._db.connected is False:
        pytest.skip('skipping test when no db present')


def pytest_runtest_setup(item):
    ''' pytest runner post setup

    Currently only runs code for marker.datasource

    '''
    # look for all "datasource" markers
    for marker in item.iter_markers(name="datasource"):
        # skip marker if ignore-datasource is set in options
        if item.config.getoption('--ignore-datasources'):
            continue

        # if no argument, generically skip test
        if not marker.args:
            pytest.skip('Assuming no local data')
            continue

        # get the marker argument
        item = marker.args[0]

        # get marker keyword flags
        db = marker.kwargs.get('db', None)
        data = marker.kwargs.get('data', None)

        # if no flag set, runs normally
        if not db and not data:
            continue

        # check for db existence
        if db:
            check_db(item)

        # check for data filepath existence
        if data:
            check_path(item)


@pytest.fixture(scope='session')
def mocksess_sas(tmp_path_factory):
    ''' session fixture to change the SAA_BASE_DIR to a temp directory '''
    path = str(tmp_path_factory.mktemp('sas'))
    orig_env = os.environ.copy()
    os.environ['SAS_BASE_DIR'] = path
    tree.replant_tree(config.release)
    yield None
    os.environ = orig_env


@pytest.fixture()
def mock_sas(tmp_path, monkeypatch):
    ''' function fixture to change the SAS_BASE_DIR to a temp directory

        if used, this fixture must come first in test invocation

        also manually monkeypatches os.environ so we can replant the tree
        environ.
    '''
    orig_env = os.environ.copy()
    path = str(tmp_path / 'sas')
    monkeypatch.setenv('SAS_BASE_DIR', path)
    tree.replant_tree(config.release)
    yield None
    os.environ = orig_env


class MockMMA(mma.MMAccess):
    ''' mock MMA mixin to allow additions of fake sdss_access template paths '''
    mock_template = None

    @property
    @access.set_access
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
    path_name = 'toy'

    # def __init__(self, data_input=None, filename=None, objectid=None, mode=None,
    #              release=None):
    #     MockMMA.__init__(self, data_input=data_input, filename=filename,
    #                      objectid=objectid, mode=mode, release=release)

    def _parse_input(self, value):
        data = {'filename': None, 'objectid': None}
        if len(str(value)) == 1 and str(value).isalpha():
            data['objectid'] = value
        else:
            data['filename'] = value
        return data

    def _set_access_path_params(self):
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
        if bad == 'nonename':
            path_name = None
        elif bad == 'noname':
            @property
            def path_name(self):
                raise AttributeError
        elif bad == 'badpath':
            path_name = 'stuff'
        else:
            path_name = 'toy'

        def _set_access_path_params(self):
            self.path_params = {'object': self.objectid}
            if bad == 'noparam':
                self.path_params = None
            elif bad == 'notdict':
                self.path_params = 'badparams'

        def _parse_input(self, value):
            if bad == 'none':
                return {}
            elif bad == 'empty':
                return {'filename': None, 'objectid': None}

            data = {'filename': None, 'objectid': None}
            if len(str(value)) == 1 and str(value).isalpha():
                data['objectid'] = value
            else:
                data['filename'] = value
            return data

    return BadToy('A')
