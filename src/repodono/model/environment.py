from repodono.model.base import (
    StructuredMapping,
    BaseMapping,
    PathMapping,
)


class Environment(StructuredMapping((
    ('environment', StructuredMapping((
        ('variables', BaseMapping,),
        ('paths', PathMapping,),
    ),),),
))):
    """
    Default environment implementation
    """
