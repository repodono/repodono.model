"""
A protocol to create proxy objects that can subsequently be bounded to
another that will provide property based access to the attributes in a
manner that is mediated by the binder class.
"""

from functools import partial


class partialproperty(property):
    """
    This property assumes the provided callable is a partial that can be
    invoked with zero arguments.
    """

    def __get__(self, name, owner):
        return self.fget()


class ProxyBase(object):

    def __init__(self, inst):
        object.__setattr__(self, '__proxied_instance', inst)

    def __getattr__(self, attr):
        return getattr(
            object.__getattribute__(self, '__proxied_instance'), attr)

    def __getattribute__(self, attr):
        if attr == '__proxied_instance':
            raise AttributeError()
        return object.__getattribute__(self, attr)

    def __setattr__(self, attr, value):
        raise TypeError(
            "cannot assign attribute to instances of '%s'" % self.__class__)

    def __get__(self, inst, cls):
        """
        Implementation of this method will allow instances of this class
        to be attached to a subclass of this as some attribute such that
        instances of that subclass may retrieve the original instance
        using that attribute on that instance, without having to resort
        to force users to figure out how to actually do this or rely on
        the dunder attribute.
        """

        return object.__getattribute__(inst, '__proxied_instance')


class MappingBinderMeta(type):

    def __new__(metaclass, name, bases, kwargs, *, proxy_base=ProxyBase):
        """
        for each instance
        """

        # Various functions that will become methods for the classes to
        # be constructed that will provide the framework for defining
        # unbounded and bounded instances of the class.

        def bind(self, mapping):
            # self in this case will be the unbounded object
            # inst will be the actual object to be wrapped.
            inst = self.unwrapped
            full_kwargs = {}
            full_kwargs.update(kwargs)
            full_kwargs.update({
                k: partialproperty(partial(v, mapping, getattr(inst, k)))
                for k, v in vars(metaclass).items()
                if not k.startswith('_') and callable(v)
            })

            bounded_class = type(
                name, (proxy_base, bounded_base,), full_kwargs)
            bounded_inst = bounded_class(inst)
            return bounded_inst

        def __getattribute__(self, attr):
            if attr in ('bind', 'unwrapped'):
                return object.__getattribute__(self, attr)
            raise AttributeError(
                "unbounded objects must be bounded with 'bind' to a mapping "
                "before use"
            )

        def __getattr__(self, attr):
            raise AttributeError(
                "unbounded objects must be bounded with 'bind' to a mapping "
                "before use"
            )

        # Bounded class will not take part or contain the actual
        # metaclass as only the wrapper needs to be marked as such.
        bounded_base = type(name, bases, kwargs)
        bounded_base.__abstractmethods__ = frozenset(['__init__'])
        unbounded_class = super().__new__(
            metaclass, 'Unbounded' + name, (proxy_base,), {
                'bind': bind,
                'bounded': bounded_base,
                'unwrapped': proxy_base(None),
                '__getattribute__': __getattribute__,
                '__getattr__': __getattr__,
            }
        )

        return unbounded_class
