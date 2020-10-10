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
            log.error('Could not load Spectrum1D for format '
                      f'{self.specutils_format}, {self.filename}')
            self.spectrum = None

    def _load_object_from_db(self, data=None):
        raise BrainNotImplemented('This method must be implemented by the user')

    def _load_object_from_api(self, data=None):
        pass
        #raise BrainNotImplemented('loading data from API not yet implemented')

    def plot(self, **kwargs):
        if not self.spectrum:
            return

        __, ax = plt.subplots()
        ax.plot(self.spectrum.wavelength, self.spectrum.flux, **kwargs)
        return ax


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


class Apogee(Spectrum):
    mapped_version = 'apogee'

    def _parse_input(self, value):
        ''' '''
        pattern = (r'(?P<telescope>(?:apo|lco)(?:1|25)m)(?:--|;)(?P<field>[a-z0-9A-Z+-_.]+)(?:--|;)'
                   r'(?P<obj>[a-z0-9A-Z+-_.:]+)')
        data = parse_data_input(value, regex=pattern)
        data['objectid'] = data.get('obj', 'objectid')
        return data


class ApStar(Apogee):
    specutils_format = 'APOGEE apStar'
    path_name = 'apStar'

    def _set_access_path_params(self):
        apred = get_mapped_version(self.mapped_version, release=self.release)
        self.path_params = {'apstar': 'stars', 'prefix': 'ap', 'telescope': self.telescope,
                            'apred': apred, 'field': self.field, 'obj': self.obj}


class ApVisit(Apogee):
    specutils_format = 'APOGEE apVisit'
    path_name = 'apVisit'

    def _set_access_path_params(self):
        apred = get_mapped_version(self.mapped_version, release=self.release)
        self.path_params = {'prefix': 'ap', 'telescope': self.telescope,
                            'apred': apred, 'field': self.field, 'plate': self.plate,
                            'mjd': self.mjd, 'fiber': self.fiberid}


class AspcapStar(Apogee):
    specutils_format = 'APOGEE aspcapStar'
    path_name = 'aspcapStar'

    def _set_access_path_params(self):
        apred = get_mapped_version(self.mapped_version, release=self.release)
        self.path_params = {'telescope': self.telescope, 'apred': apred,
                            'field': self.field, 'obj': self.objectid, 'aspcap': self.aspcap}

# In [17]: access.lookup_keys('apStar')
# Out[17]: ['apred', 'apstar', 'field', 'telescope', 'prefix', 'obj']

# In [18]: access.lookup_keys('apVisit')
# Out[18]: ['fiber', 'field', 'telescope', 'prefix', 'mjd', 'plate', 'apred']

# In [19]: access.lookup_keys('aspcapStar')
# Out[19]: ['apred', 'field', 'telescope', 'aspcap', 'obj']


@sdss_loader(name='mangacube', defaults={'wave': 'LOG'}, mapped_version='manga:drpver',
             pattern=r'(?P<plateifu>(?P<plate>\d{4,5})-(?P<ifu>\d{3,5}))|(?P<mangaid>\d{1,2}-\d{4,9})')
class Cube(Spectrum):
    specutils_format = 'MaNGA cube'

