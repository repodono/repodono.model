import unittest
from collections import namedtuple

from uritemplate import URITemplate

try:
    from sanic.router import Router
    from sanic.exceptions import NotFound
except ImportError:  # pragma: no cover
    skip = True
else:
    skip = False

from repodono.model.urimatch_sanic import templateuri_to_sanic_routeuri


FakeRequest = namedtuple('FakeRequest', ['path', 'method'])


def make_request(path, method='GET'):
    return FakeRequest(path, method)


@unittest.skipIf(skip, "sanic package not available")
class SanicRouterTestCase(unittest.TestCase):

    def test_basic(self):
        router = Router()
        template = URITemplate('/root')
        routeuri = templateuri_to_sanic_routeuri(template)
        router.add(routeuri, ['GET'], 'root')
        request = make_request('/root')
        self.assertEqual(('root', [], {}, routeuri,), router.get(request))

    def test_fail_on_partial(self):
        router = Router()
        template = URITemplate('/rooted')
        routeuri = templateuri_to_sanic_routeuri(template)
        router.add(routeuri, ['GET'], 'root')
        request = make_request('/root')
        with self.assertRaises(NotFound):
            router.get(request)

        request = make_request('/roottedmore')
        with self.assertRaises(NotFound):
            router.get(request)

    def test_basic_target_path(self):
        router = Router()
        template = URITemplate('/root/{target}{/path*}')
        routeuri = templateuri_to_sanic_routeuri(template)
        # have to use strict slashes to avoid ambiguity.
        router.add(routeuri, ['GET'], 'root-target-path', strict_slashes=True)
        request = make_request('/root/base/some/test/path')
        self.assertEqual((
            'root-target-path',
            [], {
                'target': 'base',
                'path': '/some/test/path',
            },
            routeuri,
        ), router.get(request))

        request = make_request('/root/base/some/test/path/')
        with self.assertRaises(NotFound):
            router.get(request)
