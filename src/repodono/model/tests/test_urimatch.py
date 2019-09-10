import unittest
import regex

from uritemplate import URITemplate

from repodono.model.urimatch import template_to_regex_patternstr
from repodono.model.urimatch import check_variable
from repodono.model.urimatch import check_template_leading_slash
from repodono.model.urimatch import match
from repodono.model.urimatch import URITemplateMatcher


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
        self.assertUnsupported('/target?foo={count}')
        self.assertUnsupported('/{x,y}')
        self.assertUnsupported('/{+values}')
        self.assertUnsupported('{/values}/{values}')
        self.assertUnsupported('/{x,y}/{y}')

    def test_no_slash_leading_fail(self):
        with self.assertRaises(ValueError):
            check_template_leading_slash(URITemplate('{}'))

        with self.assertRaises(ValueError):
            check_template_leading_slash(URITemplate('{count}'))

        check_template_leading_slash(URITemplate('/{count}'))


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

    def test_explode_path_cases(self):
        template = URITemplate('{/path*}')
        rule = regex.compile(template_to_regex_patternstr(template))
        self.assertEqual([], rule.match('').captures('path'))
        self.assertIsNone(rule.match('foo'))
        self.assertEqual(
            ['foo', 'bar', 'baz'],
            rule.match('/foo/bar/baz').captures('path'),
        )
        self.assertEqual(
            [''],
            rule.match('/').captures('path'),
        )

    def test_suffixed(self):
        template = URITemplate('/root/{target}{/path*}/somewhere')
        rule = regex.compile(template_to_regex_patternstr(template))
        self.assertFalse(rule.match('/root/some_target/a/nested/path'))

        match = rule.match('/root/some_target/a/nested/path/somewhere')
        self.assertEqual(['some_target'], match.captures('target'))
        self.assertEqual(
            ['a', 'nested', 'path'],
            match.captures('path'),
        )

        match = rule.match('/root/some_target/a/path/somewhere')
        self.assertEqual(['some_target'], match.captures('target'))
        self.assertEqual(
            ['a', 'path'],
            match.captures('path'),
        )

        match = rule.match('/root/some_target//somewhere')
        self.assertEqual(['some_target'], match.captures('target'))
        self.assertEqual([''], match.captures('path'))


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


class URITemplateMatcherTestcase(unittest.TestCase):

    def test_matcher_basics(self):
        static = URITemplateMatcher(URITemplate('/test'))
        self.assertEqual(static('/test'), {})

    def test_matcher_invalid(self):
        with self.assertRaises(ValueError):
            URITemplateMatcher(URITemplate('/{value}/{value}'))

    def test_matcher_equality_static(self):
        first = URITemplateMatcher(URITemplate('/test'))
        second = URITemplateMatcher(URITemplate('/test'))
        self.assertEqual(first, second)

    def test_matcher_equality_dynamic(self):
        first = URITemplateMatcher(URITemplate('/test{/path*}'))
        second = URITemplateMatcher(URITemplate('/test{/path*}'))
        self.assertEqual(first, second)


