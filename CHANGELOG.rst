.. _sdss_brain-changelog:

==========
Change Log
==========

* :release:`0.1.2 <unknown>`
* :feature:`-` adds new convenience spectrum tools, ``Eboss``, ``MangaCube``, ``ApStar``, ``ApVisit``, and ``AspcapStar``
* :feature:`-` adds simple IO functions ``load_fits_file`` and ``load_from_url``
* :feature:`1` adds a base ``Spectrum`` class to handle spectral data

* :release:`0.1.1 <2020-10-09>`
* :feature:`-` added decorators, `access_loader`, `parser_loader, `sdss_loader` to reduce boilerplate for overriding abstract methods
* :feature:`-` added new ``BrainNoAccess`` class to support non sdss_access paths
* :feature:`-` added new ``MMAccess`` mixin combining ``AccessMixIn`` and ``MMAMixIn``
* :feature:`-` split out `sdss_access` parts into new ``AccessMixIn``.
* :bug:`2` fixed conflict between loading files and `sdss_access` necessary path parameters

* :release:`0.1.0 <2020-03-20>`
* :feature:`-` Initial release of `sdss_brain`
* :feature:`-` new mixin class, ``MMAMixIn``, aids implementation of multi-modal data access
* :feature:`-` new ``Brain`` class, helper class to subclass new tools from
* :feature:`-` new global ``Config`` class, to control global configuration handling across SDSS tools
