import unittest

from uritemplate import URITemplate

try:
    from werkzeug.routing import Map
    from werkzeug.exceptions import NotFound
except ImportError:  # pragma: no cover
    skip = True
else:
    skip = False
    from repodono.model.urimatch_flask import URITemplateRule


@unittest.skipIf(skip, "werkzeug package not available")
class URITemplateRuleTestCase(unittest.TestCase):

    def test_basic_route(self):
        rule = URITemplateRule(URITemplate('/browse/{id}'), endpoint='root')
        m = Map()
        m.add(rule)
        bm = m.bind('example.com')
        self.assertEqual('/browse/{id}', str(rule))
        self.assertEqual(('', '/browse/321'), rule.build({'id': '321'}))
        self.assertEqual('/browse/321', bm.build('root', {'id': '321'}))

    def test_build_only(self):
        rule = URITemplateRule(
            '/browse/{id}', endpoint='root', build_only=True)
        m = Map()
        m.add(rule)
        bm = m.bind('example.com')
        self.assertIsNone(rule.match('/browse/123'))
        with self.assertRaises(NotFound):
            bm.match('/browse/123')
        self.assertEqual(('', '/browse/321'), rule.build({'id': '321'}))
        self.assertEqual('/browse/321', bm.build('root', {'id': '321'}))


@unittest.skipIf(skip, "werkzeug package not available")
class WerkzeugRoutingTestCase(unittest.TestCase):

    def test_basic_creation_from_template(self):
        m = Map([
            URITemplateRule(URITemplate('/'), endpoint='root'),
            URITemplateRule(URITemplate('/somewhere'), endpoint='elsewhere'),
        ]).bind('example.com')
        self.assertEqual(('root', {}), m.match('/'))
        self.assertEqual(('elsewhere', {}), m.match('/somewhere'))

        with self.assertRaises(NotFound):
            m.match('/nowhere')

    def test_basic_creation_from_str(self):
        m = Map([
            URITemplateRule('/', endpoint='root'),
            URITemplateRule('/somewhere', endpoint='elsewhere'),
        ]).bind('example.com')
        self.assertEqual(('root', {}), m.match('/'))
        self.assertEqual(('elsewhere', {}), m.match('/somewhere'))

        with self.assertRaises(NotFound):
            m.match('/nowhere')

    def test_with_variables(self):
        m = Map([
            URITemplateRule('/', endpoint='root'),
            URITemplateRule('/browse/', endpoint='entry'),
            URITemplateRule('/browse/{id}/', endpoint='entry/id'),
            # this has to explicitly consume the final '/' path fragment
            URITemplateRule('/browse/{id}{/path*}/', endpoint='entry/id/dir'),
            # before the fully consumed version
            URITemplateRule('/browse/{id}{/path*}', endpoint='entry/id/path'),
        ]).bind('example.com')
        self.assertEqual(('root', {}), m.match('/'))
        # TODO allow this type of redirects to work?
        # self.assertEqual(('entry', {}), m.match('/browse'))

        self.assertEqual(('entry', {}), m.match('/browse/'))
        self.assertEqual(('entry/id', {
            'id': '1',
        }), m.match('/browse/1/'))  # ditto for /browse/1

        # however, if we have this kind of distinction...
        self.assertEqual(('entry/id/path', {
            'id': '1',
            'path': ['some', 'nested', 'path'],
        }), m.match('/browse/1/some/nested/path'))

        # ... this forces endpoint implementation to be explicit about
        # how they handle the paths passed.
        self.assertEqual(('entry/id/dir', {
            'id': '1',
            'path': ['some', 'nested', 'path'],
        }), m.match('/browse/1/some/nested/path/'))

    def test_with_variables_without_trailing_slash(self):
        m = Map([
            URITemplateRule('/', endpoint='root'),
            URITemplateRule('/browse/', endpoint='entry'),
            URITemplateRule('/browse/{id}/', endpoint='entry/id'),
            URITemplateRule('/browse/{id}{/path*}', endpoint='entry/id/path'),
        ]).bind('example.com')
        # unlike the previous where there is a "...{/path*}/" version
        # defined, this will simply be fed into the other view, with
        # path list containing a trailing empty string path fragment.
        self.assertEqual(('entry/id/path', {
            'id': '1',
            'path': ['some', 'nested', 'path', ''],
        }), m.match('/browse/1/some/nested/path/'))

    def test_precedence(self):
        m = Map([
            URITemplateRule('/entry/{id}', endpoint='entry'),
            URITemplateRule('/entry/index', endpoint='entry_index'),
        ]).bind('example.com')
        self.assertEqual(('entry', {'id': '1'}), m.match('/entry/1'))
        self.assertEqual(('entry_index', {}), m.match('/entry/index'))
