# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: netrc.py
# Project: auth
# Author: Brian Cherinka
# Created: Wednesday, 21st October 2020 2:52:15 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Wednesday, 21st October 2020 2:52:15 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import

import netrc
import pathlib
import warnings
from sdss_brain import cfg_params
from sdss_brain.exceptions import BrainError


class Netrc(object):
    """ Class representing a netrc file

    This class represents a local .netrc file, used for authenticating users
    against remote machines. This class validates a netrc file for existence and
    correct permissions.  It also checks its hosts against the allowed
    SDSS host domains data.sdss.org and api.sdss.org and ensures their presence.

    Parameters
    ----------
    path : str
        The path to a .netrc file.  Defaults to custom "netrc_path" config path or ~/.netrc
    """

    def __init__(self, path: str = None):
        path = path or cfg_params.get('netrc_path', None) or '~/.netrc'
        self.path = pathlib.Path(path).expanduser()
        self.allowed_hosts = ['data.sdss.org', 'api.sdss.org', 'magrathea.sdss.org']
        self._valid_hosts = {}

        self.check_netrc()

    def __repr__(self) -> str:
        return f'<Netrc(path="{self.path}", valid={self.is_valid})>'

    @property
    def valid_hosts(self) -> list:
        """ A list of valid netrc machine hosts """
        return [k for k, v in self._valid_hosts.items() if v]

    @property
    def is_valid(self) -> bool:
        """ Checks for a valid netrc file """
        try:
            return self.check_netrc()
        except BrainError:
            return False

    def check_netrc(self) -> None:
        """ Validates the netrc file """

        # check for file existence
        if not self.path.is_file():
            raise BrainError(f'No .netrc file found at {self.path}!')

        # check for correct permissions
        if oct(self.path.stat().st_mode)[-3:] != '600':
            raise BrainError('Your .netrc file does not have 600 permissions. Please fix it by '
                             'running chmod 600 on it. Authentication will not work with '
                             'permissions different from 600.')

        # read the netrc file
        try:
            netfile = netrc.netrc(self.path)
        except netrc.NetrcParseError as nerr:
            raise BrainError(f'Your netrc file was not parsed correctly. Error: {nerr}') from nerr

        # check the netrc file has the allowed SDSS host machines
        nethosts = netfile.hosts.keys()
        badlist = []
        for host in self.allowed_hosts:
            self._valid_hosts[host] = host in nethosts
            if host not in nethosts:
                badlist.append(host)

        # check that the required domains are included
        required = set(['data.sdss.org', 'api.sdss.org']) & set(badlist)
        if required:
            warnings.warn(f"Hosts {', '.join(required)} not found in netrc.  "
                          "You will not be able to remotely access SDSS data.", UserWarning)

        # validate if any are good
        return any(self._valid_hosts.values())

    def check_host(self, host: str) -> bool:
        """ Checks the host against the local netrc file

        Checks if the host is a valid machine in the netrc file

        Parameters
        ----------
        host : str
            The netrc machine name

        Returns
        -------
        bool
            True if the host is valid
        """
        netfile = netrc.netrc(self.path)
        return (host in netfile.hosts.keys() and host in self._valid_hosts and
                self._valid_hosts[host])

    def read_netrc(self, host: str) -> tuple:
        """ Read the netrc file for a given host

        Reads the username, password for the given host machine.  Note this
        returns plaintext username and password.  Do not write out these
        values some place transparent and publicly visible.

        Parameters
        ----------
        host : str
            The netrc machine name

        Returns
        -------
        tuple
            Plain text netrc username, password

        Raises
        ------
        BrainError
            when netrc file fails to pass checks
        ValueError
            when input host is not valid
        """

        if not self.check_netrc():
            raise BrainError('netrc did not pass checks.  Cannot read!')

        if not self.check_host(host):
            raise ValueError(f'{host} must be a valid host in the netrc')

        netfile = netrc.netrc(self.path)
        user, acct, passwd = netfile.authenticators(host)  # pylint: disable=unused-variable
        return user, passwd
