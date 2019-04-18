"""
The confiration classes for the repodono framework.
"""

import toml

from repodono.model.base import (
    BaseMapping,
    ExecutionLocals,
    RouteTrieMapping,
    CompiledRouteResourceDefinitionMapping,
)
from repodono.model.mappings import (
    Environment,
    Resource,
    Endpoint,
)


# Perhaps this could be another class in the base module?
class BaseConfiguration(BaseMapping):

    def __init__(self, config_mapping):
        # TODO figure out how to apply some sort of schema.
        self.config_str = ''
        super().__init__(config_mapping)

    @classmethod
    def from_toml(cls, config_str):
        inst = cls(toml.loads(config_str))
        inst.config_str = config_str
        return inst


class Configuration(BaseConfiguration):
    """
    The main configuration class.

    This is a mapping that aids with the creation of execution locals
    and/or environments within the repodono.model framework.

    This class also provides two attributes for ease of access to the
    environment and the resources defined by the configuration file in
    the form that is expected by the users of the repodono.model
    framework.
    """

    def __init__(self, config_mapping):
        super().__init__(config_mapping)
        self.environment = Environment(self)
        self.resource = Resource(self)
        self.endpoint = Endpoint(self)
        self.compile()

    def compile(self):
        """
        Compile the configuration into the form that may be used.
        """

        self.endpoint_keys = set()
        for endpoint_definition in self.endpoint.values():
            self.endpoint_keys.update(endpoint_definition.keys())

        rtres = RouteTrieMapping(self.resource)
        for endpoints in self.endpoint_keys:
            # using setdefault to assign an empty list for endpoints
            # that do not already have a correlated set of resources
            # defined.
            rtres.setdefault(endpoints, [])

        self.compiled_route_resources = CompiledRouteResourceDefinitionMapping(
            rtres)

    def execution_locals_from_route_mapping(self, route, mapping):
        """
        Generates an execution locals from a route and a mapping that
        may be produced externally to this class.

        Arguments:

        route
            the route that was picked
        mapping
            the mapping extracted from the url.
        """

        resources = self.compiled_route_resources[route]  # raises KeyError
        # TODO figure out how to "execute" the endpoint
        # TODO how to actually figure out which "profile" to use
        # XXX the usage of '_' is hardcoded.
        endpoint = self.endpoint['_'][route]
        return ExecutionLocals([
            endpoint.environment, self.environment, resources, dict(mapping)])
