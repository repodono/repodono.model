from logging import getLogger
from inspect import signature
from functools import partial
from operator import attrgetter
from pathlib import Path
from types import FunctionType
from types import MappingProxyType
from collections import (
    Sequence,
    Mapping,
    MutableMapping,
    defaultdict,
)

from pkg_resources import EntryPoint
from uritemplate import URITemplate

from repodono.model.proxbind import MappingBinderMeta

logger = getLogger(__name__)


def map_vars_value(value, vars_):
    # these are assumed to be produced by the toml/json loads,
    # which should only produce instances of list/dict for the
    # structured data types.
    if isinstance(value, list):
        return [map_vars_value(key, vars_) for key in value]
    elif isinstance(value, dict):
        return {
            name: map_vars_value(key, vars_) for name, key in value.items()}
    elif isinstance(value, attrgetter):
        return value(vars_)
    elif '.' in value:
        return attrgetter(value)(vars_)
    else:
        return vars_[value]


def structured_mapper(
        definition_pairs, input_mapping, _maps=NotImplemented, vars_=None):
    """
    Produce a list of some mapping based on input definition pairs.

    Arguments:

    definition_pairs
        This is in the form of a 2-tuple of key, value, the key being
        the key to extract the actual values from the input_mapping,
        the value being the class to map the values provided at the key
        from the input_mapping, or another nested 2-tuple for a
        recursively generated flattened group mapping.
    input_mapping
        The raw input map (dict)
    """

    def _mapper(definition_pairs, input_mapping, _maps=NotImplemented):
        maps = [] if _maps is NotImplemented else _maps
        for key, value in definition_pairs:
            if key not in input_mapping:
                continue
            if isinstance(value, Sequence):
                _mapper(value, input_mapping[key], _maps=maps)
                continue
            # XXX assuming value to be a class
            sig = signature(value)
            if 'vars_' in sig.parameters:
                maps.append(value(input_mapping[key], vars_=vars_))
            else:
                maps.append(value(input_mapping[key]))

        return maps

    return _mapper(definition_pairs, input_mapping, _maps)


class BaseMapping(MutableMapping):

    def __init__(self, *a, **kw):
        self.__map = {}
        # calling self.update instead to use methods defined by parent
        # that will properly cascade down to the implementation here.
        self.update(*a, **kw)

    def __getitem__(self, key):
        return self.__map[key]

    def __setitem__(self, key, value):
        self.__map[key] = value

    def __delitem__(self, key):
        self.__map.__delitem__(key)

    def __iter__(self):
        return iter(self.__map)

    def __len__(self):
        return len(self.__map)

    def __contains__(self, key):
        return key in self.__map

    def __repr__(self):
        return repr(self.__map)

    # TODO
    # implement from_json / from_toml class constructors?


class FlatGroupedMapping(BaseMapping):
    """
    A mapping that allows assignments to keys that do not already have a
    value defined for that key in any of the inner mappings.
    """

    def __init__(self, mappings):
        # FIXME implement error checks
        # TODO verify uniqueness??  How do we deal with the subclass of
        # this??
        self.__mappings = mappings
        super().__init__()

    def __get(self, key):
        """
        Acquire values from submappings
        """

        for mapping in self.__mappings:
            if key in mapping:
                try:
                    return mapping[key]
                except KeyError:
                    # the mapping may have lied about having the key, or
                    # it cannot fulfill the request.
                    continue
        else:
            raise KeyError(key)

    def __getitem__(self, key):
        try:
            return self.__get(key)
        except KeyError:
            return super().__getitem__(key)

    def __setitem__(self, key, value):
        try:
            self.__get(key)
        except KeyError:
            super().__setitem__(key, value)
        else:
            raise KeyError("%r is read-only" % key)

    def __delitem__(self, key):
        try:
            self.__get(key)
        except KeyError:
            super().__delitem__(key)
        else:
            raise KeyError("%r is read-only" % key)

    def __combined(self):
        results = set()
        for mapping in reversed(self.__mappings):
            results.update(mapping.keys())
        # cheat access to parent _map.
        results.update(self._BaseMapping__map.keys())
        return results

    def __iter__(self):
        return iter(self.__combined())

    def __len__(self):
        return len(self.__combined())

    def __contains__(self, key):
        return key in self.__combined()

    def __repr__(self):
        return repr({k: self[k] for k in self.__combined()})


