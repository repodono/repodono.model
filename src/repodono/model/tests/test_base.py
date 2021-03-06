import unittest
from operator import attrgetter
from pathlib import Path, PurePath
from functools import partial
from ast import literal_eval
from tempfile import TemporaryDirectory

from repodono.model.base import (
    BaseMapping,
    BasePreparedMapping,
    BaseResourceDefinition,
    PathMapping,
    DeferredComputedMapping,
    PreparedMapping,
    CompiledRouteResourceDefinitionMapping,
    DeferredPreparedMapping,
    ExecutionLocals,
    FlatGroupedMapping,
    ObjectInstantiationMapping,
    ReMappingProxy,
    PartialReMappingProxy,
    MultiReMappingProxy,
    ResourceDefinitionMapping,
    BaseBucketDefinition,
    BucketDefinitionMapping,
    EndpointDefinitionMapping,
    BoundedEndpointDefinition,
    ReMappingDefinitionMapping,
    RouteTrieMapping,
    structured_mapper,
    StructuredMapping,
)
from repodono.model.exceptions import MappingReferenceError
from repodono.model.testing import Thing
from repodono.model.testing import AttrBaseMapping


class BaseMappingTestCase(unittest.TestCase):

    def test_basic(self):
        mapping = BaseMapping()
        self.assertEqual(0, len(mapping))
        self.assertEqual([], sorted(iter((mapping))))
        mapping['abc'] = 1
        self.assertEqual(mapping['abc'], 1)
        self.assertIn('abc', mapping)
        self.assertEqual(dict(mapping), literal_eval(str(mapping)))

    def test_casted(self):
        mapping = BaseMapping({'a': 1})
        self.assertEqual(mapping['a'], 1)

    def test_attr_access_checks(self):
        # Test the one with the mixin.
        mapping = AttrBaseMapping({'a': 1})
        self.assertEqual(mapping.a, 1)

        with self.assertRaises(AttributeError) as e:
            mapping.b

        self.assertEqual(
            "'AttrBaseMapping' object has no attribute 'b'",
            e.exception.args[0])

        with self.assertRaises(TypeError) as e:
            mapping.b = 1

    def test_attr_access_private_rejected(self):
        mapping = AttrBaseMapping({
            '_private': 1,
        })

        with self.assertRaises(AttributeError) as e:
            mapping._private

        self.assertEqual(
            "'AttrBaseMapping' object has no attribute '_private'",
            e.exception.args[0])

    def test_attr_assignment_private_accepted(self):
        mapping = AttrBaseMapping([])

        with self.assertRaises(AttributeError):
            mapping._private

        mapping._private = 1
        self.assertEqual(mapping._private, 1)

    def test_attr_assignment_public_rejected(self):
        mapping = AttrBaseMapping([])
        with self.assertRaises(TypeError) as e:
            mapping.a = 1

        self.assertEqual(
            "can't set attributes of 'AttrBaseMapping' objects",
            e.exception.args[0])

    def test_prepared_mappings(self):
        pm = PreparedMapping()
        pm['1'] = 1
        self.assertEqual(1, pm['1'])

        dpm = DeferredPreparedMapping()
        dpm['1'] = 1
        self.assertEqual(1, dpm['1'])

    def test_prepared_mappings_subclassing(self):
        class BaseNoneValueMapping(BasePreparedMapping):
            @classmethod
            def prepare_from_item(cls, key, value):
                if value is not None:
                    raise TypeError('None required')

        class NPM(BaseNoneValueMapping, PreparedMapping):
            pass

        class DPM(BaseNoneValueMapping, DeferredPreparedMapping):
            pass

        npm = NPM()
        npm['0'] = None
        with self.assertRaises(TypeError):
            npm['1'] = 1

        self.assertIn('0', npm)
        self.assertNotIn('1', npm)

        dpm = DPM()
        dpm['0'] = None
        dpm['1'] = 1

        self.assertIn('0', dpm)
        self.assertIn('1', dpm)
        self.assertEqual(None, dpm['0'])
        with self.assertRaises(TypeError):
            dpm['1']

    def test_path_mapping(self):
        pm = PathMapping()
        pm['test'] = 'test'
        self.assertTrue(isinstance(pm['test'], Path))

    def test_deferred_computed_mapping(self):
        dcm = DeferredComputedMapping()
        items = {1: 'value'}
        dcm['object'] = object
        dcm['test'] = partial(items.pop, 1)
        # repr shouldn't execute anything
        self.assertIn('partial', repr(dcm))
        self.assertTrue(isinstance(dcm['object'], object))
        self.assertEqual(dcm['test'], 'value')
        self.assertEqual({}, items)

        with self.assertRaises(TypeError):
            dcm['object'] = object()


class FlatGroupedMappingTestCase(unittest.TestCase):

    def test_empty(self):
        mapping = FlatGroupedMapping([])
        self.assertEqual(0, len(mapping))
        self.assertEqual({}, dict(mapping))
        with self.assertRaises(KeyError):
            mapping[1]

        mapping['a'] = 1
        self.assertEqual(mapping['a'], 1)
        self.assertEqual(literal_eval(str(mapping)), {'a': 1})

    def test_mapping_instantiation_empty_map(self):
        mapping = FlatGroupedMapping([
            {
                'abc': '1',
                'def': '2',
            }, {
                'abc': 'abc',
                'def': 'def',
                'ghi': 'ghi',
            }
        ])
        self.assertEqual(mapping['abc'], '1')
        self.assertEqual(mapping['ghi'], 'ghi')
        self.assertIn('abc', mapping)
        self.assertIn('ghi', mapping)

        self.assertEqual(
            ['abc', 'def', 'ghi'],
            sorted(iter(mapping)),
        )

        self.assertEqual(
            {
                'abc': '1',
                'def': '2',
                'ghi': 'ghi',
            },
            dict(mapping),
        )
        self.assertEqual(
            {
                'abc': '1',
                'def': '2',
                'ghi': 'ghi',
            },
            literal_eval(str(mapping)),
        )

        self.assertEqual(3, len(mapping))

    def test_mapping_instantiation_assigned(self):
        mapping = FlatGroupedMapping([
            {
                'abc': '1',
                'def': '2',
            }, {
                'abc': 'abc',
                'def': 'def',
                'ghi': 'ghi',
            }
        ])

        with self.assertRaises(KeyError):
            mapping['abc'] = False

        with self.assertRaises(KeyError):
            del mapping['abc']

        mapping['custom'] = 1

        self.assertEqual(
            {
                'abc': '1',
                'custom': 1,
                'def': '2',
                'ghi': 'ghi',
            },
            dict(mapping),
        )
        self.assertEqual(
            {
                'abc': '1',
                'custom': 1,
                'def': '2',
                'ghi': 'ghi',
            },
            literal_eval(str(mapping)),
        )
        self.assertEqual(
            ['abc', 'custom', 'def', 'ghi'],
            sorted(iter(mapping)),
        )
        self.assertIn('custom', mapping)
        self.assertEqual(4, len(mapping))

        del mapping['custom']
        self.assertNotIn('custom', mapping)
        self.assertEqual(3, len(mapping))

    def test_mapping_deferred_keyerror(self):
        def key_error():
            raise KeyError()

        def value_error():
            raise ValueError()

        mapping = FlatGroupedMapping([
            DeferredComputedMapping({
                'error': key_error,
                'foo': key_error,
                'bar': value_error,
            }), {
                'foo': '1',
                'bar': '2',
            },
        ])

        self.assertIn('error', mapping)
        with self.assertRaises(KeyError):
            mapping['error']

        self.assertEqual(mapping['foo'], '1')

        with self.assertRaises(ValueError):
            mapping['bar']


