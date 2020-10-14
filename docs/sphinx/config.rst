

.. _config:

Global Config
-------------

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

Only valid releases are allowed when setting a new release.  Allowed releases are those returned by the
SDSS `tree` package, using the ``get_available_releases`` method.  Valid releases are typically any public
data releases (DRs) or official survey-specific internal releases, e.g interal MaNGA Product Launches (MPLs).

Additionally, setting the release to ``work`` allows ``sdss_brain`` and ``sdss_access`` to access files not yet
within a release, specified in the current ``sdsswork.cfg`` Tree environment configuration.

To set a new release:
::

    from sdss_brain.config import config
    config.set_release('DR14')

You can set a default release to use when loading ``sdss_brain`` by setting the `default_release` config
parameter in your custom `~/.config/sdss/sdss_brain.yml` file.  For example, setting `default_release: DR15`
will instruct the ``sdss_brain`` to load release DR15 on startup.







