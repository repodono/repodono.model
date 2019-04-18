import unittest
import regex

from uritemplate import URITemplate

from repodono.model.urimatch import template_to_regex_patternstr
from repodono.model.urimatch import check_variable
from repodono.model.urimatch import match
from repodono.model.urimatch import URITemplateMatcher
from repodono.model.urimatch import URITemplateRouter


class BaseTestCase(unittest.TestCase):

    def test_check_variable(self):
        with self.assertRaises(ValueError) as e:
            check_variable('name')

        self.assertEqual(
            "'variable' argument must be a URIVariable",
            str(e.exception)
        )

        failure = URITemplate('{bad,name}')
        with self.assertRaises(ValueError) as e:
            check_variable(failure.variables[0])

        self.assertEqual(
            'multiple variables {bad,name} not supported',
            str(e.exception)
        )


class ValidityTestCase(unittest.TestCase):

    def assertSupported(self, tmplstr):
        template = URITemplate(tmplstr)
        self.assertTrue(
            template_to_regex_patternstr.supported(template),
            "%r should be a valid template but is marked as invalid" % tmplstr
        )

    def assertUnsupported(self, tmplstr):
        template = URITemplate(tmplstr)
        self.assertFalse(
            template_to_regex_patternstr.supported(template),
            "%r should be an invalid template but is marked as valid" % tmplstr
        )

    def test_valid_templates(self):
        self.assertSupported('/{count}')
        self.assertSupported('{/count*}')
        self.assertSupported('/target{?foo}')

    def test_invalid_templates(self):
        self.assertUnsupported('{count}')  # missing leading /
        self.assertUnsupported('{}')
        self.assertUnsupported('/target?foo={count}')
        self.assertUnsupported('/{x,y}')
        self.assertUnsupported('/{+values}')
        self.assertUnsupported('{/values}/{values}')
        self.assertUnsupported('/{x,y}/{y}')


class TemplateRegexFactoryTestCase(unittest.TestCase):

    def test_basic(self):
        template = URITemplate('/root/{target}{/path*}')
        rule = regex.compile(template_to_regex_patternstr(template))
        match = rule.match('/root/some_target/a/nested/path')
        self.assertEqual(
            # TODO figure out how to remap it all back down to a string
            # for the dumb tokens?
            ['some_target'],
            match.captures('target'),
        )
        self.assertEqual(
            ['a', 'nested', 'path'],
            match.captures('path'),
        )

    def test_suffixed(self):
        template = URITemplate('/root/{target}{/path*}/somewhere')
        rule = regex.compile(template_to_regex_patternstr(template))
        self.assertFalse(rule.match('/root/some_target/a/nested/path'))

        match = rule.match('/root/some_target/a/nested/path/somewhere')
        self.assertEqual(
            ['a', 'nested', 'path'],
            match.captures('path'),
        )

        match = rule.match('/root/some_target/a/path/somewhere')
        self.assertEqual(
            ['a', 'path'],
            match.captures('path'),
        )


class UriMatchTestCase(unittest.TestCase):

    def test_simple_variable_matcher(self):
        template = URITemplate('/{count}')
        url = '/123'
        result = match(template, url)
        self.assertEqual({
            'count': '123',
        }, result)

    def test_no_match(self):
        template = URITemplate('/{count}')
        url = '123'
        result = match(template, url)
        self.assertIsNone(result)

    def test_single_path_matcher(self):
        template = URITemplate('{/count}')
        url = '/root/foo/bar'
        result = match(template, url)
        # nothing because additional path segment separator which does
        # not match.
        self.assertIsNone(result)

    def test_multi_path_matcher(self):
        template = URITemplate('{/path*}')
        url = '/one%2Ctwo%2Cthree/some/path'
        result = match(template, url)
        self.assertEqual({
            'path': ['one%2Ctwo%2Cthree', 'some', 'path'],
        }, result)

    def test_interim_query(self):
        # query variables are not exactly implemented due to significant
        # complexities involved with integration with various platforms
        # and frameworks.
        template = URITemplate('/{root}/somewhere{?hello}')
        url = '/value/somewhere'
        matcher = URITemplateMatcher(template)
        result = matcher(url)
        # missing values ignored
        self.assertEqual({
            'root': 'value',
        }, result)


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