class StructuredMapperTestCase(unittest.TestCase):

    def test_creation(self):
        definition = (
            ('root', (
                ('child1', BaseMapping),
                ('child2', BaseMapping),
            ),),
        )
        raw_mapping = {
            'root': {
                'child1': {
                    'key1': 'child1.1',
                    'key2': 'child1.2',
                },
                'child2': {
                    'key2': 'child2.2',
                    'key3': 'child2.3',
                },
            },
        }
        mappings = structured_mapper(definition, raw_mapping)
        self.assertEqual(2, len(mappings))
        self.assertTrue(isinstance(mappings[0], BaseMapping))
        self.assertTrue(isinstance(mappings[1], BaseMapping))
        self.assertEqual(mappings[0], {
            'key1': 'child1.1',
            'key2': 'child1.2',
        })
        self.assertEqual(mappings[1], {
            'key2': 'child2.2',
            'key3': 'child2.3',
        })

    def test_creation_special_vars(self):
        class WithoutVars(BaseMapping):
            def __init__(self, *a, **kw):
                self.vars = NotImplemented

        class WithVars(BaseMapping):
            def __init__(self, *a, vars_=None, **kw):
                self.vars = vars_

        definition = (
            ('root', (
                ('without_vars', WithoutVars),
                ('with_vars', WithVars),
            ),),
        )
        raw_mapping = {
            'root': {
                'without_vars': {
                    'key1': 'value1',
                },
                'with_vars': {
                    'key2': 'value2',
                },
            },
        }
        vars_ = {}
        mappings = structured_mapper(definition, raw_mapping, vars_=vars_)
        self.assertEqual(2, len(mappings))
        self.assertTrue(isinstance(mappings[0], WithoutVars))
        self.assertTrue(isinstance(mappings[1], WithVars))
        self.assertIs(mappings[1].vars, vars_)


class StructuredMappingTestCase(unittest.TestCase):

    def test_creation_single(self):
        cls = StructuredMapping((
            ('root', BaseMapping),
        ))
        mapping = cls({
            'root': {
                'child1': 'value1',
                'child2': 'value2',
            },
        })
        self.assertEqual(2, len(mapping))
        self.assertEqual(mapping['child1'], 'value1')
        self.assertEqual(mapping['child2'], 'value2')

        self.assertFalse(callable(mapping))
        self.assertNotIn('child3', mapping)
        mapping['child3'] = 'new'
        self.assertEqual(mapping['child3'], 'new')
        self.assertEqual(3, len(mapping))
        with self.assertRaises(KeyError) as e:
            mapping['child2'] = 'new'

        self.assertEqual(e.exception.args[0], "'child2' is read-only")

    def test_creation_nested_definition(self):
        cls = StructuredMapping((
            ('root', (
                ('child1', BaseMapping),
                ('child2', BaseMapping),
            ),),
        ))
        mapping = cls({
            'root': {
                'child1': {
                    'key1': 'child1.1',
                    'key2': 'child1.2',
                },
                'child2': {
                    'key2': 'child2.2',
                    'key3': 'child2.3',
                },
            },
        })
        self.assertFalse(callable(mapping))
        self.assertEqual(3, len(mapping))
        self.assertEqual(mapping['key1'], 'child1.1')
        self.assertEqual(mapping['key2'], 'child1.2')
        self.assertEqual(mapping['key3'], 'child2.3')

        self.assertNotIn('key4', mapping)
        mapping['key4'] = 'new'
        self.assertEqual(mapping['key4'], 'new')
        self.assertEqual(4, len(mapping))
        with self.assertRaises(KeyError) as e:
            mapping['key3'] = 'new'

        self.assertEqual(e.exception.args[0], "'key3' is read-only")

    def test_creation_nested_structured_mapping(self):
        cls = StructuredMapping((
            ('root', StructuredMapping((
                ('child1', BaseMapping),
                ('child2', BaseMapping),
            ),),),
        ))
        mapping = cls({
            'root': {
                'child1': {
                    'key1': 'child1.1',
                    'key2': 'child1.2',
                },
                'child2': {
                    'key2': 'child2.2',
                    'key3': 'child2.3',
                },
            },
        })
        self.assertFalse(callable(mapping))
        self.assertEqual(3, len(mapping))
        self.assertEqual(mapping['key1'], 'child1.1')
        self.assertEqual(mapping['key2'], 'child1.2')
        self.assertEqual(mapping['key3'], 'child2.3')

        self.assertNotIn('key4', mapping)
        mapping['key4'] = 'new'
        self.assertEqual(mapping['key4'], 'new')
        self.assertEqual(4, len(mapping))
        with self.assertRaises(KeyError) as e:
            mapping['key3'] = 'new'

        self.assertEqual(e.exception.args[0], "'key3' is read-only")

    def test_creation_with_callable_mapping(self):
        called = []

        class CallableMapping(BaseMapping):
            def __call__(self):
                called.append(True)

        cls = StructuredMapping((
            ('root', CallableMapping),
        ))
        mapping = cls({'root': {'key': 'value'}})
        self.assertTrue(callable(mapping))
        self.assertNotIn(True, called)
        mapping()
        self.assertIn(True, called)


