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
from astropy.io import fits
from sdss_brain import log
from sdss_brain.api.client import SDSSClient
from sdss_brain.exceptions import BrainError


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
