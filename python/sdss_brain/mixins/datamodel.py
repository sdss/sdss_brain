# !/usr/bin/env python
# -*- coding: utf-8 -*-
#

from __future__ import print_function, division, absolute_import

from sdss_brain.config import config, log
from sdss_brain.datamodel.products import create_object_model


__all__ = ['DataModelMixIn']


class DataModelMixIn:
    """ Class to handle datamodel """
    datamodel: str = None

    def __init__(self, *args, model: str = None, **kwargs):
        release = kwargs.get('release') or config.release
        name = model or getattr(self.__class__, 'datamodel', None)
        self.datamodel = create_object_model(name, release=release)

        super(DataModelMixIn, self).__init__(*args, **kwargs)

    def check_data(self) -> bool:
        """ Check the data against the set datamodel

        Checks the currently loaded data against the expected
        datamodel for any discrepant HDU extensions. Returns
        True if no discrepanices or False if the loaded
        data has extensions not in the datamodel.

        Returns
        -------
        bool
            _description_
        """
        if not self.data or not self.datamodel:
            log.warning('No data or datamodel attributes specified.  Cannot check.')
            return

        model_hdus = self.datamodel.list_hdus(names=True)
        if not model_hdus:
            log.warning(f'No HDUS found for model {self.datamodel.name} in release {self.release}.')
            return

        data_hdus = {i.name for i in self.data}
        if missing := data_hdus - set(model_hdus):
            log.warning("HDU extension mismatch between loaded data and expected datamodel. "
                        f"Loaded data has extra extensions: {missing}")
            return False
        return True