class ObjectInstantiationMappingTestCase(unittest.TestCase):

    def test_empty(self):
        result = ObjectInstantiationMapping([], {})
        self.assertEqual(0, len(result))

    def test_bad_value(self):
        with self.assertRaises(ValueError):
            ObjectInstantiationMapping([{
                '__name__': 'missing the rest',
            }], {})

        with self.assertRaises(ValueError):
            ObjectInstantiationMapping([{
                '__init__': 'repodono.model.testing:Thing',
                'path': 'a_path',
            }], {})

    def test_list_dict_name_construction(self):
        value = [{
            '__name__': 'thing',
            '__init__': 'repodono.model.testing:Thing',
            'path': 'a_path',
        }]
        marker = object()
        vars_ = {'a_path': marker}
        result = ObjectInstantiationMapping(value, vars_)
        self.assertEqual({'a_path': marker}, vars_)
        # ensure source value is untouched
        self.assertEqual([{
            '__name__': 'thing',
            '__init__': 'repodono.model.testing:Thing',
            'path': 'a_path',
        }], value)
        self.assertTrue(isinstance(result['thing'], Thing))
        self.assertEqual(result['thing'].path, marker)

    def test_list_dict_name_construction_multiple(self):
        value = [{
            '__name__': 'thing1',
            '__init__': 'repodono.model.testing:Thing',
            'path': 'a_path',
        }, {
            '__name__': 'thing2',
            '__init__': 'repodono.model.testing:Thing',
            'path': 'a_path',
        }, {
            '__name__': 'thing3',
            '__init__': 'repodono.model.testing:Thing',
            'path': 'a_path',
        }]
        marker = object()
        vars_ = {'a_path': marker}
        result = ObjectInstantiationMapping(value, vars_)
        # ensure source value is untouched
        self.assertEqual([{
            '__name__': 'thing1',
            '__init__': 'repodono.model.testing:Thing',
            'path': 'a_path',
        }, {
            '__name__': 'thing2',
            '__init__': 'repodono.model.testing:Thing',
            'path': 'a_path',
        }, {
            '__name__': 'thing3',
            '__init__': 'repodono.model.testing:Thing',
            'path': 'a_path',
        }], value)
        self.assertTrue(isinstance(result['thing1'], Thing))
        self.assertEqual(result['thing1'].path, marker)
        self.assertTrue(isinstance(result['thing2'], Thing))
        self.assertEqual(result['thing2'].path, marker)
        self.assertTrue(isinstance(result['thing3'], Thing))
        self.assertEqual(result['thing3'].path, marker)

    def test_key_value_construction(self):
        value = {'target': {
            '__init__': 'repodono.model.testing:Thing',
            'path': 'a_path',
        }}
        marker = object()
        vars_ = {'a_path': marker}
        result = ObjectInstantiationMapping(value, vars_)
        self.assertEqual({'a_path': marker}, vars_)
        # ensure source value is untouched
        self.assertEqual({'target': {
            '__init__': 'repodono.model.testing:Thing',
            'path': 'a_path',
        }}, value)
        self.assertTrue(isinstance(result['target'], Thing))
        self.assertEqual(result['target'].path, marker)

        values = {
            'target1': {
                '__init__': 'repodono.model.testing:Thing',
                'path': 'a_path',
            },
            'target2': {
                '__init__': 'repodono.model.testing:Thing',
                'path': 'a_path',
            },
            'target3': {
                '__init__': 'repodono.model.testing:Thing',
                'path': 'a_path',
            },
        }
        results = ObjectInstantiationMapping(values, vars_)
        self.assertEqual({'a_path': marker}, vars_)
        self.assertTrue(isinstance(results['target1'], Thing))
        self.assertEqual(results['target1'].path, marker)
        self.assertTrue(isinstance(results['target2'], Thing))
        self.assertEqual(results['target2'].path, marker)
        self.assertTrue(isinstance(results['target3'], Thing))
        self.assertEqual(results['target3'].path, marker)

    def test_2tuple_construction(self):
        value = [('target', {
            '__init__': 'repodono.model.testing:Thing',
            'path': 'a_path',
        })]
        marker = object()
        vars_ = {'a_path': marker}
        result = ObjectInstantiationMapping(value, vars_)
        self.assertEqual({'a_path': marker}, vars_)
        self.assertTrue(isinstance(result['target'], Thing))
        self.assertEqual(result['target'].path, marker)

        values = [('target1', {
            '__init__': 'repodono.model.testing:Thing',
            'path': 'a_path',
        }), ('target2', {
            '__init__': 'repodono.model.testing:Thing',
            'path': 'a_path',
        })]
        results = ObjectInstantiationMapping(values, vars_)
        self.assertEqual({'a_path': marker}, vars_)
        self.assertTrue(isinstance(results['target1'], Thing))
        self.assertEqual(results['target1'].path, marker)
        self.assertTrue(isinstance(results['target2'], Thing))
        self.assertEqual(results['target2'].path, marker)

    def test_instantiation_order(self):
        value = [{
            '__name__': 'thing1',
            '__init__': 'repodono.model.testing:Thing',
            'path': 'thing0',
        }, {
            '__name__': 'thing2',
            '__init__': 'repodono.model.testing:Thing',
            'path': 'thing1',
        }, {
            '__name__': 'thing3',
            '__init__': 'repodono.model.testing:Thing',
            'path': 'thing2',
        }]
        thing0 = object()
        vars_ = {'thing0': thing0}
        result = ObjectInstantiationMapping(value, vars_)
        self.assertTrue(isinstance(result['thing1'], Thing))
        self.assertEqual(result['thing1'].path, thing0)
        self.assertTrue(isinstance(result['thing2'], Thing))
        self.assertEqual(result['thing2'].path, result['thing1'])
        self.assertTrue(isinstance(result['thing3'], Thing))
        self.assertEqual(result['thing3'].path, result['thing2'])

    def test_instantiation_order_failure(self):
        value = [{
            '__name__': 'thing1',
            '__init__': 'repodono.model.testing:Thing',
            'path': 'thing2',
        }, {
            '__name__': 'thing2',
            '__init__': 'repodono.model.testing:Thing',
            'path': 'thing0',
        }]
        thing0 = object()
        vars_ = {'thing0': thing0}

        with self.assertRaises(MappingReferenceError):
            ObjectInstantiationMapping(value, vars_)

    def test_instantiation_redefinition_blocked(self):
        value = [{
            '__name__': 'thing0',
            '__init__': 'repodono.model.testing:Thing',
            'path': 'thing0',
        }, {
            '__name__': 'thing1',
            '__init__': 'repodono.model.testing:Thing',
            'path': 'thing0',
        }]
        thing0 = object()
        vars_ = {'thing0': thing0}
        result = ObjectInstantiationMapping(value, vars_)
        # since in the system, environment values always have precedence
        # over objects.
        self.assertIsNot(result['thing0'], thing0)
        self.assertIs(result['thing0'].path, thing0)
        self.assertIsNot(result['thing1'].path, result['thing0'])
        self.assertIs(result['thing1'].path, thing0)


class ReMappingProxyTestCase(unittest.TestCase):

    def test_empty(self):
        mapping = ReMappingProxy({}, {})
        self.assertEqual(len(mapping), 0)

    def test_empty_remap(self):
        mapping = ReMappingProxy({}, {'thing': 'other'})
        self.assertEqual(len(mapping), 0)
        self.assertNotIn('thing', mapping)

    def test_empty_mapping(self):
        mapping = ReMappingProxy({'local': 'external'}, {})
        self.assertEqual(len(mapping), 1)
        self.assertNotIn('local', mapping)
        self.assertNotIn('external', mapping)

    def test_proxying_one_to_one(self):
        base = {
            'external1': 'value1',
            'external2': 'value2',
        }
        mapping = ReMappingProxy({
            'internal1': 'external1',
            'internal2': 'external2',
            'internal3': 'external3',
        }, base)
        self.assertIn('internal1', mapping)
        self.assertIn('internal2', mapping)
        self.assertNotIn('internal3', mapping)
        self.assertEqual(list(mapping), [
            'internal1', 'internal2', 'internal3'])
        self.assertEqual(mapping['internal1'], 'value1')
        self.assertEqual(mapping['internal2'], 'value2')

        with self.assertRaises(MappingReferenceError):
            mapping['internal3']

        self.assertEqual(len(mapping), 3)
        base.update({
            'external3': 'value3',
            'external4': 'value4',
        })
        self.assertEqual(len(mapping), 3)
        self.assertIn('internal3', mapping)
        self.assertEqual(list(mapping), [
            'internal1', 'internal2', 'internal3'])

    def test_proxying_many_to_one(self):
        value1 = object()
        value2 = object()
        base = {
            'external1': value1,
        }
        mapping = ReMappingProxy({
            'internal1': 'external1',
            'internal2': 'external1',
            'internal3': 'external1',
            'internal4': 'external2',
            'internal5': 'external2',
            'internal6': 'external2',
        }, base)
        self.assertIn('internal1', mapping)
        self.assertIn('internal2', mapping)
        self.assertIn('internal3', mapping)
        self.assertEqual(list(mapping), [
            'internal1', 'internal2', 'internal3',
            'internal4', 'internal5', 'internal6',
        ])
        self.assertIs(mapping['internal1'], value1)
        self.assertIs(mapping['internal2'], value1)
        self.assertIs(mapping['internal3'], value1)
        # length is based completely on the remap.
        self.assertEqual(len(mapping), 6)
        base['external2'] = value2
        # likewise here.
        self.assertEqual(len(mapping), 6)
        self.assertEqual(list(mapping), [
            'internal1', 'internal2', 'internal3',
            'internal4', 'internal5', 'internal6',
        ])
        self.assertEqual(dict(mapping), {
            'internal1': value1,
            'internal2': value1,
            'internal3': value1,
            'internal4': value2,
            'internal5': value2,
            'internal6': value2,
        })


