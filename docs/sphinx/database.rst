
.. _database:

Connecting to Database Objects
==============================

To enable tools built with the ``Brain`` to access a "database" mode, i.e. `data_origin="db"`, you must
attach a database object to the tool or provide one during tool instantiation.  The ``Brain`` relies on,
and uses, `sdssdb <https://sdssdb.readthedocs.io>`_ for all database-related items.  Schema not defined
in ``sdssdb`` are currently not supported.

Adding a Database to a Tool
---------------------------

We can add a valid ``sdssdb`` database object via one of three ways.  Using the ``_db`` class attribute
when defining a new tool class from the ``Brain``.  In this case, all instances and subclasses of this
tool will use the attached database object.
::

    from sdssdb.sqlalchemy.mangadb import datadb

    class MangaCube(Brain):
        _db = datadb.Cube

When using the `~sdss_brain.core.Brain.set_database_object` class method on a pre-defined tool.  This
temporarily sets a database object to the class.  In this case, all new instances and subclasses will use
the new database object set in the current Python session.
::

    from sdss_brain.tools import MangaCube
    from sdssdb.sqlalchemy.mangadb import datadb

    MangaCube.set_database_object(datadb.Cube)

When using the ``use_db`` keyword argument when instantiating the tool directly.  In this case, only
this instance will have access to the database object.
::

    from sdss_brain.tools import MangaCube
    from sdssdb.sqlalchemy.mangadb import datadb

    c = MangaCube('8485-1901', use_db=datadb.Cube)

Valid Input
-----------

There are multiple types of ``sdssdb`` database objects that are valid input:

- a valid sdssdb `~sdssdb.connection.DatabaseConnection`
- a valid sdssdb Object-Relational Model (ORM) from a specific schema
- a valid sdssdb database schema, containing a set of ORM models, as a named python module

Here we pass in the **mangadb** sdssdb `~sdssdb.sqlalchemy.mangadb.MANGAdbDatabaseConnection` itself.
::

    >>> from sdss_brain.tool import MangaCube
    >>> from sdssdb.sqlalchemy.mangadb import database

    >>> # passing in a database connection
    >>> c = MangaCube('8485-1901', use_db=database)
    >>> c.db
    <DatabaseHandler (orm="sqla", db="manga")>

Here we pass in the ``mangadb`` schema module ``datadb``, which represents the database schema
``mangadatadb``, which houses information related to the output from the MaNGA DRP pipeline.
::

    >>> from sdss_brain.tool import MangaCube
    >>> from sdssdb.sqlalchemy.mangadb import datadb

    >>> # passing in an entire ORM schema
    >>> c = MangaCube('8485-1901', use_db=datadb)
    >>> c.db
    <DatabaseHandler (orm="sqla", schema="mangadb.datadb", db="manga")>

Here we pass in an individual sdssdb ORM model, like the examples in the previous section, for ``Cube``
representing the MaNGA cube database table in the ``mangadb`` database.
::

    >>> from sdss_brain.tools import MangaCube
    >>> from sdssdb.sqlalchemy.mangadb.datadb import Cube

    >>> c = MangaCube('8485-1901', use_db=Cube)
    >>> c.db
    <DatabaseHandler (orm="sqla", model="Cube", schema="mangadatadb", db="manga")>

Passing in any of these objects results in a `~sdss_brain.helpers.database.DatabaseHandler` object being
created.

The DatabaseHandler
-------------------

When passing in a valid `sdssdb <https://sdssdb.readthedocs.io>`_ database object as input,
a `~sdss_brain.helpers.database.DatabaseHandler` object is created and attached to the ``db`` attribute.
The ``DatabaseHandler`` is a simple container around any ``peewee`` or ``sqlalchemy`` database connection,
schema, or ORM defined in `sdssdb`.  It normalizes the input between ``peewee`` or ``sqlalchemy`` and
provides access to the ORM model, the schema set of relational models, and the underlying connection
no matter what input is provided.  Here we load the ORM model ``Field`` from the ``sdss5db.targetdb``
schema.
::

    >>> from sdss_brain.helpers import DatabaseHandler
    >>> from sdssdb.peewee.sdss5db.targetdb import Field
    >>> d = DatabaseHandler(Field)
    >>> d
    <DatabaseHandler (orm="peewee", model="Field", schema="targetdb", db="sdss5db")>

    >>> # check the underling database connection
    >>> d.connected
    True

