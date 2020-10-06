# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: helpers.py
# Project: sdss_brain
# Author: Brian Cherinka
# Created: Monday, 16th March 2020 1:00:14 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Monday, 16th March 2020 5:29:39 pm
# Modified By: Brian Cherinka


from __future__ import absolute_import, division, print_function

import re
import pathlib
from astropy.io import fits
from sdss_brain import log
from sdss_brain.config import config
from sdss_brain.exceptions import BrainError


def get_mapped_version(name, release=None, key=None):
    ''' Get a version id mapped to a release number

    For a given named category, looks up the "mapped_versions" attribute from
    the configuration yaml file and returns a version number that has been mapped
    to a specific release. For example, for manga, DR16 maps to drpver='v2_4_3'
    and dapver='2.2.1'. This can be useful when needing to specify certain versions
    when defining paths to files.

    Parameters:
        name (str):
            The name of the set of versions to access
        release (str):
            The SDSS release.  Default is config.release.
        key (str):
            Optional name of dictionary key to access specific value

    Example:
        >>> # access the MaNGA versions for release DR16
        >>> get_mapped_version('manga', release='DR16')
        >>> {'drpver': 'v2_4_3', 'dapver': '2.2.1'}
        >>>
        >>> # access specific key
        >>> get_mapped_version('manga', release='DR16', key='drpver')
        >>> 'v2_4_3'
    '''

    # get the mapped_versions attribute from the configuration
    mapped_versions = config._custom_config.get('mapped_versions', None)
    assert mapped_versions, 'mapped_versions must be defined'
    assert type(mapped_versions) == dict, 'mapped_versions must be a dictionary'

    # ensure that the name is a valid entry
    assert name is not None, 'a valid name must be specified'
    assert name in mapped_versions, f'{name} not found in mapped_versions dictionary'
    versions = mapped_versions.get(name, None)
    assert type(versions) == dict, f'release versions for {name} must be a dictionary'

    # ensure that the release is a valid entry
    release = release or config.release
    assert release in versions, f'release {release} not found in list of {name} versions'
    version = versions.get(release, None)
    if not version:
        raise BrainError(f'no version found for release {release} in {name}')

    # check for a specific key in the version dictionary
    if key:
        assert type(version) == dict, f'version must be a dictionary to access a key,value pair'
        assert key in version, f'key {key} not found in version'
        version = version.get(key, None)

    return version


def load_fits_file(filename):
    ''' Load a FITS file

    Opens and loads a FITS file with astropy.io.fits.

    Parameters:
        filename (str):
            A FITS filen to open

    Returns:
        an Astropy HDUList
    '''

    path = pathlib.Path(filename)
    assert path.exists() and path.is_file(), 'input filename must exist and be a file'

    assert '.fits' in path.suffixes, 'filename is not a valid FITS file'

    try:
        hdulist = fits.open(path)
    except (IOError, OSError) as err:
        log.error(f'Cannot open FITS file {filename}: {err}')
        raise BrainError(f'Failed to open FITS files {filename}: {err}')
    else:
        return hdulist


def create_object_pattern(regex=None, keys=None, delimiter='-', exclude=None, include=None,
                          order=None):
    """ Create a regex pattern to parse data input by

    Parameters
    ----------
        regex : str
            A custom regex pattern
        keys : list
            A list of (access) names to build a pattern out of
        delimiter : str
            The delimiter to use when joining the keys.  Default is "-".
        exclude : list
            A list of names to exclude from the keys
        include : list
            A list of names to only include from the keys
        order : list
            A list of names specifying the order in which create the keyed pattern

    Returns
    -------
        pattern : str
            A regex pattern to use for parsing an objectid
    """

    # use a custom regex pattern
    if regex:
        pattern = rf'(?P<objectid>(?![/$.])({regex}))'
        return pattern

    # if no keys, use a greedy default
    if not keys:
        pattern = r'(?P<objectid>^[^/$.](.+)?)'
        return pattern

    # exclude the named keys
    if exclude:
        keys = list(set(keys) - set(exclude))

    # only include the named keys
    if include or order:
        good = order or include
        keys = list(set(good) & set(keys))

    # order the keys
    if order:
        keys.sort(key=lambda i: order.index(i))

    patts = []
    for k in keys:
        patts.append(fr'(?P<{k}>(.+)?)')

    # join into a single pattern
    pattern = rf'(?P<objectid>(?![/$.])({delimiter.join(patts)}))'

    return pattern


def parse_data_input(value, regex=None, keys=None, delimiter='-', exclude=None, include=None,
                     order=None):
    ''' Parse data input for a filename or an object id

    Parameters
    ----------
        value : str
            The input string to perform a pattern match on
        regex : str
            A custom regex pattern
        keys : list
            A list of (access) names to build a pattern out of
        delimiter : str
            The delimiter to use when joining the keys.  Default is "-".
        exclude : list
            A list of names to exclude from the keys
        include : list
            A list of names to only include from the keys
        order : list
            A list of names specifying the order in which create the keyed pattern


    Returns
    -------
        matches : dict
            A dict with keys "filename", "objectid", and any other matches
    '''

    assert isinstance(value, (str, pathlib.Path)), 'input value must be a str or pathlib.Path'

    # set default file pattern
    file_pattern = r'(?P<filename>^[/$.](.+)?(.[a-z]+))'

    # create an object id regex pattern using a specified pattern or generate a default one
    obj_pattern = create_object_pattern(regex=regex, keys=keys, delimiter=delimiter,
                                        exclude=exclude, include=include,
                                        order=order)

    # final pattern
    pattern = fr'^{file_pattern}|{obj_pattern}$'

    # compile and match the patterm
    comp_pattern = re.compile(pattern)
    pattern_match = re.match(comp_pattern, str(value))

    # if no match, assume value is a filename and return nothing
    if not pattern_match:
        return None

    # check for named group, then any groups, then a match without groups
    matches = pattern_match.groupdict() or pattern_match.groups() or pattern_match.group()
    return matches