class PartialReMappingProxyTestCase(unittest.TestCase):

    def test_empty(self):
        mapping = PartialReMappingProxy({}, {})
        self.assertEqual(len(mapping), 0)

    def test_empty_remap(self):
        mapping = PartialReMappingProxy({}, {'thing': 'other'})
        self.assertEqual(len(mapping), 0)
        self.assertNotIn('thing', mapping)

    def test_empty_mapping(self):
        mapping = PartialReMappingProxy({'local': 'external'}, {})
        self.assertEqual(len(mapping), 0)
        self.assertNotIn('local', mapping)
        self.assertNotIn('external', mapping)

    def test_proxying_one_to_one(self):
        base = {
            'external1': 'value1',
            'external2': 'value2',
        }
        mapping = PartialReMappingProxy({
            'internal1': 'external1',
            'internal2': 'external2',
            'internal3': 'external3',
        }, base)
        self.assertIn('internal1', mapping)
        self.assertIn('internal2', mapping)
        self.assertEqual(list(mapping), ['internal1', 'internal2'])
        self.assertEqual(mapping['internal1'], 'value1')
        self.assertEqual(mapping['internal2'], 'value2')
        self.assertNotIn('internal3', mapping)
        self.assertEqual(len(mapping), 2)
        base.update({
            'external3': 'value3',
            'external4': 'value4',
        })
        self.assertEqual(len(mapping), 3)
        self.assertIn('internal3', mapping)
        self.assertEqual(list(mapping), [
            'internal1', 'internal2', 'internal3'])

    def test_proxying_many_to_one(self):
        value1 = object()
        value2 = object()
        base = {
            'external1': value1,
        }
        mapping = PartialReMappingProxy({
            'internal1': 'external1',
            'internal2': 'external1',
            'internal3': 'external1',
            'internal4': 'external2',
            'internal5': 'external2',
            'internal6': 'external2',
        }, base)
        self.assertIn('internal1', mapping)
        self.assertIn('internal2', mapping)
        self.assertIn('internal3', mapping)
        self.assertEqual(list(mapping), [
            'internal1', 'internal2', 'internal3'])
        self.assertIs(mapping['internal1'], value1)
        self.assertIs(mapping['internal2'], value1)
        self.assertIs(mapping['internal3'], value1)
        # length is actually three, even though original mapping as one.
        # element.
        self.assertEqual(len(mapping), 3)
        base['external2'] = value2
        # likewise here.
        self.assertEqual(len(mapping), 6)
        self.assertEqual(list(mapping), [
            'internal1', 'internal2', 'internal3',
            'internal4', 'internal5', 'internal6',
        ])
        self.assertEqual(dict(mapping), {
            'internal1': value1,
            'internal2': value1,
            'internal3': value1,
            'internal4': value2,
            'internal5': value2,
            'internal6': value2,
        })


class MultiReMappingProxyTestCase(unittest.TestCase):

    def test_empty(self):
        mapping = MultiReMappingProxy({}, {})
        self.assertEqual(len(mapping), 0)

    def test_empty_remap(self):
        mapping = MultiReMappingProxy({}, {'thing': 'other'})
        self.assertEqual(len(mapping), 0)
        self.assertNotIn('thing', mapping)

    def test_nested_remap(self):
        mapping = MultiReMappingProxy(remap={
            'local': 'external',
            'nested': {
                'foo': 'external_foo',
                'bar': 'external_bar',
                'baz': 'external_baz',
                'level2': {
                    'final': 'external',
                }
            }
        }, mapping={
            'external': 'E',
            'external_foo': 'F',
            'external_bar': 'B',
            'external_baz': 'Z',
        })
        self.assertEqual(len(mapping), 2)
        self.assertEqual(len(mapping['nested']), 4)
        self.assertEqual(mapping['nested']['foo'], 'F')
        self.assertEqual(mapping['nested']['level2']['final'], 'E')
        # iteration
        self.assertEqual(sorted(mapping), ['local', 'nested'])
        # membership
        self.assertIn('local', mapping)
        self.assertIn('nested', mapping)
        self.assertNotIn('not_present', mapping)
        self.assertIn('foo', mapping['nested'])


class BaseResourceDefinitionTestCase(unittest.TestCase):

    def test_construction_and_usage(self):
        missing = BaseResourceDefinition(name='missing', call=Thing, kwargs={})
        full = BaseResourceDefinition(name='full', call=Thing, kwargs={
            'path': 'path_key',
        })

        partial_m = missing(vars_={})
        partial_f = full(vars_={'path_key': 'the_path'})

        with self.assertRaises(TypeError):
            # missing argument path
            partial_m()

        inst_m = partial_m(path='m')
        inst_f = partial_f()
        inst_f_reassign = partial_f(path='hi')

        self.assertEqual(inst_m.path, 'm')
        self.assertEqual(inst_f.path, 'the_path')
        self.assertEqual(inst_f_reassign.path, 'hi')

    def test_cast_list_to_mapping(self):
        key1 = BaseResourceDefinition(name='key1', call=Thing, kwargs={})
        key2 = BaseResourceDefinition(name='key2', call=Thing, kwargs={})
        values = [key1, key2, ('key3', 'other')]
        mapping = dict(values)
        # automatically be usable as part of a cast as part of an item
        # in a list to a mapping under the key provided by name.
        self.assertIs(mapping['key1'], key1)
        self.assertIs(mapping['key2'], key2)
        self.assertIs(mapping['key3'], 'other')

    def test_call_with_various_keys(self):
        key_str = BaseResourceDefinition(
            name='key1', call='thing', kwargs={'path': 'target'})
        key_callable = BaseResourceDefinition(
            name='key2', call=Thing, kwargs={'path': 'target'})
        key_attrgetter = BaseResourceDefinition(
            name='key3', call=attrgetter('thing'), kwargs={'path': 'target'})
        key_attrgetter_dot = BaseResourceDefinition(
            name='key4', call=attrgetter('dot_thing.path'),
            kwargs={'path': 'dot_target'})

        raw_dict = {
            'dot_thing': Thing(path=Thing),
            'thing': Thing,
            'target': 'the_value',
            'dot_target': 'dot_value',
        }
        attr_mapping = AttrBaseMapping(raw_dict)
        kwargs = {}

        result = key_str(vars_=raw_dict, **kwargs)
        self.assertTrue(callable(result))
        self.assertEqual(result().path, 'the_value')

        result = key_callable(vars_=raw_dict, **kwargs)
        self.assertTrue(callable(result))
        self.assertEqual(result().path, 'the_value')

        # for the ones involving attrgetter, BaseMapping is required.
        result = key_attrgetter(vars_=attr_mapping, **kwargs)
        self.assertTrue(callable(result))
        self.assertEqual(result().path, 'the_value')

        result = key_attrgetter_dot(vars_=attr_mapping, **kwargs)
        self.assertTrue(callable(result))
        self.assertEqual(result().path, 'dot_value')

    def test_consts(self):
        # normally, the consts mapping is not provided by the user,
        # but reserved for usage by the system.
        static = BaseResourceDefinition(name='static', call=Thing, kwargs={
            'path': '__path__'
        }, consts={
            '__path__': 'static'
        })
        mapping = dict([static])
        # automatically be usable as part of a cast as part of an item
        # in a list to a mapping under the key provided by name.
        self.assertIs(mapping['static'], static)
        self.assertEqual(mapping['static'](vars_={
            '__path__': 'modified',
        })().path, 'static')

    def test_various_types(self):
        # More additional testing is done in test_config for more
        # varied use cases from simulated toml configurations.

        key_missing = BaseResourceDefinition(
            name='missing', call=Thing, kwargs={'path': 'missing'})
        key_literal = BaseResourceDefinition(
            name='literal', call=Thing, kwargs={'path': '"literal"'})
        key_number = BaseResourceDefinition(
            name='number', call=Thing, kwargs={'path': 1})
        key_boolean = BaseResourceDefinition(
            name='boolean', call=Thing, kwargs={'path': True})
        key_invalid_literal = BaseResourceDefinition(
            name='invalid_lit', call=Thing, kwargs={'path': '"unterminated'})
        key_invalid_type = BaseResourceDefinition(
            name='invalid_type', call=Thing, kwargs={'path': NotImplemented})

        raw_dict = {
            'literal': 'oops this got resolved?',
            '"literal"': 'oops this got resolved?',
            '"unterminated': 'oops this got resolved?',
            1: 'oops this got resolved?',
            True: 'oops this got resolved?',
        }

        literal = key_literal(vars_=raw_dict)
        self.assertEqual(literal().path, 'literal')

        number = key_number(vars_=raw_dict)
        self.assertEqual(number().path, 1)

        boolean = key_boolean(vars_=raw_dict)
        self.assertEqual(boolean().path, True)

        with self.assertRaises(MappingReferenceError) as e:
            key_missing(vars_=raw_dict)()

        self.assertEqual(
            e.exception.args[0],
            "reference to 'missing' could not be resolved")

        with self.assertRaises(MappingReferenceError) as e:
            key_invalid_literal(vars_=raw_dict)()

        self.assertEqual(
            e.exception.args[0],
            "'\"unterminated' is an unsupported literal value")

        with self.assertRaises(MappingReferenceError) as e:
            key_invalid_type(vars_=raw_dict)()

        self.assertEqual(
            e.exception.args[0],
            "NotImplemented is of an unsupported type for mapping")


