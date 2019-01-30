"""
Base configuration
"""

import toml
from repodono.model.base import BaseMapping


class Configuration(BaseMapping):

    def __init__(self, config_str):
        # TODO figure out how to apply some sort of schema.
        super().__init__(toml.loads(config_str))
        self.config_str = config_str
