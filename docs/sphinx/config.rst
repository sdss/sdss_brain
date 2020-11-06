

.. _config:

About the Global Config
-----------------------

``sdss_brain`` includes a global configuration class, ``Config``, which handles parameters used globally
by ``sdss_brain`` and potentially other SDSS packages.

General custom configuration can be accomplished using the `sdss_brain.yml` YAML configuration file.  This file
can also be used to set custom user choices.  See the `sdsstools config <https://github.com/sdss/sdsstools#configuration>`_
or the `Python template config <https://sdss-python-template.readthedocs.io/en/python-template-v2/#configuration-file-and-logging>`_
for more details on the custom configuration file.The ``Config`` class reads in this file and updates any
overlapping parameters with user values.  This way you can set a custom SDSS configuration only once.

The ``Config`` class contains the following attributes:

- **mode**: the MMA mode to operate in
- **release**: the data release to use
- **download**: If True, downloads any files accessed with `sdss_access`
- **ignore_db**: If True, ignores any database connections used with ``Brain``-based tools
- **work_versions**: defines the specified versions to use when accessing "sdsswork" files

Only valid releases are allowed when setting a new release.  Allowed releases are those returned by the
SDSS `tree` package, using the ``get_available_releases`` method.  Valid releases are typically any public
data releases (DRs) or official survey-specific internal releases, e.g interal MaNGA Product Launches (MPLs).

Additionally, setting the release to ``work`` allows ``sdss_brain`` and ``sdss_access`` to access files not yet
within a release, specified in the current ``sdsswork.cfg`` Tree environment configuration.

To set a new global release:
::

    from sdss_brain.config import config
    config.set_release('DR14')

To set global "working" versions:
::

    # set the new work versions
    from sdss_brain.config import config
    config.set_work_versions({'drpver': 'v2_4_3', 'run2d': 'v5_10_0', 'apred': 'r12'})

    # access the set work versions
    config.work_versions

To set a new global user for remote data access:
::

    # set a new global user
    config.set_user('sdss')

To set a global API to use for remote data access:
::

    # set the new global API as the MaNGA marvin API.
    config.set_api('marvin')

Note that most APIs do not allow data access to all types of SDSS data.  APIs are often data specific.  In cases where you
know you only want to work with a certain type of data, which has an available API for remote access, you can set it globally
in your Python session with this config.


.. _config_file:

The Custom Config File
----------------------

To customize the configuration for the ``Brain``, you can create a new YAML config file at
`~/.config/sdss/sdss_brain.yml`.  This config file allows you to set custom configuration options that
are loaded when the ``Brain`` config is instantiated.  The following entries are available:

- **ignore_db**: If True, ignores any database connections used with ``Brain``-based tools
- **download**: If True, downloads any data files accessed with `sdss_access`
- **default_release**: Sets the default data release to use
- **work_versions**: Sets the specified versions to use when accessing "sdsswork" files
- **netrc_path**: The path to a local ``.netrc`` file
- **default_api**: The name of the default API to use
- **default_username**: The name of the default SDSS user
- **default_password**: The password for the SDSS user

The following example config file instructs the ``Brain`` to always ignore database connections, to not
download data files by default, to use DR15 as the default release, and to set the work versions for
MaNGA, APOGEE, and EBOSS data to (v2_4_3, 2.2.1), r12, and v5_10_0, respectively.

.. code-block:: yaml

    ignore_db: True
    download: False
    default_release: DR15
    work_versions:
      drpver: v2_4_3
      dapver: 2.2.1
      apred: r12
      run2d: v5_10_0