class AttributeMapping(Mapping):
    """
    A mixin class that allow access of the keys tracked by the Mapping
    class via attribute access.  This is to aid in usage in conjunction
    with operator.attrgetter.

    This implementation omits all attributes not prefixed with an
    underscore (``_``).
    """

    def __setattr__(self, attr, value):
        if not attr.startswith('_'):
            raise TypeError("can't set attributes of '%s' objects" % (
                type(self).__name__,)) from None
        super().__setattr__(attr, value)

    def __getattr__(self, attr):
        """
        This is only invoked in the case where the object doesn't
        actually have the attribute assigned directly to the object.
        The goal here is such that valid items returned by __getitem__
        will still fail if the key is prefixed with an underscore.
        """

        try:
            result = self.__getitem__(attr)
        except KeyError:
            # while a missing '_' prefixed attribute will also have this
            # message, it is useful to include all previous exceptions
            # that triggered this.
            raise AttributeError("'%s' object has no attribute '%s'" % (
                type(self).__name__, attr))
        else:
            if not attr.startswith('_'):
                return result
        raise AttributeError("'%s' object has no attribute '%s'" % (
            type(self).__name__, attr))


class AttributeFlatGroupedMapping(FlatGroupedMapping, AttributeMapping):
    """
    A mapping that combines the features of FlatGroupedMapping with
    AttributeMapping.
    """


class BasePreparedMapping(BaseMapping):
    """
    This base class provides a prepare_from_item classmethod which
    should be implemented.  Although in some implementations it may be
    necessary to implement as a normal method.
    """

    @classmethod
    def prepare_from_item(cls, key, value):
        """
        This must be implemented by the subclasses as it is specific to
        their implementations.  Typically a classmethod should suffice.

        Default implementation is the identity method.
        """

        return value


class PreparedMapping(BasePreparedMapping):
    """
    A mapping where assignment of some value is passed through the
    prepare_from_item method method which must be implemented.  This is
    to establish a standard for restriction of types assigned.
    """

    def __setitem__(self, key, value):
        super().__setitem__(key, self.prepare_from_item(key, value))


class DeferredPreparedMapping(BasePreparedMapping):
    """
    A mapping where retrieval of some value from some key is passed
    through the prepare_from_item method method which must be
    implemented.  This is so that the retrieval is calculated at
    access dynamically.
    """

    def __getitem__(self, key):
        return self.prepare_from_item(key, super().__getitem__(key))


class PathMapping(PreparedMapping):
    """
    A mapping that cast all incoming value to a pathlib.Path.
    """

    @classmethod
    def prepare_from_item(self, key, value):
        return Path(value)


class DeferredComputedMapping(DeferredPreparedMapping):
    """
    A mapping that ensures that all assigned values are standalone
    callable objects without any arguments.
    """

    def __setitem__(self, key, value):
        if not callable(value):
            # TODO check that the callable may be called without any
            # arguments, and raise a different exception otherwise.
            raise TypeError("%r is not callable" % value)
        super().__setitem__(key, value)

    @classmethod
    def prepare_from_item(self, key, value):
        return value()


class SequencePreparedMapping(PreparedMapping):
    """
    A base mapping with values that are a sequence of elements of a
    uniform type produced by a well-defined class method.  Values being
    assigned to instances of such a mapping will be another mapping or
    a list of mappings that contain the requisite keys.  Assignment of
    a single mapping will simply be appended to the internal mapping,
    while assignment of a complete list will set the value to the
    list of instances of the uniform type.
    """

    def __setitem__(self, key, value):
        if key not in self:
            result = []
            # using the base mapping directly as the semantics of how
            # assignments are done have been changed here
            BaseMapping.__setitem__(self, key, result)
        else:
            result = self.get(key)

        if isinstance(value, Sequence):
            result.clear()
            for item in value:
                result.append(self.prepare_from_item(key, item))
        else:
            result.append(self.prepare_from_item(key, value))


class ReMappingProxy(Mapping):
    """
    A read-only mapping proxy to some real mapping.  Note that this is
    a complete version such that any remap keys whoes value references
    a key that is absent in the provided mapping will likely result in
    some KeyError being raised.
    """

    def __init__(self, remap, mapping):
        self.__map = (
            mapping if isinstance(mapping, MappingProxyType) else
            MappingProxyType(mapping)
        )
        self.__remap = MappingProxyType(dict(remap))

    @property
    def _map(self):
        return self.__map

    @property
    def _remap(self):
        return self.__remap

    def __getitem__(self, key):
        return self._map[self._remap[key]]

    def __iter__(self):
        return iter(k for k, v in self._remap.items())

    def __len__(self):
        return len(list(iter(self)))

    def __contains__(self, key):
        return key in self._remap and self._remap[key] in self._map


class PartialReMappingProxy(ReMappingProxy):
    """
    A version of the ReMappingProxy where the iterator will skip over
    any remap keys whoes value is a key that is absent in the provided
    mapping.
    """

    def __iter__(self):
        return iter(k for k, v in self._remap.items() if v in self._map)


