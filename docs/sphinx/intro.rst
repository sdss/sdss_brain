
.. _intro:

Introduction to sdss_brain
===============================

``sdss_brain`` provides a set of core of classes and helper functions to aid in the development of
user-facing tools and interfaces.  It combines the utility of other core SDSS packages, e.g. 
``sdss-access``, ``sdss-tree``, ``sdssdb``, ``sdsstools`` to enable a more streamlined and simplified 
SDSS user experience.

This package provides the following:

- Multi-Modal data access with the ``MMAMixIn`` and ``Brain`` classes
- xxx

.. _mma:

Multi-Modal Data Access System (MMA)
------------------------------------

The ``MMAMixIn`` is a bare-bones class to be mixed with any other class.  When mixed in, it adds MMA
functionality to that class. The MMA provides three operating modes: `auto`, `local`, and `remote`. 

- **auto**: Automatically tries to load objects locally, and upon failure loads object remotely.
- **local**: Load objects locally first from a database, and upon failure from a local filepath.
- **remote**: Load objects remotely over an API.

Depending on the mode and the logic preformed, the MMA will load data from origin `file`, `db`, or `api`.
See the :ref:`Mode Decision Tree <mma_tree>` for a workflow diagram. 

When subclassing ``MMAMixIn``, there are several abstract methods that you must define.  These methods are

- ``_parse_inputs``: Defines the logic to parse the input string into an object id or filename
- ``_set_access_path_params``: Defines parameters needed by `sdss_access` to generate filepaths
- ``_load_object_from_file``: Defines the logic for loading a local file from disk
- ``_load_object_from_db``: Defines the logic for loading an object from a database
- ``_load_object_from_api``: Defines the logic for loading an object remotely over an API


The ``Brain`` class is a convenience class that creates a basic object template with the ``MMAMixIn`` already
applied.  It also provides a ``repr`` and some placeholder logic to load objects based on the ``data_origin``.

.. _example:

Example Usage
-------------

Let's step through the creation of new class to interface with MaNGA data cubes using the ``Brain`` convenience
class, highlighting how to integrate the MMA into a new tool.

::

    from sdss_brain.core import Brain
    from sdss_brain.helpers import get_mapped_version
    from sdssdb.sqlalchemy.mangadb import database as mangadb

    class MangaCube(Brain):
        _db = mangadb
        mapped_version = 'manga'

        def _set_access_path_params(self):
            ''' set sdss_access parameters '''
            # set path name
            self.path_name = 'mangacube'

            # set path keyword arguments 
            drpver = get_mapped_version(self.mapped_version, key='drpver')
            self.path_params = {'plate': self.plate, 'ifu':self.ifu, 'drpver': drpver}

        def _parse_input(self, value):
            ''' parse the input value string '''
            # match for plate-ifu designation, e.g. 8485-1901
            plateifu_pattern = re.compile(r'([0-9]{4,5})-([0-9]{4,9})')
            plateifu_match = re.match(plateifu_pattern, value)
            
            # match on plate-ifu or else assume a filename
            if plateifu_match is not None:
                self.objectid = value
                self.plateifu = plateifu_match.group(0)
                self.plate, self.ifu = plateifu_match.groups(0)
            else:
                self.filename = value

To set up database access for your tool, set the ``_db`` class attribute to the appropriate database containing
information for.  Since we're creating a tool for MaNGA cubes, we use the `mangadb` database from `sdssdb`.

Next, we define the ``_set_access_path_params`` method for our tool.  Here we must specify the ``sdss_access`` 
path template **name** and **keyword parameters** needed to build complete file paths.  ``_set_access_path_params``
requires both a string `self.path_name` and dictionary `self.path_params` to be set.  Otherwise an error will be raised.
For MaNGA DRP cubes, the ``sdss_access`` name is **mangacube**, and it takes three keyword arguments, a plate id, 
an IFU designation, and the DRP version to define a complete filepath.

Finally we define the ``_parse_input`` method.  This method defines the logic of determining what kind of input
has been passed, either an object ID or a filepath.  We add some logic to determine if the input string is a 
plate-IFU designation, otherwise we assume it is a filepath.   

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

Note this class does not actually load any data, as we have not yet defined any of the 
``_load_object_from_xxx`` methods.