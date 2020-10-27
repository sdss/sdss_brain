# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: database.py
# Project: helpers
# Author: Brian Cherinka
# Created: Sunday, 18th October 2020 11:54:01 am
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Sunday, 18th October 2020 11:54:01 am
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import

import importlib
import inspect
from types import ModuleType
from typing import List, Union, Type

import sdssdb.peewee
import sdssdb.sqlalchemy
from sdssdb.connection import DatabaseConnection, PeeweeDatabaseConnection, SQLADatabaseConnection

from sdss_brain.exceptions import BrainError

db_type = Union[Type[PeeweeDatabaseConnection], Type[SQLADatabaseConnection],
                Type[sdssdb.peewee.BaseModel], Type[sdssdb.sqlalchemy.BaseModel],
                Type[ModuleType]]


class DatabaseHandler(object):
    """ Convenience class for handling an sdssdb database connection / ORM

    A convenience class to provide a simple API to any sdssdb database or ORM.
    Accepts as input any sdssdb peewee or sqlalchemy ORM Model, DatabaseConnection,
    or a sdssdb schema ORM python module. Given valid input will determine, which
    database, schema, set of ORMs, and primary ORM.

    Parameters
    ----------
    db_input : db_type
        The type of sdssdb database input.

    Attributes
    ----------
        orm : str
            Indicates whether the ORM is peewee or sqlalchemy
        model : `~sdssdb.peewee.BaseModel` | `~sdssdb.sqlalchemy.BaseModel`
            Any database ORM Model
        models : py module
            A database schema python module containing all ORM models
        db : `~sdssdb.connection.DatabaseConnection`
            A database connection object
        schema : str
            The schema name
        session : `~sqlalchemy.orm.session.Session`
            A sqlalchemy database session needed for querying
    """

    def __init__(self, db_input: db_type = None) -> None:
        self.orm = None
        self.model = None
        self.models = None
        self._session = None
        self.db = None
        self.schema = None

        self._determine_input(db_input)

    def __repr__(self) -> str:
        d = {'orm': self.orm, 'model': self.model.__name__ if self.model else None,
             'schema': self.schema, 'db': self.db.dbname if self.db else None}
        repr_items = ', '.join([m for m in map(lambda x: '{0}="{1}"'.format(
                     *x) if x[1] else '', d.items()) if m])
        return f'<DatabaseHandler ({repr_items})>'

    def _determine_input(self, value: db_type = None) -> None:
        """ Determine the type of database input

        Determines whether the input is a valid sdssdb ORM Model,
        DatabaseConnection, or schema module, and sets the instance
        attributes for orm, db, schema, model and models.

        Parameters
        ----------
        value : db_type, optional
            The type of ``sdssdb`` database input, by default None
        """
        if not value:
            return

        if any(self._is_a_model(value)):
            self._check_models(value)
        elif any(self._is_a_db(value)):
            self._check_dbs(value)
        elif any(self._is_a_schema(value)):
            self._check_schema(value)

    @staticmethod
    def _is_a_model(value: db_type) -> List[bool]:
        """ Conditional check if input is an ORM Model """
        if not inspect.isclass(value):
            return [None, None]

        pmodel, smodel = issubclass(value, sdssdb.peewee.BaseModel), issubclass(
            value, sdssdb.sqlalchemy.BaseModel)
        return [pmodel, smodel]

    def _check_models(self, value: db_type) -> None:
        """ Checks a sdssdb ORM

        Given any sdssdb peewee or sqlalchemy ORM, extracts
        relevant information on the ORM, database, schema name, and set of ORM
        models.

        Parameters
        ----------
        value : `~sdssdb.peewee.BaseModel` | `~sdssdb.sqlalchemy.BaseModel`
            A valid sdssdb peewee or sqla ORM
        """
        pmodel, smodel = self._is_a_model(value)

        self.model = value
        self.models = importlib.import_module(value.__module__)
        if pmodel:
            self.orm = 'peewee'
            self.schema = value._meta.schema
            self.db = value._meta.database
        elif smodel:
            self.orm = 'sqla'
            self.schema = value._schema
            self.db = getattr(self.models, 'database', None)
            self._set_session()

    @staticmethod
    def _is_a_db(value: db_type) -> List[bool]:
        """ Conditional check if input is a DatabaseConnection """
        pdatabase, sdatabase = isinstance(value, PeeweeDatabaseConnection), isinstance(
            value, SQLADatabaseConnection)
        return [pdatabase, sdatabase]

    def _check_dbs(self, value: Type[DatabaseConnection]) -> None:
        """ Checks a sdssdb database connection

        Given a sdssdb peewee or sqlalchemy database connection, extracts
        relevant information on the ORM, database, schema name, and set of ORM
        models.

        Parameters
        ----------
        value : `~sdssdb.connection.DatabaseConnection`
            A valid sdssdb database connection
        """
        pdatabase, sdatabase = self._is_a_db(value)
        self.db = value
        if pdatabase:
            self.orm = 'peewee'
        elif sdatabase:
            self.orm = 'sqla'
            self._set_session()

    @staticmethod
    def _is_a_schema(value: db_type) -> List[bool]:
        """ Conditional check if input is a schema module """
        is_module = inspect.ismodule(value)
        name = value.__name__ if is_module else ''
        pschema, sschema = is_module and 'peewee' in name, is_module and 'sqlalchemy' in name
        return [pschema, sschema]

    def _check_schema(self, value: Type[ModuleType]) -> None:
        """ Checks a sdssdb schema module file

        Given a schema module files, extracts relevant information
        on the ORM, database, schema name, and set of ORM models

        Parameters
        ----------
        value : py module
            A valid sdssdb database schema module file
        """
        pschema, sschema = self._is_a_schema(value)

        self.models = value
        self.db = getattr(value, 'database', None)
        self.schema = self.models.__name__.split('.', 2)[-1]

        if pschema:
            self.orm = 'peewee'
        elif sschema:
            self.orm = 'sqla'
            self._set_session()

    @property
    def connected(self) -> bool:
        """ Returns True if the database is connected """
        return self.db.connected if self.db else None

    def _set_session(self):
        """ Sets the sqla database Session if db is connected """
        if self.connected:
            self._session = self.db.Session()

    @property
    def session(self):
        """ A sqlalchemy database session needed for querying

        Returns
        -------
        `~sqlalchemy.orm.session.Session`
            A sqlalchemy database session needed for querying

        Raises
        ------
        AttributeError
            when the orm is "peewee"
        """

        if self.orm == 'peewee':
            raise AttributeError('peewee ORMs do not use sessions. To query, access the model '
                                 'directly or load a sqlalchemy ORM')
        return self._session

    def load_schema(self, schema: str):
        """ Load an sdssdb schema module

        Loads an input sdssdb schema module name from the currently loaded database
        and into the handler. The input name can be dot-qualified as "[orm].[database].[schema]"
        and it will attempt to find and load the correct module.  For example
        ``targetdb``, ``sdss5db.targetdb``, ``peewee.sdss5db.targetdb`` are all
        valid names.

        Parameters
        ----------
        schema : str
            The name of an sdssdb schema module

        Raises
        ------
        TypeError
            when the input is not a string
        BrainError
            when no database connection is present
        BrainError
            when no schema module is found by importlib.import_module
        """

        if type(schema) != str:
            raise TypeError(f'Input {schema} must be a string.')

        if not self.db:
            raise BrainError(f'No db present. Cannot load schema {schema}.')

        orm = 'sqlalchemy' if self.orm == 'sqla' else 'peewee'
        dbname = self.db.dbname if self.db else ''
        if schema.count('.') == 0:
            modname = f'sdssdb.{orm}.{dbname}.{schema}'
        elif schema.count('.') == 1:
            modname = f'sdssdb.{orm}.{schema}'
        elif schema.count('.') == 2:
            modname = f'sdssdb.{schema}'
        else:
            modname = schema

        try:
            self.models = importlib.import_module(modname)
        except ModuleNotFoundError as e:
            raise BrainError(f'No module found matching {modname}') from e
        else:
            self.schema = self.models.__name__.split('.', 2)[-1]
            self.model = None

    def load_model(self, model: str):
        """ Loads an ORM model

        Loads an input ORM model name from the currently loaded database
        and schema into the handler.

        Parameters
        ----------
        model : str
            The name of an ORM model to load

        Raises
        ------
        BrainError
            when no valid schema is set
        AttributeError
            when no model is found within the loaded schema
        """

        if not self.models:
            raise BrainError('No valid schema set containing ORM models.')

        model_obj = getattr(self.models, model, None)
        if not model_obj:
            raise AttributeError(f'schema {self.schema} does not have model {model}')

        self.model = model_obj

    def close(self):
        """ Close database connections and sessions """
        if self.orm == 'sqlalchemy':
            self.session.close()
        elif self.orm == 'peewee':
            self.db.close()