class MultiReMappingProxy(ReMappingProxy):
    """
    A version of the ReMappingProxy where any remap values that is an
    instance of dict it will return a new instance of a type of itself
    with that value as a new type.
    """

    def __getitem__(self, key):
        if isinstance(self._remap[key], Mapping):
            return type(self)(self._remap[key], self._map)
        return super().__getitem__(key)

    def __contains__(self, key):
        return key in self._remap and (
            isinstance(self._remap[key], Mapping) or
            self._remap[key] in self._map
        )


class BaseResourceDefinition(object):
    """
    The BaseResourceDefinition class.  More of a marker/common ancestor
    for all ResourceDefinition types.
    """

    def __init__(self, name, call, kwargs, consts=None):
        """
        name
            The name that the resulting resource should be bound to
        call
            The callable target; either an attrgetter or a callable
        kwargs
            The indirect mapping from keyword to some other binding that
            will be resolved right before final instantiation of the
            reference at call
        consts
            A mapping of constants that will override the mapping
        """

        self.name = name
        self.call = call
        self.kwargs = kwargs
        self.consts = {} if consts is None else consts

    def __iter__(self):
        yield self.name
        yield self

    def __call__(self, vars_, omit_keys=(), kwargs={}):
        """
        Prepares a callable object that can be invoked immediately
        with the required definitions.

        Arguments:

        vars_
            The incoming mapping
        omit_keys
            Omit the following keys from the kwargs from the partial to
            be returned.
        kwargs
            Additional kwargs (as a dict) to be provided into the
            returned partial.
        """

        if callable(self.call) and not isinstance(self.call, attrgetter):
            call = self.call
        else:
            call = map_vars_value(self.call, vars_)

        omit = set(omit_keys)

        final_kwargs = map_vars_value({
            k: v for k, v in self.kwargs.items() if k not in omit
        }, AttributeFlatGroupedMapping([self.consts, vars_]))
        final_kwargs.update(kwargs)
        # XXX this does NOT actually trigger the assignment to
        # vars_[self.name], as the current definition on how the
        # protocol works is not yet defined; it may be possible to
        # encapsulate the Environment in a submapping representing
        # some RuntimeEnvironment for the actual usage.
        return partial(call, **final_kwargs)


class BaseResourceDefinitionMapping(BasePreparedMapping):
    """
    This defines the base resource definition mapping, where the value
    assigned should be a dict, or a a mapping of arguments to the
    function being called.  They must be specified with either the
    __init__ or the __call__ key, plus a __name__ which the return value
    will be assigned to.  Only one of __init__ or __call__ may be
    specified; The __init__ key must reference some valid entry point
    within the environment, while the __call__ key must reference an
    existing value in the environment that will be invoked.

    This base class makes no assumption as to how the assignment and/or
    retrieval should proceed.
    """

    class ResourceDefinition(BaseResourceDefinition):

        @classmethod
        def from_call(cls, name, call, kwargs, consts=None):
            # XXX call must be an indirect call that will load the
            # actual thing from vars then return call(**kwargs)
            # FIXME this is currently a placeholder
            return cls(
                name=name, call=attrgetter(call), kwargs=kwargs, consts=consts)

        @classmethod
        def from_entry_point(cls, name, init, kwargs, consts=None):
            entry = EntryPoint.parse('target=' + init)
            call = entry.resolve()
            return cls(name=name, call=call, kwargs=kwargs, consts=consts)

        # TODO vars_ as an argument determine if sane?

    @classmethod
    def create_resource_definition(cls, name, call, init, kwargs, consts=None):
        # a naive, generic creation method.
        if call is not None:
            return cls.ResourceDefinition.from_call(
                name, call, kwargs, consts=consts)
        elif init is not None:
            return cls.ResourceDefinition.from_entry_point(
                name, init, kwargs, consts=consts)

    @classmethod
    def prepare_from_item(cls, key, value):
        kwargs = dict(value)

        # quick check
        if ('__call__' in kwargs) == ('__init__' in kwargs):
            raise ValueError(
                "only one of '__call__' or '__init__' must be defined.")

        # TODO figure out how to find duplicate __name__, if that is
        # needed for all implementations.
        name = kwargs.pop('__name__')
        # either of the callables.
        call = kwargs.pop('__call__', None)
        init = kwargs.pop('__init__', None)
        consts = {
            '__route__': key,
        }
        return cls.create_resource_definition(name, call, init, kwargs, consts)

    # one possible way for subclass to do a lazy load of the definition
    # during access is to override __getitem__ and apply self to kwargs
    # so that it would instantiate via values provided by itself.


