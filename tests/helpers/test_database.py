# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: test_database.py
# Project: helpers
# Author: Brian Cherinka
# Created: Monday, 19th October 2020 5:49:42 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Monday, 19th October 2020 5:49:42 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import

import pytest
from sdss_brain.helpers import DatabaseHandler
from sdss_brain.exceptions import BrainError
from sdssdb.peewee.sdss5db import database, SDSS5dbDatabaseConnection, targetdb


@pytest.mark.datasource(database, db=True)
class TestDatabaseHandler(object):
    kls = SDSS5dbDatabaseConnection

    def assert_db(self, d, db):
        assert d.db == db
        assert isinstance(d.db, self.kls)
        assert d.orm == 'peewee'
        assert d.connected is True

    @staticmethod
    def assert_schema(d, schema):
        assert d.schema == schema
        assert d.models == targetdb

    def test_input_db(self):
        d = DatabaseHandler(database)
        self.assert_db(d, database)
        assert (d.models, d.model) == (None, None)

    def test_input_schema(self):
        d = DatabaseHandler(targetdb)
        self.assert_db(d, database)
        self.assert_schema(d, 'sdss5db.targetdb')
        assert d.model is None

    def test_input_model(self):
        d = DatabaseHandler(targetdb.Field)
        self.assert_db(d, database)
        self.assert_schema(d, 'targetdb')
        assert d.model == targetdb.Field

    @pytest.mark.parametrize('schema',
                             [('targetdb'),
                              ('sdss5db.targetdb'),
                              ('peewee.sdss5db.targetdb'),
                              ('sdssdb.peewee.sdss5db.targetdb')])
    def test_load_schema(self, schema):
        d = DatabaseHandler(database)
        assert d.models is None
        d.load_schema(schema)
        self.assert_schema(d, 'sdss5db.targetdb')

    def test_load_model(self):
        d = DatabaseHandler(targetdb)
        assert d.model is None
        d.load_model('Instrument')
        self.assert_schema(d, 'sdss5db.targetdb')
        assert d.model == targetdb.Instrument


class TestDbHandlerFails(object):

    def test_bad_model(self):
        d = DatabaseHandler(targetdb)
        with pytest.raises(AttributeError, match='schema sdss5db.targetdb does not have model *'):
            d.load_model('BadModel')

    def test_bad_schema(self):
        d = DatabaseHandler(database)
        with pytest.raises(BrainError, match='No module found matching'):
            d.load_schema('badschema')

    def test_other_input(self):
        d = DatabaseHandler('badinput')
        assert d.db is None
        assert d.orm is None
