# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: htpass.py
# Project: auth
# Author: Brian Cherinka
# Created: Wednesday, 21st October 2020 2:52:25 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Wednesday, 21st October 2020 2:52:25 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import

import pathlib
import warnings
from sdss_brain import cfg_params
from sdss_brain.exceptions import BrainError

try:
    import passlib
except ImportError:
    passlib = None
else:
    from passlib.apache import HtpasswdFile


class Htpass(object):
    """ Class representing a htpasswd file

    This class represents a local .htpasswd file, used for authenticating users
    against the Apache password file used for HTTP Basic Authentication.  This class
    validates a htpasswd file for existence.  It allows one to list the user entries
    found in a local htpasswd file, as well as validate a user against the htpasswd file.

    Parameters
    ----------
    path : str
        The path to a .htpasswd file.  Defaults to custom "htpass_path" config path or ~/.htpasswd
    """

    def __init__(self, path: str = None):
        path = path or cfg_params.get('htpass_path', None) or '~/.htpasswd'
        self.path = pathlib.Path(path).expanduser()

        self.htpass = None
        self._check_htpass()

    def __repr__(self) -> str:
        return f'<Htpass(path="{self.path}", valid={self.is_valid})>'

    @property
    def is_valid(self) -> bool:
        """ Checks if the htpass file exists and htpass object is loaded """
        return self.path.is_file() and self.htpass is not None

    def validate_user(self, username: str, password: str) -> bool:
        """ Validate a user entry in the htpass file

        Checks the provided username and password against the entry in
        the htpass file.

        Parameters
        ----------
        username : str
            A valid htpass username entry
        password : str
            The password for the provided username

        Returns
        -------
        bool
            True when the username/password validates successfully
        """
        if not self.is_valid:
            warnings.warn('htpass is not valid.  Cannot validate user.  Check file path.')
            return False
        return self.htpass.check_password(username, password)

    def _check_htpass(self) -> None:
        """ Check existence of the htpasswd file

        Reads in the htpass file with passlib.apache.HtpasswdFile

        Raises
        ------
        ImportError
            when passlib package not installed
        BrainError
            when the provided htpass file path does not exist
        """
        if not passlib:
            raise ImportError('passlib package not installed.  Cannot use Htpass.')

        if not self.path.is_file():
            raise BrainError(f'No .htpasswd file found at {self.path}!')

        self.htpass = HtpasswdFile(self.path)

    def list_users(self) -> list:
        """ Return a list of users in the htpasswd file

        Returns
        -------
        list
            list of users in the htpasswd file
        """
        if not self.is_valid:
            warnings.warn('htpass is not valid.  Cannot list users.  Check file path.')
            return None
        return self.htpass.users()
