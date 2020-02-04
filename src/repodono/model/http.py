import json
from mimetypes import MimeTypes

from repodono.model.base import Execution

mimetypes = MimeTypes()


class Response(object):
    """
    Generic response object.
    """

    def __init__(self, content, headers=None):
        self.content = content
        self.headers = {} if headers is None else headers


class HttpExecution(Execution):
    """
    Execution within the context of http.  This provides a customised
    call method that will ensure the response is of the custom response
    type defined above in this module.
    """

    def __call__(self):
        """
        Invoke the execute method of this instance and reprocess that
        into an instance of Response, if the result produced by execute
        has not already done so.
        """

        result = self.execute()
        if result is None:
            return None

        elif isinstance(result, Response):
            # It may be possible for results be already wrapped, so in
            # this instance return it as is.
            return result

        elif isinstance(result, bytes):
            mimetype, encoding = mimetypes.guess_type(
                self.locals['__path__'].name)
            if mimetype is None:
                mimetype = 'application/octet-stream'
            elif mimetype.endswith('javascript') or mimetype.endswith('html'):
                mimetype = 'text/plain'
            headers = {'content-type': mimetype}
            if encoding:
                headers['content-encoding'] = encoding
            return Response(result, headers)

        elif isinstance(result, str):
            return Response(result, {'content-type': 'text/plain'})

        elif isinstance(result, dict):
            # Assuming dicts are JSON objects.
            return Response(
                json.dumps(result),
                {'content-type': 'application/json'},
            )

        raise ValueError('unsupported execution result')
