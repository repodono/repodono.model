"""
Defines the classes that encapsulate the resources that can be loaded
from a provided configuration.
"""

from repodono.model.base import (
    StructuredMapping,
    BaseMapping,
    PathMapping,
    ObjectInstantiationMapping,
    ResourceDefinitionMapping,
    RouteTrieMapping,
    CompiledRouteResourceDefinitionMapping,
)


class Environment(StructuredMapping((
    ('environment', StructuredMapping((
        ('variables', BaseMapping,),
        ('paths', PathMapping,),
        ('objects', ObjectInstantiationMapping,),
    ),),),
))):
    """
    Default environment implementation

    In the future this may be possible to be represented in terms of
    toml as:

    [[Environment]]
    [[Environment.environment]]
    variables = "repodono.model.base:BaseMapping"
    [[Environment.environment]]
    paths = "repodono.model.base:PathMapping"
    [[Environment.environment]]
    objects = "repodono.model.base:ObjectInstantiationMapping"
    """


class Resource(StructuredMapping((
    ('resource', lambda x: CompiledRouteResourceDefinitionMapping(
        RouteTrieMapping(ResourceDefinitionMapping(x)))),
))):
    """
    Default resource mapping implementation

    [[Resource]]
    resource = "repodono.model.base:ResourceDefinitionMapping"
    """
