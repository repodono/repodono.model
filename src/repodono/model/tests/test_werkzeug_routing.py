"""
Currently just a note

>>> from uritemplate import URITemplate
>>> from werkzeug.routing import Map
>>> from repodono.model.urimatch_flask import URITemplateRule
>>> m = Map([
...     URITemplateRule(URITemplate('/'), endpoint='root'),
...     URITemplateRule(URITemplate('/browse/'), endpoint='entry'),
...     URITemplateRule(URITemplate('/browse/{id}/'), endpoint='entry/id'),
...     URITemplateRule(URITemplate('/browse/{id}{/path*}'), endpoint='path')
... ]).bind('example.com')
>>> m.match('/')
('kb/index', {})
>>> m.match('/browse/1/3')
('kb/browse', {'id': 1, 'page': 3})
"""

import unittest

try:
    from werkzeug.routing import Map, Rule
    from repodono.model import urimatch_flask
except ImportError:  # pragma: no cover
    skip = True
else:
    skip = False


@unittest.skipIf(skip, "werkzeug package not available")
class WerkzeugRoutingTestCase(unittest.TestCase):

    def test_basic(self):
        m = Map([
            Rule('/', endpoint='kb/index'),
        ])
        urimatch_flask
        return m
