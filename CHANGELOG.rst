.. _sdss_brain-changelog:

==========
Change Log
==========

# :support:`23` switches docs Sphinx theme to Furo
* :feature:`21` adds support for API auth token refreshing
* :support:`16` updates User and Netrc support for ``sdss5`` user

* :release:`0.3.1 <2020-11-20>`
* :support:`-` adding ``change_domain`` convenience method to ``ApiHandler``
* :support:`-` raising exception when invalid users attempts to set a work release or IPL
* :bug:`-` fixing ``Brain`` ``__del__`` dunder to exit cleanly when `db` and `remote` are None

* :release:`0.3.0 <2020-11-06>`
* :support:`-` adds function, ``send_post_request``, for sending simple ``httpx`` POST requests
* :support:`-` adds support classes, ``User``, ``Netrc``, ``Htpass`` for user authentication
* :feature:`-` adds convenience class for sending http requests, ``SDSSClient``, ``SDSSAsyncClient``
* :support:`-` adds classes ``ApiManager``, ``Domain`` for API management
* :feature:`-` adds ``ApiProfile`` class for constructing API connections
* :feature:`6` adds ``ApiHandler`` class to support adding remote API data access to tools

* :release:`0.2.0 <2020-10-20>`
* :feature:`5` adds ``DatabaseHandler`` class to support `sdssdb` database objects

* :release:`0.1.3 <2020-10-18>`
* :bug:`-` fixing github actions release yaml

* :release:`0.1.2 <2020-10-18>`
* :feature:`9` adds ability to specify work versions to access unreleased data products
* :support:`7` issues a warning when a mismatch is found between extracted filename version and the release or work version
* :feature:`-` adds new convenience spectrum tools, ``Eboss``, ``MangaCube``, ``ApStar``, ``ApVisit``, and ``AspcapStar``
* :feature:`-` adds simple IO functions ``load_fits_file`` and ``load_from_url``
* :feature:`1` adds a base ``Spectrum`` class to handle spectral data

* :release:`0.1.1 <2020-10-09>`
* :feature:`-` added decorators, `access_loader`, `parser_loader`, `sdss_loader` to reduce boilerplate for overriding abstract methods
* :feature:`-` added new ``BrainNoAccess`` class to support non sdss_access paths
* :feature:`-` added new ``MMAccess`` mixin combining ``AccessMixIn`` and ``MMAMixIn``
* :feature:`-` split out `sdss_access` parts into new ``AccessMixIn``.
* :bug:`2` fixed conflict between loading files and `sdss_access` necessary path parameters

* :release:`0.1.0 <2020-03-20>`
* :feature:`-` Initial release of `sdss_brain`
* :feature:`-` new mixin class, ``MMAMixIn``, aids implementation of multi-modal data access
* :feature:`-` new ``Brain`` class, helper class to subclass new tools from
* :feature:`-` new global ``Config`` class, to control global configuration handling across SDSS tools