class URITemplateMatcherSortTestcase(unittest.TestCase):

    def assertSorted(self, templates):
        matchers = sorted(
            URITemplateMatcher(URITemplate(t)) for t in templates)
        self.assertEqual(templates, [
            matcher.template.uri for matcher in matchers])
        self.assertEqual(templates, [
            matcher.template.uri for matcher in sorted(
                list(reversed(matchers)))])

    def test_static(self):
        self.assertSorted([
            '/root/first',
            '/root/second',
        ])

    def test_static_equal(self):
        self.assertSorted([
            '/root/same',
            '/root/same',
        ])

    def test_variables_static_mix(self):
        self.assertSorted([
            '/root/view',
            '/root/{view}',
        ])

    def test_variables_static_mix2(self):
        self.assertSorted([
            '/root/first',
            '/root/second',
            '/root/first/{view}',
            '/root/second/{view}',
        ])

    def test_variable_root_variables_mix(self):
        self.assertSorted([
            '/{root}/view',
            '/{root}/{view}',
        ])

    def test_variable_root_variables_mix2(self):
        self.assertSorted([
            '/{root}/first',
            '/{root}/second',
            '/{root}/{single}',
            '/{root}{/path*}',
        ])

    def test_multiple_defined_suffixes(self):
        self.assertSorted([
            '/{some_id}/foo/view',
            '/{some_id}/view',
            '/{some_id}/{foo}/view',
            '/{some_id}/{foo}/{view}',
        ])

    def test_variable_root_variables_mix3(self):
        self.assertSorted([
            '/root/{id}/view',
            '/root/{id}/zzz/{lang}/view"',
            '/root/{id}/{zzz}/{lang}/view"',
        ])
        self.assertSorted([
            '/root/{id}/view',
            '/root/{id}/aaa/{lang}/view"',
            '/root/{id}/{aaa}/{lang}/view"',
        ])

    def test_multi_single_variable_mix(self):
        self.assertSorted([
            '/root/{somepath}/view',
            '/root/{somepath}/foo/{some_id}/view',
            '/root/{somepath}/{some_id}/foo/view',
        ])

    def test_multi_path_variable(self):
        self.assertSorted([
            '/root{/somepath*}/foo',
            '/root{/somepath*}/foo/',
            '/root{/somepath*}/view',
            '/root{/somepath*}/foo/{some_id}/view',
        ])

    def test_multi_path_variable_mix(self):
        self.assertSorted([
            # sortest fragment is matched first
            '/root{/somepath*}/view',
            # the following contain a pair of templates that would only
            # trigger an ambiguous condition if some_id is 'foo', but
            # otherwise ordering isn't too important, as the first
            # most static prefix is "/foo/" and thus has priority.
            '/root{/somepath*}/foo/{some_id}/view',
            '/root{/somepath*}/{some_id}',
            '/root{/somepath*}/{some_id}/foo/view',
        ])

    def test_multi_path_empty_tail_lower_priority(self):
        self.assertSorted([
            '/root/{target}{/path*}/index',
            '/root/{target}{/path*}/view',
            '/root/{target}{/path*}/',
            # if this is higher, it would apply over the one with the
            # trailing '/'
            '/root/{target}{/path*}',
        ])
        # however, non-expansion rules would not be relevant as the
        # path separator will not be fed to/consumed inside {zzz}
        self.assertSorted([
            '/root/',
            '/root/{zzz}/',
            '/{zzz}',
            '/{zzz}/',
        ])

    def test_path_suffix_variable_priority(self):
        # subsequent templates without further matches (i.e. templates
        # lacking {lang}) will always be matched first.
        self.assertSorted([
            '/root/{id}{/path*}/view',
            '/root/{id}{/path*}/view/{lang}/view',
            '/root/{id}{/path*}/zzz/{lang}/view',
        ])
        self.assertSorted([
            '/root/{id}{/path*}/view',
            '/root/{id}{/path*}/view/{lang}/view',
            '/root/{id}{/path*}/zzz/{lang}/view',
        ])
        self.assertSorted([
            '/root/{id}{/path*}/view',
            '/root/{id}{/path*}/zzz/{lang}/view',
            '/root/{id}{/path*}/{zzz}/{lang}/view',
        ])

        # same level static only elements should be attempted before the
        # variable version.
        self.assertSorted([
            '/root/{id}{/path*}/view',
            '/root/{id}{/path*}/{view}',
        ])
        self.assertSorted([
            '/root/{id}{/path*}/view',
            '/root/{id}{/path*}/{view}/view',
        ])
        # ditto for a mixture like so - the static view prefix after the
        # path will always match first, then follow by the wildcard
        # version with an explicit static suffix, finally the full wild.
        self.assertSorted([
            '/root/{id}{/path*}/view',
            '/root/{id}{/path*}/view/{captures}',
            '/root/{id}{/path*}/{view}/captures',
            '/root/{id}{/path*}/{view}/{captures}',
        ])
        # should behave the same without the wildcards.
        self.assertSorted([
            '/view',
            '/view/{captures}',
            '/{view}/captures',
            '/{view}/{captures}',
        ])

        self.assertSorted([
            '/root/{id}{/path*}/root/wat',
            '/root/{id}{/path*}/{zzz}/wat',
        ])

        self.assertSorted([
            '/root/{id}{/path*}/root/wat',
            '/root/{id}{/path*}/root/{zzz}/wat',
            '/root/{id}{/path*}/{zzz}/wat',
        ])

        self.assertSorted([
            '/root/{id}{/path*}/root/',
            '/root/{id}{/path*}/root/{zzz}/',
            '/root/{id}{/path*}/{zzz}/',
        ])

        self.assertSorted([
            '/root/{id}{/path*}/root',
            '/root/{id}{/path*}/root/{zzz}',
            '/root/{id}{/path*}/{zzz}',
        ])

        # Further cases.
        self.assertSorted([
            '/root/{id}{/path*}/root/{zzz}',
            '/root/{id}{/path*}/root/{zzz}/suffix',
            '/root/{id}{/path*}/root/suffix/{wat}',
            '/root/{id}{/path*}/{zzz}/suffix',
            '/root/{id}{/path*}/{zzz}/',
            '/root/{id}{/path*}/root/{zzz}/{lang}',
            '/root/{id}{/path*}/root/{zzz}/{lang}/suffix',
            '/root/{id}{/path*}/root/{zzz}/{lang}/',
            '/root/{id}{/path*}/{zzz}/{lang}',
            '/root/{id}{/path*}/{zzz}/{lang}/suffix',
            '/root/{id}{/path*}/{zzz}/{lang}/',
            '/root/{id}{/path*}/root/{zzz}/{lang}/{a}',
            '/root/{id}{/path*}/root/{zzz}/{lang}/{a}/suffix',
            '/root/{id}{/path*}/root/{zzz}/{lang}/{a}/',
            '/root/{id}{/path*}/{zzz}/{lang}/{a}',
            '/root/{id}{/path*}/{zzz}/{lang}/{a}/suffix',
            '/root/{id}{/path*}/{zzz}/{lang}/{a}/',
        ])

    def test_multi_path_variable_with_ambiguous(self):
        self.assertSorted([
            '/root{/somepath*}/{some_id}/foo/view',
            '/root{/somepath*}/{some_id}/view',
            '/root{/somepath*}/{some_id}/{foo}/view',
            # multiple parts are really ambiguous
            '/root{/somepath*}/view{/morepathwut*}/view',
        ])

    def test_mismatch_types(self):
        with self.assertRaises(TypeError):
            sorted([
                '/raw_string',
                URITemplateMatcher(URITemplate('/template'))
            ])
