# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: user.py
# Project: auth
# Author: Brian Cherinka
# Created: Thursday, 22nd October 2020 11:17:33 am
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Thursday, 22nd October 2020 11:17:33 am
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import

from sdss_brain.auth import Netrc, Htpass
from sdss_brain.exceptions import BrainError
from sdss_brain.api.io import send_post_request

try:
    from collaboration.wiki import Credential
except ImportError:
    Credential = None


class User(object):
    """ Class representing a valid user

    This class represents a valid SDSS user.  It checks and validates the user
    against a local netrc file, a local htpasswd file, and against the SDSS
    collaboration.Credentials.

    Parameters
    ----------
    user : str
        the SDSS username

    Attributes
    ----------
    member : dict
        dictionary of member information for a validated user
    netrc : type[Netrc]
        A local Netrc instance, if any
    htpass : type[Htpass]
        A local Htpass instance, if any
    cred : type[Credential]
        A local SDSS Credential instance, if any
    """

    def __init__(self, user: str):
        self.user = user
        self.netrc = None
        self.htpass = None
        self.cred = None
        self.member = None

        self._valid_netrc = False
        self._valid_htpass = False
        self._valid_sdss_cred = False

        self._setup_auths()

    def __repr__(self) -> str:
        return (f'<User("{self.user}", netrc={self.is_netrc_valid}, htpass={self.is_htpass_valid}, '
                f'cred={self.is_sdss_cred_valid})>')

    def __str__(self):
        return self.user

    def _setup_auths(self):
        """ Setup the authenticators """
        # setup netrc
        try:
            self.netrc = Netrc()
        except BrainError:
            self.netrc = None
        else:
            self._valid_netrc = (self.user in self.netrc.read_netrc('data.sdss.org') or
                                 self.user in self.netrc.read_netrc('api.sdss.org'))

        # setup htpass
        try:
            self.htpass = Htpass()
        except BrainError:
            self.htpass = None
        else:
            self._valid_htpass = False

        # setup SDSS Credential
        if Credential:
            self.cred = Credential

    @property
    def is_netrc_valid(self) -> bool:
        """ Checks if the netrc credentials are validated for the given user """
        return False if not self.netrc else self._valid_netrc

    @property
    def is_htpass_valid(self) -> bool:
        """ Checks if htpasswd credentials are validated for the given user """
        return False if not self.htpass else self._valid_htpass

    @property
    def is_sdss_cred_valid(self) -> bool:
        """ Checks if SDSS credentials are validated for the given user """
        return self._valid_sdss_cred

    @property
    def validated(self) -> bool:
        """ Checks if user is validated """
        return any([self.is_netrc_valid, self.is_htpass_valid, self.is_sdss_cred_valid])

    @property
    def in_sdss(self) -> dict:
        """ Checks member status in SDSS-IV and SDSS-V """
        if self.member:
            return {'sdss4': self.member['sdss4']['has_sdss_access'],
                    'sdss5': self.member['sdss5']['has_sdss_access']}

    def validate_user(self, password: str = None) -> None:
        """ Validate the given user

        Validates the given user for netrc, htpass, and SDSS Credential
        authentication.  Attempts to extract a valid password from the netrc file
        for the given user.  Otherwise a password must be explicitly input.

        Parameters
        ----------
        password : str, optional
            The password for the given user, by default None

        Raises
        ------
        ValueError
            when the netrc username does not match the input user
        ValueError
            when no valid password is input nor extracted from the netrc
        """
        # look up user info from validated netrc
        if self.is_netrc_valid:
            try:
                user, passwd = self.netrc.read_netrc('data.sdss.org')
            except ValueError:
                user, passwd = self.netrc.read_netrc('api.sdss.org')

            if user != self.user:
                raise ValueError(f'netrc user {user} mismatched with input user {self.user}!')

            # if no password set, use the netrc password
            password = passwd if not password else password

        # ensure a password is specified
        if not password:
            raise ValueError('Must provide a password if none extracted from netrc.')

        # validate the htpasswd
        if self.htpass:
            self._valid_htpass = self.htpass.validate_user(self.user, password) or False

        # try to validate using SDSS Credentials
        if self.cred:
            cred = Credential(self.user, password)
            cred.authenticate_via_trac()
            self._valid_sdss_cred = cred.authenticated is True
        else:
            # TODO change this dev login to production site when ready
            cred_url = 'https://internal.sdss.org/dev/collaboration/api/login'
            data = send_post_request(cred_url, data={'username': self.user, 'password': password})
            self._valid_sdss_cred = data.get('authenticated', False) == 'True'
            self.member = data.get('member', None)

