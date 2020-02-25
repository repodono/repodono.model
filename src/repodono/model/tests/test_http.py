import unittest
from os.path import exists
from pathlib import Path
from tempfile import TemporaryDirectory

from repodono.model.http import Response, HttpExecution
from repodono.model.config import Configuration


class ResponseTestCase(unittest.TestCase):

    def mk_exec_locals(self):
        root = TemporaryDirectory()
        self.addCleanup(root.cleanup)
        root_path = Path(root.name)
        # just creating "enough" of the execution object
        execution = HttpExecution.__new__(HttpExecution)
        execution.locals = {
            '__path__': root_path / 'path' / 'file.txt',
            '__metadata_path__': root_path / 'metadata' / 'file.txt',
        }
        return execution

    def test_response_base(self):
        response = Response('text')
        self.assertEqual(response.content, b'text')
        self.assertEqual(response.headers, {})

    def test_response_headers(self):
        response = Response('text', headers={
            'content-length': '4',
        })
        self.assertEqual(response.content, b'text')
        self.assertEqual(response.headers, {
            'content-length': '4',
        })

    def test_store_to_disk_success_roundtrip(self):
        execution = self.mk_exec_locals()
        self.assertFalse(exists(execution.locals['__path__']))
        self.assertFalse(exists(execution.locals['__metadata_path__']))
        response = Response('hello world', headers={
            'content-type': 'text/plain',
        })
        response.store_to_disk(execution)
        self.assertTrue(exists(execution.locals['__path__']))
        self.assertTrue(exists(execution.locals['__metadata_path__']))

        new_response = Response.restore_from_disk(execution)
        self.assertEqual(new_response.content, response.content)
        self.assertEqual(new_response.headers, response.headers)

    def test_store_to_disk_fail_missing_keys(self):
        execution = self.mk_exec_locals()
        # remove a required key
        execution.locals.pop('__metadata_path__')
        response = Response('hello world', headers={
            'content-type': 'text/plain',
        })
        with self.assertRaises(ValueError):
            response.store_to_disk(execution)
        self.assertFalse(exists(execution.locals['__path__']))

    def test_store_to_disk_fail_cannot_create_dir(self):
        execution = self.mk_exec_locals()
        # prevent directory creation with an empty file
        execution.locals['__path__'].parent.write_bytes(b'')
        response = Response('hello world', headers={
            'content-type': 'text/plain',
        })
        with self.assertRaises(ValueError):
            response.store_to_disk(execution)
        self.assertFalse(exists(execution.locals['__path__']))
        self.assertFalse(exists(execution.locals['__metadata_path__']))

    def test_restore_from_disk_failure(self):
        execution = self.mk_exec_locals()

        execution.locals['__path__'].parent.mkdir()
        execution.locals['__path__'].write_bytes(b'hi')
        with self.assertRaises(FileNotFoundError):
            Response.restore_from_disk(execution)
        execution.locals['__path__'].unlink()

        execution.locals['__metadata_path__'].parent.mkdir()
        execution.locals['__metadata_path__'].write_bytes(b'hi')
        with self.assertRaises(FileNotFoundError):
            Response.restore_from_disk(execution)
        execution.locals['__metadata_path__'].unlink()


