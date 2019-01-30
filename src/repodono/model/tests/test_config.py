import unittest

from repodono.model.config import Configuration


class ConfigTestCase(unittest.TestCase):

    def test_base(self):
        config_str = """
        [environment.variables]
        foo = 'bar'
        """

        config = Configuration(config_str)
        self.assertEqual(config['environment']['variables']['foo'], 'bar')
