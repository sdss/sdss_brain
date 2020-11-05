
.. _remote:

Connecting to Remote Sources
============================

To enable tools built with the ``Brain`` to have remote data access, i.e. `data_origin="api"` and `mode="remote"`,
you must attach an API profile or URL to the tool or provide one during tool instantiation.  The API or URL references
any remote http location to request data from.  With the exception of simple explicit urls, the ``Brain`` relies on valid
SDSS API profiles representing valid SDSS web services.  Profiles not defined in
`api_profiles.yml <https://github.com/sdss/sdss_brain/tree/master/python/sdss_brain/etc/api_profiles.yml>`_ are currently
not supported.

Remember that once you attach an API object to a tool, you must override the `_load_object_from_api` method
with logic instructing the tool with what to do for remote access.  For an example of simply retrieving a file, see
the `Spectrum tool base class <https://github.com/sdss/sdss_brain/blob/master/python/sdss_brain/tools/spectra.py#L56>`_.
For an example utilizing a remote API and the SDSS http client, see the
`MangaCube tool <https://github.com/sdss/sdss_brain/blob/master/python/sdss_brain/tools/cubes.py#L33>`_.


Adding Remote Access to a Tool
------------------------------

.. _simple:

Simple Remote File Access
^^^^^^^^^^^^^^^^^^^^^^^^^

When defining a tool around a FITS file data product, it may be enough to supply remote access to the file.  For these cases,
you can use, `~sdss_brain.helpers.io.load_from_url`, a helper function that streams the file via an HTTP get request and loads
its contents into an in-memory FITS object.  To use it in a tool, simply pass in a valid url, and, if desired, set the FITS
response to the ``data`` attribute. For example,
::

    from sdss_brain.helpers.io import load_from_url

    class MyTool(object):
        ...
        def _load_object_from_api(self):
            url = 'https://data.sdss.org/path/to/my/data/myfile.fits'
            self.data = load_from_url(url)

For a real example of retrieving a file, see its use in the
`Spectrum tool base class <https://github.com/sdss/sdss_brain/blob/master/python/sdss_brain/tools/spectra.py#L56>`_.  This
example highlights its integration with ``sdss_access`` dynamic path creation.

.. _complete:

Using an API
^^^^^^^^^^^^

Usually more complicated remote access calls, e.g. performing database queries, or retrieving information from
disparate data sources, are handled and served by an API (Application Programming Interface).  APIs are basically
web servers designed to provide programmatic remote access to data through a series of HTTP url routes.  See the
`Github API <https://docs.github.com/en/free-pro-team@latest/rest>`_ for a real-world example, or the
`SDSS-IV MaNGA Marvin API <https://sdss-marvin.readthedocs.io/en/latest/reference/web.html>`_ for an SDSS astronomy example.

We can add a valid API object via one of three ways.  Using the ``_api`` class attribute
when defining a new tool class from the ``Brain``.  In this case, all instances and subclasses of this
tool will use the attached API object.
::

    class MangaCube(Brain):
        _api = 'marvin'

When using the `~sdss_brain.core.Brain.set_api_object` class method on a pre-defined tool.  This
temporarily sets an API object to the class.  In this case, all new instances and subclasses will use
the new API object set in the current Python session.
::

    from sdss_brain.tools import MangaCube

    MangaCube.set_api_object('marvin')

When using the ``use_api`` keyword argument when instantiating the tool directly.  In this case, only
this instance will have access to the API object.
::

    from sdss_brain.tools import MangaCube

    c = MangaCube('8485-1902', use_api='marvin')


Valid Input
-----------

There are multiple types of remote objects that are valid input:

- a valid explicit http url string
- a valid string name or instance of an SDSS `~sdss_brain.api.manager.ApiProfile`
- a valid tuple containing the API name, a url route, and optional domain; e.g. ('marvin', 'cubes/8485-1901', 'dr15')

