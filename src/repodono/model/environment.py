from collections.abc import Mapping

from repodono.model.base import BaseMapping


class Environment(BaseMapping):
    """
    Default environment implementation
    """

    def __init__(self, config):
        # TODO optimize the following pattern
        environment = config.get('environment', None)
        if not isinstance(environment, Mapping):
            return super().__init__()
        variables = environment.get('variables', None)
        if not isinstance(variables, Mapping):
            return super().__init__()
        super().__init__(variables)
