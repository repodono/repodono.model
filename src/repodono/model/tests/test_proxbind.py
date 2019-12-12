import unittest

from repodono.model.proxbind import (
    ProxyBase,
    MappingBinderMeta,
)
from repodono.model.testing import Thing


# demo classes

class ExtThing(Thing):
    """
    An extended thing
    """

    def __init__(self, path, paths=[], default=42):
        self.path = path
        self.paths = paths
        self.default = default

    def get_all_targets(self):
        return (self.path, self.paths,)


class MappedExtThingMeta(MappingBinderMeta):
    """
    Demonstrates how to implement mapping from a provided mapping to the
    attribute value using the MappingBinderMeta class in a manner that
    fully contains the mapping to a single class and single function for
    each remapped attribute
    """

    def path(mapping, attr_value):
        return mapping[attr_value]

    def paths(mapping, attr_value):
        return [mapping.get(k) for k in attr_value]


class MappedExtThing(ExtThing, metaclass=MappedExtThingMeta):
    """
    The final MappedExtThing class set up with the API as defined by
    the classes provided by the proxbind module.
    """


# the unit tests.

class ProxyBaseTestCase(unittest.TestCase):

    def test_basic(self):
        thing = Thing('value')
        self.assertEqual(thing.path, 'value')
        proxy = ProxyBase(thing)
        self.assertEqual(proxy.path, 'value')

    def test_restrictions(self):
        proxy = ProxyBase(None)
        with self.assertRaises(AttributeError):
            getattr(proxy, '__proxied_instance')
        with self.assertRaises(TypeError):
            proxy.foo = 1


class BindingProtocolTestCase(unittest.TestCase):

    def test_basic(self):
        thing = ExtThing('foo', ['foo', 'bar', 'baz'])
        mapping = {
            'foo': '/somewhere/foo',
            'bar': '/somewhere/bar',
            'baz': '/elsewhere/baz',
        }

        mapped_thing = MappedExtThing(thing).bind(mapping)

        self.assertEqual(mapped_thing.path, '/somewhere/foo')
        self.assertEqual(mapped_thing.paths, [
            '/somewhere/foo', '/somewhere/bar', '/elsewhere/baz'])
        self.assertEqual(mapped_thing.get_all_targets(), (
            ('/somewhere/foo'),
            ['/somewhere/foo', '/somewhere/bar', '/elsewhere/baz']
        ))

        self.assertTrue(isinstance(mapped_thing, MappedExtThing.bounded))

        with self.assertRaises(AttributeError):
            # cannot access attributes of an unbounded mapped thing
            MappedExtThing(thing).path

        with self.assertRaises(AttributeError):
            # cannot access attributes of an unbounded mapped thing
            MappedExtThing(thing).path

        # again, accessing the other permitted unwrapped (original)
        # instance will not be an issue
        self.assertIs(MappedExtThing(thing).unwrapped, thing)
