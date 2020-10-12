
.. _intro:

Introduction to sdss_brain
===============================

``sdss_brain`` provides a set of core of classes and helper functions to aid in the development of
user-facing tools and interfaces.  It combines the utility of other core SDSS packages, e.g.
``sdss-access``, ``sdss-tree``, ``sdssdb``, ``sdsstools`` to enable a more streamlined and simplified
SDSS user experience.

This package provides the following:

- Multi-Modal data access with the `~sdss_brain.mixins.mma.MMAccess` and `~sdss_brain.core.Brain` classes
- Convenient starter tools for spectra with

.. _mma:

Multi-Modal Data Access System (MMA)
------------------------------------

The ``MMAccess`` is a bare-bones class to be mixed with any other class.  When mixed in, it adds MMA
functionality to that class. The MMA provides three operating modes: `auto`, `local`, and `remote`.

- **auto**: Automatically tries to load objects locally, and upon failure loads object remotely.
- **local**: Load objects locally first from a database, and upon failure from a local filepath.
- **remote**: Load objects remotely over an API.

Depending on the mode and the logic preformed, the MMA will load data from origin `file`, `db`, or `api`.
See the :ref:`Mode Decision Tree <mma_tree>` for a workflow diagram.

When subclassing ``MMAccess``, there are several abstract methods that you must define.  These methods are

- ``_parse_inputs``: Defines the logic to parse the input string into an object id or filename
- ``_set_access_path_params``: Defines parameters needed by `sdss_access` to generate filepaths

The ``Brain`` class is a convenience class that creates a basic object template with the ``MMAccess`` already
applied.  It also provides a ``repr`` and some placeholder logic to load objects based on the ``data_origin``.
When subclassing from ``Brain``, there are several abstract methods that you must define.

- ``_load_object_from_file``: Defines the logic for loading a local file from disk
- ``_load_object_from_db``: Defines the logic for loading an object from a database
- ``_load_object_from_api``: Defines the logic for loading an object remotely over an API

The ``Brain`` and ``MMAccess`` are designed to build classes that contain valid entries in `~sdss_access`.
Multi-modal data access can still be provided to files without defined paths in `sdss_access` using the
`~sdss_brain.mixins.mma.MMAMixIn` class instead of ``MMAccess``.  The main difference is, when using the
``MMAMixIn`` class instead, you will need to define two additional abstract methods:

- ``get_full_path``: Returns a local filepath to a data file
- ``download``: Downloads a file from a remote location to a local path on disk

There exists a version of the ``Brain`` with with standard MMA mixed in.  Sub-classing from
`~sdss_brain.core.BrainNoAccess` will give you functionality of the ``Brain`` but without reliance on
``sdss_access`` paths.

.. note::
    The MMA by itself does not contain the logic for accessing data from a filename, database, or over an API.
    That logic must be created by the user.  Methods and classes containing default logic will be provided
    at a later time.  The logic for the remote API access mode is not yet implemented.  It will
    be unavailable until a SDSS API to serve data has been created.


.. _example:

Example Usage
-------------

Let's step through the creation of new class to interface with MaNGA data cubes using the ``Brain`` convenience
class, highlighting how to integrate the MMA into a new tool.

::

    import re
    from sdss_brain.core import Brain
    from sdss_brain.helpers import get_mapped_version, load_fits_file
    from sdssdb.sqlalchemy.mangadb import database as mangadb

    class MangaCube(Brain):
        _db = mangadb
        mapped_version = 'manga' # set the release mapping key
        path_name = 'mangacube'  # set path name for sdss_access

        def _set_access_path_params(self):
            ''' set sdss_access parameters '''

            # set path keyword arguments
            drpver = get_mapped_version(self.mapped_version, release=self.release, key='drpver')
            self.path_params = {'plate': self.plate, 'ifu':self.ifu, 'drpver': drpver}

        def _parse_input(self, value):
            ''' parse the input value string into a filename or objectid '''

            # match for plate-ifu designation, e.g. 8485-1901
            plateifu_pattern = re.compile(r'(?P<plate>\d{4,5})-(?P<ifu>\d{3,5})')
            plateifu_match = re.match(plateifu_pattern, value)

            # create the output dictionary
            data = dict.fromkeys(['filename', 'objectid'])

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

These two methods combine to instruct the ``Brain`` how to take a custom input "object id" and turn it into
a valid filename path, database entry, or remote API call.  There are convenience helpers available to
simpify the boilerplate process of defining logic for ``_parse_input`` and ``_set_access_path_params``.
See :ref:`helpers` for more information.

Finally we define the ``_load_object_from_file`` method to load FITS file data using a ``load_fits_file``
helper function.  These methods can perform any number of tasks related to handling of said data.  In
this example, we keep it simple by only loading the data itself into the ``data`` attribute.  The ``data``
attribute is a common attribute to store any data loaded from files, a db, or over the API.  Note that we
must define all abstract methods even if we aren't ready to use them.  Thus we also define placeholders
for the `api` and `db` load methods.

