repodono.model
==============

Foundation to the runtime and execution model for repodono framework.

.. image:: https://github.com/repodono/repodono.model/actions/workflows/build.yml/badge.svg?branch=master
    :target: https://github.com/repodono/repodono.model/actions/workflows/build.yml?query=branch:master
.. image:: https://ci.appveyor.com/api/projects/status/2tanwnx1vmssb4pb/branch/master?svg=true
    :target: https://ci.appveyor.com/project/metatoaster/repodono-model/branch/master
.. image:: https://coveralls.io/repos/github/repodono/repodono.model/badge.svg?branch=master
    :target: https://coveralls.io/github/repodono/repodono.model?branch=master


Introduction
------------

This project is currently under planning and initial phase of
development.


Features
--------

The following are a list of features currently being implemented.

Base Environment
~~~~~~~~~~~~~~~~

An ``Environment`` mapping class that would load a toml configuration
string that has the following three sections:

.. code:: toml

    [environment.variables]
    title = "Example site"

    [environment.paths]
    site_root = "/var/www/site.example.com"

    [[environment.objects]]
    __name__ = "a_thing"
    __init__ = "repodono.model.testing:Thing"
    path = "site_root"

The resulting instance will have keys of the specific required types as
defined by the class constructor for each of the sections.

.. code:: pycon

    >>> from repodono.model.config import Configuration
    >>> from repodono.model.environment import Environment
    >>> env = Environment(Configuration(config_string))
    >>> env['a_thing']
    <repodono.model.testing.Thing object at 0x7f79dd31b828>
    >>> env['a_thing'].path
    PosixPath('/var/www/site.example.com')
    >>> env['site_root']
    PosixPath('/var/www/site.example.com')

Generic routing specification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For specifying variables to be made available for a given route/endpoint
acceptable for the generated application, the routes are defined using a
subset of the syntax as defined in RFC 6570 - URI Template.

The reason for this limitation is done for practical reasons, as there
are existing routing frameworks that have their own specific limitations
and thus keeping to a common subset will ease the conversion to handlers
for those frameworks.

Currently, the supported variable definitions are:

- Standard expansion or a series of one, e.g. ``/work/{id}/{option}``
- Slash-prefixed path fragments, e.g. ``/root{/some_path*}``

  - One of the more generally targeted usage for server side routing.

Restrictions that may be lifted:

- Standard expansion with length modifiers, e.g. ``{var:3}``
- Reserved expansion: while too vague and can conflict with path
  fragment expansion.  e.g. ``/{+some_var}``, some target framework does
  explicitly support this in some form so this has to be brought into
  consideration.

Restrictions that are unlikely to be supported in the future:

- All routes must begin with '/'
- Standard expansion with value modifiers ``/{var*}``
- Path-style parameters, semicolon-prefixed.  e.g. ``/{;some_var}``
- Any additional interpretation of standard expansion
- Multiple variables expressions are not supported (e.g. ``/{x,y}``,
  write instead ``/{x},{y}``)
- Fragment expansions will be ignored (as fragments are typically not
  submitted to the server by clients through http).
- Form-style query ignored (as supported backend targets typically have
  their own implementation for dealing with query fragments sent by
  clients.  Thus everything after a query token ``?`` will be ignored.
- Standard expansion with value modifiers ``{var*}``

Defined constants from configuration bound to execution locals
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``__route__``

    The current route.
