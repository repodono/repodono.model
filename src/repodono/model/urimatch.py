import regex
from operator import attrgetter
from functools import partial
from uritemplate import URITemplate
from uritemplate.variable import URIVariable


nr_chars = regex.escape(URIVariable.reserved)

raw_single_pattern = r"(?:{joiner}(?{option}[^" + nr_chars + "]{count}))"
raw_list_pattern = r"(?:{joiner}(?{option}[^" + nr_chars + "]+)){explode}"
raw_empty_pattern = ""

# if placeholder wrapper be done, it could isntead be:
# raw_single_pattern = r"(?:{joiner}" + group("[^" + nr_chars + "]{count})")

raw_operator_patterns = (
    ('', raw_single_pattern),
    ('/', raw_list_pattern),
    ('.', raw_list_pattern),
    ('?', raw_empty_pattern),
    ('&', raw_empty_pattern),
)


def check_variable(variable):
    """
    Checks whether the provided URIVariable is supported by the variable
    matching framework as implemented in this package.  All functions as
    implemented in this framework will assume this is the canonical
    validation function.
    """

    if not isinstance(variable, URIVariable):
        raise ValueError("'variable' argument must be a URIVariable")

    if len(variable.variables) != 1:
        raise ValueError(
            "multiple variables {%s} not supported" % variable.original)

    return variable.variables[0][0]


def default_pattern_finalizer(pattern_str, variable):
    """
    Assumes the pattern string has a slot for the default token to name
    the group that provides the value matched for the name.
    """

    name = check_variable(variable)

    return name, pattern_str.format(
        option='P<%s>' % name,
        joiner=variable.operator,
        # for now ensure at least one value, if the value modifier is to
        # be supported it should be replaced with a specific max count?
        # perhaps {1,count}
        count='+',
        explode='+' if variable.variables[0][1]['explode'] else '',
    )


def noncapture_pattern_finalizer(pattern_str, variable):
    """
    Assumes the pattern string has a slot for the default token to name
    the group that provides the value matched for the name.

    This pattern ensures that the group is not captured to allow the
    name be used/captured under a different context (or usage), or
    wrapped by specific routing frameworks that do not use raw regex as
    the means to encode routes for their application framework.
    """

    name = check_variable(variable)

    return name, pattern_str.format(
        option=':',
        joiner=variable.operator,
        count='+',
        explode='+' if variable.variables[0][1]['explode'] else '',
    )


def build_pattern_map(
        operator_patterns=raw_operator_patterns,
        pattern_finalizer=default_pattern_finalizer):

    def finalizer_generator(raw_pattern):
        return partial(pattern_finalizer, pattern_str=raw_pattern)

    return {
        operator: finalizer_generator(pattern)
        for operator, pattern in operator_patterns
    }


class TemplateConverterFactory(object):

    def __init__(self, operator_patterns, pattern_finalizer):
        self.pattern_map = build_pattern_map(
            operator_patterns=operator_patterns,
            pattern_finalizer=pattern_finalizer,
        )

    def _validate_variable(self, variable):
        if variable.operator not in self.pattern_map:
            raise ValueError("operator '%s' unsupported by %s" % (
                variable.operator,
                type(self),
            ))

    def _iter_variables(self, template):
        for variable in template.variables:
            self._validate_variable(variable)
            name, pat = self.pattern_map[variable.operator](variable=variable)
            yield (name, '{%s}' % variable.original, pat)

    def _validate_uri(self, template):
        if not ((template.uri[:1] == '/') or (
                (template.uri[:1] == '{') and
                template.variables and
                template.variables[0].operator == '/')):
            raise ValueError(
                "unsupported uritemplate: missing a leading '/' or "
                "'{/path}' variable"
            )
        if '?' in template.expand():
            raise ValueError(
                "unsupported uritemplate: query expansion '?' must be defined "
                "using a query expansion (e.g. '{?query}')"
            )
        if len(template.variables) > len(template.variable_names):
            raise ValueError(
                "unsupported uritemplate: variable names have been reused"
                # TODO list out variables that were reused
            )
        # the following will not be checked as it will be checked by
        # _validate_variable for each variable name
        # if len(template.variables) < len(template.variable_names):

    def supported(self, template):
        try:
            self.validate(template)
        except ValueError:
            # should log an error.
            return False
        return True

    def validate(self, template):
        self._validate_uri(template)
        for variable in template.variables:
            # this validates whether the operator is supported
            self._validate_variable(variable)
            # this checks for the other requirements common to all
            # variables as implemented by this framework.
            check_variable(variable)

    def iter_template(self, template):
        """
        Iterate through the template

        Yields a 3-tuple of type, original and regex fragment, where the
        type is the type of original portion of the template fragment
        that produced the regex fragment.
        """

        self._validate_uri(template)
        uri = template.uri
        for name, chunk, pat in self._iter_variables(template):
            head, uri = uri.split(chunk, 1)
            yield (str, head, head)
            yield (URIVariable, chunk, pat)

        yield (str, uri, uri)
        # how to better represent the end token?
        yield (str, '', '$')

    def __call__(self, template):
        return ''.join(
            fragment for type_, orig, fragment in self.iter_template(template))


template_to_regex_patternstr = TemplateConverterFactory(
    operator_patterns=raw_operator_patterns,
    pattern_finalizer=default_pattern_finalizer,
)


class URITemplateMatcher(object):
    """
    The URI Template matcher.
    """

    def __init__(self, template):
        """
        Arguments:

        uritemplate
            The URITemplate object to build a matcher from.
        """

        self.template = template
        self.regex_pattern = regex.compile(
            template_to_regex_patternstr(template))
        self.variables = {}
        for variable in self.template.variables:
            self.variables.update(variable.variables)

    def __call__(self, uri):
        """
        Arguments:

        uri
            The uri to match.
        """

        match = self.regex_pattern.match(uri)
        if not match:
            # TODO verify that an empty mapping is a suitable response
            # for no matches
            return None

        results = {}
        for variable, details in self.variables.items():
            try:
                if details['explode']:
                    results[variable] = match.captures(variable)
                else:
                    results[variable] = match.group(variable)
            except IndexError:
                # XXX TODO figure out how to deal with operators that
                # are defined to be undefined/unused in this system
                continue

        return results


def match(template, uri, __cache={}):
    if template.uri not in __cache:
        __cache[template.uri] = URITemplateMatcher(template)
    return __cache[template.uri](uri)


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
