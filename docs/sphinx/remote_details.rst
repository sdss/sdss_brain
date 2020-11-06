
.. _remote_details:

Remote Data Access
==================

.. _sdssclient:

Sending HTTP Requests with SDSSClient
-------------------------------------

All http requests are sent using the `~sdss_brain.api.client.SDSSClient`, which is a convenience wrapper class around the
`httpx <https://www.python-httpx.org/>`_ python package for sending requests.  ``httpx`` is a modern request framework
aiming to mirror the API of the `requests <https://requests.readthedocs.io/en/master/>`_ python package.  ``httpx`` also
provides built-in async support.  See `~sdss_brain.api.client.SDSSAsyncClient` for the async version of the remote client.

The main advantage of using the ``SDSSClient`` is integration with SDSS APIs and SDSS user authentication, although it can be
used with any explicit url.  Let's submit a "hello world" request to the Marvin API using the public domain `dr15.sdss.org`.
::

    >>> from sdss_brain.api.client import SDSSClient

    >>> # load the client to use the marvin API on public domain DR15,
    >>> # accessing the "cubes hello world" url route
    >>> s = SDSSClient('cubes', use_api='marvin', domain='dr15')
    >>> s
    <SDSSClient(api="marvin", user="sdss")>

    >>> # check the full url
    >>> s.url
    'https://dr15.sdss.org/marvin/api/cubes'

When we instantiate the client with an API and a domain name, the correct base url is constructed behind the scenes.  Any input
url is then treated as a route segment to be appended to the base url.  The fully constructed url can be shown with
the ``url`` attribute.  We can now send the request.  ``request`` is a convenience wrapper for sending ``httpx`` get, post, or
stream requests.  Let's send the request as default without any parameters.
::

    >>> # send the http request
    >>> s.request()

When requests are successful, the response content is extracted into the ``data`` attribute.  If the request is not successful,
an ``httpx.HttpStatusError`` will be raised.

    >>> # access the returned data
    >>> s.data
    {'data': 'this is a cube!',
     'error': None,
     'inconfig': {'release': 'DR16'},
     'status': 1,
     'traceback': None}

To send requests to different urls on a single API, you can pass an explicit url or route segment into the
``request`` method instead of during client instantiation.  Let's send a public request to retrieve cube information for
MaNGA galaxy "8485-1901" on release DR15.
::

    >>> # load the client with the proper API
    >>> s = SDSSClient(use_api='marvin', domain='dr15', release='DR15')

    >>> # send a POST request
    >>> s.request('cubes/8485-1901/', method='post')

The full url is ``https://dr15.sdss.org/marvin/api/cubes/8485-1901/`` but we only need to input the portion of the url relative
to the base url, often referred to as "route", "segment", or "path".  We can access the response data as before.  In this case,
the response is a dictionary with galaxy metadata contained in a "data" key.
::

    >>> # access the data
    >>> s.data
    {'data': {'dec': 48.6902009334, 'header': ...,
              'mangaid': '1-209232',
              'plateifu': '8485-1901',
              'ra': 232.544703894,
              'redshift': 0.040744692,
              'shape': [34, 34],
              'wavelength': [3621.6, 3622.43, ..],
              ...
              }
     'error': None,
     'status': 1
    }


    >>> # access the manga ID, the RA and Dec, and redshift
    >>> s.data['data']['mangaid'], s.data['data']['ra'], s.data['data']['dec'], s.data['data']['redshift']
    ('1-209232', 232.544703894, 48.6902009334, 0.040744692)

The underlying http response is available in the ``response`` attribute.
::

    >>> # access the httpx response
    >>> s.response
    <Response [200 OK]>

For direct access to the ``httpx`` client, use the ``client`` attribute.
::

    >>> # access the raw httpx client or async client
    >>> s.client
    <httpx.Client at 0xb1ca12d30>

