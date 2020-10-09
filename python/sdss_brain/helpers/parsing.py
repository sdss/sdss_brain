# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: parsing.py
# Project: helpers
# Author: Brian Cherinka
# Created: Wednesday, 7th October 2020 10:54:07 am
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Wednesday, 7th October 2020 10:54:07 am
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import
import re
import pathlib
from typing import Union
from itertools import groupby
from sdss_brain import log


def create_object_pattern(regex: str = None, keys: list = None, keymap: dict = None,
                          delimiter: str = '-', exclude: list = None, include: list = None,
                          order: list = None) -> str:
    """ Create a regex pattern to parse data input by

    Parameters
    ----------
        regex : str
            A custom regex pattern
        keys : list
            A list of (access) names to build a pattern out of
        keymap : dict
            A dict of key name and pattern to build a pattern out of
        delimiter : str
            The delimiter to use when joining the keys.  Default is "-".
        exclude : list
            A list of names to exclude from the keys
        include : list
            A list of names to only include from the keys
        order : list
            A list of names specifying the order in which to create the keyed pattern

    Returns
    -------
        pattern : str
            A regex pattern to use for parsing an objectid
    """

    # use a custom regex pattern
    if regex:
        pattern = rf'(?P<objectid>(?![/$.])({regex}))'
        return pattern

    # if no keys or keymap, use a greedy default
    if not keys and not keymap:
        pattern = r'(?P<objectid>^[^/$.](.+)?)'
        return pattern

    assert keys or keymap, 'Either a list of keys or a keymap must be specified.'
    assert isinstance(keys, (list, type(None))), 'keys must be a list'
    assert isinstance(keymap, (dict, type(None))), 'keymap must be a dict'
    if not keys and keymap:
        keys = list(keymap.keys())

    # make a copy of the original key order
    keys_copy = keys.copy()

    # exclude the named keys
    if exclude:
        keys = list(set(keys) - set(exclude))

    # only include the named keys
    if include or order:
        good = order or include
        keys = list(set(good) & set(keys))

    # resort the keys by the original key order
    keys.sort(key=lambda i: keys_copy.index(i))

    # order the keys
    if order:
        keys.sort(key=lambda i: order.index(i))

    patts = []
    for k in keys:
        if not keymap:
            patts.append(fr'(?P<{k}>(.+)?)')
        else:
            patts.append(fr'(?P<{k}>{keymap[k]})')

    # join into a single pattern
    delimiter = '-' if not delimiter else delimiter
    pattern = rf'(?P<objectid>(?![/$.])({delimiter.join(patts)}))'

    return pattern


def parse_data_input(value: str, regex: str = None, keys: list = None, keymap: dict = None,
                     delimiter: str = '-', exclude: list = None, include: list = None,
                     order: list = None, inputs: bool = False) -> dict:
    ''' Parse data input for a filename or an object id

    Parameters
    ----------
        value : str
            The input string to perform a pattern match on
        regex : str
            A custom regex pattern
        keys : list
            A list of (access) names to build a pattern out of
        keymap : dict
            A dict of key name and pattern to build a pattern out of
        delimiter : str
            The delimiter to use when joining the keys.  Default is "-".
        exclude : list
            A list of names to exclude from the keys
        include : list
            A list of names to only include from the keys
        order : list
            A list of names specifying the order in which to create the keyed pattern
        inputs : bool
            If True, returns the parser inputs.  Default is False.

    Returns
    -------
        matches : dict
            A dict with keys "filename", "objectid", and any other matches

    Example
    -------
        >>> # parse a filename
        >>> parse_data_input('/path/to/a/file.txt')
            {'filename': '/path/to/a/file.txt', 'objectid': None, 'parsed_groups': None}

        >>> # parse an objectid as is
        >>> parse_data_input('8485-1901')
            {'filename': None, 'objectid': '8485-1901', 'parsed_groups': ['8485-1901', '485-1901']}

        >>> # parse an objectid using a custom pattern
        >>> parse_data_input('8485-1901', regex=r'(?P<plate>\d{4,5})-(?P<ifu>\d{3,5})')
            {'filename': None, 'objectid': '8485-1901', 'plate': '8485', 'ifu': '1901', 'parsed_groups': ['8485-1901', '8485', '1901']}

        >>> # parse an objectid using access keywords
        >>> keys=['drpver', 'plate', 'ifu', 'wave']
        >>> parse_data_input('v1-8485-1901-LOG', keys=keys)
            {'filename': None, 'objectid': 'v1-8485-1901-LOG', 'drpver': 'v1', 'plate': '8485',
             'ifu': '1901', 'wave': 'LOG', 'parsed_groups': ['v1-8485-1901-LOG', 'v1', '8485', '1901', 'LOG']}

        >>> # parse an objectid specifying the input order of the keys
        >>> parse_data_input('8485-1901', keys=keys, order=['plate', 'ifu'])
            {'filename': None, 'objectid': '8485-1901', 'plate': '8485', 'ifu': '1901', 'parsed_groups': ['8485-1901', '8485', '1901']}

    '''

    assert isinstance(value, (str, pathlib.Path)), 'input value must be a str or pathlib.Path'

    # check if regex has named groups
    # is_named = re.findall(r'\?P<(.*?)>', regex) if regex else None

    # set default file pattern
    file_pattern = r'(?P<filename>^[/$.](.+)?(.[a-z]+))'

    # create an object id regex pattern using a specified pattern or generate a default one
    obj_pattern = create_object_pattern(regex=regex, keys=keys, keymap=keymap, delimiter=delimiter,
                                        exclude=exclude, include=include, order=order)

    # final pattern
    pattern = fr'^{file_pattern}|{obj_pattern}$'

    # compile and match the patterm
    comp_pattern = re.compile(pattern)
    pattern_match = re.match(comp_pattern, str(value))

    # if no match, assume value is a filename and return nothing
    if not pattern_match:
        log.warning('No pattern match found.  Defaulting to input value as a filename.')
        return {'filename': value}

    # check for named group, then any groups, then a match without groups
    matches = pattern_match.groupdict() or pattern_match.groups() or pattern_match.group()

    # add the groups to a new key (remove None and duplicate values)
    matches['parsed_groups'] = [k for k, _ in groupby(sorted(pattern_match.groups(),
                                                             key=lambda x: pattern_match.groups().index(x))) if k] \
        if not matches.get('filename', None) else None

    # store the parser inputs
    if inputs:
        matches['parsed_inputs'] = {'pattern': pattern, 'input_regex': regex,
                                    'object_pattern': obj_pattern, 'file_pattern': file_pattern}
    return matches


def raw_parse(value: str, regex: str = None) -> Union[dict, tuple]:
    ''' Match a string via a regex pattern with no frills

    Parameters
    ----------
        value : str
            The input string to match on
        regex : str
            The regex pattern to use for matching

    Returns
    -------
        A matched group

    '''
    pattern = re.compile(regex)
    match = re.match(pattern, value)
    if not match:
        return None

    return match.groupdict() or match.groups() or match.group()
