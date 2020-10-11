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