By default, the ``SDSSClient`` uses a generic "sdss" user; see :ref:`auth` for more information.
::

    >>> # look at the user attached to the client
    >>> s.user
    <User("sdss", netrc=True, htpass=False, cred=False)>


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
     Domain(name='dr16.sdss.org', public=True, description='public domain for DR16 data access'),
     Domain(name='localhost', public=False, description='domain when running services locally')]

or you can list the available APIs.
::

    >>> # list the APIs
    >>> apim.list_apis()
    [<ApiProfile("marvin", current_domain="dr15.sdss.org", url="https://dr15.sdss.org/marvin/api")>,
     <ApiProfile("icdb", current_domain="internal.sdss.org", url="https://internal.sdss.org/collaboration/api")>,
     <ApiProfile("valis", current_domain="api.sdss.org", url="https://api.sdss.org/valis")>]

APIs can be accessed on the ``apis`` attribute.
::

    >>> # access the available APIs
    >>> apim.apis
    {'marvin': <ApiProfile("marvin", current_domain="sas.sdss.org", url="https://sas.sdss.org/marvin/api")>,
     'icdb': <ApiProfile("icdb", current_domain="internal.sdss.org", url="https://internal.sdss.org/collaboration/api")>,
     'valis': <ApiProfile("valis", current_domain="api.sdss.org", url="https://api.sdss.org/valis")>}

    >>> # select the marvin API
    >>> apim.apis['marvin']
    <ApiProfile("marvin", current_domain="sas.sdss.org", url="https://sas.sdss.org/marvin/api")>

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

Displaying the API information will also include any links to API documentation that exists for the given API.
::

    >>> apim.display('apis')
    <Table length=3>
     key        base                       description                    ...  auth                               docs
     str6      str13                          str48                       ...  str5                              object
    ------ ------------- ------------------------------------------------ ... ----- ---------------------------------------------------------------
    marvin        marvin          API for accessing MaNGA data via Marvin ... token https://sdss-marvin.readthedocs.io/en/stable/reference/web.html
      icdb collaboration API for accessing SDSS collaboration information ... netrc                                                            None
     valis         valis                         API for SDSS data access ... netrc                                                            None

The ``ApiManager`` also provides a mechanism for identifying an API and domain given a url string.
::

    >>> # attempt to identify a domain and API
    >>> apim.identify_api_from_url('https://dr15.sdss.org/marvin/api')
    ('marvin', 'dr15')


.. _apiprofile:

The Api Profile
---------------

Just as ``sdssdb`` database profiles in ``sdssdb.yml`` define connections to different SDSS databases and map to
`~sdssdb.connection.DatabaseConnection` objects, API profiles defined in ``api_profiles.yml`` define connections to
available SDSS APIs, and map to `~sdss_brain.api.manager.ApiProfile` objects.

Each API profile carries with it a list of domains and/or mirrors the API can be accessed on, any authentication type needed
for access, and the currently constructed root or base url for accessing content on that API.

The following examples are written using the MaNGA Marvin API, but the same applies to any other API.  By default, an
API is set to use the first domain in the list of domains, and will construct the base url for the API on that domain.
::

    >>> # access the "marvin" API profile
    >>> from sdss_brain.api.manager import ApiProfile
    >>> prof = ApiProfile('marvin')
    >>> prof
    <ApiProfile("marvin", current_domain="sas.sdss.org", url="https://sas.sdss.org/marvin/api")>

You can view the available domains.
::

    >>> # display the list of available domains
    >>> prof.domains
    {'sas': Domain(name='sas.sdss.org', public=False, description='domain for accessing various SAS services'),
     'lore': Domain(name='lore.sdss.utah.edu', public=False, description='domain for accessing internal content on SDSS host lore'),
     'dr15': Domain(name='dr15.sdss.org', public=True, description='public domain for DR15 data access'),
     'dr16': Domain(name='dr16.sdss.org', public=True, description='public domain for DR16 data access'),
     'local': Domain(name='localhost', public=False, description='domain when running services locally')}

