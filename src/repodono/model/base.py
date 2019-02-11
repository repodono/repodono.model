from inspect import signature
from functools import partial
from pathlib import Path
from collections import (
    Sequence,
    Mapping,
    MutableMapping,
)

from pkg_resources import EntryPoint


def map_vars_value(value, vars_):
    # these are assumed to be produced by the toml/json loads,
    # which should only produce instances of list/dict for the
    # structured data types.
    if isinstance(value, list):
        return [map_vars_value(key, vars_) for key in value]
    elif isinstance(value, dict):
        return {
            name: map_vars_value(key, vars_) for name, key in value.items()}
    else:
        return vars_[value]


def structured_mapper(
        definition_pairs, input_mapping, _maps=NotImplemented, vars_=None):
    """
    Produce a list of some mapping based on input definition pairs.

    Arguments:

    definition_pairs
        This is in the form of a 2-tuple of key, value, the key being
        the key to extract the actual values from the input_mapping,
        the value being the class to map the values provided at the key
        from the input_mapping, or another nested 2-tuple for a
        recursively generated flattened group mapping.
    input_mapping
        The raw input map (dict)
    """

    def _mapper(definition_pairs, input_mapping, _maps=NotImplemented):
        maps = [] if _maps is NotImplemented else _maps
        for key, value in definition_pairs:
            if key not in input_mapping:
                continue
            if isinstance(value, Sequence):
                _mapper(value, input_mapping[key], _maps=maps)
                continue
            # XXX assuming value to be a class
            sig = signature(value)
            if 'vars_' in sig.parameters:
                maps.append(value(input_mapping[key], vars_=vars_))
            else:
                maps.append(value(input_mapping[key]))

        return maps

    return _mapper(definition_pairs, input_mapping, _maps)


class BaseMapping(MutableMapping):

    def __init__(self, *a, **kw):
        self.__map = {}
        # calling self.update instead to use methods defined by parent
        # that will properly cascade down to the implementation here.
        self.update(*a, **kw)

    def __getitem__(self, key):
        return self.__map[key]

    def __setitem__(self, key, value):
        self.__map[key] = value

    def __delitem__(self, key):
        self.__map.__delitem__(key)

    def __iter__(self):
        return iter(self.__map)

    def __len__(self):
        return len(self.__map)

    def __contains__(self, key):
        return key in self.__map

    def __repr__(self):
        return repr(self.__map)


class FlatGroupedMapping(BaseMapping):
    """
    A mapping that allows assignments to keys that do not already have a
    value defined for that key in any of the inner mappings.
    """

    def __init__(self, mappings):
        # FIXME implement error checks
        self.__mappings = mappings
        super().__init__()

    def __get(self, key):
        """
        Acquire values from submappings
        """

        for mapping in self.__mappings:
            if key in mapping:
                return mapping[key]
        else:
            raise KeyError(key)

    def __getitem__(self, key):
        try:
            return self.__get(key)
        except KeyError:
            return super().__getitem__(key)

    def __setitem__(self, key, value):
        try:
            self.__get(key)
        except KeyError:
            super().__setitem__(key, value)
        else:
            raise KeyError("%r is read-only" % key)

    def __delitem__(self, key):
        try:
            self.__get(key)
        except KeyError:
            super().__delitem__(key)
        else:
            raise KeyError("%r is read-only" % key)

    def __combined(self):
        results = {}
        for mapping in reversed(self.__mappings):
            results.update(mapping)
        # cheat access to parent _map.
        results.update(self._BaseMapping__map)
        return results

    def __iter__(self):
        return iter(self.__combined())

    def __len__(self):
        return len(self.__combined())

    def __contains__(self, key):
        return key in self.__combined()

    def __repr__(self):
        return repr(self.__combined())


class BaseTypedMapping(BaseMapping):
    """
    A mapping where assignment of some value is passed through the
    prepare_from_value method method which must be implemented.  This is
    to establish a standard for restriction of types assigned.
    """

    @classmethod
    def prepare_from_value(cls, value):
        """
        This must be implemented by the subclasses as it is specific to
        their implementations.  Typically a classmethod should suffice.
        """

    def __setitem__(self, key, value):
        super().__setitem__(key, self.prepare_from_value(value))


class PathMapping(BaseTypedMapping):

    @classmethod
    def prepare_from_value(self, value):
        return Path(value)


class BaseSequenceTypedMapping(BaseTypedMapping):
    """
    A base mapping with values that are a sequence of elements of a
    uniform type produced by a well-defined class method.  Values being
    assigned to instances of such a mapping will be another mapping or
    a list of mappings that contain the requisite keys.  Assignment of
    a single mapping will simply be appended to the internal mapping,
    while assignment of a complete list will set the value to the
    list of instances of the uniform type.
    """

    def __setitem__(self, key, value):
        # FIXME validate key being a valid URL template
        # FIXME this needs to be co-ordinated with the endpoint mapping
        # implementation.
        if key not in self:
            result = []
            # using the base mapping directly as the semantics of how
            # assignments are done have been changed here
            BaseMapping.__setitem__(self, key, result)
        else:
            result = self.get(key)

        # TODO use the appropriate ResourceDefinition constructor
        if isinstance(value, Sequence):
            result.clear()
            for item in value:
                result.append(self.prepare_from_value(item))
        else:
            result.append(self.prepare_from_value(value))


