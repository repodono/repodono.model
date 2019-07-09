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
    BucketDefinitionMapping,
    ReMappingDefinitionMapping,
    EndpointDefinitionSetMapping,
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


class Default(StructuredMapping((
    ('default', StructuredMapping((
        ('variables', BaseMapping,),
        ('paths', PathMapping,),
        ('objects', ObjectInstantiationMapping,),
    ),),),
))):
    """
    Default value implementation

    Default global values; functionally similar to the environment,
    but only simple variables are defined and have the lowest level of
    precedence in the resolution order by the execution locals.  This is
    essentially based on the Environment class, with a different name
    and prefix.

    [[Default]]
    [[Default.default]]
    variables = "repodono.model.base:BaseMapping"
    [[Default.default]]
    paths = "repodono.model.base:PathMapping"
    [[Default.default]]
    objects = "repodono.model.base:ObjectInstantiationMapping"
    """


class Bucket(StructuredMapping((
    ('bucket', BucketDefinitionMapping,),
))):
    """
    Default bucket mapping implementation

    [[Bucket]]
    bucket = "repodono.model.base:BucketDefinitionMapping"
    """


class Localmap(StructuredMapping((
    ('localmap', ReMappingDefinitionMapping,),
))):
    """
    Default local mapping implementation (provides remap proxy)

    [[Localmap]]
    localmap = "repodono.model.base:ReMappingDefinitionMapping"
    """


class Resource(StructuredMapping((
    ('resource', ResourceDefinitionMapping),
))):
    """
    Default resource mapping implementation

    [[Resource]]
    resource = "repodono.model.base:ResourceDefinitionMapping"
    """


class Endpoint(StructuredMapping((
    ('endpoint', EndpointDefinitionSetMapping),
))):
    """
    Default endpoint mapping implementation

    [[Endpoint]]
    endpoint = "repodono.model.base:EndpointDefinitionSetMapping"
    """
