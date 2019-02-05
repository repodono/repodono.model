from repodono.model.base import (
    StructuredMapping,
    BaseMapping,
    PathMapping,
    ObjectInstantiationMapping,
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
    """
