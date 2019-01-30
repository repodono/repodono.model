import unittest

from repodono.model.config import Configuration
from repodono.model.environment import Environment

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

    # def test_environment(self):
    #     env = Environment()