class ResourceDefinitionMapping(
        BaseResourceDefinitionMapping, SequencePreparedMapping):
    """
    A resource definition mapping is a mapping with keys that reference
    some path fragment of some URI, and the value assigned being a dict
    being a mapping of arguments to the function being called, and the
    function being called be specified with either the __init__ or the
    __call__ key, plus a __name__ which the return value will be
    assigned to.  Only one of __init__ or __call__ may be specified;
    The __init__ key must reference some valid entry point within the
    environment, while the __call__ key must reference an existing value
    in the environment that will be invoked.

    Another notable difference with this mapping is that each key must
    have multiple values presented in an ordered list, as there can be
    multiple resources defined for each end point.
    """


class BaseBucketDefinition(object):
    """
    The BaseBucketDefinition class.  More of a marker/common ancestor
    for all BucketDefinition types.
    """

    def __init__(self, name, roots, environment):
        """
        Arguments

        name
            Name of this bucket.
        roots
            A list of roots that the content to be served from this
            bucket may be resolved from.
        environment
            Additional mapping for this bucket, where the key is a
            string and values implement __contains__
        """

        self.name = name
        self.roots = roots
        self.environment = environment

    def match(self, mapping):
        """
        Return a score if the provide keyword arguments are all found
        inside the environment mapping.
        """

        for key, value in self.environment.items():
            if not (key in mapping and mapping[key] in value):
                return 0
        else:
            # XXX should return a score between 0 and 1.
            return 1
            # I am not even sure how or if multidimensional matching
            # should even be handled?!


class BaseBucketDefinitionMeta(MappingBinderMeta):

    def roots(mapping, attr_value):
        def find_root(root):
            result = mapping.get(root)
            if not isinstance(result, Path):
                # TODO explicitly refer to which section/bucket this was
                # declared under
                raise TypeError(
                    "'%s' must be declared under environment.paths" % root)
            return result

        return [find_root(root) for root in attr_value]


class BoundedBucketDefinition(
        BaseBucketDefinition, metaclass=BaseBucketDefinitionMeta):
    """
    The singular bounded bucket definition
    """


class BaseBucketDefinitionMapping(BasePreparedMapping):
    """
    This defines the base bucket definition mapping, where the value
    assigned should be a dict, or a a mapping of arguments to the
    function being called.  They must be specified with the __roots__
    key.

    This base class makes no assumption as to how the assignment and/or
    retrieval should proceed.
    """

    # internal class structure similar to the resource definition
    # version for the mean time.

    class BucketDefinition(BaseBucketDefinition):
        pass

    @classmethod
    def create_bucket_definition(cls, name, roots, environment):
        return cls.BucketDefinition(name, roots, environment)

    @classmethod
    def prepare_from_item(cls, key, value):
        environment = dict(value)
        roots = environment.pop('__roots__', None)

        if not roots:
            raise ValueError('__roots__ must be defined')

        return cls.create_bucket_definition(key, roots, environment)

    # TODO formalise the implementation of this through some API?
    default_key = '_'

    # TODO if the support for advanced mimetypes, a BucketDefinition
    # that provides a more robust mimetype parsing/model of it will be
    # beneficial.

    # TODO figure out how and where to memoize the results to speed up
    # future lookups, as the variety of incoming mappings shouldn't vary
    # by much (as they are typically HTTP headers).

    def __call__(self, mapping):
        """
        As the value assigned must result in a BucketDefinition, this
        implements a lookup function based on the provided mapping.
        """

        _ = self.default_key
        key_buckets = sorted((key_bucket for score, key_bucket in (
            (bucket.match(mapping), (key, bucket))
            for key, bucket in self.items()) if score), reverse=True)
        return key_buckets if key_buckets else [(_, self[_])]


class BucketDefinitionMapping(
        BaseBucketDefinitionMapping, PreparedMapping):
    """
    The bucket mapping defines a mapping of available buckets for this
    system.  A bucket is a "profile" for an endpoint definition set,
    which must have a corresponding bucket.  A bucket defines a list of
    roots which may be resolved for statically served content, plus
    additional keys which serves as condition for the activation of the
    endpoint set and its associated bucket.

    The set of keys that serve as the condition will be specific to the
    runner of the application stack.  One example would be the "accept"
    key with a list of mimetype as its value, which when provided by
    some user-agent, would activiate this particular bucket/end point
    set.
    """


class BoundedBucketDefinitionMapping(BaseBucketDefinitionMapping):
    """
    Marker class used internally for the above.
    """


class BaseReMappingDefinition(object):
    """
    The BaseReMappingDefinition class.  More of a marker/common ancestor
    for all ReMappingDefinition types.
    """

    def __init__(self, remap):
        """
        Arguments

        remap
            The remap argument to be passed to some proxy mapping
            implementation.
        """

        self.remap = remap