Here we pass in an explicit http url itself.  Explicit urls always take precedence as input over any API profile.
::

    >>> from sdss_brain.tool import MangaCube

    >>> # passing in an explicit url
    >>> c = MangaCube('8485-1902', use_api='https://sas.sdss.org/marvin/api/cubes/8485-1901/')
    >>> c.remote
    <ApiHandler(api="marvin", url="https://sas.sdss.org/marvin/api/cubes/8485-1902/")>

Here we pass in the name of the SDSS-IV MaNGA API, ``marvin``, which represents the API connection profile used
to access any information served by the Marvin API.  This input does not set a specific url to use for access, but
one can construct one using the ``ApiProfile`` object.
::

    >>> from sdss_brain.tool import MangaCube
    >>> from sdss_brain.api.manager import apim

    >>> # passing in a string API profile name
    >>> c = MangaCube('8485-1902', use_api='marvin')
    >>> c.remote
    <ApiHandler(api="marvin", url="None")>

    >>> # passing in an ApiProfile instance
    >>> profile = apim.apis['marvin']
    >>> profile
    <ApiProfile("marvin", current_domain="sas.sdss.org", url="https://sas.sdss.org/marvin/api")>

    >>> c = MangaCube('8485-1902', use_api=profile)
    >>> c.remote
    <ApiHandler(api="marvin", url="None")>

Here we pass in a tuple containing the name of an API, a url route segment to add to the base url, and an optional
domain name.
::

    >>> from sdss_brain.tools import MangaCube

    >>> c = MangaCube('8485-1902', use_api=('marvin', 'cubes/8485-1902/', 'dr15')))
    >>> c.remote
    <ApiHandler(api="marvin", url="cubes/8485-1902/")>

Passing in any of these objects results in a `~sdss_brain.api.handler.ApiHandler` object being
created.

The ApiHandler
--------------

When passing in a valid API object or URL as input, a `~sdss_brain.api.handler.ApiHandler` object is created and
attached to the ``remote`` attribute.  The ``ApiHandler`` is a simple container around any
SDSS API, url, and http request client.  It normalizes the input and provides access to the underlying
url, the `~sdss_brain.api.manager.ApiProfile`, and remote http client, `~sdss_brain.api.client.SDSSClient`, used
to submit http requests, no matter what input is provided.  Here we provide an explicit url.
::

    >>> from sdss_brain.api.handler import ApiHandler

    >>> a = ApiHandler('https://sas.sdss.org/marvin/api/cubes/8485-1901/')
    >>> a
    <ApiHandler(api="marvin", url="https://sas.sdss.org/marvin/api/cubes/8485-1901/")>

The ``ApiHandler`` will attempt to identify a valid API, and which domain, used, but an explicit url always takes
precedence.  It will display any identified "api" or "url" found in the ``repr``.
::

    >>> # access the url
    >>> a.url
    'https://sas.sdss.org/marvin/api/cubes/8485-1901/'

    >>> # access the underlying API
    >>> a.api
    <ApiProfile("marvin", current_domain="sas.sdss.org", url="https://sas.sdss.org/marvin/api")>

You can access the underlying `~sdss_brain.api.manager.ApiProfile` via the ``api`` attribute.  See :ref:`apiprofile`
for more information on what you can do with an API profile.  You can access the http request client via the
``client`` attribute.  See :ref:`SDSSClient <sdssclient>` for more details on how to use the client to send HTTP requests.
::

    # access the client used to send requests
    a.client
    <SDSSClient(api="marvin", user="sdss")>

If instead of a single url, you wish to have access to a series of routes provided by a single API, pass in an API profile
name directly.
::

    >>> # load the marvin API
    >>> a = ApiHandler('marvin')
    >>> a.api
    <ApiHandler(api="marvin", url="None")>

