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
from itertools import groupby
from sdss_brain import log


def create_object_pattern(regex=None, keys=None, delimiter=None, exclude=None, include=None,
                          order=None):
    """ Create a regex pattern to parse data input by

    Parameters
    ----------
        regex : str
            A custom regex pattern
        keys : list
            A list of (access) names to build a pattern out of
        delimiter : str
            The delimiter to use when joining the keys.  Default is "-".
        exclude : list
            A list of names to exclude from the keys
        include : list
            A list of names to only include from the keys
        order : list
            A list of names specifying the order in which create the keyed pattern

    Returns
    -------
        pattern : str
            A regex pattern to use for parsing an objectid
    """

    # use a custom regex pattern
    if regex:
        pattern = rf'(?P<objectid>(?![/$.])({regex}))'
        return pattern

    # if no keys, use a greedy default
    if not keys:
        pattern = r'(?P<objectid>^[^/$.](.+)?)'
        return pattern

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
        patts.append(fr'(?P<{k}>(.+)?)')

    # join into a single pattern
    delimiter = '-' if not delimiter else delimiter
    pattern = rf'(?P<objectid>(?![/$.])({delimiter.join(patts)}))'

    return pattern


def parse_data_input(value, regex=None, keys=None, delimiter='-', exclude=None, include=None,
                     order=None, inputs=False):
    ''' Parse data input for a filename or an object id

    Parameters
    ----------
        value : str
            The input string to perform a pattern match on
        regex : str
            A custom regex pattern
        keys : list
            A list of (access) names to build a pattern out of
        delimiter : str
            The delimiter to use when joining the keys.  Default is "-".
        exclude : list
            A list of names to exclude from the keys
        include : list
            A list of names to only include from the keys
        order : list
            A list of names specifying the order in which create the keyed pattern
        inputs : bool
            If True, returns the parser inputs.  Default is False.

    Returns
    -------
        matches : dict
            A dict with keys "filename", "objectid", and any other matches
    '''

    assert isinstance(value, (str, pathlib.Path)), 'input value must be a str or pathlib.Path'

    # check if regex has named groups
    # is_named = re.findall(r'\?P<(.*?)>', regex) if regex else None

    # set default file pattern
    file_pattern = r'(?P<filename>^[/$.](.+)?(.[a-z]+))'

    # create an object id regex pattern using a specified pattern or generate a default one
    obj_pattern = create_object_pattern(regex=regex, keys=keys, delimiter=delimiter,
                                        exclude=exclude, include=include,
                                        order=order)

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


def raw_parse(value, regex=None):
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
