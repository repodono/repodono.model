"""
The confiration classes for the repodono framework.
"""

import logging
import toml

from repodono.model.base import (
    BaseMapping,
    Execution,
    RouteTrieMapping,
    CompiledRouteResourceDefinitionMapping,

    BoundedBucketDefinition,
    BoundedBucketDefinitionMapping,
    BoundedEndpointDefinition,
    BoundedEndpointDefinitionMapping,
)
from repodono.model.mappings import (
    Environment,
    Default,
    Bucket,
    Localmap,
    Resource,
)
from repodono.model.routing import URITemplateRouter

logger = logging.getLogger(__name__)


# Perhaps this could be another class in the base module?
class BaseConfiguration(BaseMapping):

    def __init__(self, config_mapping):
        # TODO figure out how to apply some sort of schema.
        self.config_str = ''
        super().__init__(config_mapping)

    @classmethod
    def from_toml(cls, config_str, **kw):
        inst = cls(toml.loads(config_str), **kw)
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

    def __init__(self, config_mapping, execution_class=Execution):
        super().__init__(config_mapping)
        self.environment = Environment(self)
        self.default = Default(self)
        self.bucket = Bucket(self)
        self.localmap = Localmap(self)
        self.resource = Resource(self)
        self.endpoint = self.bucket.Endpoint(self)
        self.execution_class = execution_class
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

        # Since it's too painful to bind mapping of one type to another
        # based on the same proxybind framework because of how types
        # (don't) work in Python, the mapping must be reconstructed
        # using the individual items.
        self.bucket = BoundedBucketDefinitionMapping({
            k: BoundedBucketDefinition(v).bind(self.environment)
            for k, v in self.bucket.items()
        })

        # Likewise for the end point - in this case it's a nested
        # mapping.
        # TODO may need to create/update the base class so that this
        # would also be one of EndpointDefinitionSetMapping
        self.endpoint = {
            k: BoundedEndpointDefinitionMapping(
                {
                    bucket: BoundedEndpointDefinition(v).bind(self.environment)
                    for bucket, v in edsmap.items()
                },
                bucket_name=edsmap.bucket_name,
                bucket_mapping=edsmap.bucket_mapping,
            )
            for k, edsmap in self.endpoint.items()
        }

    def request_execution(
            self, route, mapping, bucket_mapping={}, execution_class=None):
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

        if execution_class is None:
            execution_class = self.execution_class

        # resolve the target bucket with the bucket mapping and the
        # bucket config mapping.

        # Given that there could be alternative routes, it would be
        # useful to raise more specific exception, or even make the
        # behavior configurable.  Ideally, the downstream framework
        # should be able to respond with HTTP 406 Not Acceptable to
        # the user-agent, under the most pure implementation sense.

        # This currently raises a simple KeyError if endpoint cannot be
        # resolved
        endpoint = self.route_bucket_endpoint_resolver(route, bucket_mapping)
        resources = self.compiled_route_resources[route]
        # the remapping is only needed if localmap has an entry defined
        # for this route.
        remap_mapping = (
            self.localmap[route].remap if route in self.localmap else {})
        return execution_class(
            endpoint, self.environment, self.default, resources, mapping,
            remap_mapping,
        )

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

        # basically, there should be a way to spin up a thing that can
        # listen to a message that might be generated by rabbitmq and
        # then write the output to the filesystem somewhere as per the
        # designated __path__ and __root__ for the given locals
