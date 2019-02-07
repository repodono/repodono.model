repodono.model
==============

Foundation to the runtime and execution model for repodono framework.

.. image:: https://travis-ci.org/repodono/repodono.model.svg?branch=master
    :target: https://travis-ci.org/repodono/repodono.model
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

.. code:: python

    >>> from repodono.model.config import Configuration
    >>> from repodono.model.environment import Environment
    >>> env = Environment(Configuration(config_string))
    >>> env['a_thing']
    <repodono.model.testing.Thing object at 0x7f79dd31b828>
    >>> env['a_thing'].path
    PosixPath('/var/www/site.example.com')
    >>> env['site_root']
    PosixPath('/var/www/site.example.com')
