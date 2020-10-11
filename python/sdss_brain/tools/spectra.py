# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: spectra.py
# Project: tools
# Author: Brian Cherinka
# Created: Sunday, 11th October 2020 3:15:12 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Sunday, 11th October 2020 3:15:12 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None
from astropy.io.registry import IORegistryError
from specutils import Spectrum1D

from sdss_brain import log
from sdss_brain.core import Brain
from sdss_brain.exceptions import BrainNotImplemented, BrainMissingDependency
from sdss_brain.helpers import sdss_loader, get_mapped_version, load_fits_file, parse_data_input


class Spectrum(Brain):
    ''' Base class for working with spectral data using specutils

    Uses `specutils <https://specutils.readthedocs.io/en/stable/>`_ to load the
    underlying spectral data into an Astropy Spectrum1D object, which is represented as an
    nd-data array object.

    Attributes
    ----------
        spectrum : `~specutils.Spectrum1D`
            An Astropy specutils Spectrum1D object
    '''
    spectrum: str = None
    specutils_format: str = None

    def _load_object_from_file(self, data=None):
        self.data = data or load_fits_file(self.filename)
        self.header = self.data['PRIMARY'].header
        try:
            self.spectrum = Spectrum1D.read(str(self.filename), format=self.specutils_format)
        except IORegistryError:
            log.warning('Could not load Spectrum1D for format '
                        f'{self.specutils_format}, {self.filename}')

    def _load_object_from_db(self, data=None):
        raise BrainNotImplemented('This method must be implemented by the user')

    def _load_object_from_api(self, data=None):
        pass
        #raise BrainNotImplemented('loading data from API not yet implemented')

    def plot(self, **kwargs):
        ''' A simple quick matplotlib plot of the spectrum'''
        if not self.spectrum:
            return

        if not plt:
            raise BrainMissingDependency("Package matplotlib not installed.")

        __, ax = plt.subplots()
        ax.plot(self.spectrum.wavelength, self.spectrum.flux, **kwargs)
        return ax


# example of using a custom pattern in the sdss_loader
@sdss_loader(name='spec-lite', mapped_version='eboss:run2d',
             pattern=r'(?P<plateid>\d{4,5})-(?P<mjd>\d{5})-(?P<fiberid>\d{1,4})')
class Eboss(Spectrum):
    """ Class representing a single fiber SDSS spectra from BOSS/EBOSS

    Parameters
    ----------
        lite : bool
            If True, loads the "spec-lite" spectral data.  When False, loads
            the "full" spectral data.Default is True.
    """
    specutils_format: str = 'SDSS-III/IV spec'

    def __init__(self, *args: str, lite: bool = True, **kwargs: str) -> None:
        self.lite = lite
        self.path_name = f'spec{"-lite" if lite else ""}'
        super(Eboss, self).__init__(*args, **kwargs)

    def __repr__(self):
        old = super(Eboss, self).__repr__()
        return old.replace('>', f', lite={self.lite}>')


# example of using a access keys to define the pattern in the sdss_loader
# setting a custom delimiter to "--" since APOGEE field names can have "-" in them.
@sdss_loader(name='apStar', defaults={'apstar': 'stars', 'prefix': 'ap'}, delimiter='--',
             mapped_version='apogee:apred', order=['telescope', 'field', 'obj'])
class ApStar(Spectrum):
    """ Class representing an APOGEE combined spectrum for a single star """
    specutils_format: str = 'APOGEE apStar'


@sdss_loader(name='apVisit', defaults={'prefix': 'ap'}, delimiter='--',
             mapped_version='apogee:apred', order=['telescope', 'field', 'plate', 'mjd', 'fiber'])
class ApVisit(Spectrum):
    """ Class representing an APOGEE single visit spectrum for a given star """
    specutils_format: str = 'APOGEE apVisit'


# example of overloading the methods manually
class AspcapStar(Spectrum):
    """ Class representing an APOGEE spectrum for a single star with ASPCAP results """
    specutils_format: str = 'APOGEE aspcapStar'
    path_name: str = 'aspcapStar'
    mapped_version: str = 'apogee'

    def _parse_input(self, value):
        # use the sdss_access keys to form the object id and parse it
        keys = self.access.lookup_keys(self.path_name)
        data = parse_data_input(value, keys=keys, delimiter='--',
                                order=['aspcap', 'telescope', 'field', 'obj'], )
        return data

    def _set_access_path_params(self):
        # extract the apred version id based on the data release
        apred = get_mapped_version(self.mapped_version, release=self.release)

        # set the path params using the instance attributes extracted from _parse_input
        self.path_params = {'telescope': self.telescope, 'apred': apred,
                            'field': self.field, 'obj': self.objectid, 'aspcap': self.aspcap}
