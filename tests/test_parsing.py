# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: test_parsing.py
# Project: tests
# Author: Brian Cherinka
# Created: Tuesday, 6th October 2020 5:24:57 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Tuesday, 6th October 2020 5:24:58 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import
import re
import pytest
from sdss_brain.helpers import parse_data_input


template = '/tmp/path/to/file/{ver}/newfile-{ver}-{plate}-{ifu}-{wave}.txt'
ff = '/tmp/path/to/file/v1/newfile-v1-8485-1901-LOG.txt'
relf = '../../file/A/newfile-v1-8485-1901-LOG.txt'
envf = '$TOYPATH/A/newfile-v1-8485-1901-LOG.txt'

keys = ['ver', 'plate', 'ifu', 'wave']

#  using keys
output = {'filename': None,
          'objectid': 'v1-8485-1901-LOG',
          'ver': 'v1',
          'plate': '8485',
          'ifu': '1901',
          'wave': 'LOG',
          'parsed_groups': ['v1-8485-1901-LOG', 'v1', '8485', '1901', 'LOG'],
          'parsed_inputs': {'pattern': '^(?P<filename>^[/$.](.+)?(.[a-z]+))|(?P<objectid>(?![/$.])((?P<ver>(.+)?)-(?P<plate>(.+)?)-(?P<ifu>(.+)?)-(?P<wave>(.+)?)))$',
                            'input_regex': None,
                            'object_pattern': '(?P<objectid>(?![/$.])((?P<ver>(.+)?)-(?P<plate>(.+)?)-(?P<ifu>(.+)?)-(?P<wave>(.+)?)))',
                            'file_pattern': '(?P<filename>^[/$.](.+)?(.[a-z]+))'}}


class TestParsing(object):

    @pytest.mark.parametrize('file', [(ff), (relf), (envf)])
    def test_parse_files(self, file):
        out = parse_data_input(file)
        assert out['filename'] is not None
        assert out['filename'] == file
        assert out['objectid'] is None

    @pytest.mark.parametrize('value, exp',
                             [('8485-1901', None),
                              ('v1-8485-1901-LOG', 'v1-8485-1901-LOG')])
    def test_default_keys(self, value, exp):
        out = parse_data_input(value, keys=keys, inputs=True)
        assert out.get('objectid', None) == exp
        if exp:
            assert out.items() <= output.items()
            assert out['parsed_inputs']['object_pattern'] == output['parsed_inputs']['object_pattern']

    @pytest.mark.parametrize('option, vals',
                             [('exclude', ['wave', 'ifu']),
                              ('include', ['plate']),
                              ('order', ['plate', 'ifu'])])
    def test_pattern_with_key_options(self, option, vals):
        exclude = include = order = None
        if option == 'exclude':
            exclude = vals
        elif option == 'include':
            include = vals
        elif option == 'order':
            order = vals

        out = parse_data_input('v1-8485-1901-LOG', keys=keys, inputs=True,
                               exclude=exclude, include=include, order=order)
        pattern = out['parsed_inputs']['object_pattern']
        names = re.findall(r'\?P<(.*?)>', pattern)

        if option == 'exclude':
            assert not set(vals) & set(names)
        elif option == 'include':
            assert set(vals) & set(names)
            assert 'wave' not in names
        elif option == 'order':
            assert set(vals) & set(names)
            assert 'ver' not in names

    @pytest.mark.parametrize('value, opts, exp',
                             [('v1-8485', ['wave', 'ifu'], ['ver', 'plate']),
                              ('8485-1901', ['ver', 'wave'], ['plate', 'ifu'])])
    def test_keys_exclude(self, value, opts, exp):
        out = parse_data_input(value, keys=keys, exclude=opts)
        exp_data = [out[e] for e in exp]
        assert not set(opts) & set(out.keys())
        assert exp_data == value.split('-')

    @pytest.mark.parametrize('value, opts, exp',
                             [('v1-8485', ['plate', 'ver'], ['ver', 'plate']),
                              ('8485-1901', ['ifu', 'plate'], ['plate', 'ifu'])])
    def test_keys_include(self, value, opts, exp):
        out = parse_data_input(value, keys=keys, include=opts)
        exp_data = [out[e] for e in exp]
        assert set(opts) & set(out.keys())
        assert 'wave' not in out
        assert exp_data == value.split('-')

    @pytest.mark.parametrize('value, opts, order',
                             [('8485-1901', ['plate', 'ifu'], True),
                              ('8485-1901', ['ifu', 'plate'], False),
                              ('1901-8485', ['ifu', 'plate'], True)])
    def test_keys_order(self, value, opts, order):
        oo = opts if order else None
        out = parse_data_input(value, keys=keys, order=oo, exclude=['wave', 'ver'])

        exp_data = dict(zip(opts, value.split('-')))
        if order:
            assert exp_data['plate'] == out['plate']
            assert exp_data['ifu'] == out['ifu']
        else:
            assert exp_data['plate'] == out['ifu']
            assert exp_data['ifu'] == out['plate']

    @pytest.mark.parametrize('value, pattern',
                             [('abcd1234', '[a-z]+\d+'),
                              ('8485-1901', r'([0-9]{4,5})-([0-9]{4,9})'),
                              ('8485-1901', r'(?P<plateifu>(?P<plate>\d{4,5})-(?P<ifu>\d{3,5}))|(?P<mangaid>\d{1,2}-\d{4,9})'),
                              ('1-209232', r'(?P<plateifu>(?P<plate>\d{4,5})-(?P<ifu>\d{3,5}))|(?P<mangaid>\d{1,2}-\d{4,9})')
                              ], ids=['simple', 'groups', 'named-plateifu', 'named-mangaid'])
    def test_custom_regex(self, value, pattern):
        out = parse_data_input(value, regex=pattern)
        names = re.findall(r'\?P<(.*?)>', pattern)
        isplateifu = '8485-1901' in value
        assert out['objectid'] == value

        if isplateifu:
            assert out['parsed_groups'] == ['8485-1901', '8485','1901']
        else:
            assert out['parsed_groups'] == [value]

        if names:
            if isplateifu:
                assert out['plate'] == '8485'
                assert out['ifu'] == '1901'
                assert out['plateifu'] == value
            else:
                assert out['mangaid'] == value
                assert out['plateifu'] is None
