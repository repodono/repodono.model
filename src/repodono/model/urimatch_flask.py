"""
Note: this is an interim module - once dedicated support for werkzeug/
flask are provided by a dedicated package, this module will be moved
there.
"""

from werkzeug.routing import Rule
from uritemplate import URITemplate
from uritemplate.variable import URIVariable

from repodono.model.urimatch import (
    template_to_regex_patternstr,
    URITemplateMatcher,
)


class URITemplateRule(Rule):
    """
    A URITemplateRule is a Rule compatible class that routes based on a
    URITemplate instance.
    """

    def __init__(self, template, defaults=None, subdomain=None, methods=None,
                 build_only=False, endpoint=None, strict_slashes=None,
                 redirect_to=None, alias=False, host=None):

        super().__init__(
            # using '/' for rule to get around startswith '/' check,
            # and that it expects the check.
            string='/', defaults=defaults, subdomain=subdomain,
            methods=methods, build_only=build_only, endpoint=endpoint,
            strict_slashes=strict_slashes, redirect_to=redirect_to,
            alias=alias, host=host,
        )
        # replace the rule with the template directly
        self.rule = (
            template
            if isinstance(template, URITemplate) else
            URITemplate(template)
        )
        self.is_leaf = not self.rule.uri.endswith('/')

    def compile(self):
        self._trace = []
        self._converters = {}
        self._static_weights = []
        self._argument_weights = []

        # need to populate self.arguments
        # XXX subdomain and/or host ignored
        self._trace.append((False, '|'))
        for t, c, p in template_to_regex_patternstr.iter_template(self.rule):
            self._trace.append((isinstance(t, URIVariable), c))

        self._matcher = URITemplateMatcher(self.rule)

    def match(self, path, method=None):
        if self.build_only:
            return
        # assumes the path is provided in the form "subdomain|/path"
        subdomain, p = path.split('|', 1)
        return self._matcher(p)

    def build(self, values, append_unknown=True):
        """
        Formats the url.
        """

        return '', self.rule.expand(**dict(values))

    def __str__(self):
        return self.rule.uri
