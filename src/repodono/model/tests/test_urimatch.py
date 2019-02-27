import unittest

from uritemplate import URITemplate

from repodono.model.urimatch import match
from repodono.model.urimatch import TemplateRegexFactory


class ValidityTestCase(unittest.TestCase):

    validate = TemplateRegexFactory().validate

    def assertSupported(self, tmplstr):
        template = URITemplate(tmplstr)
        self.assertTrue(
            self.validate(template),
            "%r should be a valid template but is marked as invalid" % tmplstr
        )

    def assertUnsupported(self, tmplstr):
        template = URITemplate(tmplstr)
        self.assertFalse(
            self.validate(template),
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


class TemplateRegexFactoryTestCase(unittest.TestCase):

    def test_basic(self):
        template = URITemplate('/root/{target}{/path*}')
        factory = TemplateRegexFactory()
        rule = factory(template)
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
        factory = TemplateRegexFactory()
        rule = factory(template)
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


@unittest.skip("not implemented yet")
class UriMatchTestCase(unittest.TestCase):

    def test_simple_variable_matcher(self):
        template = URITemplate('/{count}')
        url = '/one,two,three'
        result = match(template, url)
        self.assertEqual({
            'count': 'one,two,three',
        }, result)

    def test_single_path_matcher(self):
        template = URITemplate('{/count}')
        url = '/one,two,three'
        result = match(template, url)
        self.assertEqual({
            'count': ['one', 'two', 'three'],
        }, result)

    def test_multi_path_matcher(self):
        template = URITemplate('{/count*}')
        # Note: `,` should be provided as the encoded value `%2C`
        url = '/one,two,three/some/path'
        result = match(template, url)
        self.assertEqual({
            'count': ['one,two,three', 'some', 'path'],
        }, result)