This won't set an explicit url, but one can be loaded with the ``load_url`` method, which constructs a new url from the base
API url and the provided url route segment.
::

    >>> # load a new url
    >>> a.load_url('cubes/8485-1901/')
    >>> a.url
    'https://sas.sdss.org/marvin/api/cubes/8485-1901'

Urls can be extended with the ``extend_url`` method, which returns a new url with the input route appended to the end of
the constructed base url.  This allows you to easily construct nested url route structures.
::

    >>> a.extend_url('extensions/flux')
    'https://sas.sdss.org/marvin/api/cubes/8485-1901/extensions/flux'

To provide an API with a known pre-defined url segment, you can use the api tuple input. If you wish to load the API with a
different domain as the default, the tuple can accept a third domain argument.  Let's load an API route to access MaNGA cube
information using the public domain for DR15 data.
::

    >>> # load the marvin API using public domain DR15
    >>> a = ApiHandler(('marvin', 'cubes/8485-1901/', 'dr15'))
    >>> a
    <ApiHandler(api="marvin", url="cubes/8485-1901/")>

    >>> # see the API profile
    >>> a.api
    <ApiProfile("marvin", current_domain="dr15.sdss.org", url="https://dr15.sdss.org/marvin/api")>

    >>> # see the complete client url
    >>> a.client.url
    'https://dr15.sdss.org/marvin/api/cubes/8485-1901/'


Resolving Url Parameters
^^^^^^^^^^^^^^^^^^^^^^^^

Sometimes URL routes have dynamic parameter arguments defining the route path, for example, a url that retrieves metadata
about a particular object, i.e. "https://sas.sdss.org/marvin/api/cubes/8485-1901" which returns information on
MaNGA galaxy "8485-1901". In practice, the galaxy id can be replaced with any other to retrieve new data.  For complete
flexibility when constructing url routes, use the bracket notation ``{}`` to define a named parameter which can be
replaced at any time.
::

    >>> # provide named parameter arguments in bracket notation
    >>> a = ApiHandler(('marvin', 'cubes/{plateifu}'))
    >>> a.url
    'cubes/{plateifu}'

    >>> # check for a valid url
    a.has_valid_url
    False

    >>> # check the client url
    >>> a.client.url
    'https://sas.sdss.org/marvin/api/cubes/{plateifu}'

Requests cannot be sent until all named parameter arguments have been resolved.
::

    >>> # resolve the named parameters
    >>> a.resolve_url({'plateifu':'8485-1902'})
    >>> a.url
    'cubes/8485-1902'

    >>> # check for a valid url
    >>> a.has_valid_url
    True

    >>> # check the client url
    >>> a.client.url
    'https://sas.sdss.org/marvin/api/cubes/8485-1902'

If needed, you can also extract the named parameters from the url.
::

    >>> a = ApiHandler(('marvin', 'cubes/{plateifu}'))
    >>> a.extract_url_brackets()
    ['plateifu']

Switching to an Async Client
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The default client used by the ``ApiHandler`` is a synchronous http client.  To switch to an async version, pass in
``async_client=True``.
::

    >>> # use the async client
    >>> a = ApiHandler('marvin', async_client=True)

    >>> a.client
    <SDSSAsyncClient(api="marvin", user="sdss")>


.. _sdssclient:

Sending HTTP Requests with SDSSClient
-------------------------------------

