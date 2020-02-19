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


class ReuseAttr(object):
    """
    A class that define attributes that will require remapping but have
    special meaning defined by the protocol/metaclass.
    """

    def __init__(self, bind, mapped_bind, bounded, unwrapped):
        self.bind = bind
        self.mapped_bind = mapped_bind
        self.bounded = bounded
        self.unwrapped = unwrapped


class MappedExtThingMeta(MappingBinderMeta):
    """
    Demonstrates how to implement mapping from a provided mapping to the
    attribute value using the MappingBinderMeta class in a manner that
    fully contains the mapping to a single class and single function for
    each remapped attribute
    """

    def alt_path(mapping, attr_value):
        return mapping[attr_value]

    def path(mapping, attr_value):
        return mapping[attr_value]

    def paths(mapping, attr_value):
        return [mapping.get(k) for k in attr_value]


class MappedExtThing(ExtThing, metaclass=MappedExtThingMeta):
    """
    The final MappedExtThing class set up with the API as defined by
    the classes provided by the proxbind module.
    """


class ReuseAttrMeta(MappingBinderMeta):
    """
    Rebind the attributes with special meaning in the system.
    """

    def bind(mapping, attr_value):
        return 'bind(%s)' % mapping[attr_value]

    def mapped_bind(mapping, attr_value):
        return 'mapped_bind(%s)' % mapping[attr_value]

    def bounded(mapping, attr_value):
        return 'bounded(%s)' % mapping[attr_value]

    def unwrapped(mapping, attr_value):
        return 'unwrapped(%s)' % mapping[attr_value]


class MappedReuseAttr(ReuseAttr, metaclass=ReuseAttrMeta):
    """
    The actual usable class for testing.
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

        with self.assertRaises(AttributeError):
            # accessing metaclass defined attribute without the
            # corresponding attribute on the original will be an
            # attribute error.
            mapped_thing.alt_path

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

    def test_modified(self):
        thing = ExtThing('foo')
        mapping = {}

        mapped_thing = MappedExtThing(thing).bind(mapping)
        with self.assertRaises(KeyError):
            # failure only happens during access
            mapped_thing.path

        mapping['foo'] = '/some/where/to/foo'
        self.assertEqual(mapped_thing.path, '/some/where/to/foo')

        thing.path = 'bar'

        # original thing being modified will have an effect
        with self.assertRaises(KeyError):
            # failure only happens during access
            mapped_thing.path

        mapping['bar'] = '/some/where/to/bar'
        self.assertEqual(mapped_thing.path, '/some/where/to/bar')

    def test_ducked_out_types(self):
        # For cases where the source object does not have the attribute
        # for the binding process.
        mapping = {'foo': '/some/foo'}
        thing = Thing('foo')
        mapped_thing = MappedExtThing(thing).bind(mapping)
        self.assertEqual(mapped_thing.path, '/some/foo')

        with self.assertRaises(AttributeError):
            mapped_thing.paths

    def test_preserved_reused_mappings(self):
        mapping = {
            'one': 1,
            'two': 2,
            'three': 3,
            'four': 4,
        }
        base_attrs = ReuseAttr(
            bind='one', bounded='two', unwrapped='three', mapped_bind='four')
        attr_tester = MappedReuseAttr(base_attrs).bind(mapping)
        # prove that classes/objects providing attributes with the same
        # names as names in this metaclass do not conflict in actual
        # usage.
        self.assertEqual(attr_tester.bind, 'bind(1)')
        self.assertEqual(attr_tester.mapped_bind, 'mapped_bind(4)')
        self.assertEqual(attr_tester.bounded, 'bounded(2)')
        self.assertEqual(attr_tester.unwrapped, 'unwrapped(3)')


class MultiBindingProtocolTestCase(unittest.TestCase):

    def test_wrong_number_argument(self):
        thing = ExtThing('foo', ['foo', 'bar', 'baz'])
        mapping = {
            'foo': '/somewhere/foo',
            'bar': '/somewhere/bar',
            'baz': '/elsewhere/baz',
        }
        with self.assertRaises(ValueError):
            MappedExtThing(thing).mapped_bind((('path',),))

        with self.assertRaises(ValueError):
            MappedExtThing(thing).mapped_bind((
                ('path', mapping, 'path', 'extra'),
            ))

    def test_basic(self):
        thing = ExtThing('foo', ['foo', 'bar', 'baz'])
        mapping_one = {
            'foo': '/nowhere/foo',
        }
        mapping_two = {
            'foo': '/somewhere/foo',
            'bar': '/somewhere/bar',
            'baz': '/elsewhere/baz',
        }

        mapped_thing = MappedExtThing(thing).mapped_bind((
            ('path', mapping_one),
            ('paths', mapping_two),
            ('alt_path', mapping_two, 'path'),
        ))

        self.assertEqual(mapped_thing.path, '/nowhere/foo')
        self.assertEqual(mapped_thing.paths, [
            '/somewhere/foo', '/somewhere/bar', '/elsewhere/baz'])
        self.assertEqual(mapped_thing.get_all_targets(), (
            ('/nowhere/foo'),
            ['/somewhere/foo', '/somewhere/bar', '/elsewhere/baz']
        ))
        # even if alt_path was not in the original, the mapped_bind
        # provided the method to resolve this attribute.
        self.assertEqual(mapped_thing.alt_path, '/somewhere/foo')

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