class ResourceDefinitionMappingTestCase(unittest.TestCase):

    def test_invalid_call_and_init(self):
        # TODO validate exception message.
        with self.assertRaises(ValueError):
            ResourceDefinitionMapping({
                '/some/path/{id}': {
                    '__name__': 'obj',
                    '__call__': 'a_function',
                    '__init__': 'repodono.model.testing:Thing',
                }
            })

        with self.assertRaises(ValueError):
            ResourceDefinitionMapping({
                '/some/path/{id}': {
                    '__name__': 'obj',
                }
            })

    def test_name_reference_creation(self):
        mapping = ResourceDefinitionMapping({
            '/some/path/{id}': {
                '__name__': 'obj',
                '__call__': 'a_function',
                'arg1': 'reference1',
            }
        })
        marker1 = object()
        vars_ = AttrBaseMapping({
            'a_function': Thing(None),
            'reference1': marker1,
        })
        definition = mapping['/some/path/{id}'][0]
        call = definition(vars_)
        self.assertTrue(callable(call))
        result = call()
        self.assertEqual(((), {'arg1': marker1},), result)

    def test_entrypoint_creation(self):
        # TODO need to test __init__ that is invalid
        mapping = ResourceDefinitionMapping({
            '/some/path/{id}': {
                '__name__': 'obj',
                '__init__': 'repodono.model.testing:Thing',
                'path': 'a_path',
            }
        })
        a_path = object()
        vars_ = {
            'a_path': a_path,
        }
        definition = mapping['/some/path/{id}'][0]
        self.assertIs(definition.call, Thing)
        call = definition(vars_)
        self.assertTrue(callable(call))
        result = call()
        self.assertTrue(isinstance(result, Thing))
        self.assertIs(result.path, a_path)

    def test_name_reference_creation_multiple_values(self):
        mapping = ResourceDefinitionMapping({
            '/some/path/{id}': [{
                '__name__': 'obj1',
                '__call__': 'a_function',
                'arg1': 'reference1',
            }, {
                '__name__': 'obj2',
                '__call__': 'a_function',
                'arg1': 'reference1',
            }]
        })
        marker1 = object()
        vars_ = AttrBaseMapping({
            'a_function': Thing(None),
            'reference1': marker1,
        })
        definition = mapping['/some/path/{id}'][0]
        call = definition(vars_)
        self.assertTrue(callable(call))
        result = call()
        self.assertEqual(((), {'arg1': marker1},), result)
        self.assertEqual(definition.name, 'obj1')
        self.assertEqual(mapping['/some/path/{id}'][1].name, 'obj2')

    def test_entrypoint_creation_multiple_values(self):
        # TODO need to test __init__ that is invalid
        mapping = ResourceDefinitionMapping({
            '/some/path/{id}': [{
                '__name__': 'obj1',
                '__init__': 'repodono.model.testing:Thing',
                'path': 'a_path',
            }, {
                '__name__': 'obj2',
                '__init__': 'repodono.model.testing:Thing',
                'path': 'a_path',
            }]
        })
        a_path = object()
        vars_ = {
            'a_path': a_path,
        }
        definition = mapping['/some/path/{id}'][0]
        self.assertIs(definition.call, Thing)
        call = definition(vars_)
        self.assertTrue(callable(call))
        result = call()
        self.assertTrue(isinstance(result, Thing))
        self.assertIs(result.path, a_path)

        self.assertEqual(definition.name, 'obj1')
        self.assertEqual(mapping['/some/path/{id}'][1].name, 'obj2')

    def test_name_reference_assignment(self):
        mapping = ResourceDefinitionMapping({
            '/some/path/{id}': [{
                '__name__': 'obj1',
                '__call__': 'a_function',
                'arg1': 'reference1',
            }, {
                '__name__': 'obj2',
                '__call__': 'a_function',
                'arg1': 'reference1',
            }]
        })
        # verify existing value
        self.assertEqual(2, len(mapping['/some/path/{id}']))
        self.assertEqual(mapping['/some/path/{id}'][0].name, 'obj1')
        self.assertEqual(mapping['/some/path/{id}'][1].name, 'obj2')

        # naive assignment function as append (non-standard)
        mapping['/some/path/{id}'] = {
            '__name__': 'obj3',
            '__call__': 'a_function',
            'arg1': 'reference1',
        }
        self.assertEqual(3, len(mapping['/some/path/{id}']))
        self.assertEqual(mapping['/some/path/{id}'][2].name, 'obj3')

        # assignment of a new list will reset
        mapping['/some/path/{id}'] = [{
            '__name__': 'obj3',
            '__call__': 'a_function',
            'arg1': 'reference1',
        }]
        self.assertEqual(1, len(mapping['/some/path/{id}']))
        self.assertEqual(mapping['/some/path/{id}'][0].name, 'obj3')


class BaseBucketDefinitionTestCase(unittest.TestCase):

    def test_base_match(self):
        bucket = BaseBucketDefinition('base', [], {'accept': ['text/html']})
        self.assertEqual(0, bucket.match({'accept': 'text/plain'}))
        self.assertEqual(1, bucket.match({'accept': 'text/html'}))
        self.assertEqual(1, bucket.match({
            'accept': 'text/html',
            'x-some-unrelated-thing': 'somevalue',
        }))

    def test_multi_match(self):
        bucket = BaseBucketDefinition('base', [], {
            'accept': ['text/xml', 'application/xml'],
            'accept-language': ['en-NZ', 'en-US'],
        })
        self.assertEqual(0, bucket.match({'accept': 'application/xml'}))
        self.assertEqual(0, bucket.match({'accept-language': 'en-NZ'}))
        self.assertEqual(1, bucket.match({
            'accept': 'text/xml',
            'accept-language': 'en-NZ',
        }))
        self.assertEqual(1, bucket.match({
            'accept': 'application/xml',
            'accept-language': 'en-US',
        }))
        self.assertEqual(0, bucket.match({
            'accept': 'text/xml',
            'accept-language': 'ja-JP',
        }))


