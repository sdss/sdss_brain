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
from sdss_brain.core import Brain
from sdss_brain.exceptions import BrainNotImplemented
from sdss_brain.helpers import get_mapped_version, load_fits_file, parse_by_regex_pattern
from specutils import Spectrum1D
import matplotlib.pyplot as plt


class Spectrum(Brain):
    ''' tool for working with spectral FITS data '''

    def _load_object_from_file(self, data=None):
        self.data = load_fits_file(self.filename)
        self.header = self.data['PRIMARY'].header
        self.spectrum = Spectrum1D.read(self.filename, format=self.spec_format)

    def _load_object_from_db(self, data=None):
        raise BrainNotImplemented('This method must be implemented by the user')

    def _load_object_from_api(self, data=None):
        pass
        #raise BrainNotImplemented('loading data from API not yet implemented')

    def plot(self):
        __, ax = plt.subplots()
        ax.plot(self.spectrum.wavelength, self.spectrum.flux)
        return ax


def _create_fn(name, args, body, *, globals=None, locals=None):
    # Note that we mutate locals when exec() is called.  Caller
    # beware!  The only callers are internal to this module, so no
    # worries about external callers.
    if locals is None:
        locals = {}
    args = ','.join(args)
    body = '\n'.join(f'  {b}' for b in body)
    # Compute the text of the entire function.
    txt = f' def {name}({args}):\n{body}'
    local_vars = ', '.join(locals.keys())
    txt = f"def __create_fn__({local_vars}):\n{txt}\n return {name}"
    ns = {}
    exec(txt, globals, ns)
    return ns['__create_fn__'](**locals)


def extend_init(cls=None, items=None, reprs=None):

    def create_newinit(cls, items):
        name = '__init__'
        args = ['self', '*args'] + items + ['**kwargs']
        names = [item.split('=')[0] for item in items]
        attrs = [f'self.{name} = {name}' for name in names]
        body = attrs + [f'super({cls.__name__}, self).__init__(*args, **kwargs)']
        ff = _create_fn(name, args, body)
        return ff

    def create_newrepr(cls, reprs):
        name = '__repr__'
        args = ['self']
        body = [f'old = super({cls.__name__}, self).__repr__()']
        params = ', '.join([f'{item}={{self.{item}}}' for item in reprs])
        body.append(f"return old.replace('>', f', {params}>')")
        return _create_fn(name, args, body)

    def wrap(cls):
        setattr(cls, '__init__', create_newinit(cls, items))
        if reprs:
            setattr(cls, '__repr__', create_newrepr(cls, reprs))
        return cls

    if cls is None:
        return wrap

    return wrap(cls)


#@extend_init(items=['lite=True'])
class Eboss(Spectrum):
    mapped_version = 'eboss'
    spec_format = 'SDSS-III/IV spec'

    def __init__(self, *args, lite=True, **kwargs):
        self.lite = lite
        super(Eboss, self).__init__(*args, **kwargs)

    def __repr__(self):
        old = super(Eboss, self).__repr__()
        return old.replace('>', f', lite={self.lite}>')

    def _parse_input(self, value):
        pattern = r'(?P<plate>\d{4,5})-(?P<mjd>\d{5})-(?P<fiberid>\d{1,4})$'
        dd = parse_by_regex_pattern(pattern, value, self)
        if isinstance(dd, dict):
            self.objectid = value
        else:
            self.filename = value

    def _set_access_path_params(self):
        self.path_name = 'spec-lite' if self.lite else 'spec'
        run2d = get_mapped_version(self.mapped_version, release=self.release)
        self.path_params = {'plateid': self.plate, 'mjd': self.mjd, 'fiberid': self.fiberid,
                            'run2d': run2d}


# class Apogee(Spectrum):
#     mapped_version = 'apogee'
#     spec_format = 'APOGEE apStar'