All http requests are sent using the `~sdss_brain.api.client.SDSSClient`, which is a convenience wrapper class around the
`httpx <https://www.python-httpx.org/>`_ Python package for sending requests.  ``httpx`` is a modern request framework
aiming to mirror the API of the `requests <https://requests.readthedocs.io/en/master/>`_ python package.  `httpx`` also
provides built-in async support.  See `~sdss_brain.api.client.SDSSAsyncClient` for the async version of the remote client.

The main advantage of using the ``SDSSClient`` is integration with SDSS APIs and SDSS user authentication.


.. _apim:

The Api Manager
---------------

``sdss_brain`` provides an API manager (`~sdss_brain.api.manager.ApiManager`) for seeing the available
SDSS domains and APIs for remotely accessing data.
::

    >>> # load the API manager
    >>> from sdss_brain.api.manager import apim
    >>> apim
    <ApiManager(current_api="None", n_domains="9", n_apis="3")>

You can list all the available domains used by SDSS.
::

    >>> # list the domains
    >>> apim.list_domains()
    [Domain(name='data.sdss.org', public=False, description='domain for accessing SDSS data on the SAS'),
     Domain(name='sas.sdss.org', public=False, description='domain for accessing various SAS services'),
     Domain(name='api.sdss.org', public=False, description='domain for accessing SDSS APIs'),
     Domain(name='lore.sdss.utah.edu', public=False, description='domain for accessing internal content on SDSS host lore'),
     Domain(name='internal.sdss.org', public=False, description='domain for accessing internal SDSS information'),
     Domain(name='magrathea.sdss.org', public=False, description="mirror domain for SDSS services, e.g. SDSS MaNGA's Marvin"),
     Domain(name='dr15.sdss.org', public=True, description='public domain for DR15 data access'),
     Domain(name='dr16.sdss.org', public=True, description='public domain for DR15 data access'),
     Domain(name='localhost', public=False, description='domain when running services locally')]

or you can list the available APIs.
::

    >>> # list the APIs
    >>> apim.list_apis()
    [<ApiProfile("marvin", current_domain="dr15.sdss.org", url="https://dr15.sdss.org/marvin/api")>,
     <ApiProfile("icdb", current_domain="internal.sdss.org", url="https://internal.sdss.org/collaboration/api")>,
     <ApiProfile("valis", current_domain="api.sdss.org", url="https://api.sdss.org/valis")>]

Each list of domains or apis can also be rendered as an Astropy `~astropy.table.Table`, with
`~sdss_brain.api.manager.ApiManager.display`.
::

    >>> # display the available domains as a table
    >>> apim.display('domains')
    <Table length=9>
       key           name        public                        description
       str9         str18         bool                            str57
    --------- ------------------ ------ ---------------------------------------------------------
         data      data.sdss.org  False                 domain for accessing SDSS data on the SAS
          sas       sas.sdss.org  False                 domain for accessing various SAS services
          api       api.sdss.org  False                            domain for accessing SDSS APIs
         lore lore.sdss.utah.edu  False   domain for accessing internal content on SDSS host lore
     internal  internal.sdss.org  False            domain for accessing internal SDSS information
    magrathea magrathea.sdss.org  False mirror domain for SDSS services, e.g. SDSS MaNGA's Marvin
         dr15      dr15.sdss.org   True                        public domain for DR15 data access
         dr16      dr16.sdss.org   True                        public domain for DR16 data access
        local          localhost  False                      domain when running services locally

The ``ApiManager`` also provides a mechanism for identifying an API and domain given a url string.
::

    >>> # attempt to identify a domain and API
    >>> apim.identify_api_from_url('https://dr15.sdss.org/marvin/api')
    ('marvin', 'dr15')


.. _apiprofile:

The Api Profile
---------------


Defining a new API Profile
--------------------------



Setting a global Url or API
---------------------------

In the rare case that you want to use a single API for all ``Brain``-based tools, you can set one on the
global config object using the `~sdss_brain.config.Config.set_api`.  This will set an API to your global config,
and all tools will use this global API.  ``config.apis`` contains an instance of the `~sdss_brain.api.manager.ApiManager`.
::

    >>> from sdss_brain.config import config

    >>> # look up the set profile in the API manager
    >>> config.apis.profile
    None

    >>> # set a global API
    config.set_api('marvin')

    >>> config.apis.profile
    <ApiProfile("marvin", current_domain="sas.sdss.org", url="https://sas.sdss.org/marvin/api")>

You can also set one permanently by setting the ``default_api`` argument in your ``~/.config/sdss/sdss_brain.yml``
config file.