from inspect import signature
from pathlib import Path
from collections import (
    Sequence,
    MutableMapping,
)

from pkg_resources import EntryPoint


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


class PathMapping(BaseMapping):

    def __setitem__(self, key, value):
        super().__setitem__(key, Path(value))


class ObjectInstantiationMapping(BaseMapping):
    """
    This takes a list of dicts that contain the prerequisite keys and
    values and it will invoke the target constructor or function as
    specified.
    """

    # XXX determine if name should be vars_ or _vars

    def __init__(self, items, _vars):
        """
        For a given mapping resolve the object and construct a mapping
        """

        super().__init__()

        def map_vars_value(value):
            # these are assumed to be produced by the toml/json loads,
            # which should only produce instances of list/dict for the
            # structured data types.
            if isinstance(value, list):
                return [map_vars_value(key) for key in value]
            elif isinstance(value, dict):
                return {
                    name: map_vars_value(key) for name, key in value.items()}
            else:
                return _vars[value]

        for item in items:
            # XXX TODO refactor this into a function
            # name = assignment
            kwargs = {}
            kwargs.update(item)
            name = kwargs.pop('__name__')
            entry = EntryPoint.parse('target=' + kwargs.pop('__init__'))
            target = entry.resolve()
            kwargs = {
                key: map_vars_value(value)
                for key, value in kwargs.items()
            }
            object_ = target(**kwargs)
            self.__setitem__(name, object_)


def structured_mapper(
        definition_pairs, input_mapping, _maps=NotImplemented, _vars=None):
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
            if '_vars' in sig.parameters:
                maps.append(value(input_mapping[key], _vars=_vars))
            else:
                maps.append(value(input_mapping[key]))

        return maps

    return _mapper(definition_pairs, input_mapping, _maps)


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
                definition, raw_mapping, _maps=mappings, _vars=self)

    return StructuredMapping
