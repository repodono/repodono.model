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


class ConfigBucketTestCase(unittest.TestCase):

    def test_basic_roots(self):
        # note that the current setup captures everything.
        config = Configuration.from_toml("""
        [bucket._]
        __roots__ = ["default_root", "generated_root"]
        accept = ["*/*"]

        [bucket.json]
        __roots__ = ["json_root"]
        accept = ["application/json", "text/json"]

        [bucket.xml]
        __roots__ = ["xml_root"]
        accept = ["application/xml", "text/xml"]
        """)

        self.assertEqual([
            'default_root', 'generated_root'], config.bucket['_'].roots)
        self.assertEqual({'accept': ['*/*']}, config.bucket['_'].environment)
        self.assertEqual(['json_root'], config.bucket['json'].roots)
        self.assertEqual({
            'accept': ['application/json', 'text/json']
        }, config.bucket['json'].environment)
        self.assertEqual(['xml_root'], config.bucket['xml'].roots)
        self.assertEqual({
            'accept': ['application/xml', 'text/xml']
        }, config.bucket['xml'].environment)


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

        [bucket._]
        __roots__ = ["default_root", "generated_root"]
        accept = ["*/*"]

        [bucket.json]
        __roots__ = ["json_root"]
        accept = ["application/json", "text/json"]

        [bucket.xml]
        __roots__ = ["xml_root"]
        accept = ["application/xml", "text/xml"]

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
        format = "default"

        [endpoint.json."/entry/{entry_id}/details"]
        __handler__ = "blog_entry_details"
        details = true
        format = "simple"

        [endpoint.xml."/entry/{entry_id}/details"]
        __handler__ = "blog_entry_details"
        details = true
        format = "verbose"
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
        self.assertEqual(details_locals['format'], 'default')

        details_locals = config.execution_locals_from_route_mapping(
            '/entry/{entry_id}/details', {'entry_id': '123'}, {
                'accept': 'application/json',
            })
        self.assertEqual(details_locals['entry_viewer'].path, '123')
        self.assertEqual(details_locals['format'], 'simple')

        details_locals = config.execution_locals_from_route_mapping(
            '/entry/{entry_id}/details', {'entry_id': '123'}, {
                'accept': 'application/xml',
            })
        self.assertEqual(details_locals['entry_viewer'].path, '123')
        self.assertEqual(details_locals['format'], 'verbose')

        with self.assertRaises(KeyError):
            config.execution_locals_from_route_mapping(
                '/entry/{entry_id}/debug', {'entry_id': '123'})

    def test_no_default_bucket(self):
        root = TemporaryDirectory()
        self.addCleanup(root.cleanup)
        config = Configuration.from_toml("""
        [environment.variables]
        foo = "bar"

        [bucket.json]
        __roots__ = ["json_root"]
        accept = ["application/json", "text/json"]

        [bucket.xml]
        __roots__ = ["xml_root"]
        accept = ["application/xml", "text/xml"]

        [environment.paths]
        base_root = %r

        [endpoint.json."/entry/{entry_id}/details"]
        __handler__ = "blog_entry_details"
        details = true
        format = "simple"

        [endpoint.xml."/entry/{entry_id}/details"]
        __handler__ = "blog_entry_details"
        details = true
        format = "verbose"

        [endpoint.xml."/entry/{entry_id}/debug"]
        __handler__ = "blog_entry_details"
        debug = true
        """ % (root.name,))

        details_locals = config.execution_locals_from_route_mapping(
            '/entry/{entry_id}/details', {'entry_id': '123'}, {
                'accept': 'application/json',
            })
        self.assertEqual(details_locals['format'], 'simple')

        with self.assertRaises(KeyError):
            # simple KeyError check for now, we will likely need a more
            # explicit type for this.
            config.execution_locals_from_route_mapping(
                '/entry/{entry_id}/details', {'entry_id': '123'}, {
                    'accept': 'text/plain',
                })

        with self.assertRaises(KeyError):
            config.execution_locals_from_route_mapping(
                '/entry/{entry_id}/debug', {'entry_id': '123'}, {
                    'accept': 'application/json',
                })