class BaseReMappingDefinitionMapping(BasePreparedMapping):
    """
    This defines the base remapping definition mapping, where the value
    assigned should be a mapping suitable for the remapping proxy.
    """

    # internal class structure similar to the resource definition
    # version for the mean time.

    class ReMappingDefinition(BaseReMappingDefinition):
        pass

    @classmethod
    def create_remapping_definition(cls, remap):
        return cls.ReMappingDefinition(remap)

    @classmethod
    def prepare_from_item(cls, key, value):
        remap = dict(value)
        return cls.create_remapping_definition(remap)


class ReMappingDefinitionMapping(
        BaseReMappingDefinitionMapping, PreparedMapping):
    """
    This defines a mapping specific to each endpoint definition that
    will be used as a way to remap assignments to a structure that
    resembles this mapping.  This is typically achieved using the
    ReMappingProxy class.
    """

    # TODO figure out how to make this class a parameter/argument/
    # attribute somewhere that may be specified by some users such that
    # the default __call__ will generate the remapping proxy object.


class BaseEndpointDefinition(object):
    """
    The BaseEndpointDefinition class.  More of a marker/common ancestor
    for all EndpointDefinition types.
    """

    def __init__(self, route, bucket_name, provider, root,
                 kwargs_mapping, environment,
                 filename=None, bucket_mapping=None):
        """
        Arguments:

        route
            The route, typically this should be a URI Template.
        bucket_name
            The name of the bucket that this endpoint is declared in.
        provider
            Specifies the name that will be retrieved from the execution
            locals to provide the data to be served from this end point.
            This will be constructed as an operator.attrgetter instance.
        root
            This should reference a name that was defined by as a path
            in the environment, so that it may be joined together with
            the path defined for this endpoint for the full path where
            the data produced by the provider may be written to.
        kwargs_mapping
            This defines an additional key-value mapping that will be
            passed to the provider, where the key will be the key in the
            kwarg, and the value will be used as a key on the endpoint
            execution locals to resolve the actual value from there;
            this essentially provide the final level of indirection to
            the underlying values available in the execution locals so
            that resource definitions and/or other values may be defined
            and the specified provider will be used in a way that is
            specific to this endpoint.

            Any unmapped/unspecified values will be resolved normally.
        environment
            The mapping of an environment variables specific to this
            endpoint definition.

        Optional Arguments:

        filename
            The name of the associated file, if and only if the provided
            route ends with '/'.

            If this is not supplied, build_cache_path will not return a
            usable value.
        bucket_mapping
            An instance BucketDefinitionMapping - if supplied, it is
            used to define an alternative value to the `root` attribute,
            if the value supplied was None.
        """

        self.route = route
        self.route_uritemplate = URITemplate(route)
        self.bucket_name = bucket_name
        # the name will be referenced by the endpoint execution locals
        # resolver to allow the kwarg_mapping to be applied.
        self.name = provider
        self.provider = attrgetter(provider)
        # TODO maybe root might be NotImplemented?
        if (root is None and bucket_mapping and
                bucket_name in bucket_mapping and
                bucket_mapping[bucket_name].roots):
            self.root = bucket_mapping[bucket_name].roots[0]
        else:
            self.root = root
        self.kwargs_mapping = kwargs_mapping
        self.environment = environment
        self.filename = filename

    def build_cache_path(self, mapping):
        # see the bounded version
        return NotImplemented


class BaseEndpointDefinitionMeta(MappingBinderMeta):

    def root(mapping, attr_value):
        result = mapping.get(attr_value)
        if not isinstance(result, Path):
            # TODO explicitly refer to which section/bucket this was
            # declared under
            raise TypeError(
                "'%s' must be declared under environment.paths" % attr_value)
        return result


class BoundedEndpointDefinition(
        BaseEndpointDefinition, metaclass=BaseEndpointDefinitionMeta):
    """
    The singular bounded endpoint definition
    """

    def build_cache_path(self, mapping):
        """
        For a bounded endpoint definition, it becomes possible to locate
        the actual path where the referenced resource on the filesystem.
        However, this implementation will simply join the root with
        expanded uri using this endpoint definition's uritemplate - this
        means that for a page that ends with a `/`, some other form of
        disambiguation external to here will be required by the users of
        this class (e.g. appending index.html in the case of html).
        """

        # TODO if root might be NotImplemented?
        # if not self.root:
        #     return None

        fragments = self.route_uritemplate.expand(**mapping).split('/')
        if '..' in fragments:
            # having '..' at this stage is undefined behavior, as the
            # resolution of this item and what may be resolved will not
            # match under circumstances involving symlinks.
            raise ValueError("'..' found in path fragments")

        if self.route.endswith('/'):
            if self.filename:
                return self.root.joinpath(*fragments) / self.filename
            else:
                logger.info(
                    "route '%s' ends with '/' but no filename provided for "
                    "the associated endpoint at bucket '%s'",
                    self.route, self.bucket_name
                )
                return None

        return self.root.joinpath(*fragments)


