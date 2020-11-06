
.. _work:

Setting Work Versions
---------------------

``sdss_brain`` can work with data files not yet explicitly released in a public or internal data release
by using what are called "work" versions, attached to a "work" release.  "Work" versions are survey
specific version numbers needed to identify file paths typically listed under the SAS "sdsswork" directory
or module, or the equivalent survey-specific work directories, e.g. "ebosswork", "apogeework", "mangawork".
For example, work versions might be `run2d = v5_10_0` for EBOSS data, `apred = r12` for APOGEE data,
or `drpver = v2_4_3, dapver = 2.2.1` for MaNGA data.

Defining Work Versions
^^^^^^^^^^^^^^^^^^^^^^

Specifying ``release="WORK"`` and these versions tells the ``Brain`` which files to look for when
operating under a work directory.  Work versions take a dictionary format with ``key:value`` set to the
``version_name:version_number``, where ``version_name`` is a valid version name normally as specified by
the ``sdss_access`` path template keyword argument.  ``version_number`` is a valid version number.  There
are several ways to set valid work versions.

By the config class:
::

    >>> # set the new work versions
    >>> from sdss_brain.config import config
    >>> config.set_work_versions({'drpver': 'v2_4_3', 'run2d': 'v5_10_0', 'apred': 'r12'})

or by using the configuration file to set them permanently.  See :ref:`config_file` for an example of how
to set the work versions.  You can also do so individually on a tool.
::

    >>> from sdss_brain.tools import Eboss
    >>> e=Eboss('3606-55182-0537', version={'run2d': 'v5_10_0'})

Version Order Precedence
^^^^^^^^^^^^^^^^^^^^^^^^

The order of precendence the ``Brain`` uses when deciding which work versions to use in a given tool is
**tool > setting the config > using the custom config file**.  Specifying versions explicitly on a
tool takes precedence over using the config `~sdss_brain.config.Config.set_work_versions` method which takes
precedence over any values found in the custom ``sdss_brain.yml`` configuration file.


Setting the Work Release
^^^^^^^^^^^^^^^^^^^^^^^^

Additionally to "work" versions, the global, or tool, ``release`` attribute must be set to **"WORK"** rather
than a data release ID.  You can set the work release globally.
::

    >>> from sdss_brain.config
    >>> config.set_release('work')

Or individually on each tools.
::

    >>> from sdss_brain.tools import Eboss
    >>> e=Eboss('3606-55182-0537', release='WORK')

Example Access of "Work" Data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Here is an example highlighting how to access different work versions for an EBOSS ``spec-lite`` file.  First
we set our default work versions using the config class, and set our release to "work".
::

    >>> # set the new work versions
    >>> from sdss_brain.config import config
    >>> config.set_work_versions({'drpver': 'v2_4_3', 'run2d': 'v5_10_0', 'apred': 'r12'})
    >>> config.work_versions
    {'drpver': 'v2_4_3', 'dapver': '2.2.1', 'apred': 'r12', 'run2d': 'v5_10_0'}

    >>> # set the global release
    config.set_release("work")

Now we import the `~sdss_brain.tools.spectra.Eboss` spectrum tool, and load some data.  We can see the full
file path is set to use the ``ebosswork`` directory, with ``run2d`` version set to `v5_10_0`.
::

    >>> from sdss_brain.tools import Eboss
    >>> e = Eboss('3606-55182-0537')
    >>> e
    <Eboss objectid='3606-55182-0537', mode='local', data_origin='file', lite=True>

    >>> # check the filename path
    >>> e.get_full_path()
    '/Users/Brian/Work/sdss/sas/ebosswork/eboss/spectro/redux/v5_10_0/spectra/lite/3606/spec-3606-55182-0537.fits'

    >>> # check the version number
    >>> e.run2d
    'v5_10_0'

We can explicitly change the work version accessed by specifying the ``version`` keyword as input.  This lets
us load a different work file without changing the default work version set. Let's load the same file but for
`run2d = v5_13_0`.
::

    >>> from sdss_brain.tools import Eboss
    >>> e = Eboss('3606-55182-0537', version={'run2d': 'v5_13_0')
    >>> e
    <Eboss objectid='3606-55182-0537', mode='remote', data_origin='api', lite=True>

    >>> # check the filename path
    >>> e.get_full_path()
    '/Users/Brian/Work/sdss/sas/ebosswork/eboss/spectro/redux/v5_13_0/spectra/lite/3606/spec-3606-55182-0537.fits'

    >>> # check the version number
    >>> e.run2d
    'v5_13_0'

.. note::
    Even though the object is instantiated in "remote" mode with ``data_origin`` set to API, you can still
    construct a valid file path using `get_full_path` which uses ``sdss_access`` under the hood which
    specifies what would the file location be.  Checking ``e.filename`` in the above will verify that the
    file does not actually exist locally.  You can always download the file with ``e.download()``.

Work Authentication
^^^^^^^^^^^^^^^^^^^

Accessing unreleased "work" data requires proper SDSS authentication.  For remote access with ``sdss_access``,
``requests``, ``httpx`` or any HTTP request library, this uses the ``~/.netrc`` file.  Any attempt to access
data without a properly set ``.netrc`` file will result in an error.
::

    >>> from sdss_brain.tools import Eboss
    >>> e = Eboss('3606-55182-0537', version={'run2d': 'v5_13_0')
    HTTPStatusError: 401 Client Error: Unauthorized for url: https://data.sdss.org/sas/ebosswork/eboss/spectro/redux/v5_13_0/spectra/lite/3606/spec-3606-55182-0537.fits
    For more information check: https://httpstatuses.com/401

See :ref:`netrc` for how to set up a ``.netrc`` file for authentication to access proprietary SDSS data content.

