# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: decorators.py
# Project: helpers
# Author: Brian Cherinka
# Created: Thursday, 8th October 2020 12:44:20 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Thursday, 8th October 2020 12:44:21 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import

import inspect
from functools import wraps

from sdss_brain.helpers import get_mapped_version, parse_data_input


# global registry of decorators
registry = {}


def register(func):
    ''' Decorator to add class decorators to the global registry '''
    registry[func.__name__] = func
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


def get_parse_input(regex=None, keys=None, keymap=None, include=None, exclude=None,
                    order=None, delimiter=None):
    """ Generate a default parse_input method to be attached to a class """

    def _parse_input(self, value):
        ''' Default parse_input applied with the decorator '''
        akeys = None
        if self.is_access_mixedin and self.path_name is not None:
            akeys = self.access.lookup_keys(self.path_name)
        pkeys = keys or akeys or None

        data = parse_data_input(value, regex=regex, keys=pkeys, keymap=keymap,
                                include=include, exclude=exclude, order=order, delimiter=delimiter)

        for k, v in data.items():
            if k != ['filename', 'objectid']:
                setattr(self, k, v)
        return data
    return _parse_input


def create_mapped_properties(kls, mapped_version):
    ''' Create new read-only properties on a given class

    Creates new read-only properties that extracts a specific version id to an input
    release.  This allows the version id to be updated when the global "release" is
    changed.  See `~sdss_brain.helpers.get_mapped_version` for more details.
    ``mapped_version`` is a mapping key, "[mapping]:[property,]", where [mapping]
    is the name of the key in the "mapped_version" attribute in the brain configuration yaml file,
    and [property,] is a list of version ids to become properties.

    For example a key of "manga:drpver" creates a new read-only property called "drpver" and uses
    `get_mapped_version` to extract the correct version number for a given release from the
    "mapped_version['manga']" key in ~sdss_brain.yaml.

    Parameters
    ----------
        kls : Type
            The class object
        mapped_version : str
            The mapping key to map a specific version onto a release
    '''
    mapkey, attrkey = mapped_version.split(':')
    # set the mapped_version class attribute
    kls.mapped_version = mapkey
    if attrkey:
        # loop over all named values found
        for attr in attrkey.split(','):
            # create read-only property that extracts the correct version number
            # for a given release
            setattr(kls, attr, property(lambda self: get_mapped_version(
                kls.mapped_version, release=self.release, key=attr)))


@register
def parser_loader(kls=None, *, pattern=None, keys=None, keymap=None, include=None, exclude=None,
                  order=None, delimiter=None):
    """ Class decorator to reduce boilerplate around definition of parse_input method

    Decorator to generate a default `_parse_input` method to be attached to a class.
    The created default method uses `~sdss_brain.helpers.parsing.parse_data_input` to
    match the input string value against the provided regex pattern and returns a dictionary
    containing the parsed "filename" or "objectid". If the pattern is a named-group regex pattern
    the method extracts the names and adds them as attributes on the class.  If no pattern is
    specified, the method checks for available sdss_access template keys and, if found, constructs
    a regex matching pattern from them.  Otherwise, if no keys are found, it performs a greedy
    match and sets the result as the objectid.  The return dictonary adds a `parsed_groups`
    attribute to the instance containing the match group output from the regex match.  This allows
    the user to access the extracted matches when the input pattern is simple, i.e. containing
    no named groups or grouping regex structure.

    Parameters
    ----------
    pattern : str
        The regex pattern to match with
    keys : list
        Optional list of names to construct a named pattern.  Default is to use any sdss_access keys.
    keymap : dict
        Optional dict mapping names to specific patterns to use. Default is None.
    include : list
        A list of access keywords to include in the objectid pattern creation
    exclude: list
        A list of access keywords to exclude in the objectid pattern creation
    order : list
        A list of access keywords to order the objectid pattern by
    delimiter : str
        The delimiter to use when joining keys for the objectid pattern creation

    Returns
    -------
        kls: class
            The decorated class
    """
    def wrap(kls):
        # setup and attach the default parse_input function
        parse_input = get_parse_input(regex=pattern, keys=keys, keymap=keymap, include=include,
                                      exclude=exclude, order=order, delimiter=delimiter)
        setattr(kls, '_parse_input', parse_input)

        # update the __abstractmethod__ with the boilerplate set
        method_set = ['_parse_input']
        kls.__abstractmethods__ = kls.__abstractmethods__.symmetric_difference(method_set)
        return kls

    if not kls:
        return wrap
    return wrap(kls)


