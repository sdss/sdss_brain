# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: io.py
# Project: helpers
# Author: Brian Cherinka
# Created: Wednesday, 7th October 2020 10:54:12 am
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Wednesday, 7th October 2020 10:54:12 am
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import
import pathlib
import gzip
from typing import Union
from astropy.io import fits
from sdss_brain import log
from sdss_brain.api.client import SDSSClient
from sdss_brain.config import config
from sdss_brain.exceptions import BrainError


def get_mapped_version(name: str, release: str = None, key: str = None) -> Union[dict, str]:
    ''' Get a version id mapped to a release number

    For a given named category, looks up the "mapped_versions" attribute from
    the configuration yaml file and returns a version number that has been mapped
    to a specific release. For example, for manga, DR16 maps to drpver='v2_4_3'
    and dapver='2.2.1'. This can be useful when needing to specify certain versions
    when defining paths to files.

    Parameters
    ----------
        name : str
            The name of the set of versions to access
        release : str
            The SDSS release.  Default is config.release.
        key : str
            Optional name of dictionary key to access specific value

    Returns
    -------
        version : dict|str
            A version number corresponding to a given release

    Example
    -------
        >>> # access the MaNGA versions for release DR16
        >>> get_mapped_version('manga', release='DR16')
            {'drpver': 'v2_4_3', 'dapver': '2.2.1'}

        >>> # access specific key
        >>> get_mapped_version('manga', release='DR16', key='drpver')
            'v2_4_3'
    '''
    # if release is a work release, return nothing
    if release.lower() == 'work':
        return None

    # get the mapped_versions attribute from the configuration
    mapped_versions = config._custom_config.get('mapped_versions', None)
    assert mapped_versions, 'mapped_versions must be defined'
    if type(mapped_versions) != dict:
        raise TypeError('mapped_versions must be a dictionary')

    # ensure that the name is a valid entry
    if name not in mapped_versions:
        raise ValueError(f'{name} not found in mapped_versions dictionary')

    versions = mapped_versions.get(name, None)
    if type(versions) != dict:
        raise TypeError(f'release versions for {name} must be a dictionary')

    # ensure that the release is a valid entry
    release = release or config.release
    version = versions.get(release, None)
    if not version:
        raise ValueError(f'no mapped_version found for release {release} in {name}. '
                         'Check the sdss_brain.yml config file.')

    # check for a specific key in the version dictionary
    if key and type(version) == dict:
        version = version.get(key, None)

    return version


def load_fits_file(filename: str) -> fits.HDUList:
    ''' Load a FITS file

    Opens and loads a FITS file with astropy.io.fits.

    Parameters
    ----------
        filename : str
            A FITS filen to open

    Returns
    -------
        hdulist : `~astropy.io.fits.HDUList`
            an Astropy HDUList
    '''

    path = pathlib.Path(filename)
    if not path.exists() and path.is_file():
        raise FileNotFoundError('input filename must exist and be a file')

    assert '.fits' in path.suffixes, 'filename is not a valid FITS file'

    try:
        hdulist = fits.open(path)
    except (IOError, OSError) as err:
        log.error(f'Cannot open FITS file {filename}: {err}')
        raise BrainError(f'Failed to open FITS files {filename}: {err}') from err
    else:
        return hdulist


def load_from_url(url: str, no_progress: bool = None) -> fits.HDUList:
    ''' Load a file from a remote url using a get request

    Streams url content with httpx.stream and pipes the response contents
    into an Astropy FITS file.

    Parameters
    ----------
        url : str
            A url path to a filename
        no_progress : bool
            If True, turns off the tqdm progress bar

    Returns
    -------
        an Astropy `~astropy.io.fits.HDUList`
    '''
    with SDSSClient(url, no_progress=no_progress) as client:
        client.request(method='stream')
        if url.endswith('.gz'):
            return fits.open(gzip.open(client.data, 'rb'))
        else:
            return fits.open(client.data)