class BaseEndpointDefinitionMapping(BasePreparedMapping):
    """
    This defines the base endpoint definition mapping, where the value
    assigned should be a dict, or as a mapping of arguments to the
    function being called.

    At the very minimum, the __provider__ key must be specified, which
    must point to a name available within the execution locals such that
    it may be retrieved to provide the data.  This may be a static value
    provided by the base environment, or dynamically computed as one of
    the resources available for this endpoint.

    The __root__ key may be specified such that the provided data may
    be persisted onto the filesystem.  This is independent of any key
    value pairs defined inside the __roots__ key for the bucket which
    this definition is part of.  However, typical use case will define
    this value to be one of them, but there is no restriction as to what
    or where this may be as the value merely reference something that
    must be available in execution locals.  Ultimately, the runner that
    make use of this configuration file will either accept or reject
    the specified value.

    Typically, the __root__ for this endpoint should be one of the
    values defined for the __roots__ defined for the endpoint set that
    this endpoint is a member of for standard usage (e.g. such that the
    stored data produced by the provider may be resolved at the level
    of the endpoint set).

    Additionally, __kwargs__ may be used to specify a set of key-value
    pairs, where the key will be the name of the new binding, and value
    being the key that may be found in the execution locals.  The intent
    of this mapping is to provide a more cohesive way to map a key
    available within this endpoint definition to the one defined at some
    common top level resource entry, to allow better usage.

    This base class makes no assumption as to how the assignment and/or
    retrieval should proceed, i.e. whether the assignments are fully
    prepared or deferred.
    """

    def __init__(self, value, bucket_name, bucket_mapping=None):
        """
        A bucket name for this set must be specified.
        """

        self.bucket_name = bucket_name
        self.bucket_mapping = bucket_mapping
        super().__init__(value)

    # internal class structure similar to the resource definition
    # version for the mean time.

    class EndpointDefinition(BaseEndpointDefinition):
        pass

    @classmethod
    def create_endpoint_definition(
            cls, route, bucket_name, provider, root, kwargs_mapping,
            environment, filename=None, bucket_mapping=None):
        return cls.EndpointDefinition(
            route, bucket_name, provider, root, kwargs_mapping, environment,
            filename=filename,
            bucket_mapping=bucket_mapping
        )

    def prepare_from_item(self, key, value):
        environment = dict(value)
        provider = environment.pop('__provider__', None)
        kwargs_mapping = environment.pop('__kwargs__', {})
        # The __root__ key is not enforced by default; this is up to the
        # actual application runner to deal with and/or make use of.
        # TODO is defaulting this to None intended?  There may need to be
        # a way to explicitly unset this?
        # TODO look into defaulting to NotImplemented
        root = environment.pop('__root__', None)
        filename = environment.pop('__filename__', None)
        route = key

        if not provider:
            raise ValueError('__provider__ must be defined')

        return self.create_endpoint_definition(
            route, self.bucket_name, provider, root,
            kwargs_mapping, environment,
            filename=filename, bucket_mapping=self.bucket_mapping,
        )


class EndpointDefinitionMapping(
        BaseEndpointDefinitionMapping, PreparedMapping):
    """
    The endpoint mapping defines all available endpoints for a given
    application instance.  It would reference a provider plus a root,
    the provider being a reference to one of the items defined via the
    environment or an available resource at that endpoint.  The root
    would be the name available inside execution locals that reference a
    path the filesystem that serves as the root for this endpoint.

    Any remaining keys will be additional environment values available
    in the context of that endpoint.
    """


class BoundedEndpointDefinitionMapping(BaseEndpointDefinitionMapping):
    """
    Bounded version of the endpoint definition mapping
    """


class EndpointDefinitionSetMapping(PreparedMapping):
    """
    This is for the representation of the sets of endpoint definitions
    available for each of the defined buckets.
    """

    @classmethod
    def prepare_from_item(self, key, value):
        return EndpointDefinitionMapping(value, bucket_name=key)