class ResourceDefinitionMapping(BaseSequenceTypedMapping):
    """
    A resource definition mapping is a mapping with keys that reference
    some path fragment of some URI, and the value assigned being a dict
    being a mapping of arguments to the function being called, and the
    function being called be specified with either the __init__ or the
    __call__ key, plus a __name__ which the return value will be
    assigned to.  Only one of __init__ or __call__ may be specified;
    The __init__ key must reference some valid entry point within the
    environment, while the __call__ key must reference an existing value
    in the environment that will be invoked.

    Another notable difference with this mapping is that each key must
    have multiple values presented in an ordered list, as there can be
    multiple resources defined for each end point.
    """

    class ResourceDefinition(object):
        def __init__(self, name, call, kwargs):
            self.name = name
            self.call = call
            self.kwargs = kwargs

        @classmethod
        def from_call(cls, name, call, kwargs):
            # XXX call must be an indirect call that will load the
            # actual thing from vars then return call(**kwargs)
            # FIXME this is currently a placeholder
            return cls(name=name, call=call, kwargs=kwargs)

        @classmethod
        def from_entry_point(cls, name, init, kwargs):
            entry = EntryPoint.parse('target=' + init)
            call = entry.resolve()
            return cls(name=name, call=call, kwargs=kwargs)

        # TODO vars_ as an argument determine if sane?

        def __call__(self, vars_, **kwargs):
            """
            Prepares a callable object that can be invoked immediately
            with the required definitions.
            """

            call = (
                self.call if callable(self.call) else
                map_vars_value(self.call, vars_)
            )
            kwargs.update(map_vars_value(self.kwargs, vars_))
            # XXX this does NOT actually trigger the assignment to
            # vars_[self.name], as the current definition on how the
            # protocol works is not yet defined; it may be possible to
            # encapsulate the Environment in a submapping representing
            # some RuntimeEnvironment for the actual usage.
            return partial(call, **kwargs)

    @classmethod
    def create_resource_definition(cls, name, call, init, kwargs):
        # a naive, generic creation method.
        if call is not None:
            return cls.ResourceDefinition.from_call(
                name, call, kwargs)
        elif init is not None:
            return cls.ResourceDefinition.from_entry_point(
                name, init, kwargs)

    @classmethod
    def prepare_from_value(cls, value):
        kwargs = dict(value)

        # quick check
        if ('__call__' in kwargs) == ('__init__' in kwargs):
            raise ValueError(
                "only one of '__call__' or '__init__' must be defined.")

        # TODO figure out how to find duplicate __name__, if that is
        # needed for all implementations.
        name = kwargs.pop('__name__')
        # either of the callables.
        call = kwargs.pop('__call__', None)
        init = kwargs.pop('__init__', None)
        return cls.create_resource_definition(name, call, init, kwargs)


class ObjectInstantiationMapping(BaseTypedMapping):
    """
    This takes a list of dicts that contain the prerequisite keys and
    values and it will invoke the target constructor or function as
    specified.

    The reason why this mapping takes a list as part of the construction
    process is due to the nature of object construction being a sequence
    of calls that must happen in a specific order, especially given that
    the constructor may reference previously defined arguments which may
    become out of order if a mapping is used (as Python<3.6 and the toml
    spec do not explicitly maintain mapping key/value order).

    This class is also meant ot be used as part of the StructuredMapping
    class factory.
    """

    # currently defining vars_ as a parameter as the current
    # StructuredMapping resolves that signature.

    def __init__(self, items, vars_):
        """
        For a given mapping resolve the object and construct a mapping
        """

        self.__vars = vars_
        super().__init__(items)

    def prepare_from_value(self, value):
        kwargs = dict(value)
        entry = EntryPoint.parse('target=' + kwargs.pop('__init__'))
        target = entry.resolve()
        kwargs = {
            key: map_vars_value(value, vars_=self.__vars)
            for key, value in kwargs.items()
        }
        return target(**kwargs)

    def update(self, *a, **kw):
        if len(a) != 1 or not (
                isinstance(a[0], Sequence) and
                a[0] and
                len(a[0]) == 1 and
                isinstance(a[0][0], Mapping)):
            return super().update(*a, **kw)

        super().update({
            kwargs.pop('__name__'): kwargs
            for kwargs in (dict(item) for item in a[0])
        })


def StructuredMapping(definition, structured_mapper=structured_mapper):
    """
    A class factory for the creation of a parent class that can
    encapsulate a predefined structure for creating a flattened group
    mapping.
    """

    class StructuredMapping(FlatGroupedMapping):

        def __init__(self, raw_mapping):
            mappings = []
            # assign mappings to the private attribute.
            super().__init__(mappings=mappings)
            structured_mapper(
                definition, raw_mapping, _maps=mappings, vars_=self)

    return StructuredMapping
