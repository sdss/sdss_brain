
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


Subclassing the ``Brain`` 
^^^^^^^^^^^^^^^^^^^^^^^^^

When subclassing ``Brain``, there are several abstract methods that you must define.  These methods are

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

        def _load_object_from_file(self, data=None):
            pass

        def _load_object_from_db(self, data=None):
            pass

        def _load_object_from_api(self, data=None):
            pass

Now that we have our class defined.
::

    cube = MangaCube('8485-1901')
    cube
