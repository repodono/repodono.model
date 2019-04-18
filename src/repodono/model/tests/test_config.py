import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from repodono.model.config import Configuration


class ConfigEnvironmentTestCase(unittest.TestCase):

    def test_base_environment_variables(self):
        config = Configuration.from_toml("""
        [environment.variables]
        foo = "bar"
        """)
        self.assertEqual(config.environment['foo'], 'bar')

    def test_paths(self):
        root = TemporaryDirectory()
        self.addCleanup(root.cleanup)
        config = Configuration.from_toml("""
        [environment.variables]
        foo = "bar"
        [environment.paths]
        base_root = %r
        """ % (root.name,))
        self.assertEqual(config.environment['foo'], 'bar')
        self.assertTrue(isinstance(config.environment['base_root'], Path))

    def test_objects(self):
        root = TemporaryDirectory()
        self.addCleanup(root.cleanup)
        config = Configuration.from_toml("""
        [environment.variables]
        foo = "bar"
        [environment.paths]
        base_root = %r
        [[environment.objects]]
        __name__ = "thing"
        __init__ = "repodono.model.testing:Thing"
        path = "base_root"
        """ % (root.name,))
        self.assertTrue(isinstance(config.environment['thing'].path, Path))

    def test_list_items_resolved(self):
        root = TemporaryDirectory()
        self.addCleanup(root.cleanup)
        config = Configuration.from_toml("""
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
        env = config.environment
        self.assertEqual(
            [env['text'], env['number'], env['base_root']],
            env['thing'].path,
        )

    def test_list_nested_list_resolved(self):
        root = TemporaryDirectory()
        self.addCleanup(root.cleanup)
        config = Configuration.from_toml("""
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
        env = config.environment
        self.assertEqual([
            ['hello', 'goodbye'],
            [0],
            [env['base_root']],
        ], env['thing'].path)

    def test_dict_items_resolved(self):
        root = TemporaryDirectory()
        self.addCleanup(root.cleanup)
        config = Configuration.from_toml("""
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
        env = config.environment
        self.assertEqual({
            'path': env['base_root'],
            'number': 0,
            'texts': ['hello', 'hello'],
        }, env['thing'].path)


class ConfigResourceTestCase(unittest.TestCase):

    def test_basic_resource(self):
        root = TemporaryDirectory()
        self.addCleanup(root.cleanup)
        config = Configuration.from_toml("""
        [environment.paths]
        root_path = %r
        [[resource."/entry/{entry_id}"]]
        __name__ = "blog_entry"
        __init__ = "repodono.model.testing:Thing"
        path = "root_path"
        """ % (root.name,))
        self.assertEqual(1, len(config.resource['/entry/{entry_id}']))
        self.assertIn('blog_entry', config.compiled_route_resources[
            '/entry/{entry_id}'])


class ConfigEndpointTestCase(unittest.TestCase):

    def test_basic_resource(self):
        config = Configuration.from_toml("""
        [endpoint._."/entry/{entry_id}"]
        __handler__ = "blog_entry"
        item = 2
        target = "html"

        [endpoint."json"."/entry/{entry_id}"]
        __handler__ = "blog_entry"
        item = 2
        target = "json"
        """)
        self.assertIn('_', config.endpoint)
        self.assertEqual({
            "item": 2,
            "target": "html",
        }, config.endpoint['_']['/entry/{entry_id}'].environment)
        self.assertEqual({
            "item": 2,
            "target": "json",
        }, config.endpoint['json']['/entry/{entry_id}'].environment)


class ConfigIntegrationTestCase(unittest.TestCase):

    def test_base(self):
        config_str = """
        [environment.variables]
        foo = 'bar'
        """

        config = Configuration.from_toml(config_str)
        self.assertEqual(config['environment']['variables']['foo'], 'bar')

    def test_compiled_details(self):
        root = TemporaryDirectory()
        self.addCleanup(root.cleanup)
        config = Configuration.from_toml("""
        [environment.variables]
        foo = "bar"

        [environment.paths]
        base_root = %r

        [[environment.objects]]
        __name__ = "thing"
        __init__ = "repodono.model.testing:Thing"
        path = "base_root"

        [[resource."/entry/{entry_id}"]]
        __name__ = "env_poker"
        __init__ = "repodono.model.testing:Thing"
        path = "thing"

        [[resource."/entry/{entry_id}"]]
        __name__ = "entry_viewer"
        __init__ = "repodono.model.testing:Thing"
        path = "entry_id"

        [endpoint._."/entry/{entry_id}"]
        __handler__ = "blog_entry"
        details = false

        [endpoint._."/entry/{entry_id}/details"]
        __handler__ = "blog_entry_details"
        details = true
        """ % (root.name,))

        top_locals = config.execution_locals_from_route_mapping(
            '/entry/{entry_id}', {'entry_id': '123'})
        self.assertEqual(top_locals['entry_viewer'].path, '123')
        self.assertEqual(
            # first path reference the "thing" environment.object
            # second path reference the "base_root" in environment.paths
            str(top_locals['env_poker'].path.path),
            # the TemporaryDirectory.name
            root.name
        )
        self.assertFalse(top_locals['details'])

        details_locals = config.execution_locals_from_route_mapping(
            '/entry/{entry_id}/details', {'entry_id': '123'})
        self.assertEqual(details_locals['entry_viewer'].path, '123')
        self.assertEqual(
            # first path reference the "thing" environment.object
            # second path reference the "base_root" in environment.paths
            str(details_locals['env_poker'].path.path),
            # the TemporaryDirectory.name
            root.name
        )
        self.assertTrue(details_locals['details'])
