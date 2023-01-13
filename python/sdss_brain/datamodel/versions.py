# !/usr/bin/env python
# -*- coding: utf-8 -*-
#

from collections import ChainMap

from sdss_brain import log
from sdss_brain.config import config
from sdss_brain.exceptions import BrainError
from sdss_brain.api.handler import ApiHandler

try:
    from datamodel.products import SDSSDataModel
except ImportError:
    SDSSDataModel = None


def generate_versions() -> dict:
    """ Get the SDSS data release version tags

    Gets the SDSS datamodel version tags for each release
    remotely using the SDSS valis API.

    Returns
    -------
    dict
        the version tags organized by release
    """
    # create a valis api handler
    a = ApiHandler(('valis', 'info/tags', 'api'))

    # send the request and get the response
    try:
        a.client.request(data={'group':'release'})
    except BrainError as ee:
        log.error(f'Error getting version tags: {ee}')
        return
    else:
        return a.client.data['tags']


def collapse_versions(vers: dict) -> dict:
    """ Collapse the versions dictionary

    Collapse the versions dictionary down one level, removing
    the "survey" key, within each data release.  The result
    is something like {"DR18": {"run2d": "v6_0_4", ...}}.

    Parameters
    ----------
    vers : dict
        the input versions dictionary

    Returns
    -------
    dict
        a collapsed versions dictionary
    """
    return {k: dict(ChainMap(*vers[k].values())) for k in vers}


def get_versions() -> dict:
    """ Get a mapping of SDSS version tags

    Returns a mapping of SDSS software version tags associated
    with each SDSS data release.

    Returns
    -------
    dict
        a release version mapping
    """
    if SDSSDataModel:
        dm = SDSSDataModel()
        vers = dm.tags.group_by('release')
    else:
        vers = generate_versions()
    return collapse_versions(vers)


def get_mapped_version(key: str = None, release: str = None) -> str:
    """ Get a version/tag id mapped to a SDSS release

    For a given SDSS data release, e.g. "DR18", and a version tag
    reference key name, e.g. "run2d", looks up the relevant tag from the SDSS
    datamodel version dictionary.  For example, key "run2d" for release "DR18"
    produces tag "v6_0_4".  Key "drpver" for release "DR16" produces "v2_4_3".
    This is useful when needing to specify certain versions
    when defining paths to files.

    It attempts to match the key name in several ways.  In order of precedence,
    it tries to do an exact key match, then matches several alternate key
    names i.e. "xxx_vers", "xxx_ver".  Finally it attempts to match against
    any version aliases set in the configuration yaml file.

    Parameters
    ----------
    key : str, optional
        the version referece name, by default None
    release : str, optional
        the SDSS data release, by default config.release

    Returns
    -------
    str
        a tag corresponding to a given release and reference version name

    Raises
    ------
    ValueError
        when no release is found in the datamodel versions dict
    TypeError
        when the datamodel versions is not a dict
    TypeError
        when the aliases config object is not a dict
    """

    # if release is a work release, return nothing
    if release.lower() == 'work':
        return None

    versions = get_versions()

    # ensure that the release is a valid entry
    release = release or config.release
    version = versions.get(release, None)
    if not version:
        raise ValueError(f'no version info found for release {release}.')

    # check that the version info is a valid dict
    if not isinstance(version, dict):
        raise TypeError(f'version info for release {release} is not a valid dict.')

    # if no key specified, return the entire dict
    if not key:
        return version

    # check for a specific key in the version dictionary
    # original key
    if ver := version.get(key, None):
        return ver

    # check for alternate keys of "xxx_vers", "xxx_ver", "xxxver", "xxxvers"
    alts = ['_vers', '_ver', 'ver', 'vers']
    for alt in alts:
        if ver := version.get(f'{key}{alt}', None):
            return ver

    # get the version_aliases attribute from the configuration
    aliases = config._custom_config.get('version_aliases', None)
    if not aliases:
        return

    # check if aliases is a dict
    if not isinstance(aliases, dict):
        raise TypeError('version_aliases must be a dictionary')

    # check for any defined version aliases
    if ver := version.get(aliases.get(key), None):
        return ver