Now that we have our class defined, let's see it in use.  We can explicitly load a filename.
::

    >>> ff = '/Users/Brian/Work/sdss/sas/dr15/manga/spectro/redux/v2_4_3/8485/stack/manga-8485-1901-LOGCUBE.fits.gz'
    >>> cube = MangaCube(filename=ff, release='DR15')
    >>> cube
    <MangaCube filename='/Users/Brian/Work/sdss/sas/dr15/manga/spectro/redux/v2_4_3/8485/stack/manga-8485-1901-LOGCUBE.fits.gz', mode='local', data_origin='file'>

The ``data_origin`` has been set to `file` and the mode is ``local``.  The ``Brain`` takes one direct
argument as any "data_input".  It will attempt to determine if the input is a valid filename or an object id.
We can provide the filename directly.
::

    >>> ff = '/Users/Brian/Work/sdss/sas/dr15/manga/spectro/redux/v2_4_3/8485/stack/manga-8485-1901-LOGCUBE.fits.gz'
    >>> cube = MangaCube(f, release='DR15')
    <MangaCube filename='/Users/Brian/Work/sdss/sas/dr15/manga/spectro/redux/v2_4_3/8485/stack/manga-8485-1901-LOGCUBE.fits.gz', mode='local', data_origin='file'>

We defined the ``_parse_input`` method to instruct the ``Brain`` on what kind of "objectid" to expect, in this case
a "plateifu" id designation, which is 4-5 digit plate id and and 3-5 digit IFU bundle number.  Now we can
directly input a "plateifu" as input.  If we specified a database to use during class
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

.. _decorators:

Decorators
^^^^^^^^^^

A few class decorators are provided as a convenience to help reduce boilerplate code when
creating new classes from the ``Brain``.  Available class decorators are:

- `~sdss_brain.helpers.decorators.access_loader`: decorator to aid in defining `_set_access_path_params`
- `~sdss_brain.helpers.decorators.parser_loader`: decorator to aid in defining `_parse_input`
- `~sdss_brain.helpers.decorators.sdss_loader`: all-purpose loader combining the others

Using the ``sdss_loader`` decorator, we can rewrite the above example as
::

    @sdss_loader(name='mangacube', defaults={'wave':'LOG'}, mapped_version='manga:drpver', pattern=r'(?P<plate>\d{4,5})-(?P<ifu>\d{3,5})')
    class MangaCube(Brain):
        _db = mangadb

        def _load_object_from_file(self, data=None):
            pass

        def _load_object_from_db(self, data=None):
            pass

        def _load_object_from_api(self, data=None):
            pass

which effectively converts to the following:
::

    class MangaCube(Brain):
        _db = mangadb
        mapped_version = 'manga'
        path_name = 'mangacube'

        @property
        def drpver(self):
            return get_mapped_version(self.mapped_version, release=self.release, key='drpver')

        def _set_access_path_params(self):
            ''' set sdss_access parameters '''

            keys = self.access.lookup_keys(self.path_name)
            self.path_params = {k: getattr(self, k) for k in keys}

        def _parse_input(self, value):
            ''' parse the input value string into a filename or objectid '''

            keys = self.access.lookup_keys(self.path_name)
            data = parse_data_input(value, regex=pattern, keys=keys)
            return data

with the following automatically added attributes, extracted from the parsed input and the
sdss_access template keys:
::

    self.plate - the extacted plate ID
    self.ifu - the extract IFU bundle designation
    self.wave - the default sdss_access key value set to "LOG"
    self.parsed_group - a list of all matched group parameters extracted from the regex parsing function

The ``sdss_loader`` decorator is equivalent to stacking multiple decorators, for example
::

    @access_loader(name='mangacube', defaults={'wave':'LOG'}, mapped_version='manga:drpver')
    @parser_loader(pattern=r'(?P<plate>\d{4,5})-(?P<ifu>\d{3,5})')
    class MangaCube(Brain):
        _db = mangadb

        def _load_object_from_file(self, data=None):
            self.data = load_fits_file(self.filename)

        def _load_object_from_db(self, data=None):
            pass

        def _load_object_from_api(self, data=None):
            pass

.. _regex:

Regex Pattern Parser
^^^^^^^^^^^^^^^^^^^^

To simplify the boilerplate code needed to determine the propert data input and parse an object identifier
within the ``_parse_input`` method, there is a convenience function, `~sdss_brain.helpers.parsing.parse_data_input`
which will attempt to determine the type of input and parse it using :doc:`regex <python:library/re>`.
It minimally returns a dictionary with keys ``filename`` and ``objectid``.  If the objectid can be further
parsed to extract named parameters, it will include those parameters as key-values in the dictionary.

::

    >>> # passing a filename to the parser
    >>> parse_data_input('/path/to/a/file.txt')
        {'filename': '/path/to/a/file.txt', 'objectid': None, 'parsed_groups': None}

    >>> # passing a custom regex pattern to parse an object id
    >>> parse_data_input('8485-1901', regex=r'(?P<plate>\d{4,5})-(?P<ifu>\d{3,5})')
        {'filename': None, 'objectid': '8485-1901', 'plate': '8485', 'ifu': '1901', 'parsed_groups': ['8485-1901', '8485', '1901']}

To read more, see :ref:`parsing`.