
.. _version:

Mapping Versions to Data Releases
---------------------------------

Paths to data products often contain a version number either in the directory path or filename itself.  These
version numbers may be tagged pipeline reduction versions, or software post-processing versions.  Eventually these
files are frozen and released in a public Data Release (DR) or in a survey-specific internal product launch, e.g.
IPLs or MaNGA's MPLs.  It may be necessary to map these specific version numbers to release numbers so that tools
like ``sdss_access`` can understand where to look for files given a specific overall data release.  ``sdss_brain``
provides a method for doing so.

Version Metadata
^^^^^^^^^^^^^^^^

The metadata describing the various software version names and tags associated for each SDSS data release is
handled by the SDSS datamodel product.  ``sdss_brain`` contains convenience methods for accessing version
metadata either from a local copy of the ``datamodel`` product, or remotely via the SDSS valis API.  To
retrieve all the version metadata, use the `~.sdss_brain.datamodel.versions.get_versions` function.

::

    >>> from sdss_brain.datamodel import get_versions
    >>> vers = get_versions()
    {'IPL1': {'apred_vers': '1.0', 'v_astra': '0.2.6', 'run2d': 'v6_0_9', 'run1d': 'v6_0_9'},
     'DR18': {'run2d': 'v6_0_4', 'run1d': 'v6_0_4', 'v_speccomp': 'v1.4.3', 'v_targ': '1.0.1'},
     'DR17': {'run2d': 'v5_13_2', 'apred_vers': 'dr17', 'apstar_vers': 'stars', 'aspcap_vers': 'synspec_rev1',
              'results_vers': 'synspec_rev1', 'run1d': 'v5_13_2', 'drpver': 'v3_1_1', 'dapver': '3.1.0'},
    ...}


Accessing a Mapping
^^^^^^^^^^^^^^^^^^^
To access a mapping you can use the ``get_mapped_version``  helper function.  It accepts as input the version
reference name, and a release to lookup.  If no version name is specified, it returns the entire mapping
for the given release.
::

    >>> # access the entire version mapping for DR16
    >>> from sdss_brain.datamodel import get_mapped_version
    >>> get_mapped_version(release='DR16')
    {'run2d': 'v5_13_0', 'apred_vers': 'r12', 'apstar_vers': 'stars', 'aspcap_vers': 'l33',
    'results_vers': 'l33', 'run1d': 'v5_13_0', 'drpver': 'v2_4_3', 'dapver': '2.2.1'}

Specifiy a version reference name to extract only the individual item from the dictionary.
::

    >>> # access only the manga DRP version mapping for DR16
    >>> from sdss_brain.datamodel import get_mapped_version
    >>> get_mapped_version('drpver', release='DR16')
    'v2_4_3'

Using a Mapping
^^^^^^^^^^^^^^^

As mentioned, the utility of this is to extract version numbers needed by ``sdss_access`` given a single release.
Consider a defined class for MaNGA datacubes:
::

    from sdss_brain.core import Brain
    from sdssdb.sqlalchemy.mangadb import database
    from sdss_brain.datamodel import get_mapped_version


    class Cube(Brain):
        _db = database
        path_name = 'mangacube'

        def _parse_input(self, value):
            plateifu_pattern = re.compile(r'([0-9]{4,5})-([0-9]{4,9})')
            plateifu_match = re.match(plateifu_pattern, value)

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

        def _set_access_path_params(self):
            drpver = get_mapped_version("drpver", release=self.release)
            self.path_params = {'plate': self.plate, 'ifu': self.ifu, 'drpver': drpver}

Inside the ``_set_access_path_params`` method we use ``get_mapped_version`` to access the
DRP version for the given release of the Cube.  Now as we load different cubes of different
releases, the correct versions and paths are updated.
::

    >>> # load a cube for DR16
    >>> cube = Cube('8485-1901', release='DR16')
    >>> cube.get_full_path()
    '/Users/Brian/Work/sdss/sas/dr16/manga/spectro/redux/v2_4_3/8485/stack/manga-8485-1901-LOGCUBE.fits.gz'

    >>> # load a cube for DR13
    >>> cube = Cube('8485-1901', release='DR13')
    >>> cube.get_full_path()
    '/Users/Brian/Work/sdss/sas/dr13/manga/spectro/redux/v1_5_4/8485/stack/manga-8485-1901-LOGCUBE.fits.gz'


Version Name Differences
^^^^^^^^^^^^^^^^^^^^^^^^

Sometimes the version name specified in an ``sdss_access`` path template and in a datamodel can be different.
This can happen with to the longetivity of SDSS, a lack of standards around naming conventions, and multiple
people contributing to the same project/code.  For example, a version name could be ``drpver`` in
the datamodel, but ``drp_ver`` or ``ver_drp`` or ``drpvers`` in various ``sdss_access`` path templates
describing data products.  A real example is the version of the APOGEE pipeline is often referenced as
``apred`` in older path templates, but ``apred_vers`` in the datamodel and in newer path templates.

To accommodate these differences, aliases can be defined using the ``version_aliases`` parameter in the
`sdss_brain.yml` configuration file, which is a dictionary of parameters read in by ``sdss_brain``.  Each
key in ``version_aliases`` is a mapping between a version alias and the true datamodel version name.  Using
the above example, the entry in the config file would like that
::

    version_aliases:
      drp_ver: drpver
      ver_drp: drpver
      drpvers: drpver
      apred: apred_vers
