"""
Base configuration
"""

import toml
from repodono.model.base import BaseMapping


class Configuration(BaseMapping):

    def __init__(self, config_mapping):
        # TODO figure out how to apply some sort of schema.
        self.config_str = ''
        super().__init__(config_mapping)

    @classmethod
    def from_toml(cls, config_str):
        inst = cls(toml.loads(config_str))
        inst.config_str = config_str
        return inst
