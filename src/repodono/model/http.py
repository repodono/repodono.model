class Response(object):
    """
    Generic response object.
    """

    def __init__(self, content, headers=None):
        self.content = content
        self.headers = {} if headers is None else headers
