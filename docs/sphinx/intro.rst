
.. _intro:

Introduction to sdss_brain
===============================

``sdss_brain`` provides a set of core of classes and helper functions to aid in the development of
user-facing tools and interfaces.  It combines the utility of other core SDSS packages, e.g.
``sdss-access``, ``sdss-tree``, ``sdssdb``, ``sdsstools`` to enable a more streamlined and simplified
SDSS user experience.

This package provides the following:

- Multi-Modal data access with the ``MMAMixIn`` and ``Brain`` classes
-

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

The ``Brain`` class is a convenience class that creates a basic object template with the ``MMAMixIn`` already
applied.  It also provides a ``repr`` and some placeholder logic to load objects based on the ``data_origin``.
When subclassing from ``Brain``, there are several abstract methods that you must define.

- ``_load_object_from_file``: Defines the logic for loading a local file from disk
- ``_load_object_from_db``: Defines the logic for loading an object from a database
- ``_load_object_from_api``: Defines the logic for loading an object remotely over an API

.. note::
    Regarding data access via remote API.  The logic for this access mode is not yet implemented.  It will
    be unavailable until a SDSS API to serve data has been created.


.. _example:

Example Usage
-------------

Let's step through the creation of new class to interface with MaNGA data cubes using the ``Brain`` convenience
class, highlighting how to integrate the MMA into a new tool.

::

    import re
    from sdss_brain.core import Brain
    from sdss_brain.helpers import get_mapped_version, load_fits_file, parse_data_input
    from sdssdb.sqlalchemy.mangadb import database as mangadb

    class MangaCube(Brain):
        _db = mangadb
        mapped_version = 'manga'
        path_name = 'mangacube'  # set path name for sdss_access

        def _set_access_path_params(self):
            ''' set sdss_access parameters '''
            # set path keyword arguments
            drpver = get_mapped_version(self.mapped_version, key='drpver')
            self.path_params = {'plate': self.plate, 'ifu':self.ifu, 'drpver': drpver}

        def _parse_input(self, value):
            ''' parse the input value string into a filename or objectid '''
            # match for plate-ifu designation, e.g. 8485-1901
            plateifu_pattern = re.compile(r'([0-9]{4,5})-([0-9]{4,9})')
            plateifu_match = re.match(plateifu_pattern, value)

            # create the output dictionary
            data = {'filename': None, 'objectid': None}

            # match on plate-ifu or else assume a filename
            if plateifu_match is not None:
                data['objectid'] = value

                # extract and set additional parameters
                self.plateifu = plateifu_match.group(0)
                self.plate, self.ifu = plateifu_match.groups(0)
            else:
                data['filename']
            return data

        def _load_object_from_file(self, data=None):
            self.data = load_fits_file(self.filename)

        def _load_object_from_db(self, data=None):
            pass

        def _load_object_from_api(self, data=None):
            pass

To set up database access for your tool, set the ``_db`` class attribute to the appropriate database containing
information for.  Since we're creating a tool for MaNGA cubes, we use the `mangadb` database from `sdssdb`.

Next, we setup our tool to interface with ``sdss_access``.  To do so, we must specify the ``sdss_access``
path template **name** and **keyword parameters** needed to build complete file paths.  The template name
is set as a class attribute, a required string parameter `path_name`.  The template keywords are set in the
defined ``_set_access_path_params`` method for our tool, as a dictionary `self.path_params`.  If neither the
`path_name` nor `path_params` are set, errors will be raised.  For MaNGA DRP cubes, the ``sdss_access``
name is **mangacube**, and it takes three keyword arguments, a plate id, an IFU designation, and the DRP
version to define a complete filepath.  To understand what the ``get_mapped_version`` function is doing,
see :ref:`version mappping <version>`.

We define the ``_parse_input`` method.  This method defines the logic of determining what kind of input
has been passed, either an object ID or a filepath.  We add some logic to determine if the input string is a
plate-IFU designation, otherwise we assume it is a filepath.  This method **must** return a dictionary
containing at minimum keys for either `filename` and `objectid`.

There are convenience helpers available to simpify the boilerplate process of defining logic for
``_parse_input`` and ``_set_access_path_params``.  See :ref:`helpers` for more information.

Finally we define the ``_load_object_from_file`` method to load FITS file data using a ``load_fits_file``
helper function.  These methods can perform any number of tasks related to handling of said data.  In
this example, we keep it simple by only loading the data itself.  Note that we must define all abstract
methods even if we aren't ready to use them.  Thus we also define placeholders for the `api` and `db`
load methods.

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


.. _helpers:

Conveniences for the MMA
------------------------



Regex Pattern Parser
^^^^^^^^^^^^^^^^^^^^

Decorators
^^^^^^^^^^
