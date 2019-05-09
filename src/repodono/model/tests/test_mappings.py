import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from repodono.model import mappings
from repodono.model.testing import Thing


class MappingsTestCase(unittest.TestCase):
    """
    A rough test since the underlying implementation should have been
    more thoroughly tested via the tests for the base classes.

    Effectively, this kind of shows what the process might look like
    when creating from raw python objects (or decoded JSON as they are
    similar).
    """

    def test_environment(self):
        root = TemporaryDirectory()
        self.addCleanup(root.cleanup)
        environment = mappings.Environment({
            'environment': {
                'variables': {
                    'foo': 'bar',
                    'bar': 'baz',
                },
                'paths': {
                    'some_root': root.name,
                },
                'objects': [{
                    '__name__': "thing",
                    '__init__': "repodono.model.testing:Thing",
                    'path': "some_root",
                }],
            }
        })

        self.assertEqual(environment['foo'], 'bar')
        self.assertEqual(environment['some_root'], Path(root.name))
        self.assertEqual(environment['thing'].path, Path(root.name))
        self.assertTrue(isinstance(environment['thing'], Thing))

    def test_resource(self):
        resource = mappings.Resource({
            'resource': {
                "/entry/{entry_id}": [{
                    '__name__': 'thing1',
                    '__init__': "repodono.model.testing:Thing",
                    'path': 'some_other_value',
                }, {
                    '__name__': 'thing2',
                    '__init__': "repodono.model.testing:Thing",
                    'path': 'some_target',
                }],
            },
        })

        self.assertEqual(2, len(resource['/entry/{entry_id}']))

    def test_endpoint(self):
        endpoint = mappings.Endpoint({
            'endpoint': {
                '_': {
                    "/entry/{entry_id}": {
                        '__provider__': 'thing1',
                        'path': 'some_other_value',
                    },
                },
            },
        })

        self.assertEqual({
            'path': 'some_other_value',
        }, endpoint['_']['/entry/{entry_id}'].environment)
