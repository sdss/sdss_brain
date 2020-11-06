
.. _auth:

Users and Authentication
========================

To access proprietary, or un-released, SDSS data, on the Science Archive Server (SAS) or on any available SDSS API service,
you must be a valid member of the SDSS collaboration.  If you are unsure if you're a member of the SDSS collaboration, check
the list of `SDSS-V <https://www.sdss5.org/collaboration/affiliate-institutions/>`_, or
`SDSS-IV <https://www.sdss.org/collaboration/affiliations/>`_ affiliate institutions.  If you know you're a member, you can try
accessing the `SDSS Collaboration site <https://internal.sdss.org/collaboration/home>`_ and logging in to your account.

.. _netrc:

Netrc Authentication
--------------------

SDSS uses ``.netrc`` authentication to access data content on many domains. To set this up, create and
edit a file in your home directory ocalled ``.netrc`` and copy these lines inside::

    machine api.sdss.org
       login <username>
       password <password>

    machine data.sdss.org
       login <username>
       password <password>

Replace ``<username>`` and ``<password>`` with your login credentials. The default SDSS username and
password is also acceptable for anonymous access.  **Finally, run** ``chmod 600 ~/.netrc`` **to make
the file only accessible to your user.**

.. _token:

Token Authentication
--------------------

Most APIs use ``netrc`` authentication, but some APIs require token authentication, such as
`JWT <https://jwt.io/introduction/>`_ or Oauth tokens.  You check which authentication type an API uses with the ``auth_type``
attribute on a given `~sdss_brain.api.manager.ApiProfile`.  It can either be set to "token" or "netrc".
::

    >>> from sdss_brain.api.manager import apim

    >>> # check the auth_type for the MaNGA Marvin API
    >>> profile = apim.apis['marvin']
    >>> prof.auth_type
    'token'

To check if a valid token is already set, access the ``token`` attribute or use the
`~sdss_brain.api.manager.ApiProfile.check_for_token` method.
::

    >>> # check for a valid token
    >>> prof.check_for_token()
    None

``check_for_token`` looks for a valid API token in your list of environment variables or as a parameter set on your custom
``sdss_brain.yml`` configuration file.  To retrieve a valid token, use the `~sdss_brain.api.manager.ApiProfile.get_token`
method.  Tokens are mapped to specific users, either the "sdss" user or your SDSS username.  The ``get_token`` method
looks for user credentials in your ``.netrc`` file, so make sure you pass the username that is listed under the
``api.sdss.org`` machine in your ``.netrc``.
::

    >>> # get a valid token for the generic SDSS user
    >>> token = prof.get_token('sdss')

This returns a new token valid only for the specific API.  To permanently set this token, you will need to set it as an
**[NAME]_API_TOKEN** environment variable or as a **[name]_api_token** parameter in your ``sdss_brain.yml`` custom configuration
file.  **[NAME]** references the name of the specific API.  For example, with the "marvin" API, you would set either
a **MARVIN_API_TOKEN** environment variable or **marvin_api_token** configuration parameter.
::

    # in your .bashrc
    MARVIN_API_TOKEN=[token]

    # in your sdss_brain.yml configuration
    marvin_api_token: [token]

The `~sdss_brain.api.client.SDSSClient` will also check for valid tokens when sending requests on APIs that use ``token``
authentication.  The ``SDSSClient`` will check for a valid token for its currently set `~sdss_brain.auth.user.User` on
its currently set `~sdss_brain.api.manager.ApiProfile`.  If you haven't already set a token, you can do so with the
client's `~sdss_brain.api.client.SDSSClient.get_token` method.


.. _users:

Users
-----

Remote data access requires a valid SDSS user, represented by the `~sdss_brain.auth.user.User` class.  A user can be validated
either with ``.netrc`` or SDSS credentials, as indicated with the ``netrc`` and ``cred`` indicators in the ``repr``.
Alternatively, you can check with the ``user.is_netrc_valid`` and ``user.is_sdss_valid`` properties.

The "sdss" user
^^^^^^^^^^^^^^^

By default ``sdss_brain`` sets the default user in the global config to the generic "sdss" user.  The "sdss" user is the default
used for all remote data access and API requests using `~sdss_brain.api.client.SDSSClient`.
::

    >>> # create an sdss user
    >>> user = User('sdss")
    >>> user
    <User("sdss", netrc=True, htpass=False, cred=False)>

Depending on how you set up your ``.netrc`` authentication, the sdss user may be already netrc validated.  Otherwise your
collaboration user will be.  To change the default user used by ``sdss_brain``, use the `~sdss_brain.config.Config.set_user`
method on the config.  Alternatively, you can also set the ``default_user`` parameter in your ``sdss_brain.yml`` configuration
file.
::

    >>> # set the global user
    >>> from sdss_brain.config import config
    >>> config.set_user('jad29')

The "collaboration" user
^^^^^^^^^^^^^^^^^^^^^^^^

If the "sdss" user is not sufficient, you can always use your SDSS collaboration username.
::

    >>> # create a new user with your username
    >>> user = User('jad29')
    >>> user
    <User("jad29", netrc=False, htpass=False, cred=False)>

The user may not be validated.  Validate the user with your SDSS Credentials using `~sdss_brain.auth.user.User.validate_user`.
::

    >>> # validate the user with your SDSS password
    >>> user.validate_user('xxxxxx')
    >>> user
    <User("jad29", netrc=False, htpass=False, cred=True)>

    >>> # check for valid credentials
    >>> user.is_sdss_cred_valid
    True

Once validated, you can also check member status in SDSS.
::

    >>> # check status in SDSS
    >>> user.in_sdss
    {'sdss4': True, 'sdss5': True}

    >>> # access member information
    >>> user.member
    {'sdss4': {'email': 'jad@university.edu',
               'fullname': 'John Doe',
               'has_sdss_access': True,
               'username': 'jad29'},
     'sdss5': {'email': 'jad@university.edu',
               'fullname': 'John Doe',
               'has_sdss_access': True,
               'username': 'jdoe1234'}
    }