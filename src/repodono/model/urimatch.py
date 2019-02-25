import regex
from uritemplate.variable import URIVariable


nr_chars = regex.escape(URIVariable.reserved)

raw_single_pattern = r"(?:{joiner}(?{option}[^" + nr_chars + "]{count}))"
raw_list_pattern = r"(?:{joiner}(?{option}[^" + nr_chars + "]+)){count}"

# if placeholder wrapper be done, it could isntead be:
# raw_single_pattern = r"(?:{joiner}" + group("[^" + nr_chars + "]{count})")


def check_variable(variable):
    if not isinstance(variable, URIVariable):
        raise TypeError("'variable' must be a URIVariable")

    if len(variable.variables) != 1:
        raise TypeError("multiple variables not supported")

    if variable.operator in '#;+':
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
        count='+' if variable.variables[0][1]['explode'] else '',
    )


def noncapture_pattern_finalizer(pattern_str, variable):
    """
    Assumes the pattern string has a slot for the default token to name
    the group that provides the value matched for the name.

    This pattern ensures that the group is not captured to allow the
    name be used/captured under a different context (or usage).
    """

    name = check_variable(variable)

    return name, pattern_str.format(
        option=':',
        joiner=variable.operator,
        count='+' if variable.variables[0][1]['explode'] else '',
    )


def default_value(variable, pattern_finalizer=default_pattern_finalizer):
    return pattern_finalizer(raw_single_pattern, variable)


def default_path(variable, pattern_finalizer=default_pattern_finalizer):
    return pattern_finalizer(raw_list_pattern, variable)


default_operator_handlers = (
    ('', default_value),
    ('/', default_path),
)


class MatchVariable(object):

    def __init__(self, variable):
        self.variable = variable

    def to_token(self):
        """
        Low level function that return a list of 2-tuple, with the name
        of the variable (if applicable) and the pattern for that group.
        """


class MatchTemplate(object):

    def __init__(self, template, matcher=MatchVariable):
        self.template = template


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
