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

import numpy as np
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
    _api = ('marvin', 'cubes/{plateifu}/')

    def _load_object_from_db(self):

        # do nothing if not connected to the database
        if not self.db.connected:
            return

        # issue warning if no model or models attached to database handler
        if not self.db.model or not self.db.models:
            warnings.warn('No model(s) found in db handler.  Cannot query for a cube.'
                          'Try passing in an explicit ORM or setting the schema and model with '
                          'db.load_model or db.load_schema.')
            return

        # make a database call to retrieve the Cube row
        self.data = self.db.session.query(self.db.model).join(self.db.models.IFUDesign,
                                                              self.db.models.PipelineInfo,
                                                              self.db.models.PipelineVersion).\
            filter(self.db.model.plateifu == self.plateifu,
                   self.db.models.PipelineVersion.version == self.drpver).one_or_none()

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
        hdulist = fits.HDUList([fits.PrimaryHDU(data=None),
                                fits.ImageHDU(flux, name='FLUX', header=self.header),
                                fits.ImageHDU(ivar, name='IVAR'), fits.ImageHDU(mask, name='MASK'),
                                fits.ImageHDU(self.data.wavelength.wavelength, name='WAVE')])

        # load the spectrum
        self._load_spectrum(hdulist)

    def _load_object_from_api(self):

        # do nothing if no remote client
        if not self.remote:
            return

        # submit the remote request
        self.remote.client.request(method='post', data={'release': self.release})

        # extract data from the response
        self.data = self.remote.client.data['data']
        self.mangaid = self.data['mangaid']
        self.ra = self.data['ra']
        self.dec = self.data['dec']
        self.redshift = self.data['redshift']
        self.wavelength = np.array(self.data['wavelength'])

        # set the header
        # TODO - fix header - see above
        header = fits.Header.fromstring(self.data['header'])
        head = [(k, int(v) if v.isnumeric() else float(v) if v.replace('.', '').isnumeric(
        ) else v.strip(), header.comments[i]) for i, (k, v) in enumerate(header.items())]
        self.header = fits.Header(head)

        # example to retrieve flux for central spaxel
        # TODO - look into improving speed of 3d flux retrieval
        # TODO - improve url extension-ing
        self.shape = np.array(self.data['shape'])
        x_cen, y_cen = self.shape // 2
        spaxel_url = self.remote.extend_url(f'quantities/{x_cen}/{y_cen}/')
        self.remote.client.request(spaxel_url, data={'release': self.release})

        # construct a FITS hdulist
        flux = np.zeros(shape=((len(self.wavelength),) + tuple(self.shape)))
        ivar = np.zeros(shape=((len(self.wavelength),) + tuple(self.shape)))
        mask = np.zeros(shape=((len(self.wavelength),) + tuple(self.shape)))
        flux[:, x_cen, y_cen] = np.array(self.remote.client.data['data']['flux']['value'])
        ivar[:, x_cen, y_cen] = np.array(self.remote.client.data['data']['flux']['ivar'])
        mask[:, x_cen, y_cen] = np.array(self.remote.client.data['data']['flux']['mask'])
        hdulist = fits.HDUList([fits.PrimaryHDU(data=None),
                                fits.ImageHDU(flux, name='FLUX', header=self.header),
                                fits.ImageHDU(ivar, name='IVAR'), fits.ImageHDU(mask, name='MASK'),
                                fits.ImageHDU(self.wavelength, name='WAVE')])

        # load the spectrum
        self._load_spectrum(hdulist)
