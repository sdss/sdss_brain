
.. _parsing:

Parsing the Data Input Argument
-------------------------------

The ``Brain`` accepts a single string `data_input` argument which can be either a filename or a shorthand
object identiier.  If the input is a shorthand object id, it must additionally be converted into parameters
that can be used to load data from a file, database or remote location.  To determine the type of input,
extract necessary parameters, or convert to a filename, you need to define some logic that instructs the
``Brain`` how to handle this parsing.  There are a few primary ways to do this.

Overloading the `_parse_input` method
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Each subclass of ``Brain``, must define a `_parse_input` method.  This method accepts as input a single
argument containing the string `data_input` passed into it.  It can contain any custom logic
but must return a dictionary containing at least two keys: `filename` and `objectid`.
::

    # simple conditional logic - is a file or else
    def _parse_input(self, value):

        data = dict.fromkeys(['filename', 'objectid'])
        if os.path.isfile(value):
            data['filename'] = value
        else:
            data['objectid'] = value

        return data

It is common to have an object id that is made up of other relevant parameters, e.g `plate`, `mjd`, `ifu`,
etc that are needed to construct accurate filepaths or for further analysis.  In these cases, you can use
regex pattern matching to parse the object id into components.  Let's see an example of parsing the string
"plate-ifu", e.g. "8454-1901", which is a 4-5 digit number, followed by a 3-5 digit number, separated by a
hyphen.  To learn more about regex, see :doc:`python:library/re` or try the
`Regex Explorer <https://regex101.com/?flavor=python>`_.
::

    import re

    # simple regex parsing
    def _parse_input(self, value):

        data = dict.fromkeys(['filename', 'objectid'])
        if os.path.isfile(value):
            data['filename'] = value
        else:
            # perform the regex pattern matching
            pattern = r'(\d{4,5})-(\d{3,5})'
            match = re.match(pattern, value)
            if match:
                data['plate'], data['ifu'] = match.groups()
                data['objectid'] = match.group()

        return data

Creating an objectid regex pattern
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the above example, we had to manually parse the regex matched group and assign it to object id.  To
simply the creation of a regex pattern, we can use `~sdss_brain.helpers.parsing.create_object_pattern`
which helps create a named group regex patterns for the objectid.  It returns a named group `objectid`,
with a custom pattern.  By default, it returns a greedy match on anything.
::

    >>> # create a greedy default
    >>> create_object_pattern()
    '(?P<objectid>^[^/$.](.+)?)'

You can pass a custom regex pattern.
::

    >>> # pass in a custom pattern
    >>> pattern = r'(\d{4,5})-(\d{3,5})'
    >>> create_object_pattern(regex=pattern)
    '(?P<objectid>(?![/$.])((\\d{4,5})-(\\d{3,5})))'

We can create a named group pattern by passing in a list of names.  This creates a series of named groups
that each are a greedy match on anything.
::

    >>> # create a named group pattern
    >>> keys = ['plate', 'ifu']
    >>> create_object_pattern(keys=keys)
    '(?P<objectid>(?![/$.])((?P<plate>(.+)?)-(?P<ifu>(.+)?)))'

We can also change the delimiter for joining the keys.
::

    >>> # create a named group pattern
    >>> keys = ['plate', 'ifu']
    >>> create_object_pattern(keys=keys, delimiter='---')
    '(?P<objectid>(?![/$.])((?P<plate>(.+)?)---(?P<ifu>(.+)?)))'

We can create a named group using specific patterns for each name by passing a dictionary into
the `keymap` keyword argument.
::

    >>> # create a named group pattern
    >>> keymap = {'plate': r'\d{4,5}', 'ifu': r'\d{3,5}'
    >>> create_object_pattern(keymap=keymap)
    '(?P<objectid>(?![/$.])((?P<plate>\\d{4,5})-(?P<ifu>\\d{3,5})))'

Using the `parse_data_input` function
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To take full advantage of the pattern creation and the data input attribute extraction, we can use
`~sdss_brain.helpers.parsing.parse_data_input` to parse the `data_input` directly into a dictionary
containing a filename, objectid, or any extracted named parameters.  This function takes a string value
as input to parse and a number of options related to the creation of the object pattern.
::

    >>> # determine input is a filename
    >>> parse_data_input('/path/to/a/file.txt')
        {'filename': '/path/to/a/file.txt', 'objectid': None, 'parsed_groups': None}

If it's not a filename, with no other input it will be parsed generically as an objectid.
::

    >>> # parse an objectid as is
    >>> parse_data_input('8485-1901')
        {'filename': None, 'objectid': '8485-1901', 'parsed_groups': ['8485-1901', '485-1901']}

You can specify a custom pattern.  Here we create a named group pattern.  The extracted names are new keys
in the dictionary.
::

    >>> # parse an objectid using a custom pattern
    >>> parse_data_input('8485-1901', regex=r'(?P<plate>\d{4,5})-(?P<ifu>\d{3,5})')
        {'filename': None, 'objectid': '8485-1901', 'plate': '8485', 'ifu': '1901', 'parsed_groups': ['8485-1901', '8485', '1901']}

We can specify a list of keys to use as the names.  These can be any names or it can be useful to use the
`sdss_access` template keys.
::

    >>> # parse an objectid using sdss_access template keywords
    >>> keys = ['drpver', 'plate', 'ifu', 'wave']
    >>> parse_data_input('v1-8485-1901-LOG', keys=keys)
        {'filename': None, 'objectid': 'v1-8485-1901-LOG', 'drpver': 'v1', 'plate': '8485',
            'ifu': '1901', 'wave': 'LOG', 'parsed_groups': ['v1-8485-1901-LOG', 'v1', '8485', '1901', 'LOG']}

If we know the input is only a subset of keys, we can set the order to include only those names.
::

    >>> # parse an objectid specifying the input order of the keys
    >>> keys = ['drpver', 'plate', 'ifu', 'wave']
    >>> parse_data_input('8485-1901', keys=keys, order=['plate', 'ifu'])
        {'filename': None, 'objectid': '8485-1901', 'plate': '8485', 'ifu': '1901', 'parsed_groups': ['8485-1901', '8485', '1901']}

Or we can exclude certain keys if we no they are never part of the input object id.
::

    >>> # parse an objectid excluding a key
    >>> keys = ['drpver', 'plate', 'ifu', 'wave']
    >>> parse_data_input('v1-1901-LOG', keys=keys, exclude=['plate'])
    {'filename': None, 'objectid': 'v1-1901-LOG', 'drpver': 'v1', 'ifu': '1901', 'wave': 'LOG', 'parsed_groups': ['v1-1901-LOG', 'v1', '1901', 'LOG']}

For simple patterns of unnamed groups or non-groups, the output of the regex match object is placed
in a `parsed_group` key where the extracted groups can be accessed.
::

    >>> parse_data_input('abc123', regex='[a-z0-9]+')
    {'filename': None, 'objectid': 'abc123', 'parsed_groups': ['abc123']}


    >>> parse_data_input('abc123', regex='([a-z]+)([0-9]+)')
    {'filename': None, 'objectid': 'abc123', 'parsed_groups': ['abc123', 'abc', '123']}
