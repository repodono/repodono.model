import regex
from functools import partial
from uritemplate.variable import URIVariable


nr_chars = regex.escape(URIVariable.reserved)

raw_single_pattern = r"(?:{joiner}(?{option}[^" + nr_chars + "]{count}))"
raw_list_pattern = r"(?:{joiner}(?{option}[^" + nr_chars + "]+)){explode}"

# if placeholder wrapper be done, it could isntead be:
# raw_single_pattern = r"(?:{joiner}" + group("[^" + nr_chars + "]{count})")


def check_variable(variable):
    if not isinstance(variable, URIVariable):
        raise TypeError("'variable' must be a URIVariable")

    if len(variable.variables) != 1:
        raise TypeError("multiple variables not supported")

    if variable.operator and variable.operator in '#;+':
        raise TypeError("unsupported operator '%s'" % variable.operator)

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
        count='+' if variable.variables[0][1]['explode'] else '',
    )


raw_operator_patterns = (
    ('', raw_single_pattern),
    ('/', raw_list_pattern),
    ('.', raw_list_pattern),
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


default_regex_pattern_map = build_pattern_map()


class TemplateRegexFactory(object):

    pattern_map = build_pattern_map()

    def _iter_variables(self, template):
        for variable in template.variables:
            # XXX KeyError unhandled
            name, pat = self.pattern_map[variable.operator](variable=variable)
            yield (name, '{%s}' % variable.original, pat)

    def __call__(self, template):
        results = []
        uri = template.uri
        for name, chunk, pat in self._iter_variables(template):
            head, uri = uri.split(chunk, 1)
            results.append(head)
            results.append(pat)

        results.append(uri)
        return regex.compile(''.join(results))


def variable_to_regexp(variable):
    """
    Convert a URIVariable to a regular expression string.
    """


def template_to_regex(template):

    # validate all variables first

    # check that no duplicates are done
    if len(template.variable_names) < len(template.variables):
        raise ValueError('multiple definitions of the same')

    # iterate through the list of variables, stick in path fragments,
    # until a variable that start with '?' is encountered, where every
    # one of them will be marked as arguments.  Anything else that do
    # not start with & is ignored/warned

    # URL path parameter will NOT be supported due to everything
    # surrounding this particular syntax is too underspecified for any
    # sensible use case.  (Any variable start with ';' will be an error

    # anything that is placed _after_ variables with start in ('?&')
    # should also result in an error as typical frameworks consider that
    # as part of a parameter.

    # the templater thing will have to combine the two.


def match(template, uri):
    pass


def validate(template):
    pass
