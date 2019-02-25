import unittest

from uritemplate import URITemplate

from repodono.model.urimatch import match
from repodono.model.urimatch import validate


class ValidityTestCase(unittest.TestCase):

    def assertSupported(self, tmplstr):
        template = URITemplate(tmplstr)
        self.assertTrue(
            validate(template),
            "%r should be a valid template but is marked as invalid" % tmplstr
        )

    def assertUnsupported(self, tmplstr):
        template = URITemplate(tmplstr)
        self.assertFalse(
            validate(template),
            "%r should be an invalid template but is marked as valid" % tmplstr
        )

    def test_valid_templates(self):
        self.assertSupported('/{count}')
        self.assertSupported('{/count*}')
        self.assertSupported('/target{?foo}')

    def test_invalid_templates(self):
        self.assertUnsupported('{count}')  # missing leading /
        self.assertUnsupported('/target?foo={count}')


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
