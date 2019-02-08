import unittest
from ast import literal_eval

from repodono.model.base import (
    BaseMapping,
    FlatGroupedMapping,
    ObjectInstantiationMapping,
    structured_mapper,
    StructuredMapping,
)


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
                self._vars = NotImplemented

        class WithVars(BaseMapping):
            def __init__(self, *a, _vars=None, **kw):
                self._vars = _vars

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
        mappings = structured_mapper(definition, raw_mapping, _vars=vars_)
        self.assertEqual(2, len(mappings))
        self.assertTrue(isinstance(mappings[0], WithoutVars))
        self.assertTrue(isinstance(mappings[1], WithVars))
        self.assertIs(mappings[1]._vars, vars_)


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

    def test_stability(self):
        value = [{
            '__name__': 'thing',
            '__init__': 'repodono.model.testing:Thing',
            'path': 'a_path',
        }]
        marker = object()
        vars_ = {'a_path': marker}
        result = ObjectInstantiationMapping(value, vars_)
        self.assertEqual({'a_path': marker}, vars_)
        self.assertEqual([{
            '__name__': 'thing',
            '__init__': 'repodono.model.testing:Thing',
            'path': 'a_path',
        }], value)
        self.assertEqual(result['thing'].path, marker)
