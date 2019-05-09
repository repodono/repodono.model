"""
The confiration classes for the repodono framework.
"""

import toml

from repodono.model.base import (
    BaseMapping,
    Execution,
    RouteTrieMapping,
    CompiledRouteResourceDefinitionMapping,
)
from repodono.model.mappings import (
    Environment,
    Bucket,
    Resource,
    Endpoint,
)
from repodono.model.routing import URITemplateRouter


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
        self.bucket = Bucket(self)
        self.resource = Resource(self)
        self.endpoint = Endpoint(self)
        self.compile()

    @property
    def endpoint_keys(self):
        return [matcher.template.uri for matcher in self.router.matchers]

    def compile(self):
        """
        Compile the configuration into the form that may be used.
        """

        self._endpoint_keys = set()
        for endpoint_definition in self.endpoint.values():
            self._endpoint_keys.update(endpoint_definition.keys())

        rtres = RouteTrieMapping(self.resource)
        for endpoints in self._endpoint_keys:
            # using setdefault to assign an empty list for endpoints
            # that do not already have a correlated set of resources
            # defined.
            rtres.setdefault(endpoints, [])

        self.compiled_route_resources = CompiledRouteResourceDefinitionMapping(
            rtres)
        # just use the router to "sort" the endpoint keys for now.
        self.router = URITemplateRouter.from_strings(self._endpoint_keys)

    def request_execution(
            self, route, mapping, bucket_mapping={},
            execution_class=Execution):
        """
        Generates an execution object from a route and a mapping that
        may be produced externally to this class.

        Arguments:

        route
            the route that was picked
        mapping
            the mapping extracted from the url.

        Optional Argument:

        bucket_mapping
            the mapping for the values for bucket resolution.
        execution_class
            the class that implements the execution
        """

        # resolve the target bucket with the bucket mapping and the
        # bucket config mapping.

        # Given that there could be alternative routes, it would be
        # useful to raise more specific exception, or even make the
        # behavior configurable.  Ideally, the downstream framework
        # should be able to respond with HTTP 406 Not Acceptable to
        # the user-agent, under the most pure implementation sense.

        # This currently raises a simple KeyError
        endpoint = self.route_bucket_endpoint_resolver(route, bucket_mapping)
        resources = self.compiled_route_resources[route]
        return execution_class(endpoint, self.environment, resources, mapping)

    def route_bucket_endpoint_resolver(self, route, bucket_mapping={}):
        """
        Resolves the bucket based on the incoming keyword arguments
        passed to this method.
        """

        # TODO this may be a useful method to memoize

        for bucket_key, bucket in self.bucket(bucket_mapping):
            endpoint = self.endpoint[bucket_key].get(route, NotImplemented)
            if endpoint is NotImplemented:
                continue
            return endpoint
        else:
            raise KeyError(
                "route '%s' cannot be resolved from endpoints" % route)

    def endpoint_callable_factory(self):
        """
        Produce generic callables (possibly from an input function) that
        would have a way to disambiguate the bucket to use, and then
        select the intended provider to produce the desired output.

        We would need a way to match some auxilary input mapping (i.e.
        http headers) against the ones specified by the bucket.

        Alternatively, allow hooking of middleware of the supported
        frameworks (e.g. sanic or flask) and have it set the bucket
        name such that the generic endpoint will do its work.

        Or, the configuration specify the generic endpoint constructor
        which will build the thing?  Wouldn't this be something that
        should be specified at runtime?
        """
