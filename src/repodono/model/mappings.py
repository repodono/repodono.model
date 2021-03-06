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
    EndpointDefinitionMapping,
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


class Metadata(StructuredMapping((
    ('metadata', StructuredMapping((
        ('variables', BaseMapping,),
        ('paths', PathMapping,),
        ('objects', ObjectInstantiationMapping,),
    ),),),
))):
    """
    Default metadata implementation - based on the environment, given
    that there are some use-cases where a relevant counterpart for a
    given key-value will be required depending on the run time
    requirements.

    [[Metadata]]
    [[Metadata.metadata]]
    variables = "repodono.model.base:BaseMapping"
    [[Metadata.metadata]]
    paths = "repodono.model.base:PathMapping"
    [[Metadata.metadata]]
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

    @property
    def Endpoint(bucket_mapping):
        class BucketEndpointDefinitionSetMapping(EndpointDefinitionSetMapping):
            @classmethod
            def prepare_from_item(self, key, value):
                return EndpointDefinitionMapping(
                    value, bucket_name=key, bucket_mapping=bucket_mapping)

        return StructuredMapping((
            ('endpoint', BucketEndpointDefinitionSetMapping),
        ))


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
