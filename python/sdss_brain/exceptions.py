# !usr/bin/env python
# -*- coding: utf-8 -*-
#
# Licensed under a 3-clause BSD license.
#
# @Author: Brian Cherinka
# @Date:   2017-12-05 12:01:21
# @Last modified by:   Brian Cherinka
# @Last Modified time: 2017-12-05 12:19:32

from __future__ import print_function, division, absolute_import


class Sdss_brainError(Exception):
    """A custom core Sdss_brain exception"""

    def __init__(self, message=None):

        message = 'There has been an error' \
            if not message else message

        super(Sdss_brainError, self).__init__(message)


class Sdss_brainNotImplemented(Sdss_brainError):
    """A custom exception for not yet implemented features."""

    def __init__(self, message=None):

        message = 'This feature is not implemented yet.' \
            if not message else message

        super(Sdss_brainNotImplemented, self).__init__(message)


class Sdss_brainAPIError(Sdss_brainError):
    """A custom exception for API errors"""

    def __init__(self, message=None):
        if not message:
            message = 'Error with Http Response from Sdss_brain API'
        else:
            message = 'Http response error from Sdss_brain API. {0}'.format(message)

        super(Sdss_brainAPIError, self).__init__(message)


class Sdss_brainApiAuthError(Sdss_brainAPIError):
    """A custom exception for API authentication errors"""
    pass


class Sdss_brainMissingDependency(Sdss_brainError):
    """A custom exception for missing dependencies."""
    pass


class Sdss_brainWarning(Warning):
    """Base warning for Sdss_brain."""


class Sdss_brainUserWarning(UserWarning, Sdss_brainWarning):
    """The primary warning class."""
    pass


class Sdss_brainSkippedTestWarning(Sdss_brainUserWarning):
    """A warning for when a test is skipped."""
    pass


class Sdss_brainDeprecationWarning(Sdss_brainUserWarning):
    """A warning for deprecated features."""
    pass
