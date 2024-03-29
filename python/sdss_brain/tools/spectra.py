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
from typing import Type, Union, BinaryIO, List

from sdss_brain import log
from sdss_brain.core import Brain
from sdss_brain.datamodel import get_mapped_version
from sdss_brain.exceptions import BrainNotImplemented, BrainMissingDependency
from sdss_brain.helpers import (sdss_loader, load_fits_file, parse_data_input,
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
        if not self.data:
            log.warning('Failed to retrieve remote data.')
            return
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
@sdss_loader(name='spec-lite', mapped_version='run2d',
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
    datamodel: str = 'specFull'

    def __init__(self, *args: str, lite: bool = True, **kwargs: str) -> None:
        self.lite = lite
        self.path_name = f'spec{"-lite" if lite else ""}'
        self.__class__.datamodel = f'spec{"Lite" if self.lite else "Full"}'
        super(Eboss, self).__init__(*args, **kwargs)

    def __repr__(self):
        old = super(Eboss, self).__repr__()
        return old.replace('>', f', lite={self.lite}>')


# example of using a access keys to define the pattern in the sdss_loader
# setting a custom delimiter to "--" since APOGEE field names can have "-" in them.
@sdss_loader(name='apStar', defaults={'apstar': 'stars', 'prefix': 'ap'}, delimiter='--',
             mapped_version='apred', order=['telescope', 'field', 'obj'])
class ApStar(Spectrum):
    """ Class representing an APOGEE combined spectrum for a single star """
    specutils_format: str = 'APOGEE apStar'
    datamodel: str = 'apStar'


@sdss_loader(name='apVisit', defaults={'prefix': 'ap'}, delimiter='--',
             mapped_version='apred', order=['telescope', 'field', 'plate', 'mjd', 'fiber'])
class ApVisit(Spectrum):
    """ Class representing an APOGEE single visit spectrum for a given star """
    specutils_format: str = 'APOGEE apVisit'
    datamodel: str = 'apVisit'


# example of overloading the methods manually
class AspcapStar(Spectrum):
    """ Class representing an APOGEE spectrum for a single star with ASPCAP results """
    specutils_format: str = 'APOGEE aspcapStar'
    path_name: str = 'aspcapStar'

    def _parse_input(self, value):
        # use the sdss_access keys to form the object id and parse it
        keys = self.access.lookup_keys(self.path_name)
        data = parse_data_input(value, keys=keys, delimiter='--',
                                order=['aspcap', 'telescope', 'field', 'obj'], )
        return data

    def _set_access_path_params(self):
        # extract the apred version id based on the data release
        apred = get_mapped_version('apred', release=self.release)

        # set the path params using the instance attributes extracted from _parse_input
        self.path_params = {'telescope': self.telescope, 'apred': apred,
                            'field': self.field, 'obj': self.obj, 'aspcap': self.aspcap}


def create_tool(species: str, base: Union[tuple, list, Spectrum] = None, specutils_format: str = None,
                release: str = None,  api: str = None, base_api_route: str = None,
                path_name: str = None, mapped_version: str = None, pattern: str = None, delimiter: str = None,
                defaults: dict = None, order: List[str] = None, keys: list = None, keymap: dict = None,
                exclude: list = None, include: list = None) -> Type[Spectrum]:
    """ Dynamically create a new tool

    Creates a new tool class dynamically from a datamodel file species product name. The new tool is
    subclassed from `~.sdss_brain.tools.spectra.Spectrum`, but the base class can be customized with
    the ``base`` option.  The new class is wrapped in the ``sdss_loader`` decorator, which provides
    convenience for specifying a unique object identifier for the tool, and any sdss_access information.

    Keyword arguments ``specutils_format``, ``api``, and ``base_api_route``, along with the ``species``
    argument are used to define tool class attributes.

    The remainder of the keyword arguments are those passed to the ``sdss_loader`` decorator for defining
    a unique object id pattern, as well as the pertinent sdss_access parameters.

    Parameters
    ----------
    species : str
        a file species product name
    base : Union[tuple, list, Spectrum], optional
        a new base class or tuple of classes to subclass from, by default Spectrum
    specutils_format : str, optional
        the format identifier used by specutils.Spectrum1D, by default None
    release : str, optional
        the SDSS data release, by default None
    api : str, optional
        the name of the API to use, by default None
    base_api_route : str, optional
        the base API route for this tool, by default None
    path_name : str, optional
        the sdss_access template path name, by default None
    mapped_version : str, optional
        a mapping key to map a specific version onto a release, e.g. "manga:drpver", by default None
    defaults : dict, optional
        default values for the sdss_access template keyword arguments, by default None
    pattern : str, optional
        the regex pattern to match with, by default None
    delimiter : str, optional
        the delimiter to use when joining keys for the objectid pattern creation, by default None
    order : List[str], optional
        a list of access keywords to order the objectid pattern by, by default None
    keys : list, optional
        optional list of names to construct a named pattern.  Default is to use any sdss_access keys.
    keymap : dict, optional
        optional dict mapping names to specific patterns to use, by default None
    exclude : list, optional
        a list of access keywords to exclude in the objectid pattern creation, by default None
    include : list, optional
        a list of access keywords to include in the objectid pattern creation, by default None

    Returns
    -------
    Spectrum
        a new tool class

    Raises
    ------
    ValueError
        when no mapped_version is specified
    """
    # create class name
    name = species[0].title() + species[1:]

    # set class attributes
    kwds = {'datamodel': species, 'specutils_format': specutils_format}

    # check for any api info
    if api:
        api_tup = (api, base_api_route)
        kwds['_api'] = api_tup

    # resolve the bases
    if not base:
        base = (Spectrum,)
    elif isinstance(base, list):
        base = tuple(base)
    elif not isinstance(base, tuple):
        base = (base,)
    from types import resolve_bases
    resolved_bases = resolve_bases(base)

    # create the new class
    kls = type(name, resolved_bases, kwds)

    # TODO - improve the inputs and code around mapped_versions
    # TODO - improve the inputs and code around path keywords and object id creation
    # NOTE - can we reduce the number of inputs and auto-input to sdss_loader?

    # check inputs
    if not mapped_version:
        raise ValueError('A mapped_version must be specified.')

    # look up path name if none is specified
    if not path_name:
        # create datamodel
        from sdss_brain.datamodel.products import create_object_model
        model = create_object_model(species, release=release)

        info = model.get_access_info()
        if not info or info['in_sdss_access'] is False:
            log.warning(f'No access info found for datamodel {name} in {release}.')
            return

        path_name = info['path_name']


    # apply the sdss_loader decorator
    kls = sdss_loader(name=path_name, defaults=defaults or {}, delimiter=delimiter,
                    mapped_version=mapped_version, order=order, pattern=pattern,
                    keys=keys, keymap=keymap, exclude=exclude, include=include)(kls)

    return kls
