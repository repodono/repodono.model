from repodono.model.base import BaseMapping, AttributeMapping


class Thing(object):

    def __init__(self, path):
        self.path = path

    def __call__(self, *a, **kw):
        return a, kw


class Die(object):

    def __init__(self, *a, **kw):
        raise Exception('instantiation of this class is forbidden')


class Results(object):

    sample_bytes = b'example'
    sample_str = 'example'
    sample_dict = {'1': 'example'}
    sample_list = ['example']
    sample_none = None


class AttrBaseMapping(BaseMapping, AttributeMapping):
    "Only for this local base test class."
