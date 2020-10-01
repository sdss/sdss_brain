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

import pathlib
import re
import six
import requests
from io import BytesIO
from astropy.io import fits
from sdss_brain import log
from sdss_brain.config import config
from sdss_brain.exceptions import BrainError


def get_mapped_version(name: str, release: str = None, key: str = None) -> str:
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


def load_fits_file(filename: str) -> fits.HDUList:
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


def load_from_url(url: str) -> fits.HDUList:
    ''' load a file from a remote url using a get requests

    Performs a request.get to a given url and streams response contents
    into an Astropy hdu.

    Parameters:
        url (str):
            A url path to a filename

    Returns:
        an Astropy HDUList
    '''
    r = requests.get(url)
    if not r.ok:
        msg = f'Could not retrive file: {url}'
        log.error(msg)
        raise BrainError(msg)

    return fits.open(BytesIO(r.content))


def parse_by_regex_pattern(pattern: str, value: str, obj: object = None):
    ''' parse an input value by a regex pattern

    Matches a given string value against a regex pattern.

    Parameters:
        pattern (str):
            A regex pattern to match with
        value (str):
            The string value to match on
        obj (instance):
            Optional object to assign matched attributes to

    Returns:


    '''
    assert isinstance(pattern, six.string_types), 'pattern must be a string'
    comp_pattern = re.compile(pattern)
    pattern_match = re.match(comp_pattern, value)

    # if no object given:
    if not obj:
        if not pattern_match:
            return value
        else:
            # return the named group first or the groups second
            return pattern_match.groupdict() or pattern_match.groups()

    if not pattern_match:
        obj.filename = value
        return value
    else:
        # check for a named match
        match_dict = pattern_match.groupdict()
        if match_dict:
            for name, val in match_dict.items():
                setattr(obj, name, val)
            return match_dict
        else:
            log.warning('Pattern match is not a named group. Cannot set object attributes. '
                        'Returning only values')
            return pattern_match.groups()