class HttpExecutionTestCase(unittest.TestCase):

    def test_execution_basic_call(self):
        std_root = TemporaryDirectory()
        self.addCleanup(std_root.cleanup)

        config = Configuration.from_toml("""
        [environment.variables]
        some_result = "A simple text result"

        [environment.paths]
        std_root = %r

        [bucket._]
        __roots__ = ['std_root']
        accept = ["*/*"]

        [endpoint._."/"]
        __provider__ = "some_result"
        """ % (std_root.name,))

        exe = config.request_execution('/', {}, execution_class=HttpExecution)
        # Invoking execute object directly
        response = exe()
        self.assertEqual(b'A simple text result', response.content)
        self.assertEqual({
            'content-type': 'text/plain',
        }, response.headers)

    def test_execution_bytes_type(self):
        std_root = TemporaryDirectory()
        self.addCleanup(std_root.cleanup)

        config = Configuration.from_toml("""
        [[environment.objects]]
        __name__ = "results"
        __init__ = "repodono.model.testing:Results"

        [environment.paths]
        std_root = %r

        [bucket._]
        __roots__ = ['std_root']
        accept = ["*/*"]

        [endpoint._."/results{/path*}"]
        __provider__ = "results.sample_bytes"
        """ % (std_root.name,), execution_class=HttpExecution)

        data = config.request_execution('/results{/path*}', {'path': ['data']})
        response = data()
        self.assertEqual(b'example', response.content)
        self.assertEqual({
            'content-type': 'application/octet-stream',
        }, response.headers)

        self.assertEqual({
            'content-type': 'text/plain',
        }, config.request_execution('/results{/path*}', {
            'path': ['index.html']
        })().headers)

        self.assertEqual({
            'content-type': 'text/plain',
        }, config.request_execution('/results{/path*}', {
            'path': ['index.js']
        })().headers)

        self.assertEqual({
            'content-encoding': 'gzip',
            'content-type': 'application/x-tar'
        }, config.request_execution('/results{/path*}', {
            'path': ['archive.tar.gz']
        })().headers)

    def test_execution_none(self):
        std_root = TemporaryDirectory()
        self.addCleanup(std_root.cleanup)

        config = Configuration.from_toml("""
        [[environment.objects]]
        __name__ = "results"
        __init__ = "repodono.model.testing:Results"

        [environment.paths]
        std_root = %r

        [bucket._]
        __roots__ = ['std_root']
        accept = ["*/*"]

        [endpoint._."/nothing"]
        __provider__ = "results.sample_none"
        """ % (std_root.name,), execution_class=HttpExecution)

        response = config.request_execution('/nothing', {})()
        self.assertIsNone(response)

    def test_execution_json(self):
        std_root = TemporaryDirectory()
        self.addCleanup(std_root.cleanup)

        config = Configuration.from_toml("""
        [[environment.objects]]
        __name__ = "results"
        __init__ = "repodono.model.testing:Results"

        [environment.paths]
        std_root = %r

        [bucket._]
        __roots__ = ['std_root']
        accept = ["*/*"]

        [endpoint._."/json"]
        __provider__ = "results.sample_dict"
        """ % (std_root.name,), execution_class=HttpExecution)

        response = config.request_execution('/json', {})()
        self.assertEqual(b'{"1": "example"}', response.content)
        self.assertEqual({
            'content-type': 'application/json'
        }, response.headers)

    def test_execution_unknown_type(self):
        std_root = TemporaryDirectory()
        self.addCleanup(std_root.cleanup)

        config = Configuration.from_toml("""
        [[environment.objects]]
        __name__ = "results"
        __init__ = "repodono.model.testing:Results"

        [environment.paths]
        std_root = %r

        [bucket._]
        __roots__ = ['std_root']
        accept = ["*/*"]

        [endpoint._."/unknown"]
        __provider__ = "results"
        """ % (std_root.name,), execution_class=HttpExecution)

        with self.assertRaises(ValueError):
            config.request_execution('/unknown', {})()

    def test_execution_composed_reponse(self):
        std_root = TemporaryDirectory()
        self.addCleanup(std_root.cleanup)

        config = Configuration.from_toml("""
        [environment.variables]
        default = "hello"

        [[environment.objects]]
        __name__ = "response"
        __init__ = "repodono.model.http:Response"
        content = "default"

        [environment.paths]
        std_root = %r

        [bucket._]
        __roots__ = ['std_root']
        accept = ["*/*"]

        [endpoint._."/constructed"]
        __provider__ = "response"
        """ % (std_root.name,), execution_class=HttpExecution)

        response = config.request_execution('/constructed', {})()
        self.assertEqual(b'hello', response.content)
        self.assertEqual({}, response.headers)
