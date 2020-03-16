
.. _intro:

Introduction to sdss_brain
===============================

``sdss_brain`` provides a set of core of classes and helper functions to aid in the development of
user-facing tools and interfaces.  It combines the utility of other core SDSS packages, e.g. 
``sdss-access``, ``sdss-tree``, ``sdssdb``, ``sdsstools`` to enable a more streamlined and simplified 
SDSS user experience.

.. _mma:

Multi-Modal Data Access System
------------------------------

The ``MMAMixIn`` is bare-bones class to be mixed with any other class.  When mixed in, it adds MMA
functionality to that class. A convenience class, ``Brain`` to fu 


When subclassing ``MMAMixIn``, there are several abstract methods that you must define.  These methods are

- ``_parse_inputs``: Defines the logic to parse the input string into an object id or filename
- ``_set_access_path_params``: Defines parameters needed by `sdss_access` to generate filepaths
- ``_load_object_from_file``: Defines the logic for loading a local file from disk
- ``_load_object_from_db``: Defines the logic for loading an object from a database
- ``_load_object_from_api``: Defines the logic for loading an object remotely over an API

.. _example:

Example
-------

Let's step through the creation of new class to interface with MaNGA data cubes.   

::

    from sdss_brain.core import Brain
    from sdss_brain.helpers import get_mapped_version
    from sdssdb.sqlalchemy.mangadb import database as mangadb

    class MangaCube(Brain):
        _db = mangadb
        mapped_version = 'manga'

        def _set_access_path_params(self):
            self.path_name = 'mangacube'
            drpver = get_mapped_version(self.mapped_version, key='drpver')
            self.path_params = {'plate': self.plate, 'ifu':self.ifu, 'drpver': drpver}

        def _parse_inputs(self, value):
            pass

Now that we have our class defined, let's see it in use.  If we specified a database to use during class
definition, the default local action is to attempt to connect via the db.
::

    >>> cube = MangaCube('8485-1901')
    >>> cube
        <MangaCube objectid='8485-1901', mode='local', data_origin='db'>

The ``data_origin`` has been set to `db` and the mode is ``local``.  We can override the default database we 
use with the ``use_db`` keyword during instantiation.
::  

        cube = MangaCube('8485-1901', use_db=mangadb)

Or we can ignore the database altogther with the ``ignore_db`` keyword.  If you don't have a database, it
defaults to using local files. You can also turn off the database globally by setting the ``ignore_db`` option
in your custom configuration. 
::

    >>> cube = MangaCube('8485-1901', ignore_db=True)
    >>> cube
        <MangaCube objectid='8485-1901', mode='local', data_origin='file'>

Now the ``data_origin`` is set to ``file``.  If we don't have the file locally, or we explicitly set the
``mode='remote'``, it uses the remote API.
::

    >>> # explicitly set the mode to remote
    >>> cube = MangaCube('8485-1901', mode='remote')
    >>> cube 
        <MangaCube objectid='8485-1901', mode='remote', data_origin='api'>

    >>> # load a cube we don't have 
    >>> cube = MangaCube('8485-1902')
    >>> cube
        <MangaCube objectid='8485-1902', mode='remote', data_origin='api'>

