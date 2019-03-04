"""
Note: this is an interim module - once dedicated support for sanic is
provided by a dedicated package, this module will be moved there.
"""

from repodono.model.urimatch import (
    noncapture_pattern_finalizer,
    raw_operator_patterns,
    TemplateConverterFactory,
)


def sanic_pattern_finalizer(pattern_str, variable):
    name, pattern_str = noncapture_pattern_finalizer(pattern_str, variable)
    return name, '<%s:%s>' % (name, pattern_str)


templateuri_to_sanic_routeuri = TemplateConverterFactory(
    operator_patterns=raw_operator_patterns,
    pattern_finalizer=sanic_pattern_finalizer,
)
