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

    def test_default_objects(self):
        root = TemporaryDirectory()
        self.addCleanup(root.cleanup)
        config = Configuration.from_toml("""
        [default.variables]
        foo = "bar"
        [default.paths]
        base_root = %r
        [[default.objects]]
        __name__ = "thing"
        __init__ = "repodono.model.testing:Thing"
        path = "base_root"
        """ % (root.name,))
        self.assertTrue(isinstance(config.default['thing'].path, Path))
        self.assertEqual(config.default['foo'], 'bar')

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
        one = 1
        [environment.paths]
        base_root = %r

        # The indentations are to indicate the relative associations
        [[environment.objects]]
        __name__ = "thing"
        __init__ = "repodono.model.testing:Thing"
            [environment.objects.path]
            path = "base_root"
            number = "number"
            texts = ["text", "text"]

        [[environment.objects]]
        __name__ = "other"
        __init__ = "repodono.model.testing:Thing"
            [environment.objects.path]
            path = "base_root"
            number = "one"
            numbers = ["number", "one"]
        """ % (root.name,))
        env = config.environment

        self.assertEqual({
            'path': env['base_root'],
            'number': 0,
            'texts': ['hello', 'hello'],
        }, env['thing'].path)

        self.assertEqual({
            'path': env['base_root'],
            'number': 1,
            'numbers': [0, 1],
        }, env['other'].path)


class ConfigBucketTestCase(unittest.TestCase):

    def test_basic_roots(self):
        # note that the current setup captures everything.
        config = Configuration.from_toml("""
        [environment.paths]
        default_root = "/default"
        generated_root = "/generated"
        xml_root = "/xml"
        json_root = "/json"

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
            '/default', '/generated'
        ], [
            str(r) for r in config.bucket['_'].roots
        ])
        self.assertEqual({'accept': ['*/*']}, config.bucket['_'].environment)
        self.assertEqual([
            '/json'], [str(r) for r in config.bucket['json'].roots])
        self.assertEqual({
            'accept': ['application/json', 'text/json']
        }, config.bucket['json'].environment)
        self.assertEqual([
            '/xml'], [str(r) for r in config.bucket['xml'].roots])
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

    def test_environment_shadowing(self):
        config_str = """
        [environment.paths]
        foo = 'bar'

        [[environment.objects]]
        __name__ = "foo"
        __init__ = "repodono.model.testing:Thing"
        path = "foo"

        [bucket._]
        __roots__ = ["foo"]

        [endpoint._."/"]
        __provider__ = "foo"
        """

        config = Configuration.from_toml(config_str)
        self.assertEqual(str(config['environment']['paths']['foo']), 'bar')
        # entry is defined.
        self.assertEqual(
            config['environment']['objects'][0]['__name__'], 'foo')
        exe = config.request_execution('/', {})
        self.assertEqual(str(exe.locals['foo']), 'bar')
        # auxilary check
        self.assertEqual(str(exe.locals['__root__']), 'bar')

    def test_compiled_details(self):
        root = TemporaryDirectory()
        self.addCleanup(root.cleanup)
        config = Configuration.from_toml("""
        [environment.variables]
        foo = "bar"

        [environment.paths]
        base_root = %(root)r
        default_root = %(root)r
        generated_root = %(root)r
        json_root = %(root)r
        xml_root = %(root)r

        [bucket._]
        __roots__ = ["default_root", "generated_root"]
        accept = ["*/*"]

        [bucket.json]
        __roots__ = ["json_root"]
        accept = ["application/json", "text/json"]

        [bucket.xml]
        __roots__ = ["xml_root"]
        accept = ["application/xml", "text/xml"]

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
        """ % {'root': root.name})

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

        [environment.paths]
        base_root = %(root)r
        json_root = %(root)r
        xml_root = %(root)r

        [bucket.json]
        __roots__ = ["json_root"]
        accept = ["application/json", "text/json"]

        [bucket.xml]
        __roots__ = ["xml_root"]
        accept = ["application/xml", "text/xml"]

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
        """ % {'root': root.name})

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

        [environment.paths]
        somewhere = "/"

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

    def test_endpoint_kwargs_nested_remap(self):
        config = Configuration.from_toml("""
        [environment.variables]
        thing = "env"

        [environment.paths]
        somewhere = "/"

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
        __kwargs__.thing.mock_id = "entry_id"
        __kwargs__.thing.mock_method = "action"
        __kwargs__.thing.mock_thing = "thing"
        """)

        exe = config.request_execution('/entry/{entry_id}/{action}', {
            'entry_id': '123',
            'action': 'blah',
        })
        self.assertEqual(exe.locals['a_mock'].thing['mock_id'], '123')
        self.assertEqual(exe.locals['a_mock'].thing['mock_method'], 'blah')
        self.assertEqual(exe.locals['a_mock'].thing['mock_thing'], 'env')

    def test_endpoint_kwargs_shadowing(self):
        config = Configuration.from_toml("""
        [environment.variables]
        thing = "thing"

        [environment.paths]
        somewhere = "/"

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
        [environment.paths]
        somewhere = "/"

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

        [environment.paths]
        somewhere = "/"

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

        [environment.paths]
        somewhere = "/"

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

    def test_resource_kwarg_dict(self):
        # Test that dictionary values passed to resource also resolved.
        config = Configuration.from_toml("""
        [environment.variables]
        some_name = "the value"

        [environment.paths]
        somewhere = "/"

        [bucket._]
        __roots__ = ['somewhere']

        [[resource."/"]]
        __name__ = "thing"
        __init__ = "repodono.model.testing:Thing"
        path.key = "some_name"

        [endpoint._."/entry/view"]
        __provider__ = "thing"
        """)

        exe = config.request_execution('/entry/view', {})
        self.assertEqual(exe.locals['thing'].path, {'key': 'the value'})
        # this would have simply access the value like above also
        self.assertEqual(exe().path, {'key': 'the value'})

    def test_resource_dot_access_argument(self):
        # Test that dictionary values passed to resource also resolved.
        config = Configuration.from_toml("""
        [environment.variables]
        some_value = "the value"

        [environment.paths]
        somewhere = "/"

        [[environment.objects]]
        __name__ = "dot"
        __init__ = "repodono.model.testing:AttrBaseMapping"
        value = "some_value"

        [bucket._]
        __roots__ = ['somewhere']

        [[resource."/"]]
        __name__ = "thing"
        __init__ = "repodono.model.testing:Thing"
        path = "dot.value"

        [endpoint._."/entry/view"]
        __provider__ = "thing"
        """)

        exe = config.request_execution('/entry/view', {})
        self.assertEqual(exe.locals['thing'].path, "the value")
        # this would have simply access the value like above also
        self.assertEqual(exe().path, "the value")

    def test_localmap(self):
        # Test out the resource definition that specified a required
        # keyword argument with a reference, but then that reference is
        # to be defined later.

        config = Configuration.from_toml("""
        [environment.variables]
        some_name = "the value"

        [environment.paths]
        somewhere = "/"

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

    def test_execution_locals_shadowing_environment(self):
        config = Configuration.from_toml("""
        [environment.variables]
        value = "value"
        target = "the target"
        one = "one"

        [environment.paths]
        somewhere = "/"

        [bucket._]
        __roots__ = ['somewhere']

        # this should not be able to shadow the environment variables.
        [[resource."/"]]
        __name__ = "target"
        __init__ = "repodono.model.testing:Die"

        [[resource."/"]]
        __name__ = "die"
        __init__ = "repodono.model.testing:Die"

        [[resource."/"]]
        __name__ = "three"
        __init__ = "repodono.model.testing:Die"

        [endpoint._."/"]
        __provider__ = "target"
        one = 1
        three = 3
        """)

        exe = config.request_execution('/', {})
        self.assertEqual(exe.locals['target'], 'the target')
        # environment has greatest precedence
        self.assertEqual(exe.locals['one'], 'one')
        # endpoint environment has second greatest
        self.assertEqual(exe.locals['three'], 3)

        with self.assertRaises(Exception):
            # just to ensure that this other definition will then
            # trigger the loading.
            exe.locals['die']

    def test_execution_locals_resource_shadowing(self):
        config = Configuration.from_toml("""
        [environment.variables]
        one = "one"
        two = "two"

        [environment.paths]
        somewhere = "/"

        [bucket._]
        __roots__ = ['somewhere']

        [[resource."/"]]
        __name__ = "thing"
        __init__ = "repodono.model.testing:Thing"
        path = "one"

        # resource entries are shadowed in reverse order.
        [[resource."/"]]
        __name__ = "thing"
        __init__ = "repodono.model.testing:Thing"
        path = "two"

        [endpoint._."/"]
        __provider__ = "target"
        """)

        exe = config.request_execution('/', {})
        self.assertEqual(exe.locals['thing'].path, 'two')

    def test_execution_locals_default_shadowing(self):
        config = Configuration.from_toml("""
        [environment.variables]
        one = "one"
        two = "two"

        [environment.paths]
        somewhere = "/"

        [default.variables]
        two = 2
        three = 3
        four = 4

        [bucket._]
        __roots__ = ['somewhere']

        [[resource."/"]]
        __name__ = "thing"
        __init__ = "repodono.model.testing:Thing"
        path = "one"

        # resource entries are shadowed in reverse order.
        [[resource."/"]]
        __name__ = "thing"
        __init__ = "repodono.model.testing:Thing"
        path = "two"

        # resource entries are shadowed in reverse order.
        [[resource."/"]]
        __name__ = "default"
        __init__ = "repodono.model.testing:Thing"
        path = "three"

        # resource entries are shadowed in reverse order.
        [[resource."/"]]
        __name__ = "four"
        __init__ = "repodono.model.testing:Thing"
        path = "three"

        [endpoint._."/"]
        __provider__ = "target"
        """)

        exe = config.request_execution('/', {})
        # the default value should be shadows as environment has it
        self.assertEqual(exe.locals['thing'].path, 'two')
        # default value should be available
        self.assertEqual(exe.locals['default'].path, 3)
        # had "four" defined at environment.variables, test fails here.
        self.assertTrue(hasattr(exe.locals.four, 'path'))
        self.assertNotEqual(exe.locals['four'], 4)

    def test_localmap_default_shadowing(self):
        config = Configuration.from_toml("""
        [environment.variables]
        some_name = "the value"

        [environment.paths]
        somewhere = "/"

        [default.variables]
        some_map = {}

        [bucket._]
        __roots__ = ['somewhere']
        accept = ["*/*"]

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
        self.assertEqual(exe.locals['some_map'], {
            'key1': 'the value',
            'key2': 'the value',
        })

    def test_default_bindings(self):
        """
        This tests out some of the common default bindings to ensure
        their availability from the endpoint.
        """

        config = Configuration.from_toml("""
        [environment.variables]
        __route__ = "this must be overridden"

        [environment.paths]
        somewhere = "/"

        [bucket._]
        __roots__ = ['somewhere']

        [[resource."/"]]
        __name__ = "a_mock"
        __init__ = "unittest.mock:Mock"

        [endpoint._."/"]
        __provider__ = "a_mock"

        [endpoint._."/entry/"]
        __provider__ = "a_mock"

        [endpoint._."/post/"]
        __provider__ = "a_mock"

        [endpoint._."/post/{id}"]
        __provider__ = "a_mock"
        __route__ = "fake"
        """)

        entry = config.request_execution('/entry/', {})
        self.assertEqual(entry.locals['__route__'], "/entry/")
        post_id = config.request_execution('/post/{id}', {})
        self.assertEqual(post_id.locals['__route__'], "/post/{id}")

    def test_route_binding_scope(self):
        """
        Test where/how the __route__ is actually accessed/used/bounded
        depending on where/how it is specified.
        """

        config = Configuration.from_toml("""
        [environment.paths]
        base_root = "/"

        [bucket._]
        __roots__ = ['base_root']

        [[resource."/static"]]
        __name__ = "static"
        __init__ = "unittest.mock:Mock"
        route = "__route__"

        [[resource."/dynamic"]]
        __name__ = "dynamic"
        __init__ = "unittest.mock:Mock"
        route = "route"

        [endpoint._."/static/subpath"]
        __provider__ = "static"

        [localmap."/dynamic/{value}"]
        route = "__route__"
        [endpoint._."/dynamic/{value}"]
        __provider__ = "dynamic"
        """)

        static = config.request_execution('/static/subpath', {})
        static_mock = static.locals['static']
        dynamic = config.request_execution('/dynamic/{value}', {
            'value': 'subpath',
        })
        dynamic_mock = dynamic.locals['dynamic']

        self.assertEqual(dynamic_mock.route, "/dynamic/{value}")
        self.assertEqual(static_mock.route, "/static")

    # __root__ and path and other filesystem interaction tests

    def test_config_bucket_roots_usage(self):
        with self.assertRaises(TypeError) as e:
            config = Configuration.from_toml("""
            [environment.variable]
            root = "foo"

            [bucket._]
            __roots__ = ['root']
            """)
            config.bucket['_'].roots

        self.assertEqual(
            e.exception.args[0],
            "'root' must be declared under environment.paths",

            # TODO ideally this can be done, if we have more provenance
            # information as to where exactly the value was defined.
            # "'root' must be declared under environment.paths, "
            # "referenced by bucket '_'",
        )

    def test_config_endpoint_root_usage(self):
        with self.assertRaises(TypeError) as e:
            config = Configuration.from_toml("""
            [environment.variable]
            root = "foo"

            [endpoint._."/"]
            __provider__ = 'root'
            __root__ = 'root'
            """)
            config.endpoint['_']['/'].root

        self.assertEqual(
            e.exception.args[0],
            "'root' must be declared under environment.paths",
            # see above TODO
        )

    def test_root_resolution(self):
        """
        Test where/how the __route__ is actually accessed/used/bounded
        depending on where/how it is specified.
        """

        std_root = TemporaryDirectory()
        self.addCleanup(std_root.cleanup)
        alt_root = TemporaryDirectory()
        self.addCleanup(alt_root.cleanup)

        config = Configuration.from_toml("""
        [environment.paths]
        std_root = %r
        alt_root = %r

        [bucket._]
        __roots__ = ['std_root']

        [bucket."alt"]
        __roots__ = ['alt_root', 'std_root']
        accept = ['application/x-alt']

        [[resource."/"]]
        __name__ = "mock"
        __init__ = "unittest.mock:Mock"

        [endpoint._."/entry/"]
        __provider__ = "mock"

        [endpoint."alt"."/entry/"]
        __provider__ = "mock"

        [endpoint."alt"."/post/"]
        __provider__ = "mock"
        __root__ = "std_root"
        """ % (std_root.name, alt_root.name))

        std_entry = config.request_execution(
            '/entry/', {}, {'accept': 'text/plain'})
        self.assertEqual(
            str(std_entry.locals['__root__']), std_root.name,
            'not equal to std_root.name',
        )

        alt_entry = config.request_execution(
            '/entry/', {}, {'accept': 'application/x-alt'})
        self.assertEqual(
            str(alt_entry.locals['__root__']), alt_root.name,
            'not equal to alt_root.name',
        )

        alt_post = config.request_execution(
            '/post/', {}, {'accept': 'application/x-alt'})
        self.assertEqual(
            str(alt_post.locals['__root__']), std_root.name,
            'not equal to std_root.name',
        )
