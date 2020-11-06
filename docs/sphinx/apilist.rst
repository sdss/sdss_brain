
.. _apilist:

Available SDSS Domains and APIs
===============================

.. _domains:

Domains
-------
Available domains hosting various SDSS services

=========  ==================  ========  =========================================================
key        name                public    description
=========  ==================  ========  =========================================================
data       data.sdss.org       False     domain for accessing SDSS data on the SAS
sas        sas.sdss.org        False     domain for accessing various SAS services
api        api.sdss.org        False     domain for accessing SDSS APIs
lore       lore.sdss.utah.edu  False     domain for accessing internal content on SDSS host lore
internal   internal.sdss.org   False     domain for accessing internal SDSS information
magrathea  magrathea.sdss.org  False     mirror domain for SDSS services, e.g. SDSS MaNGA's Marvin
dr15       dr15.sdss.org       True      public domain for DR15 data access
dr16       dr16.sdss.org       True      public domain for DR16 data access
local      localhost           False     domain when running services locally
=========  ==================  ========  =========================================================

.. _apis:

APIs
----
Available APIs serving various SDSS content and/or data

======  =============  ================================================  ============================  =========  ======  ===============================================================
key     base           description                                       domains                       mirrors    auth    docs
======  =============  ================================================  ============================  =========  ======  ===============================================================
marvin  marvin         API for accessing MaNGA data via Marvin           sas, lore, dr15, dr16, local  magrathea  token   https://sdss-marvin.readthedocs.io/en/stable/reference/web.html
icdb    collaboration  API for accessing SDSS collaboration information  internal, local                          netrc
valis   valis          API for SDSS data access                          api, local                               netrc
======  =============  ================================================  ============================  =========  ======  ===============================================================