class ObjectInstantiationMapping(PreparedMapping):
    """
    This takes a list of dicts that contain the prerequisite keys and
    values and it will invoke the target constructor or function as
    specified.

    The reason why this mapping takes a list as part of the construction
    process is due to the nature of object construction being a sequence
    of calls that must happen in a specific order, especially given that
    the constructor may reference previously defined arguments which may
    become out of order if a mapping is used (as Python<3.6 and the toml
    spec do not explicitly maintain mapping key/value order).

    This class is also meant ot be used as part of the StructuredMapping
    class factory.
    """

    # currently defining vars_ as a parameter as the current
    # StructuredMapping resolves that signature.

    def __init__(self, items, vars_):
        """
        For a given mapping resolve the object and construct a mapping
        """

        self.__vars = FlatGroupedMapping([vars_, self])
        super().__init__(items)

    def prepare_from_item(self, key, value):
        # TODO if value is of a BaseResourceDefinition...
        kwargs = dict(value)
        if '__init__' not in kwargs:
            raise ValueError(
                "provided object mapping missing the '__init__' key")
        entry = EntryPoint.parse('target=' + kwargs.pop('__init__'))
        target = entry.resolve()
        kwargs = {
            key: map_vars_value(value, vars_=self.__vars)
            for key, value in kwargs.items()
        }
        return target(**kwargs)

    def update(self, *a, **kw):
        if len(a) != 1 or not (
                isinstance(a[0], Sequence) and
                a[0] and
                isinstance(a[0][0], Mapping)):
            return super().update(*a, **kw)

        try:
            mapping = {
                kwargs.pop('__name__'): kwargs
                for kwargs in (dict(item) for item in a[0])
            }
        except KeyError:
            raise ValueError(
                "an incoming mapping is missing the '__name__' key") from None
        else:
            super().update(mapping)


def StructuredMapping(definition, structured_mapper=structured_mapper):
    """
    A class factory for the creation of a parent class that can
    encapsulate a predefined structure for creating a flattened group
    mapping.  Depending on the number of definition entries, certain
    attributes of the incoming class may be reflected on the class
    produced by this factory function.
    """

    # Previously as implemented, the idea was to have the following:

    # 1) Provide a FlatGroupedMapping, with the possibility for nesting
    #    and resolution of the value through one of the internal
    #    mappings as per the implementation
    # 2) Provide immutability for the initial set of keys provided by
    #    the initial input mapping.
    # 3) Combined together with other classes of the same type, a set of
    #    these classes can work together to form the required mapping
    #    from a single input mapping (i.e. uniform across all of them),
    #    extracting just the relevant information from this while also
    #    maintaining the mapping based API usage.

    # However, if the definition for a particular section is provided by
    # a single definition, wrapping that one single thing around the
    # StructuredMapping class removes any potential ergonomic methods
    # that may be provided by that singular class thus removing the
    # ability for direct usage due to this encapsulation.  Instead of a
    # simple mapping class definition that subclass directly from
    # FlatGroupedMapping, a more involved dynamic class construction is
    # needed.

    # Currently, the scope of this is limited to support callable
    # mappings

    __dict__ = {}

    def __init__(self, raw_mapping):
        # TODO figure out if we want to keep using the double dunder
        # private prefix, as while on one hand we want to really keep
        # this hidden, but on the other hand internal usage does make it
        # more accessible if we are to make this kind of semi-public.
        self.__mappings = []
        # assign mappings to the private attribute for parent class.
        super().__init__(mappings=self.__mappings)
        structured_mapper(
            definition, raw_mapping, _maps=self.__mappings, vars_=self)

    def __call__(self, *a, **kw):
        return self.__mappings[0](*a, **kw)

    if (len(definition) == 1 and
            isinstance(definition[0][1], type) and
            isinstance(
                getattr(definition[0][1], '__call__', None), FunctionType)):
        __dict__['__call__'] = __call__

    # Multiple definition case will encapsulate the entire thing as a
    # FlatGroupedMapping.
    __dict__['__init__'] = __init__
    __class__ = type('StructuredMapping', (FlatGroupedMapping,), __dict__)
    return __class__


def create_empty_trie():
    return defaultdict(create_empty_trie)


class RouteTrieMapping(MutableMapping):
    """
    The implementation interally is effectively managed by a trie for
    all the characters coming in.
    """

    def __init__(self, *a, **kw):
        self.__trie = create_empty_trie()
        # while the usage of this inner attribute is similar enough to
        # BaseMapping, this is going to remain distinct due to the
        # special usage present.
        self.__map = {}
        self.__marker = object()
        # calling self.update instead to use methods defined by parent
        # that will properly cascade down to the implementation here.
        self.update(*a, **kw)

    def __get_trie_nodes(self, key):
        node = self.__trie
        nodes = []

        def push(key):
            if self.__marker in node:
                # include all the intervening marked nodes
                nodes.append((key, node[self.__marker]))

        for i, c in enumerate(key):
            push(key[:i])
            if c not in node:
                break
            node = node[c]
        else:
            # add the final target node
            push(key)
        return nodes

    def __getitem__(self, key):
        if key not in self.__map:
            raise KeyError(key)
        return list(reversed(self.__get_trie_nodes(key)))

    def get(self, key, default=NotImplemented):
        return list(reversed(self.__get_trie_nodes(key)))

    def __set_trie_nodes(self, key):
        node = self.__trie
        for c in key:
            node = node[c]
        return node

    def __setitem__(self, key, value):
        if not isinstance(key, str):
            raise TypeError("keys must be of type 'str'")
        self.__set_trie_nodes(key)[self.__marker] = value
        self.__map[key] = value

    def __delitem__(self, key):
        self.__map.__delitem__(key)

        stack = []
        node = self.__trie
        for c in key:
            if len(node) == 1:
                stack.append((node, c))
            else:
                stack = [(node, c)]
            node = node[c]
        else:
            node.pop(self.__marker)
            # could traverse the stack and manually pop
            if not node and stack:
                target, c = stack[0]
                target.pop(c)

    def __iter__(self):
        return iter(self.__map)

    def __len__(self):
        return len(self.__map)

    def __contains__(self, key):
        return key in self.__map

    def __repr__(self):
        return repr(self.__map)


