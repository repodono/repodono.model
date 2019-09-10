import unittest

from uritemplate import URITemplate
from repodono.model.routing import URITemplateRouter


class URITemplateRouterTestCase(unittest.TestCase):

    def test_unacceptable_route(self):
        # TODO decide whether failing all routes because one route has
        # failed is intended.
        with self.assertRaises(ValueError):
            URITemplateRouter([
                URITemplate('{target}'),
                URITemplate('/{target}'),
            ])

    def assertRouting(self, uri, template_str, variables):
        self.assertEqual((template_str, variables), self.router(uri))
        # test that the round-trip back to the uri actuallyworks.
        self.assertEqual(URITemplate(template_str).expand(**variables), uri)

    def test_assertion_sane(self):
        # just lazily inline this test here.
        def fake_router(uri):
            return ('good', {},)

        self.router = fake_router
        self.assertRouting('good', 'good', {})

        with self.assertRaises(AssertionError):
            # fail the first equality
            self.assertRouting('bad', 'bad', {})

        with self.assertRaises(AssertionError):
            # fail the second equality
            self.assertRouting('', 'good', {})

    def test_standard_construction(self):
        self.router = URITemplateRouter([
            URITemplate('/e/{target}'),
            URITemplate('/e/{target}{/path*}'),
            URITemplate('/e/{target}{/path*}/alternate/{view}'),
            URITemplate('/w/{target}{/path*}'),
            URITemplate('/w/{target}{/path*}/view'),
            URITemplate('/w/{target}{/path*}/index'),
        ])

        self.assertRouting(
            '/e/hello', '/e/{target}', {
                'target': 'hello',
            }
        )

        self.assertRouting(
            '/e/a_target/some/path/down/the/line',
            '/e/{target}{/path*}', {
                'target': 'a_target',
                'path': ['some', 'path', 'down', 'the', 'line'],
            }
        )

        self.assertRouting(
            '/e/a_target/short/path/alternate/some_view',
            '/e/{target}{/path*}/alternate/{view}', {
                'view': 'some_view',
                'target': 'a_target',
                'path': ['short', 'path'],
            }
        )

        self.assertRouting(
            '/w/other_target/some/other/path',
            '/w/{target}{/path*}', {
                'target': 'other_target',
                'path': ['some', 'other', 'path'],
            }
        )

        self.assertRouting(
            '/w/other_target/some/other/path/view',
            '/w/{target}{/path*}/view', {
                'target': 'other_target',
                'path': ['some', 'other', 'path'],
            }
        )

        self.assertIsNone(
            self.router('/e/+wat'))
        self.assertIsNone(
            self.router('/z/nowhere/short/path/alternate/some_view'))

        self.assertRouting(
            '/w/not_enough',
            '/w/{target}{/path*}', {
                'target': 'not_enough',
                'path': [],
            }
        )

        self.assertRouting(
            '/w/other_target/view',
            '/w/{target}{/path*}/view', {
                'target': 'other_target',
                'path': [],
            }
        )

    def test_from_list_of_strings(self):
        self.router = URITemplateRouter.from_strings([
            '/e/{target}',
            '/e/{target}{/path*}',
            '/e/{target}{/path*}/alternate/{view}',
            '/w/{target}{/path*}',
            '/w/{target}{/path*}/view',
            '/w/{target}{/path*}/index',
        ])

        self.assertRouting(
            '/e/goodbye',
            '/e/{target}', {
                'target': 'goodbye',
            }
        )

        self.assertRouting(
            '/w/primary/path/to/the/index',
            '/w/{target}{/path*}/index', {
                'target': 'primary',
                'path': ['path', 'to', 'the'],
            }
        )
