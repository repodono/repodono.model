import unittest
from tempfile import TemporaryDirectory

from repodono.model.http import Response, HttpExecution
from repodono.model.config import Configuration


class ResponseTestCase(unittest.TestCase):

    def test_response_base(self):
        response = Response('text')
        self.assertEqual(response.content, 'text')
        self.assertEqual(response.headers, {})

    def test_response_headers(self):
        response = Response('text', headers={
            'Content-length': '4',
        })
        self.assertEqual(response.content, 'text')
        self.assertEqual(response.headers, {
            'Content-length': '4',
        })


class HttpExecutionTestCase(unittest.TestCase):

    def test_execution_basic_call(self):
        std_root = TemporaryDirectory()
        self.addCleanup(std_root.cleanup)

        config = Configuration.from_toml("""
        [environment.variables]
        some_result = "A simple text result"

        [environment.paths]
        std_root = "%s"

        [bucket._]
        __roots__ = ['std_root']
        accept = ["*/*"]

        [endpoint._."/"]
        __provider__ = "some_result"
        """ % (std_root.name,))

        exe = config.request_execution('/', {}, execution_class=HttpExecution)
        # Invoking execute object directly
        response = exe()
        self.assertEqual('A simple text result', response.content)
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
        std_root = "%s"

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
        std_root = "%s"

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
        std_root = "%s"

        [bucket._]
        __roots__ = ['std_root']
        accept = ["*/*"]

        [endpoint._."/json"]
        __provider__ = "results.sample_dict"
        """ % (std_root.name,), execution_class=HttpExecution)

        response = config.request_execution('/json', {})()
        self.assertEqual('{"1": "example"}', response.content)
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
        std_root = "%s"

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
        std_root = "%s"

        [bucket._]
        __roots__ = ['std_root']
        accept = ["*/*"]

        [endpoint._."/constructed"]
        __provider__ = "response"
        """ % (std_root.name,), execution_class=HttpExecution)

        response = config.request_execution('/constructed', {})()
        self.assertEqual('hello', response.content)
        self.assertEqual({}, response.headers)