#     def _parse_input(self, value):
#         ''' '''
#         pattern = (r'(?P<telescope>(?:apo|lco)(?:1|25)m)(?:--|;)(?P<field>[a-z0-9A-Z+-_.]+)(?:--|;)'
#                    r'(?P<objectid>[a-z0-9A-Z+-_.:]+)')
#         dd = parse_by_regex_pattern(pattern, value, self)
#         self.objectid = dd.get('objectid')

#     def _set_access_path_params(self):
#         self.path_name = 'apStar'
#         apred = get_mapped_version(self.mapped_version, release=self.release)
#         self.path_params = {'apstar': 'stars', 'prefix': 'ap', 'telescope': self.telescope,
#                             'apred': apred, 'field': self.field, 'obj': self.objectid}


class Apogee(Spectrum):
    mapped_version = 'apogee'

    def _parse_input(self, value):
        ''' '''
        pattern = (r'(?P<telescope>(?:apo|lco)(?:1|25)m)(?:--|;)(?P<field>[a-z0-9A-Z+-_.]+)(?:--|;)'
                   r'(?P<objectid>[a-z0-9A-Z+-_.:]+)')
        dd = parse_by_regex_pattern(pattern, value, self)
        self.objectid = dd.get('objectid')


class ApStar(Apogee):
    spec_format = 'APOGEE apStar'

    def _set_access_path_params(self):
        self.path_name = 'apStar'
        apred = get_mapped_version(self.mapped_version, release=self.release)
        self.path_params = {'apstar': 'stars', 'prefix': 'ap', 'telescope': self.telescope,
                            'apred': apred, 'field': self.field, 'obj': self.objectid}


class ApVisit(Apogee):
    spec_format = 'APOGEE apVisit'

    def _set_access_path_params(self):
        self.path_name = 'apVisit'
        apred = get_mapped_version(self.mapped_version, release=self.release)
        self.path_params = {'prefix': 'ap', 'telescope': self.telescope,
                            'apred': apred, 'field': self.field, 'plate': self.plate,
                            'mjd': self.mjd, 'fiber': self.fiberid}


class AspcapStar(Apogee):
    spec_format = 'APOGEE aspcapStar'

    def _set_access_path_params(self):
        self.path_name = 'aspcapStar'
        apred = get_mapped_version(self.mapped_version, release=self.release)
        self.path_params = {'telescope': self.telescope, 'apred': apred,
                            'field': self.field, 'obj': self.objectid, 'aspcap': self.aspcap}

# In [17]: access.lookup_keys('apStar')
# Out[17]: ['apred', 'apstar', 'field', 'telescope', 'prefix', 'obj']

# In [18]: access.lookup_keys('apVisit')
# Out[18]: ['fiber', 'field', 'telescope', 'prefix', 'mjd', 'plate', 'apred']

# In [19]: access.lookup_keys('aspcapStar')
# Out[19]: ['apred', 'field', 'telescope', 'aspcap', 'obj']

class Cube(Brain):
    mapped_version = 'manga'

    def _parse_input(self, value):
        pattern = r'(?P<plateifu>(?P<plate>\d{4,5})-(?P<ifu>\d{3,5}))|(?P<mangaid>\d{1,2}-\d{4,9})'
        dd = parse_by_regex_pattern(pattern, value, self)
        if isinstance(dd, dict):
            self.objectid = dd.get('mangaid') or dd.get('plateifu')
        else:
            self.filename = dd

    def _set_access_path_params(self):
        self.path_name = 'mangacube'
        drpver = get_mapped_version(self.mapped_version, release=self.release, key='drpver')
        self.path_params = {'plate': self.plate, 'ifu': self.ifu, 'drpver': drpver, 'wave': 'LOG'}

    def _load_object_from_file(self, data=None):
        self.data = load_fits_file(self.filename)
        self.header = self.data['PRIMARY'].header
        self.plateifu = self.header.get("plateifu")
        self.plate, self.ifu = self.plateifu.split('-')
        self.mangaid = self.header.get("mangaid")

    def _load_object_from_db(self, data=None):
        pass

    def _load_object_from_api(self, data=None):
        pass
