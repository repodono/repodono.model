import unittest

from repodono.model.testing import Die


class TestingTestCase(unittest.TestCase):

    def test_die_class(self):
        with self.assertRaises(Exception):
            Die()
