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

    def test_basic_endpoint_environment(self):
        config = Configuration.from_toml("""
        [endpoint._."/entry/{entry_id}"]
        __provider__ = "blog_entry"
        item = 2
        target = "html"

        [endpoint."json"."/entry/{entry_id}"]
        __provider__ = "blog_entry"
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

    def test_basic_endpoints_lists(self):
        config = Configuration.from_toml("""
        [endpoint._."/entry/{entry_id}"]
        __provider__ = "blog_entry"
        item = 2
        target = "html"

        [endpoint."json"."/entry/{entry_id}/debug"]
        __provider__ = "blog_entry"
        item = 2
        target = "json"
        """)
        self.assertEqual([
            '/entry/{entry_id}',
            '/entry/{entry_id}/debug',
        ], config.endpoint_keys)

        # TODO need to test cases when more sanity checking, such as the
        # checking of routes that cannot be resolved because it collides
        # with a similar route (e.g. two routes with same prefix/id).


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

        [[environment.objects]]
        __name__ = "mock_object"
        __init__ = "unittest.mock:Mock"

        [endpoint._."/mock_object"]
        __provider__ = "mock_object.some_attribute"

        [[resource."/mock_resource"]]
        __name__ = "mock_resource_attr"
        __call__ = "mock_object.mock_resource_attr"
        path = "id"

        [endpoint._."/mock_resource/{id}"]
        __provider__ = "mock_resource_attr"

        [[resource."/"]]
        __name__ = "blog_entry_details"
        __init__ = "repodono.model.testing:Thing"
        path = "format"

        [[resource."/entry/{entry_id}"]]
        __name__ = "env_poker"
        __init__ = "repodono.model.testing:Thing"
        path = "thing"

        [[resource."/entry/{entry_id}"]]
        __name__ = "entry_viewer"
        __init__ = "repodono.model.testing:Thing"
        path = "entry_id"

        [endpoint._."/entry/{entry_id}"]
        __provider__ = "blog_entry"
        details = false

        [endpoint._."/entry/{entry_id}/details"]
        __provider__ = "blog_entry_details"
        details = true
        format = "default"

        [endpoint.json."/entry/{entry_id}/details"]
        __provider__ = "blog_entry_details"
        details = true
        format = "simple"

        [endpoint.xml."/entry/{entry_id}/details"]
        __provider__ = "blog_entry_details"
        details = true
        format = "verbose"
        """ % (root.name,))

        top = config.request_execution(
            '/entry/{entry_id}', {'entry_id': '123'})
        self.assertEqual(top.locals['entry_viewer'].path, '123')
        self.assertEqual(
            # first path reference the "thing" environment.object
            # second path reference the "base_root" in environment.paths
            str(top.locals['env_poker'].path.path),
            # the TemporaryDirectory.name
            root.name
        )
        self.assertFalse(top.locals['details'])

        details = config.request_execution(
            '/entry/{entry_id}/details', {'entry_id': '123'})
        self.assertEqual(details.locals['entry_viewer'].path, '123')
        self.assertEqual(
            # first path reference the "thing" environment.object
            # second path reference the "base_root" in environment.paths
            str(details.locals['env_poker'].path.path),
            # the TemporaryDirectory.name
            root.name
        )
        self.assertTrue(details.locals['details'])
        self.assertEqual(details.locals['format'], 'default')
        # testing the simple invocation.
        self.assertEqual(details().path, 'default')

        json_details = config.request_execution(
            '/entry/{entry_id}/details', {'entry_id': '123'}, {
                'accept': 'application/json',
            })
        self.assertEqual(json_details.locals['entry_viewer'].path, '123')
        self.assertEqual(json_details.locals['format'], 'simple')
        self.assertEqual(json_details().path, 'simple')

        xml_details = config.request_execution(
            '/entry/{entry_id}/details', {'entry_id': '123'}, {
                'accept': 'application/xml',
            })
        self.assertEqual(xml_details.locals['entry_viewer'].path, '123')
        self.assertEqual(xml_details.locals['format'], 'verbose')
        self.assertEqual(xml_details().path, 'verbose')

        with self.assertRaises(KeyError):
            config.request_execution(
                '/entry/{entry_id}/debug', {'entry_id': '123'})

        # get the mock object, which the relevant endpoint.provider is
        # defined to access an attribute of this object.
        mock = config.environment['mock_object']
        mockobj_exe = config.request_execution('/mock_object', {})
        some_attribute = mockobj_exe()
        # Verify that we have the same object.
        self.assertIs(some_attribute, mock.some_attribute)
        # Being an object, specifying that as a provider will simply
        # access the predefined environment object and return it
        self.assertFalse(mock.some_attribute.called)

        # For the second case, ensure
        # defined to access an attribute of this object.
        self.assertFalse(mock.mock_resource_attr.called)
        mockres_exe = config.request_execution('/mock_resource/{id}', {
            'id': '321',
        })
        result = mockres_exe()
        self.assertTrue(mock.mock_resource_attr.called)
        mock.mock_resource_attr.assert_called_with(path='321')
        self.assertIs(result, mockres_exe.locals['mock_resource_attr'])

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
        __provider__ = "blog_entry_details"
        details = true
        format = "simple"

        [endpoint.xml."/entry/{entry_id}/details"]
        __provider__ = "blog_entry_details"
        details = true
        format = "verbose"

        [endpoint.xml."/entry/{entry_id}/debug"]
        __provider__ = "blog_entry_details"
        debug = true
        """ % (root.name,))

        details = config.request_execution(
            '/entry/{entry_id}/details', {'entry_id': '123'}, {
                'accept': 'application/json',
            })
        self.assertEqual(details.locals['format'], 'simple')

        with self.assertRaises(KeyError):
            # simple KeyError check for now, we will likely need a more
            # explicit type for this.
            config.request_execution(
                '/entry/{entry_id}/details', {'entry_id': '123'}, {
                    'accept': 'text/plain',
                })

        with self.assertRaises(KeyError):
            config.request_execution(
                '/entry/{entry_id}/debug', {'entry_id': '123'}, {
                    'accept': 'application/json',
                })

    def test_endpoint_kwargs_indirection(self):
        config = Configuration.from_toml("""
        [environment.variables]
        thing = "env"

        [bucket._]
        __roots__ = ['somewhere']
        accept = ["*/*"]

        # A common shared mock object
        [[resource."/"]]
        __name__ = "a_mock"
        __init__ = "unittest.mock:Mock"

        [endpoint._."/entry/{entry_id}/{action}"]
        # the template is fixed, but to test this thing out the kwargs
        # can be remapped using the __kwargs__ key
        __provider__ = "a_mock"
        __kwargs__.mock_id = "entry_id"
        __kwargs__.mock_method = "action"
        __kwargs__.mock_thing = "thing"
        """)

        exe = config.request_execution('/entry/{entry_id}/{action}', {
            'entry_id': '123',
            'action': 'blah',
        })
        self.assertEqual(exe.locals['a_mock'].mock_id, '123')
        self.assertEqual(exe.locals['a_mock'].mock_method, 'blah')
        self.assertEqual(exe.locals['a_mock'].mock_thing, 'env')

    def test_endpoint_kwargs_shadowing(self):
        config = Configuration.from_toml("""
        [environment.variables]
        thing = "thing"

        [bucket._]
        __roots__ = ['somewhere']
        accept = ["*/*"]

        # A common shared mock object
        [[resource."/"]]
        __name__ = "a_mock"
        __init__ = "unittest.mock:Mock"
        mock_id = "thing"
        mock_method = "thing"

        [endpoint._."/entry/{entry_id}/{action}"]
        __provider__ = "a_mock"
        __kwargs__.mock_id = "entry_id"
        """)

        exe = config.request_execution('/entry/{entry_id}/{action}', {
            'entry_id': '123',
            'action': 'blah',
        })
        self.assertEqual(exe.locals['a_mock'].mock_id, '123')
        self.assertEqual(exe.locals['a_mock'].mock_method, 'thing')

    def test_endpoint_kwargs_missing(self):
        config = Configuration.from_toml("""
        [bucket._]
        __roots__ = ['somewhere']
        accept = ["*/*"]

        # A common shared mock object
        [[resource."/"]]
        __name__ = "a_mock"
        __init__ = "unittest.mock:Mock"

        [endpoint._."/entry/"]
        # the template is fixed, but to test this thing out the kwargs
        # can be remapped using the __kwargs__ key
        __provider__ = "a_mock"
        __kwargs__.mock_id = "no_such_thing"
        """)

        exe = config.request_execution('/entry/', {})
        with self.assertRaises(KeyError) as e:
            exe.locals['a_mock']
        self.assertEqual(e.exception.args[0], 'no_such_thing')

    def test_resource_missing_kwargs_provided_endpoint(self):
        # Test out the resource definition that did not define a
        # required argument with a reference, but then the provider has
        # provided one.

        config = Configuration.from_toml("""
        [environment.variables]
        some_name = "the value"

        [bucket._]
        __roots__ = ['somewhere']
        accept = ["*/*"]

        # A common shared mock object
        [[resource."/"]]
        __name__ = "thing"
        __init__ = "repodono.model.testing:Thing"

        [endpoint._."/entry/"]
        # the template is fixed, but to test this thing out the kwargs
        # can be remapped using the __kwargs__ key
        __provider__ = "thing"
        __kwargs__.path = "some_name"

        [endpoint._."/entry/view"]
        # the provider is simply the value, but for this test the locals
        # will be requested from here but will test deferencing the
        # above.
        __provider__ = "some_name"
        """)

        exe = config.request_execution('/entry/', {})
        self.assertEqual(exe.locals['thing'].path, 'the value')
        # this would have simply access the value like above also
        self.assertEqual(exe().path, 'the value')

        # this other view did not directly inititate or provide a value
        other_exe = config.request_execution('/entry/view', {})
        with self.assertRaises(TypeError):
            other_exe.locals['thing']

    def test_resource_referenced_kwargs_to_be_provided(self):
        # Test out the resource definition that specified a required
        # keyword argument with a reference, but then that reference is
        # to be defined later.

        config = Configuration.from_toml("""
        [environment.variables]
        some_name = "the value"

        [bucket._]
        __roots__ = ['somewhere']
        accept = ["*/*"]

        # A common shared mock object
        [[resource."/"]]
        __name__ = "thing"
        __init__ = "repodono.model.testing:Thing"
        path = "some_reference"

        [endpoint._."/entry/"]
        # the template is fixed, but to test this thing out the kwargs
        # can be remapped using the __kwargs__ key
        __provider__ = "thing"
        __kwargs__.path = "some_name"

        [endpoint._."/entry/other"]
        # this endpoint will also make use of thing, but it defines a
        # static reference as a endpoint environment value
        __provider__ = "thing"
        some_reference = "static_value"

        [endpoint._."/entry/both"]
        # this endpoint has the required reference provided, but will
        # have a specific kwargs specified
        __provider__ = "thing"
        __kwargs__.path = "some_name"
        some_reference = "static_value"
        """)

        # check the other thing first, show that this typical creation
        # is not impeded.
        other_exe = config.request_execution('/entry/other', {})
        self.assertEqual(other_exe.locals['thing'].path, 'static_value')

        # now for the main test, show that the path in kwargs will make
        # a reference to some_name, and where some_name is from the root
        # environment; note that 'some_reference' is not defined in this
        # set of execution locals.
        exe = config.request_execution('/entry/', {})
        self.assertEqual(exe().path, 'the value')

        both_exe = config.request_execution('/entry/both', {})
        # the one provided by kwargs will take precedence.
        self.assertEqual(both_exe().path, 'the value')

    def test_localmap(self):
        # Test out the resource definition that specified a required
        # keyword argument with a reference, but then that reference is
        # to be defined later.

        config = Configuration.from_toml("""
        [environment.variables]
        some_name = "the value"

        [bucket._]
        __roots__ = ['somewhere']
        accept = ["*/*"]

        # A common shared mock object
        [[resource."/"]]
        __name__ = "a_mock"
        __init__ = "unittest.mock:Mock"

        [localmap."/entry/"]
        key = "some_name"
        some_map.key1 = "some_name"
        some_map.key2 = "some_name"

        [endpoint._."/entry/"]
        __provider__ = "a_mock"
        __kwargs__.arg1 = "key"
        __kwargs__.arg2 = "some_map"

        [endpoint._."/entry/other"]
        # this endpoint will be invalid as the localmap entry would not
        # apply here.
        __provider__ = "a_mock"
        __kwargs__.arg1 = "key"
        """)

        exe = config.request_execution('/entry/', {})
        self.assertEqual(exe().arg1, 'the value')
        self.assertEqual(exe().arg2, {
            'key1': 'the value',
            'key2': 'the value',
        })

        # check the other thing first, show that this typical creation
        # is not impeded.
        other_exe = config.request_execution('/entry/other', {})
        with self.assertRaises(KeyError):
            other_exe.locals['a_mock']