You can change the domain the API uses to any other available one.  Let's change to the DR15 domain.
::

    >>> # change to dr15.sdss.org
    >>> prof.change_domain('dr15')
    >>> prof
    <ApiProfile("marvin", current_domain="dr15.sdss.org", url="https://dr15.sdss.org/marvin/api")>

The base url has now been updated.  For development, we often set up a system on a localhost domain.  ``localhost`` domains
require a port number or ngrok id to be given as input.  `ngrok <https://ngrok.com/>`_ is a service used for opening up local
web servers publicly.
::

    >>> # change to localhost domain on port 5000
    >>> prof.change_domain('local', port=5000)
    >>> prof.url
    'http://localhost:5000/marvin/api'

    >>> # change to localhost domain served with ngrok
    >>> prof.change_domain('local', ngrokid=12345)
    >>> prof.url
    'http://12345.ngrok.io/marvin/api'

Often APIs have test sites available to check changes and new features before pushing to production.  These paths can be
accessed with the ``change_path`` method.  Setting the ``test=True`` keyword switches the path to the designated test site.
Calling ``change_path`` without arguments sets the API to its production path.

::

    >>> # change back to the production site on the SAS domain
    >>> prof.change_domain('sas')
    >>> prof.url
    'https://sas.sdss.org/marvin/api'

    >>> # change to the test site
    >>> prof.change_path(test=True)
    >>> prof.url
    'https://sas.sdss.org/test/marvin/api'

    >>> # switch back to production
    >>> prof.change_path()
    >>> prof.url
    'https://sas.sdss.org/marvin/api'

The ``url`` attribute always defines the base url to the top level API.  To build urls that point to specific routes on the
API, use the ``construct_route`` method.  Let's construct a new url to access the cube data for MaNGA galaxy "8485-1901".
::

    >>> # build a new url to a specific known API route
    >>> prof.construct_route('cubes/8485-1901/')
    'https://sas.sdss.org/marvin/api/cubes/8485-1901/'



Defining a new API Profile
--------------------------

Once a new API has been built, to make it available to ``sdss_brain``, a new profile must be created in the
``python/sdss_brain/etc/api_profiles.yml`` YAML file in the `sdss_brain Github repo <https://github.com/sdss/sdss_brain>`_.
A new API is defined using the following schema:
::

    schema:
      base: the base name of the API. Required.
      domains: the domains where the API is active. Required.
      description: a brief description of the API purpose
      docs: a url link to any API documentation
      mirrors: the domains for possible mirrors
      stems: path stems to denote test or alternate servers
        test: the name of the development stem.
        affix: whether the alternate base is a prefix or suffix
      api: whether the API is under an "api" stem
      routemap: an API route relative to the base url that returns the available routes on the given API
      auth: the type of authentication the API needs for non-public APIs
        type: whether the auth is netrc or token
        route: the API route relative to the base url to use for retrieving a token

Only the first two items, ``base`` and ``domains`` are required entries.  As an example, let's create an entry for a fake
API called "infoviz" available on domains "sas.sdss.org" and "dr15.sdss.org".  It also has a test server located at
``sas.sdss.org/dev/infoviz``.  Our profile entry would like that:
::

    apis:
      info:
        base: infoviz
        domains:
          - sas
          - dr15
        stems:
          test: dev
          affix: prefix

An `~sdss_brain.api.manager.ApiProfile` is automatically constructed and is made accessible via the
`~sdss_brain.api.manager.ApiManager`.
::

    >>> from sdss_brain.api.manager import apim

    >>> # load our new infoviz API
    >>> info = apim.apis['info']
    >>> info
    <ApiProfile("info", current_domain="sas.sdss.org", url="https://sas.sdss.org/infoviz")>

    >>> # access the test server
    >>> info.change_path(test=True)
    >>> info
    <ApiProfile("info", current_domain="sas.sdss.org", url="https://sas.sdss.org/dev/infoviz")>

We can now construct urls to access specific routes on this API.
::

    >>> info.construct_route('/getinfo/here/')
    'https://sas.sdss.org/dev/infoviz/getinfo/here/'


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