def _set_access_path_params(self):
    ''' Default set_access_path_params applied with the decorator'''
    keys = self.access.lookup_keys(self.path_name)
    self.path_params = {k: getattr(self, k) for k in keys}


@register
def access_loader(kls=None, *, name=None, defaults={}, mapped_version=None):
    """ Class decorator to reduce boilerplate around setting of sdss_access parameters

    Decorator to generate a default `_set_access_path_params` method given a template
    path name.  The default method creates an empty `path_params` dictionary using the
    template keywords given a path name.  Default values for template kwargs can be specified
    using the "defaults" argument.

    ``mapped_version`` is a mapping key, "[mapping]:[property,]",
    where [mapping] is the name of the key in the "mapped_version" attribute in the brain
    configuration yaml file, and [property,] is a list of version ids to become properties.  See
    `~sdss_brain.helpers.get_mapped_version` for more details.

    For example a key of "manga:drpver" creates a new read-only property called "drpver" and uses
    `get_mapped_version` to extract the correct version number for a given release from the
    "mapped_version['manga']" key in ~sdss_brain.yaml.

    Parameters
    ----------
        name : str
            The sdss_access template path name
        defaults : dict
            Default values for the sdss_access template keyword arguments
        mapped_version : str
            A mapping key to map a specific version onto a release, e.g. "manga:drpver"

    Returns
    -------
        kls: class
            The decorated class
    """
    def wrap(kls):
        # add the path_name class attribute and add defaults for path_params
        kls.path_name = name
        kls._path_defaults = defaults

        # create new properties for mapped versions
        if mapped_version:
            create_mapped_properties(kls, mapped_version)

        # attach the default set_access_path_params
        setattr(kls, '_set_access_path_params', _set_access_path_params)

        # update the __abstractmethod__ with the boilerplate set
        method_set = ['_set_access_path_params']

        kls.__abstractmethods__ = kls.__abstractmethods__.symmetric_difference(method_set)
        return kls

    if not kls:
        return wrap
    return wrap(kls)


# def sdss_loader(kls=None, *, name=None, defaults={}, mapped_version=None, pattern=None,
#                 include=None, exclude=None, order=None, delimiter=None):
#     """ """

#     def wrap(kls):
#         if name:
#             kls = access_loader(kls=kls, name=name, defaults=defaults,
#                                 mapped_version=mapped_version)

#         parser = any([pattern, include, exclude, order])
#         if parser:
#             kls = parser_loader(kls=kls, pattern=pattern, include=include, exclude=exclude,
#                                 order=order, delimiter=delimiter)
#         return kls

#     if not kls:
#         return wrap

#     return wrap(kls)


def use_decorators(*args):
    ''' Decorator that adds the specified decorators to the function as an attribute '''
    def actual_decorator(func):

        # create a list of the used decorators
        func.registry = list(args)

        @wraps(func)
        def wrapper(*args, **kwargs):
            # append the function to itself as a keyword argument
            return func(*args, **kwargs, self=func)
        return wrapper
    return actual_decorator


@use_decorators('access_loader', 'parser_loader')
def sdss_loader(kls=None, *args, **kwargs):
    """ Class decorator that combines and applies other class decorators

    This decorator applies the decorators specified in `use_decorators` to
    the input class instance.  It effectively combines individual decorators allowing
    a global entry point for the keyword arguments.  This is equivalvent to stacking
    decorators, e.g.::

        @access_loader()
        @parser_loader()
        class B(object):
            pass

    Parameters
    ----------
        args : list
            Any appropriate decorator arguments
        kwargs : list
            Any appropriate decoratoy keyword arguments

    Returns
    -------
        The class that has been decorated

    """

    self = kwargs.get('self', None)
    loaders = self.registry

    def wrap(kls):
        for decorator in loaders:
            # identify the decorator function and get its keyword arguments
            func = registry.get(decorator, None)
            func_kwargs = inspect.getfullargspec(
                func).kwonlyargs or inspect.getfullargspec(func.__wrapped__).kwonlyargs

            # extract any matching input keyword arguments
            found_kwargs = set(func_kwargs) & set(kwargs.keys())
            relevant_kwargs = {k: kwargs[k] for k in found_kwargs}

            # apply the class decorator with relevant kwargs
            kls = func(kls=kls, **relevant_kwargs)

        return kls

    if not kls:
        return wrap

    return wrap(kls)