class CompiledRouteResourceDefinitionMapping(BaseMapping):
    """
    An instance of RouteTrieMapping should be provided for conversion.
    """

    def process_value(self, value):
        return [dict(v) for k, v in value]

    def check_mappings(self, key, value):
        """
        Subclass could implement the specific strategy for validation.
        """

    def build_item(self, key, value):
        mappings = self.process_value(value)
        self.check_mappings(key, mappings)
        # this base type does not do any checking.
        return key, FlatGroupedMapping(mappings)

    def __setitem__(self, key, value):
        super().__setitem__(*self.build_item(key, value))


class ExecutionLocals(AttributeFlatGroupedMapping):
    """
    This should be constructed from a FlatGroupedMapping that has
    grouped all the relevant resource definitions mapping defined for
    the current endpoint plus the extracted values from the route.  The
    __getitem__ method will automatically instantiate all resource
    definitions using values provided by itself.
    """

    def process_resource_definition(self, resource_definition):
        return resource_definition(vars_=self)()

    def __getitem__(self, key):
        # TODO use some kind of threadlocal to track keys retrieved?
        # TODO static version?
        value = super().__getitem__(key)
        if isinstance(value, BaseResourceDefinition):
            return self.process_resource_definition(value)
        else:
            return value


class EndpointExecutionLocals(ExecutionLocals):
    """
    An execution locals specific to an endpoint, such that the kwargs
    mapping defined for it will come into effect.
    """

    # TODO consider replacing mappings with the arguments that go into
    # the original Execution object.

    def __init__(self, mappings, endpoint, remap, default):
        self.__endpoint = endpoint
        self.__remap = remap
        super().__init__(mappings + [
            MultiReMappingProxy(self.__remap, self),
            default,
        ])

    def process_resource_definition(self, resource_definition):
        if resource_definition.name != self.__endpoint.name:
            return resource_definition(vars_=self)()
        return resource_definition(
            vars_=self, omit_keys=self.__endpoint.kwargs_mapping.keys(),
        )(**MultiReMappingProxy(self.__endpoint.kwargs_mapping, self))


class Execution(object):
    """
    This tentatively named object will encapsulate an invoked endpoint
    of an application.
    """

    def __init__(
            self, endpoint, environment, default, resources, endpoint_mapping,
            remap_mapping):
        """
        Arguments:

        endpoint
            an instance of BaseEndpointDefinition
        environment
            a mapping representing the primary mapping of environment
            values in the runtime environment
        default
            a mapping representing the default mapping of values in
            the runtime environment to be provided as a last resort
            default value.
        resources
            the mapping of resources available resolved for the current
            endpoint.
        endpoint_mapping
            additional mapping of values destructured from the url.
        remap_mapping
            additional remap
        """

        self.endpoint = endpoint
        self.environment = environment
        self.default = default
        self.resources = resources
        self.endpoint_mapping = endpoint_mapping
        self.locals = EndpointExecutionLocals([
            # TODO figure out further reserved bindings and formalise
            # the system for this.
            # TODO make this first mapping lazy
            {
                # Also ensure the "dynamic" locally bounded version is
                # also available.
                '__route__': endpoint.route,
                '__root__': endpoint.root,
                # XXX TODO provide a path of some kind associated with
                # this resource from endpoint, e.g. join with __root__
                # '__path__': endpoint.route,
                '__path__': endpoint.build_cache_path(endpoint_mapping),
            },
            environment,
            endpoint.environment,
            resources,
            dict(endpoint_mapping),
        ], endpoint, remap_mapping, self.default)
        # import pdb;pdb.set_trace()

    def execute(self):
        """
        Executes the instructions encoded in the endpoint object.
        """

        return self.endpoint.provider(self.locals)

    def __call__(self):
        """
        Default implementation simply return the result from calling
        execute.
        """

        return self.execute()