class BucketDefinitionMappingTestCase(unittest.TestCase):

    def test_missing_provider(self):
        # TODO validate exception message.
        with self.assertRaises(ValueError):
            BucketDefinitionMapping({
                '_': {
                    # missing __root__
                }
            })

    def test_basic_creation(self):
        mapping = BucketDefinitionMapping({
            '_': {
                '__roots__': ['some_location'],
                'accept': ['*/*'],
            },
            'json': {
                '__roots__': ['json_location'],
                'accept': ['application/json'],
            },
        })
        self.assertEqual(mapping['_'].roots, ['some_location'])
        self.assertEqual(mapping['_'].environment, {'accept': ['*/*']})
        self.assertEqual(mapping['json'].roots, ['json_location'])
        self.assertEqual(mapping['json'].environment, {
            'accept': ['application/json']})

    def test_basic_score_matching(self):
        mapping = BucketDefinitionMapping({
            '_': {
                '__roots__': ['some_location'],
                # not going to provide a full capture as this isn't
                # exactly implemented.
                # 'accept': ['*/*'],
            },
            'json': {
                '__roots__': ['json_location'],
                'accept': ['text/json', 'application/json'],
            },
            'xml': {
                '__roots__': ['xml_location'],
                'accept': ['text/xml', 'application/xml'],
            },
        })
        key_buckets = mapping({'accept': 'text/xml'})
        # XXX currently with how the algorithm is set up, an empty
        # accept as defined will simply match everything, so of course
        # there will be a fallback to the default _ bucket.
        self.assertEqual(2, len(key_buckets))
        key, bucket = key_buckets[0]
        # first match should be xml
        self.assertEqual('xml', key)
        self.assertEqual(['xml_location'], bucket.roots)

        key, bucket = mapping({'accept': 'text/html'})[0]
        self.assertEqual('_', key)
        self.assertEqual(['some_location'], bucket.roots)

        # more generic matching of different unmatched default fallbacks.
        self.assertEqual(
            mapping({'accept': 'text/html'}), mapping({'accept': '*/*'}))


class EndpointDefinitionMappingTestCase(unittest.TestCase):

    def test_missing_provider(self):
        # TODO validate exception message.
        with self.assertRaises(ValueError):
            EndpointDefinitionMapping({
                '/some/path/{id}': {
                    'key': 'some_value',
                    'target': 'some_other_value',
                }
            }, bucket_name='bucket_name')

    def test_missing_optional(self):
        mapping = EndpointDefinitionMapping({
            '/some/path/{id}': {
                '__provider__': 'some_provider',
                'key': 'some_value',
                'target': 'some_other_value',
            },
            '/some/path/{id}/details': {
                '__provider__': 'some_provider',
            },
        }, bucket_name='bucket_name')
        definition = mapping['/some/path/{id}']
        # for the mean time, this would be unspecified.
        self.assertIsNone(definition.root)
        self.assertEqual(definition.kwargs_mapping, {})
        self.assertEqual(definition.not_none, [])
        self.assertEqual(definition.route, '/some/path/{id}')
        self.assertEqual(
            '/some/path/{id}/details',
            mapping['/some/path/{id}/details'].route,
        )

    def test_basic_creation(self):
        mapping = EndpointDefinitionMapping({
            '/some/path/{id}': {
                '__provider__': 'some_provider',
                '__root__': 'some_root',
                '__notnone__': ['some_root'],
                '__kwargs__': {
                    'local_key', 'execution_key',
                },
                'key': 'some_value',
                'target': 'some_other_value',
            }
        }, bucket_name='bucket_name')
        definition = mapping['/some/path/{id}']
        # provide access to the raw keys
        provider = object()
        demo = AttrBaseMapping({'some_provider': provider})
        # actually test the provider as an attrgetter
        self.assertTrue(isinstance(definition.provider, attrgetter))
        self.assertIs(definition.provider(demo), provider)
        self.assertEqual(definition.root, 'some_root')
        self.assertEqual(definition.not_none, ['some_root'])
        self.assertEqual(definition.kwargs_mapping, {
            'local_key', 'execution_key',
        })
        self.assertEqual(definition.environment, {
            'key': 'some_value',
            'target': 'some_other_value',
        })
        self.assertEqual(definition.route, '/some/path/{id}')

    def test_usage_with_bucket_definition_mapping(self):
        bucket_mapping = BucketDefinitionMapping({
            '_': {
                '__roots__': ['default_root'],
                'accept': ['*/*'],
            },
        })
        mapping = EndpointDefinitionMapping({
            '/some/path/{id}': {
                '__provider__': 'some_provider',
                'key': 'some_value',
                'target': 'some_other_value',
            },
            '/some/path/{id}/details': {
                '__root__': 'some_other_root',
                '__provider__': 'some_provider',
            },
        }, bucket_name='_', bucket_mapping=bucket_mapping)

        # since the additional information is supplied
        self.assertEqual(
            mapping['/some/path/{id}'].root, 'default_root')
        self.assertEqual(
            mapping['/some/path/{id}/details'].root, 'some_other_root')


class BoundedEndpointDefinitionTestCase(unittest.TestCase):

    def test_build_fs_cache_path_simple(self):
        # create the required mappings
        default_root = TemporaryDirectory()
        self.addCleanup(default_root.cleanup)
        bucket_mapping = BucketDefinitionMapping({
            '_': {
                '__roots__': ['default_root'],
                'accept': ['*/*'],
            },
        })
        mapping = EndpointDefinitionMapping({
            '/some/path/{id}': {
                '__provider__': 'some_provider',
            },
        }, bucket_name='_', bucket_mapping=bucket_mapping)

        self.assertEqual(
            NotImplemented, mapping['/some/path/{id}'].build_cache_path({}))

        # manually bind one
        ed = BoundedEndpointDefinition(mapping['/some/path/{id}']).bind({
            'default_root': Path(default_root.name)
        })
        self.assertEqual(
            PurePath(default_root.name) / 'some' / 'path' / '3',
            ed.build_cache_path({'id': '3'}),
        )

    # Can't exactly test this when __root__ seems to be required
    #
    # def test_build_fs_cache_rootless(self):
    #     default_root = TemporaryDirectory()
    #     self.addCleanup(default_root.cleanup)
    #     bucket_mapping = BucketDefinitionMapping({
    #         '_': {
    #             '__roots__': ['default_root'],
    #             'accept': ['*/*'],
    #         },
    #     })
    #     mapping = EndpointDefinitionMapping({
    #         '/target/{id}': {
    #             '__provider__': 'some_provider',
    #             '__root__': None,
    #         },
    #     }, bucket_name='_', bucket_mapping=bucket_mapping)
    #     ed = BoundedEndpointDefinition(mapping['/target/{id}']).bind({
    #         'default_root': Path(default_root.name)
    #     })
    #     self.assertIsNone(ed.build_cache_path({'id': '42'}))

    def test_build_fs_cache_errors(self):
        default_root = TemporaryDirectory()
        self.addCleanup(default_root.cleanup)
        bucket_mapping = BucketDefinitionMapping({
            '_': {
                '__roots__': ['default_root'],
                'accept': ['*/*'],
            },
        })
        mapping = EndpointDefinitionMapping({
            '/path{/some_path*}': {
                '__provider__': 'some_provider',
            },
        }, bucket_name='_', bucket_mapping=bucket_mapping)

        # manually bind one
        ed = BoundedEndpointDefinition(mapping['/path{/some_path*}']).bind({
            'default_root': Path(default_root.name)
        })
        with self.assertRaises(ValueError):
            ed.build_cache_path({'some_path': ['some', 'where', '..', 'oops']})

    def test_end_as_directory_error(self):
        default_root = TemporaryDirectory()
        self.addCleanup(default_root.cleanup)
        bucket_mapping = BucketDefinitionMapping({
            '_': {
                '__roots__': ['default_root'],
                'accept': ['*/*'],
            },
        })
        mapping = EndpointDefinitionMapping({
            '/thing/{id}/broken/': {
                '__provider__': 'some_provider',
            },
            '/thing/{id}/lists/': {
                '__provider__': 'some_provider',
                '__filename__': 'index.html',
            },
            '/thing/{id}/lists/foo': {
                '__provider__': 'some_provider',
                '__filename__': 'index.html',
            },
        }, bucket_name='_', bucket_mapping=bucket_mapping)
        # /thing/1/broken/ should be a directory
        broken = BoundedEndpointDefinition(
            mapping['/thing/{id}/broken/']).bind({
                'default_root': Path(default_root.name)})
        self.assertIsNone(broken.build_cache_path({'id': '42'}))

        good = BoundedEndpointDefinition(
            mapping['/thing/{id}/lists/']).bind({
                'default_root': Path(default_root.name)})
        self.assertEqual(
            PurePath(default_root.name) / 'thing' / '42' / 'lists' /
            'index.html',
            good.build_cache_path({'id': '42'})
        )

        ignored = BoundedEndpointDefinition(
            mapping['/thing/{id}/lists/foo']).bind({
                'default_root': Path(default_root.name)})
        self.assertEqual(
            PurePath(default_root.name) / 'thing' / '42' / 'lists' / 'foo',
            ignored.build_cache_path({'id': '42'})
        )


