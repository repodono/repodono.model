import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from repodono.model.config import Configuration
from repodono.model.environment import Environment
from repodono.model.environment import Resource

"""
[environment.variables]  # strings??
# fs_root is a reference to some filesystem location that may be
# served, perhaps separating these things out to own section?
exposure_root = "https://example.com/e"

[environment.paths]
git_checkout_root = "/tmp/data/pmrdemo"
generated_root = "/tmp/data/pmrdata"
"""


class EnvironmentTestCase(unittest.TestCase):

    def test_base_environment_variables(self):
        config = Configuration("""
        [environment.variables]
        foo = "bar"
        """)
        base_environment = Environment(config)
        self.assertEqual(base_environment['foo'], 'bar')

    def test_paths(self):
        root = TemporaryDirectory()
        self.addCleanup(root.cleanup)
        config = Configuration("""
        [environment.variables]
        foo = "bar"
        [environment.paths]
        base_root = %r
        """ % (root.name,))
        base_environment = Environment(config)
        self.assertEqual(base_environment['foo'], 'bar')
        self.assertTrue(isinstance(base_environment['base_root'], Path))

    def test_objects(self):
        root = TemporaryDirectory()
        self.addCleanup(root.cleanup)
        config = Configuration("""
        [environment.variables]
        foo = "bar"
        [environment.paths]
        base_root = %r
        [[environment.objects]]
        __name__ = "thing"
        __init__ = "repodono.model.testing:Thing"
        path = "base_root"
        """ % (root.name,))
        base_environment = Environment(config)
        self.assertTrue(isinstance(base_environment['thing'].path, Path))

    def test_list_items_resolved(self):
        root = TemporaryDirectory()
        self.addCleanup(root.cleanup)
        config = Configuration("""
        [environment.variables]
        text = "hello"
        number = 0
        [environment.paths]
        base_root = %r
        [[environment.objects]]
        __name__ = "thing"
        __init__ = "repodono.model.testing:Thing"
        path = ["text", "number", "base_root"]
        """ % (root.name,))
        env = Environment(config)
        self.assertEqual(
            [env['text'], env['number'], env['base_root']],
            env['thing'].path,
        )

    def test_list_nested_list_resolved(self):
        root = TemporaryDirectory()
        self.addCleanup(root.cleanup)
        config = Configuration("""
        [environment.variables]
        greeting = "hello"
        farewell = "goodbye"
        number = 0
        [environment.paths]
        base_root = %r
        [[environment.objects]]
        __name__ = "thing"
        __init__ = "repodono.model.testing:Thing"
        path = [ ["greeting", "farewell"], ["number",], ["base_root",],]
        """ % (root.name,))
        env = Environment(config)
        self.assertEqual([
            ['hello', 'goodbye'],
            [0],
            [env['base_root']],
        ], env['thing'].path)

    def test_dict_items_resolved(self):
        root = TemporaryDirectory()
        self.addCleanup(root.cleanup)
        config = Configuration("""
        [environment.variables]
        text = "hello"
        number = 0
        [environment.paths]
        base_root = %r
        [[environment.objects]]
        __name__ = "thing"
        __init__ = "repodono.model.testing:Thing"
        [environment.objects.path]
        path = "base_root"
        number = "number"
        texts = ["text", "text"]
        """ % (root.name,))
        env = Environment(config)
        self.assertEqual({
            'path': env['base_root'],
            'number': 0,
            'texts': ['hello', 'hello'],
        }, env['thing'].path)


class ResourceTestCase(unittest.TestCase):

    def test_basic_resource(self):
        root = TemporaryDirectory()
        self.addCleanup(root.cleanup)
        config = Configuration("""
        [environment.paths]
        root_path = %r
        [[resource."/entry/{entry_id}"]]
        __name__ = "blog_entry"
        __init__ = "repodono.model.testing:Thing"
        path = "root_path"
        """ % (root.name,))
        resource = Resource(config)
        self.assertIn('blog_entry', resource['/entry/{entry_id}'])
