import unittest

from uritemplate import URITemplate
from repodono.model.routing import URITemplateRouter


class URITemplateRouterTestCase(unittest.TestCase):

    def test_standard_construction(self):
        router = URITemplateRouter([
            URITemplate('/e/{target}'),
            URITemplate('/e/{target}{/path*}'),
            URITemplate('/e/{target}{/path*}/alternate/{view}'),
            URITemplate('/w/{target}{/path*}'),
            URITemplate('/w/{target}{/path*}/view'),
            URITemplate('/w/{target}{/path*}/index'),
        ])

        self.assertEqual(('/e/{target}', {
            'target': 'hello',
        }), router('/e/hello'))

        self.assertEqual(('/e/{target}{/path*}', {
            'target': 'a_target',
            'path': ['some', 'path', 'down', 'the', 'line'],
        }), router('/e/a_target/some/path/down/the/line'))

        self.assertEqual(('/e/{target}{/path*}/alternate/{view}', {
            'view': 'some_view',
            'target': 'a_target',
            'path': ['short', 'path'],
        }), router('/e/a_target/short/path/alternate/some_view'))

        self.assertEqual(('/w/{target}{/path*}', {
            'target': 'other_target',
            'path': ['some', 'other', 'path'],
        }), router('/w/other_target/some/other/path'))

        self.assertEqual(('/w/{target}{/path*}/view', {
            'target': 'other_target',
            'path': ['some', 'other', 'path'],
        }), router('/w/other_target/some/other/path/view'))

        self.assertIsNone(router('/e/+wat'))
        self.assertIsNone(router('/z/nowhere/short/path/alternate/some_view'))
        self.assertIsNone(router('/w/not_enough'))

    def test_from_list_of_strings(self):
        router = URITemplateRouter.from_strings([
            '/e/{target}',
            '/e/{target}{/path*}',
            '/e/{target}{/path*}/alternate/{view}',
            '/w/{target}{/path*}',
            '/w/{target}{/path*}/view',
            '/w/{target}{/path*}/index',
        ])

        self.assertEqual(('/e/{target}', {
            'target': 'goodbye',
        }), router('/e/goodbye'))

        self.assertEqual(('/w/{target}{/path*}/index', {
            'target': 'primary',
            'path': ['path', 'to', 'the'],
        }), router('/w/primary/path/to/the/index'))