class ReMappingDefinitionMappingTestCase(unittest.TestCase):

    def test_basic_creation(self):
        mapping = ReMappingDefinitionMapping({
            '/some/path/{id}': {
                'key': 'some_value',
                'target': 'some_other_value',
                'nested': {
                    'somekey': "with_nested_value"
                }
            }
        })
        definition = mapping['/some/path/{id}']
        self.assertEqual(definition.remap, {
            'key': 'some_value',
            'target': 'some_other_value',
            'nested': {
                'somekey': "with_nested_value"
            },
        })


def dump_trie(o):
    def dump(d):
        for k, v in d.items():
            if not isinstance(k, str):
                yield ('_node_', str(v))
            else:
                yield (k, sorted(dump(v)))
    return sorted(dump(o._RouteTrieMapping__trie))


class RouteTrieMappingTestCase(unittest.TestCase):

    def test_basic(self):
        rt_map = RouteTrieMapping()
        rt_map['/root/{foo}'] = 'root_foo'
        self.assertEqual([
            ('/root/{foo}', 'root_foo'),
        ], rt_map['/root/{foo}'])
        self.assertEqual(1, len(rt_map))

        rt_map['/root/{foo}/{bar}'] = 'root_foo_bar'
        self.assertEqual([
            ('/root/{foo}', 'root_foo'),
        ], rt_map['/root/{foo}'])
        self.assertEqual([
            ('/root/{foo}/{bar}', 'root_foo_bar'),
            ('/root/{foo}', 'root_foo'),
        ], rt_map['/root/{foo}/{bar}'])

        self.assertEqual(2, len(rt_map))

        self.assertEqual([
            '/root/{foo}', '/root/{foo}/{bar}'
        ], sorted(iter(rt_map)))

    def test_repr(self):
        rt_map = RouteTrieMapping()
        rt_map['/root/{foo}'] = 'root_foo'
        self.assertEqual(str(rt_map), str({'/root/{foo}': 'root_foo'}))

    def test_get(self):
        rt_map = RouteTrieMapping()
        rt_map['/root/{foo}'] = 'root_foo'
        rt_map['/root/{foo}/{bar}'] = 'root_foo_bar'
        original = dump_trie(rt_map)
        self.assertEqual([
            ('/root/{foo}/{bar}', 'root_foo_bar'),
            ('/root/{foo}', 'root_foo'),
        ], rt_map.get('/root/{foo}/{bar}/{baz}'))
        self.assertEqual(original, dump_trie(rt_map))

    def test_empty_str_key(self):
        rt_map = RouteTrieMapping()
        self.assertEqual(0, len(rt_map))

        rt_map['/root/{foo}'] = 'root_foo'
        self.assertEqual(1, len(rt_map))

        self.assertEqual([
            ('/root/{foo}', 'root_foo'),
        ], rt_map['/root/{foo}'])

        rt_map[''] = 'empty_str'
        self.assertEqual([
            ('/root/{foo}', 'root_foo'),
            ('', 'empty_str'),
        ], rt_map['/root/{foo}'])

        self.assertEqual([
            ('', 'empty_str'),
        ], rt_map[''])

        self.assertEqual(2, len(rt_map))

        self.assertNotIn('/root', rt_map)
        self.assertIn('/root/{foo}', rt_map)

    def test_single_char_str_key(self):
        rt_map = RouteTrieMapping()
        rt_map['/'] = 'root'
        rt_map['a'] = 'the_a_char'
        original = dump_trie(rt_map)

        self.assertEqual([
            ('/', 'root'),
        ], rt_map['/'])

        self.assertEqual([
            ('a', 'the_a_char'),
        ], rt_map['a'])

        self.assertEqual(original, dump_trie(rt_map))

        with self.assertRaises(KeyError):
            rt_map['////']

    def test_non_str_key(self):
        rt_map = RouteTrieMapping()
        with self.assertRaises(TypeError):
            rt_map[object()] = 1

    def test_not_found(self):
        rt_map = RouteTrieMapping()
        original = dump_trie(rt_map)
        with self.assertRaises(KeyError):
            rt_map['/root/{foo}']

        self.assertNotIn('/root', rt_map)

        # does not add a new node on access
        self.assertEqual(original, dump_trie(rt_map))

    def test_partial_not_found(self):
        rt_map = RouteTrieMapping()
        rt_map['/root/{foo}'] = 'root_foo'
        original = dump_trie(rt_map)

        with self.assertRaises(KeyError):
            rt_map['/root']

        # not modified
        self.assertEqual(original, dump_trie(rt_map))

    def test_del_route_single(self):
        rt_map = RouteTrieMapping()
        empty = dump_trie(rt_map)
        rt_map['/root/{foo}'] = 'root_foo'
        del rt_map['/root/{foo}']
        self.assertNotIn('/root/{foo}', rt_map)
        # restored to empty state
        self.assertEqual(empty, dump_trie(rt_map))

    def test_del_route_multiple_long(self):
        rt_map = RouteTrieMapping()
        rt_map['/'] = 'root'
        rt_map['/root/{foo}'] = 'root_foo'
        original = dump_trie(rt_map)
        rt_map['/root/{foo}/{bar}'] = 'root_foo_bar'
        self.assertEqual(3, len(rt_map['/root/{foo}/{bar}']))
        del rt_map['/root/{foo}/{bar}']
        self.assertNotIn('/root/{foo}/{bar}', rt_map)
        # restored to empty state
        self.assertEqual(original, dump_trie(rt_map))

        self.assertEqual([
            ('/root/{foo}', 'root_foo'),
            ('/', 'root'),
        ], rt_map['/root/{foo}'])

        with self.assertRaises(KeyError):
            rt_map['/root/{foo}/{bar}']

    def test_del_route_multiple_short(self):
        rt_map = RouteTrieMapping()
        rt_map['/root/{foo}/{bar}'] = 'root_foo_bar'
        rt_map['/root/{foo}'] = 'root_foo'
        original = dump_trie(rt_map)
        rt_map['/'] = 'root'
        self.assertEqual(1, len(rt_map['/']))
        del rt_map['/']
        self.assertNotIn('/', rt_map)
        # restored to original state
        self.assertEqual(original, dump_trie(rt_map))

        self.assertEqual([
            ('/root/{foo}/{bar}', 'root_foo_bar'),
            ('/root/{foo}', 'root_foo'),
        ], rt_map['/root/{foo}/{bar}'])

        with self.assertRaises(KeyError):
            rt_map['/']

    def test_del_route_common_remain(self):
        rt_map = RouteTrieMapping()
        rt_map['/root/{foo}/{bar}'] = 'root_foo_bar'
        original = dump_trie(rt_map)
        rt_map['/root/{foo}/{baz}'] = 'root_foo_baz'

        self.assertEqual(1, len(rt_map['/root/{foo}/{baz}']))
        del rt_map['/root/{foo}/{baz}']
        self.assertNotIn('/root/{foo}/{baz}', rt_map)
        # restored to original state
        self.assertEqual(original, dump_trie(rt_map))

    def test_del_route_short(self):
        rt_map = RouteTrieMapping()
        rt_map['/a'] = 'a'
        rt_map['/b'] = 'b'
        original = dump_trie(rt_map)
        rt_map['/c'] = 'c'

        self.assertEqual(1, len(rt_map['/c']))
        del rt_map['/c']
        self.assertNotIn('/c', rt_map)
        # restored to original state
        self.assertEqual(original, dump_trie(rt_map))

        del rt_map['/b']
        self.assertNotEqual(original, dump_trie(rt_map))

    def test_default_values(self):
        rt_map = RouteTrieMapping({
            '/e/{root}': [
                'a', 'b',
            ],
            '/e/{root}{/target*}': [
                'b', 'a',
            ],
            '/w/{root}': [
                'c', 'd',
            ],
        })
        self.assertEqual([
            ('/e/{root}{/target*}', ['b', 'a']),
            ('/e/{root}', ['a', 'b']),
        ], rt_map['/e/{root}{/target*}'])
        self.assertEqual([
            ('/w/{root}', ['c', 'd']),
        ], rt_map['/w/{root}'])

    def test_resource_map_conversion(self):
        # Ensure that the resource definition mapping, a class designed
        # to be compatible with the deserializer, be convertable to the
        # specific and specialized mapping class that can be used in the
        # context of routing.

        # While this _can_ be done as a unified class, there are two
        # separate concerns here so it would be best to keep both of
        # these as two distinct classes, with the form that is generated
        # from a direct loading into one that is internal usage.

        mapping = ResourceDefinitionMapping({
            '/browse/{id}': [{
                '__name__': 'name1',
                '__call__': 'a_function',
                'arg1': 'reference1',
            }, {
                '__name__': 'name2',
                '__init__': 'repodono.model.testing:Thing',
                'path': 'a_path',  # references a_path
            }, {
                '__name__': 'name3',
                '__init__': 'repodono.model.testing:Thing',
                'path': 'name1',  # references name1, defined here
            }],
            '/browse/{id}/{mode}': [{
                '__name__': 'use_id',
                '__init__': 'repodono.model.testing:Thing',
                'path': 'id',  # references a_path
            }, {
                '__name__': 'use_mode',
                '__init__': 'repodono.model.testing:Thing',
                'path': 'mode',  # references name1, defined here
            }],
        })

        rt_map = RouteTrieMapping(mapping)

        level2 = rt_map['/browse/{id}/{mode}']
        level1 = rt_map['/browse/{id}']
        self.assertEqual(2, len(level2))
        self.assertEqual(1, len(level1))

        # the idea is that there will need to be another layer, probably
        # subclassed from FlatGroupedMapping, that take the returned
        # list of mappings and formalize that as a group that can be
        # retrived.  Then another layer on top of that that combines
        # with a mapping formed from the incoming values extracted from
        # a url with this one that will have something similar to the
        # ObjectInstantiationMapping where it will instead use itself
        # to provide the mapping of values, and its __getitem__ will
        # instantiate the target ResourceDefinition entry.  Somehow this
        # result should also be cached somewhere, perhaps in a thread
        # local store.


