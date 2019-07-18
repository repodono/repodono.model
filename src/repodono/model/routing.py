"""
This module provides helper functions and classes to assist in and
demonstrates routing using URITemplates.
"""

from uritemplate import URITemplate

from repodono.model.urimatch import (
    TemplateConverterFactory,
    URITemplateMatcher,
    raw_operator_patterns,
    check_template_leading_slash,
    default_template_validators,
    default_pattern_finalizer,
)


class RoutableTemplateConverterFactory(TemplateConverterFactory):

    def __init__(
            self, operator_patterns, pattern_finalizer,
            template_validators=[
                check_template_leading_slash] + default_template_validators):
        super().__init__(
            operator_patterns, pattern_finalizer, template_validators)


routable_template_to_regex_patternstr = RoutableTemplateConverterFactory(
    operator_patterns=raw_operator_patterns,
    pattern_finalizer=default_pattern_finalizer,
)


class RoutableURITemplateMatcher(URITemplateMatcher):
    """
    An implementation that further restricts what template may be
    converted.  Mainly this requires a template to support a leading
    '/' of some kind.
    """

    def __init__(
            self, template,
            template_converter=routable_template_to_regex_patternstr):
        return super().__init__(
            template, template_converter=template_converter)


class URITemplateRouter(object):
    """
    A naive implementation of a router that would route based on a set
    of provided URITemplates through the RoutableURITemplateMatcher
    class above as typical routing engines do require routes to be
    specified in absolute terms.
    """

    def __init__(self, uritemplates):
        """
        Arguments

        uritemplates
            A list of URITemplate objects.
        """

        self.matchers = sorted(
            RoutableURITemplateMatcher(template) for template in uritemplates)

    @classmethod
    def from_strings(cls, uritemplate_strs):
        """
        Construct a router from a list of strings that can be formed
        into a valid URITemplate.
        """

        return cls(URITemplate(s) for s in uritemplate_strs)

    def __call__(self, uri):
        for matcher in self.matchers:
            result = matcher(uri)
            if result is not None:
                return matcher.template.uri, result
