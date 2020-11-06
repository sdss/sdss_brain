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

import warnings

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None
from astropy.io.registry import IORegistryError
from astropy.io.fits import HDUList
from specutils import Spectrum1D
from typing import Type, Union, BinaryIO

from sdss_brain.core import Brain
from sdss_brain.exceptions import BrainNotImplemented, BrainMissingDependency
from sdss_brain.helpers import (sdss_loader, get_mapped_version, load_fits_file, parse_data_input,
                                load_from_url)


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
    spectrum: Type[Spectrum1D] = None
    specutils_format: str = None

    def _load_object_from_file(self) -> None:
        self.data = load_fits_file(self.filename)
        self.header = self.data['PRIMARY'].header
        self._load_spectrum()

    def _load_object_from_db(self) -> None:
        raise BrainNotImplemented('This method must be implemented by the user')

    def _load_object_from_api(self) -> None:
        # for now, do a simple get request to grab the file into memory
        # TODO replace this with better API request framework
        self.data = load_from_url(self.get_full_path(url=True))
        self.header = self.data['PRIMARY'].header
        self._load_spectrum()

    def _load_spectrum(self, data: Union[str, BinaryIO, HDUList] = None) -> None:
        """ Load the `~specutils.Spectrum1D` object

        Loads data into a Spectrum1D object, using ``Spectrum1D.read``.
        If no input data is specified, uses the data attached to the ``self.data``
        attribute.  Valid ``Spectrum1D.read`` inputs are a filename, an open
        file-like object, or an Astropy fits.HDUList.

        Parameters
        ----------
        data : str | `~python.io.BinaryIO` |`~astropy.io.fits.HDUList`, optional
            The data object to be read by Spectrum1D, by default None
        """
        data = data if data else self.data
        try:
            # check robustness of this to self.data/self.filename when specutils 1.1.1 is released
            self.spectrum = Spectrum1D.read(data, format=self.specutils_format)
        except IORegistryError:
            warnings.warn('Could not load Spectrum1D for format '
                          f'{self.specutils_format}, {self.filename}')

    def plot(self, *args, ax=None, x_label: str = 'Wavelength', y_label: str = 'Flux',
             title: str = None, **kwargs):
        """ A simple quick matplotlib plot of the spectrum

        Create a quickplot matplotlib line profile plot for spectra

        Parameters
        ----------
        args : int|list, optional
            for multi-dimensional spectra, the index to plot, by default None
        ax : object, optional
            An existing matplotlib Axes object by default None
        x_label : str, optional
            The x-axis plot label, by default 'Wavelength'
        y_label : str, optional
            The y-axis plot label, by default 'Flux'
        title : str, optional
            The plot title, by default None

        Returns
        -------
        matplotlib.plt.Axes
            The matplotlib Axes object

        Raises
        ------
        BrainMissingDependency
            when matplotlib is not installed
        """
        if not self.spectrum:
            return

        if not plt:
            raise BrainMissingDependency("Package matplotlib not installed.")

        if self.spectrum.flux.ndim > 1:
            index = args
            if not index:
                raise ValueError('The spectrum is n-dimensional.  You must specify a spectrum '
                                 'index to plot.')

            if not all([type(i) == int for i in index]):
                raise ValueError('Input spectrum indices must be integers')

            min_index = self.spectrum.flux.ndim - 1
            index = index if isinstance(index, (tuple, list)) else [index] if type(index) == int else index
            if len(index) < min_index:
                raise ValueError(f'The spectrum has dimension={self.spectrum.flux.ndim}. '
                                 f'You must specify a minimum of {min_index} indices')

            if min_index == 1:
                ii = index[0]
                ydata = self.spectrum.flux[ii]
            elif min_index == 2:
                ii, jj = index
                ydata = self.spectrum.flux[ii, jj]
            else:
                raise ValueError('plot cannot currently support spectral dimensions higher than 3')
        else:
            ydata = self.spectrum.flux

        if not ax:
            ax = plt.gca()

        title = title or f'Object: {self.objectid or self.filename.stem}'
        ax.plot(self.spectrum.wavelength, ydata, **kwargs)
        ax.set_ylabel(f'{y_label} [{self.spectrum.flux.unit.to_string(format="latex_inline")}]')
        ax.set_xlabel(f'{x_label} [{self.spectrum.wavelength.unit.to_string(format="latex_inline")}]')
        ax.set_title(title)
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
        apred = get_mapped_version(self.mapped_version, release=self.release, key='apred')

        # set the path params using the instance attributes extracted from _parse_input
        self.path_params = {'telescope': self.telescope, 'apred': apred,
                            'field': self.field, 'obj': self.obj, 'aspcap': self.aspcap}
