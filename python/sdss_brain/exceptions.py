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


class BrainError(Exception):
    """A custom core Brain exception"""

    def __init__(self, message=None):

        message = 'There has been an error' \
            if not message else message

        super(BrainError, self).__init__(message)


class BrainNotImplemented(BrainError):
    """A custom exception for not yet implemented features."""

    def __init__(self, message=None):

        message = 'This feature is not implemented yet.' \
            if not message else message

        super(BrainNotImplemented, self).__init__(message)


class BrainAPIError(BrainError):
    """A custom exception for API errors"""

    def __init__(self, message=None):
        if not message:
            message = 'Error with Http Response from Brain API'
        else:
            message = 'Http response error from Brain API. {0}'.format(message)

        super(BrainAPIError, self).__init__(message)


class BrainApiAuthError(BrainAPIError):
    """A custom exception for API authentication errors"""
    pass


class BrainMissingDependency(BrainError):
    """A custom exception for missing dependencies."""
    pass


class BrainWarning(Warning):
    """Base warning for Brain."""


class BrainUserWarning(UserWarning, BrainWarning):
    """The primary warning class."""
    pass


class BrainSkippedTestWarning(BrainUserWarning):
    """A warning for when a test is skipped."""
    pass


class BrainDeprecationWarning(BrainUserWarning):
    """A warning for deprecated features."""
    pass
