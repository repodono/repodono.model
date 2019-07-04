class Thing(object):

    def __init__(self, path):
        self.path = path

    def __call__(self, *a, **kw):
        return a, kw


class Die(object):

    def __init__(self, *a, **kw):
        raise Exception('instantiation of this class is forbidden')
