import unittest

from repodono.model.http import Response


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
