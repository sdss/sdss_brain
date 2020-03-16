
.. _version:

Mapping Versions to Data Releases
---------------------------------

Paths to data products often contain a version number either in the directory path or filename itself.  These 
version numbers may be tagged pipeline reduction versions, or software post-processing versions.  Eventually these 
files are frozen and released in a public Data Release (DR) or in a survey-specific internal product launch, 
e.g MaNGA's MPLs.  It may be necessary to map these specific version numbers to release numbers so that tools
like ``sdss_access`` can understand where to look for files given a specific overall data release.  ``sdss_brain``
provides a method for doing so.

Creating a Mapping
^^^^^^^^^^^^^^^^^^

To create a mapping, we use the ``mapped_versions`` parameter in the `sdss_brain.yml` configuration file, which
is a dictionary of parameters read in by ``sdss_brain``.  Each key in ``mapped_versions`` is a survey or category
keyword, e.g. "manga" or "eboss", to differentiate between surveys.  Within each category is another dictionary 
containing (key,value) pairs of (release ID, version number).  For example:
::

    mapped_versions:
      manga:
        DR16: {drpver: v2_4_3, dapver: 2.2.1}  
        DR15: {drpver: v2_4_3, dapver: 2.2.1}  
        DR14: {drpver: v2_1_2, dapver: null}  
        DR13: {drpver: v1_5_4, dapver: null}  
        MPL9: {drpver: v2_7_1, dapver: 2.4.1}  
        MPL8: {drpver: v2_5_3, dapver: 2.3.0}  
        MPL7: {drpver: v2_4_3, dapver: 2.2.1}  
        MPL6: {drpver: v2_3_1, dapver: 2.1.3}  
        MPL5: {drpver: v2_0_1, dapver: 2.0.2}  
        MPL4: {drpver: v1_5_1, dapver: 1.1.1}
      eboss:
        DR16: v5_13_0
        DR15: v5_10_0

The value specified for each key can be arbitrarily simple or complex.  Here we specify that for 
EBOSS, `DR16` maps to a single version number `v5_13_0`.  However, MaNGA has more complex versioning due to 
multiple pipelines processing the data.  Here we map each release id to a dictionary of values containing both 
the DRP and DAP pipeline version numbers, e.g. the `DR15` data release maps to the DRP version `v2_4_3` 
and DAP version `2.2.1`.

Accessing a Mapping
^^^^^^^^^^^^^^^^^^^
To access a mapping you can use the ``get_mapped_version``  helper function.  It accepts as input the category 
name, and a release to lookup.
::

    >>> # access a manga mapping for DR16
    >>> from sdss_brain.helpers import get_mapped_version
    >>> get_mapped_version('manga', release='DR16')
    >>> {'drpver': 'v2_4_3', 'dapver': '2.2.1'}

It optionally accepts a ``key`` input to extract individual items from dictionaries.
::

    >>> # access only the manga DRP version mapping for DR16
    >>> from sdss_brain.helpers import get_mapped_version
    >>> get_mapped_version('manga', release='DR16', key='drpver')
    >>> 'v2_4_3'

Using a Mapping
^^^^^^^^^^^^^^^

As mentioned, the utility of this is to extract version numbers needed by ``sdss_access`` given a single release.
Consider a defined class for MaNGA datacubes:
::

    from sdss_brain.core import Brain
    from sdssdb.sqlalchemy.mangadb import database
    from sdss_brain.helpers import get_mapped_version


    class Cube(Brain):
        _db = database
        mapped_version = 'manga'

        def _parse_input(self, value):
            plateifu_pattern = re.compile(r'([0-9]{4,5})-([0-9]{4,9})')
            plateifu_match = re.match(plateifu_pattern, value)
            if plateifu_match is not None:
                self.objectid = value
                self.plateifu = plateifu_match.group(0)
                self.plate, self.ifu = plateifu_match.groups(0)
            else:
                self.filename = value

        def _set_access_path_params(self):
            self.path_name = 'mangacube'
            drpver = get_mapped_version(self.mapped_version, release=self.release, key='drpver')
            self.path_params = {'plate': self.plate, 'ifu': self.ifu, 'drpver': drpver}

We specify the ``mapped_version`` class attribute as **manga**.  Inside the ``_set_access_path_params`` method
we use ``get_mapped_version`` to access the DRP version for the given release of the Cube.  Now as we load
different cubes of different releases, the correct versions and paths are updated.
::

    >>> # load a cube for DR16
    >>> cube = Cube('8485-1901', release='DR16')
    >>> cube.get_full_path()
    '/Users/Brian/Work/sdss/sas/dr16/manga/spectro/redux/v2_4_3/8485/stack/manga-8485-1901-LOGCUBE.fits.gz'

    >>> # load a cube for DR13
    >>> cube = Cube('8485-1901', release='DR13')
    >>> cube.get_full_path()
    '/Users/Brian/Work/sdss/sas/dr13/manga/spectro/redux/v1_5_4/8485/stack/manga-8485-1901-LOGCUBE.fits.gz'
