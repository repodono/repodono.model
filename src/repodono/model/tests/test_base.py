import unittest
from ast import literal_eval

from repodono.model.base import (
    BaseMapping,
    BasePreparedMapping,
    PreparedMapping,
    DeferredPreparedMapping,
    FlatGroupedMapping,
    ObjectInstantiationMapping,
    ResourceDefinitionMapping,
    RouteTrieMapping,
    structured_mapper,
    StructuredMapping,
)
from repodono.model.testing import Thing


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
            def prepare_from_value(cls, value):
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

    def test_creation_basic(self):
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
        self.assertEqual(3, len(mapping))
        self.assertEqual(mapping['key1'], 'child1.1')
        self.assertEqual(mapping['key2'], 'child1.2')
        self.assertEqual(mapping['key3'], 'child2.3')


class ObjectInstantiationMappingTestCase(unittest.TestCase):

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
        vars_ = {
            'a_function': Thing(None),
            'reference1': marker1,
        }
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
        vars_ = {
            'a_function': Thing(None),
            'reference1': marker1,
        }
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