The ``DatabaseHandler`` displays the type of ORM it is, either ``peewee`` or ``sqla``. You can access the
provided model.
::

    >>> d.model
    <Model: Field>

You can access the underlying related schema the model is a part of, for when you need to join to other
models.
::

    >>> # see the schema name
    >>> d.schema
    'targetdb'

    >>> # access the underlying schema models
    >>> d.models
    <module 'sdssdb.peewee.sdss5db.targetdb' from '..sdssdb/peewee/sdss5db/targetdb.py'>

    >>> # accessing individual models
    >>> d.models.Instrument, d.models.Observatory
    (<Model: Instrument>, <Model: Observatory>)

You can access the underlying database connection.
::

    >>> d.db
    <SDSS5dbDatabaseConnection (dbname='sdss5db', profile='local', connected=True)>

For ``sqlalchemy`` connections, you can access the ``Session`` object for querying.
::

    >>> from sdssdb.sqlalchemy.mangadb.datadb import Cube
    >>> d = DatabaseHandler(Cube)
    >>> d
    <DatabaseHandler (orm="sqla", model="Cube", schema="mangadatadb", db="manga")>

    >>> # access the Session for quering
    >>> d.session
    <sqlalchemy.orm.session.Session at 0x118d9db00>

Information on models, schema, and databases are extracted in a bottom-up approach.  The ``DatabaseHandler``
cannot extract low-level information, e.g. ORM models, when high-level objects, e.g. a database connection,
are provided.  For example, here we pass in only the **sdss5db** database connection.
::

    >>> # pass in the sdss5db database connection
    >>> from sdssdb.peewee.sdss5db import database
    >>> d = DatabaseHandler(database)
    >>> d
    <DatabaseHandler (orm="peewee", db="sdss5db")>

No information on ORM models or schema has been extracted.
::

    >>> d.model, d.schema, d.models
    (None, None, None)

We can post-load schema or models using the `~sdss_brain.helpers.database.DatabaseHandler.load_schema`
and `~sdss_brain.helpers.database.DatabaseHandler.load_model` methods.  Let's load the sdss5
database targetdb schema.
::

    >>> # Load the targetdb schema
    >>> d.load_schema('targetdb')
    >>> d
    <DatabaseHandler (orm="peewee", schema="sdss5db.targetdb", db="sdss5db")>

    >>> # access a model
    >>> d.models.Instrument
    <Model: Instrument>

Now we have access to all the ORM models on the "targetdb" schema.  We can also load individual models.
::

    >>> # load the Field ORM
    >>> d.load_model('Field')
    >>> d
    <DatabaseHandler (orm="peewee", model="Field", schema="sdss5db.targetdb", db="sdss5db")>

    >>> d.model
    <Model: Field>

Using the handler in a Tool
---------------------------

Once you've attached a database object to a tool, you have full access to that object through the ``DatabaseHandler``
to perform queries.  Remember that you must override the `_load_object_from_db` method
with logic instructing the tool with what to do with the database object.  Let's see an example on the ``MangaCube`` tool
after we've attached the ``datadb.Cube`` ORM model.
::

    from sdssdb.sqlalchemy.mangadb import datadb

    class MangaCube(Brain):
        _db = datadb.Cube

        def _load_object_from_db(self, data=None):
            # make a database call to retrieve the first Cube row
            self.data = self.db.session.query(self.db.model).join(self.db.models.IFUDesign).\
            filter(self.db.model.plateifu == self.plateifu).first()

In the above example, we use the handler to perform a sqlalchemy query to retrieve the first row from the ``cube`` database
table that matches the tool's plateifu attribute, joining to another table available in the ``datadb`` schema.  For a more
complete example, see the
`MangaCube tool <https://github.com/sdss/sdss_brain/blob/master/python/sdss_brain/tools/cubes.py#L33>`_.