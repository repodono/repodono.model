import unittest
import regex

from uritemplate import URITemplate

from repodono.model.urimatch import template_to_regex_patternstr
from repodono.model.urimatch import check_variable
from repodono.model.urimatch import match


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
        # TODO whether empty results are good for no match.
        self.assertEqual({}, result)

    def test_single_path_matcher(self):
        template = URITemplate('{/count}')
        url = '/root/foo/bar'
        result = match(template, url)
        # no match because too long
        self.assertEqual({}, result)

    def test_multi_path_matcher(self):
        template = URITemplate('{/path*}')
        url = '/one%2Ctwo%2Cthree/some/path'
        result = match(template, url)
        self.assertEqual({
            'path': ['one%2Ctwo%2Cthree', 'some', 'path'],
        }, result)
