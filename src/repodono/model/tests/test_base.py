import unittest
from ast import literal_eval

from repodono.model.base import BaseMapping
from repodono.model.base import FlatGroupedMapping


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

        del mapping['custom']
        self.assertNotIn('custom', mapping)
