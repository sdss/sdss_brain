# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: tools.py
# Project: sdss_brain
# Author: Brian Cherinka
# Created: Tuesday, 14th April 2020 2:51:34 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Tuesday, 14th April 2020 2:51:34 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import
import matplotlib.pyplot as plt
from astropy.io.registry import IORegistryError
from specutils import Spectrum1D

from sdss_brain import log
from sdss_brain.core import Brain
from sdss_brain.exceptions import BrainNotImplemented
from sdss_brain.helpers import sdss_loader, get_mapped_version, load_fits_file, parse_data_input


class Spectrum(Brain):
    ''' Class for working with spectral data '''

    def _load_object_from_file(self, data=None):
        self.data = data or load_fits_file(self.filename)
        self.header = self.data['PRIMARY'].header
        try:
            self.spectrum = Spectrum1D.read(str(self.filename), format=self.specutils_format)
        except IORegistryError:
            log.warning('Could not load Spectrum1D for format '
                        f'{self.specutils_format}, {self.filename}')
            self.spectrum = None

    def _load_object_from_db(self, data=None):
        raise BrainNotImplemented('This method must be implemented by the user')

    def _load_object_from_api(self, data=None):
        pass
        #raise BrainNotImplemented('loading data from API not yet implemented')

    def plot(self, **kwargs):
        ''' A simple quick matplotlib plot '''
        if not self.spectrum:
            return

        __, ax = plt.subplots()
        ax.plot(self.spectrum.wavelength, self.spectrum.flux, **kwargs)
        return ax


# example of using a custom pattern in the sdss_loader
@sdss_loader(name='spec-lite', mapped_version='eboss:run2d',
             pattern=r'(?P<plateid>\d{4,5})-(?P<mjd>\d{5})-(?P<fiberid>\d{1,4})')
class Eboss(Spectrum):
    specutils_format = 'SDSS-III/IV spec'

    def __init__(self, *args, lite=True, **kwargs):
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
    specutils_format = 'APOGEE apStar'


@sdss_loader(name='apVisit', defaults={'prefix': 'ap'}, delimiter='--',
             mapped_version='apogee:apred', order=['telescope', 'field', 'plate', 'mjd', 'fiber'])
class ApVisit(Spectrum):
    specutils_format = 'APOGEE apVisit'


# example of overloading the methods manually
class AspcapStar(Spectrum):
    specutils_format = 'APOGEE aspcapStar'
    path_name = 'aspcapStar'
    mapped_version = 'apogee'

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


@sdss_loader(name='mangacube', defaults={'wave': 'LOG'}, mapped_version='manga:drpver',
             pattern=r'(?P<plateifu>(?P<plate>\d{4,5})-(?P<ifu>\d{3,5}))|(?P<mangaid>\d{1,2}-\d{4,9})')
class Cube(Spectrum):
    specutils_format = 'MaNGA cube'

