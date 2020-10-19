# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: cubes.py
# Project: tools
# Author: Brian Cherinka
# Created: Sunday, 11th October 2020 3:15:17 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Sunday, 11th October 2020 3:15:17 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import

import warnings
from astropy.io import fits
from sdss_brain.tools import Spectrum
from sdss_brain.helpers import sdss_loader


class Cube(Spectrum):
    """ Base class for cubes """
    pass


@sdss_loader(name='mangacube', defaults={'wave': 'LOG'}, mapped_version='manga:drpver',
             pattern=r'(?P<plateifu>(?P<plate>\d{4,5})-(?P<ifu>\d{3,5}))|(?P<mangaid>\d{1,2}-\d{4,9})')
class MangaCube(Spectrum):
    """ Class representing a MaNGA IFU datacube for a single galaxy """
    specutils_format: str = 'MaNGA cube'

    def _load_object_from_db(self, data=None):
        if not self._db.connected:
            return

        # make a database call to retrieve the Cube row
        self.data = self._db.session.query(self._db.model).join(self._db.models.IFUDesign,
                                                                self._db.models.PipelineInfo,
                                                                self._db.models.PipelineVersion).\
            filter(self._db.model.plateifu == self.plateifu,
                   self._db.models.PipelineVersion.version == self.drpver).one_or_none()

        if not self.data:
            warnings.warn(f"No data returned from database for {self.plateifu}")
            return

        # extract header info and reformat to proper fits.Header
        # TODO move this into the datamodel product
        head = [(k, int(v) if v.isnumeric() else float(v) if v.replace('.', '').isnumeric(
        ) else v.strip(), self.data.header.comments[i]) for i, (k, v) in enumerate(self.data.header.items())]
        self.header = fits.Header(head)

        # TODO - slow; 5 seconds to access all 3 from local db; improve this?
        flux = self.data.get3DCube('flux')
        ivar = self.data.get3DCube('ivar')
        mask = self.data.get3DCube('mask')

        # construct a new astropy FITS HDUList
        hdulist = fits.HDUList([fits.PrimaryHDU(data=None), fits.ImageHDU(flux, header=self.header),
                                fits.ImageHDU(ivar, name='IVAR'), fits.ImageHDU(mask, name='MASK'),
                                fits.ImageHDU(self.data.wavelength.wavelength, name='WAVE')])

        # load the spectrum
        self._load_spectrum(hdulist)
