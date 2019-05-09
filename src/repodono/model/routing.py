"""
This module provides helper functions and classes to assist in and
demonstrates routing using URITemplates.
"""

from operator import attrgetter
from uritemplate import URITemplate

from repodono.model.urimatch import URITemplateMatcher


class URITemplateRouter(object):
    """
    A naive implementation of a router that would route based on a set
    of provided URITemplates through the URITemplateMatcher class above.
    """

    def __init__(self, uritemplates):
        """
        Arguments

        uritemplates
            A list of URITemplate objects.
        """

        self.matchers = [URITemplateMatcher(template) for template in sorted(
            uritemplates, key=attrgetter('uri'), reverse=True)]

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