class CompiledRRDTestCase(unittest.TestCase):

    def test_resource_map_conversion(self):
        rd_map = ResourceDefinitionMapping({
            '/browse/{id}': [{
                '__name__': 'name1',
                '__call__': 'a_function',
                'arg1': 'reference1',
            }, {
                '__name__': 'name2',
                '__init__': 'repodono.model.testing:Thing',
                'path': 'a_path',  # references a_path
            }, {
                '__name__': 'name3',
                '__init__': 'repodono.model.testing:Thing',
                'path': 'name1',  # references name1, defined here
            }],
            '/browse/{id}/{mode}': [{
                '__name__': 'use_id',
                '__init__': 'repodono.model.testing:Thing',
                'path': 'id',  # references a_path
            }, {
                '__name__': 'use_mode',
                '__init__': 'repodono.model.testing:Thing',
                'path': 'mode',  # references name1, defined here
            }],
        })
        rt_map = RouteTrieMapping(rd_map)
        crrd_map = CompiledRouteResourceDefinitionMapping(rt_map)

        self.assertEqual(2, len(crrd_map))
        self.assertEqual(3, len(crrd_map['/browse/{id}']))
        self.assertEqual(5, len(crrd_map['/browse/{id}/{mode}']))

        browse_id = crrd_map['/browse/{id}']
        browse_id_mode = crrd_map['/browse/{id}/{mode}']
        self.assertIs(browse_id['name1'], browse_id_mode['name1'])
        self.assertEqual(browse_id['name1'].kwargs, {
            'arg1': 'reference1',
        })
        self.assertEqual(browse_id_mode['use_id'].kwargs, {
            'path': 'id',
        })


class ExecutionLocalsTestCase(unittest.TestCase):

    def test_access_by_attribute(self):
        exe_locals = ExecutionLocals([
            {
                'key': 'some_key',
                'method': 'a_method',
            },
            {
                'another_key': 'some other value',
                'elsewhere': None,
            }
        ])

        self.assertEqual(exe_locals.key, 'some_key')

        with self.assertRaises(AttributeError) as e:
            exe_locals.does_not_exist

        self.assertEqual(
            "'ExecutionLocals' object has no attribute 'does_not_exist'",
            e.exception.args[0])

    def test_access_private_rejected(self):
        exe_locals = ExecutionLocals([{
            '_private': 1,
        }])

        with self.assertRaises(AttributeError) as e:
            exe_locals._private

        self.assertEqual(
            "'ExecutionLocals' object has no attribute '_private'",
            e.exception.args[0])

    def test_assignment_private_accepted(self):
        exe_locals = ExecutionLocals([])

        with self.assertRaises(AttributeError):
            exe_locals._private

        exe_locals._private = 1
        self.assertEqual(exe_locals._private, 1)

    def test_assignment_public_rejected(self):
        exe_locals = ExecutionLocals([])
        with self.assertRaises(TypeError) as e:
            exe_locals.a = 1

        self.assertEqual(
            "can't set attributes of 'ExecutionLocals' objects",
            e.exception.args[0])

    def test_execution_environment_usage(self):
        rd_map = ResourceDefinitionMapping({
            '/browse/{id}': [{
                '__name__': 'name1',
                '__call__': 'a_function',
                'arg1': 'reference1',
            }, {
                '__name__': 'name2',
                '__init__': 'repodono.model.testing:Thing',
                'path': 'a_path',  # references a_path
            }, {
                '__name__': 'name3',
                '__init__': 'repodono.model.testing:Thing',
                'path': 'name1',  # references name1, defined here
            }],
            '/browse/{id}/{mode}': [{
                '__name__': 'use_id',
                '__init__': 'repodono.model.testing:Thing',
                'path': 'id',  # references a_path
            }, {
                '__name__': 'use_mode',
                '__init__': 'repodono.model.testing:Thing',
                'path': 'mode',  # references name1, defined here
            }],
        })
        rt_map = RouteTrieMapping(rd_map)
        crrd_map = CompiledRouteResourceDefinitionMapping(rt_map)

        # /browse/the_id/the_mode
        exec_locals = ExecutionLocals([
            crrd_map['/browse/{id}/{mode}'],
            {
                'id': 'the_id',
                'mode': 'the_mode',
            },
        ])
        self.assertEqual(exec_locals['use_mode'].path, 'the_mode')


# Test cases for the Execution class is found in test_config
