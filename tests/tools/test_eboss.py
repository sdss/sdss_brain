# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: test_eboss.py
# Project: tools
# Author: Brian Cherinka
# Created: Thursday, 15th October 2020 3:32:23 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Thursday, 15th October 2020 3:32:23 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import
import pytest
from sdss_brain.tools.spectra import Eboss
from sdss_brain.config import config
from sdss_brain.exceptions import BrainError
from .conftest import WorkTests, get_mocked, BaseTests
from tests.conftest import object_data

releases = object_data.get('eboss').keys()


@pytest.fixture(params=releases)
def release(request):
    yield request.param


@pytest.mark.use_test_data('eboss', fake_missing=True)
class TestEbossWorkVersions(WorkTests):
    mock = get_mocked(Eboss)
    version = 'run2d'

    def test_set_work_version(self, monkeypatch):
        monkeypatch.setattr(config, 'work_versions', {})
        monkeypatch.setattr(Eboss, '_version', None)
        assert config.work_versions == {}
        assert getattr(Eboss, '_version') is None
        ver = {'run2d': 'v5_10_0'}
        Eboss.set_work_version(ver)
        assert Eboss._version == {'run2d': 'v5_10_0'}


class TestEbossWorkFails(BaseTests):

    def test_no_work_version_set(self, monkeypatch):
        monkeypatch.setattr(config, 'work_versions', {})
        with pytest.raises(BrainError, match='You are using a "work" release but have no work versions set!*'):
            Eboss('3606-55182-0537', release='WORK')

    def test_release_version_set(self):
        with pytest.raises(BrainError, match='version is only used for "work" data.'):
            Eboss('3606-55182-0537', release='DR14', version={'run2d': 'v5_10_0'})


@pytest.mark.use_test_data('eboss', fake_missing=True)
class TestEbossDataModel(WorkTests):
    mock = get_mocked(Eboss)
    version = 'run2d'
    model = 'specLite'

    def assert_model(self, inst):
        assert hasattr(inst, 'datamodel')
        assert inst.datamodel is not None
        assert inst.release == inst.datamodel.release
        assert inst.datamodel.name == 'specLite'

    def get_tool(self, release):
        e = Eboss('3606-55182-0537', release=release)
        self.assert_model(e)
        assert e.datamodel.release == release
        return e

    def test_datamodel(self):
        e = self.get_tool('DR17')
        assert e.datamodel.release_model is not None

    @pytest.mark.xfail(reason='Need to fix the work release stuff with datamodels first')
    def test_dm_no_release(self, monkeypatch):
        e =  self.get_tool('WORK')
        assert e.datamodel.release_model is None
