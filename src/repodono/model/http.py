import json
import logging
from mimetypes import MimeTypes

from repodono.model.base import Execution

mimetypes = MimeTypes()
logger = logging.getLogger(__name__)


def check_path(mapping, key):
    result = mapping[key]
    parent = result.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
        # logger.debug("created dir '%s'", parent)
    except OSError as e:
        raise ValueError(
            "failed to create '%s' in execution.locals: %s" % (result, e))
    return result


def checked_write_bytes(mapping, key, payload):
    path = check_path(mapping, key)
    path.write_bytes(payload)
    logger.debug("wrote %d bytes to '%s'", len(payload), path)


class Response(object):
    """
    Generic response object.
    """

    def __init__(self, content, headers=None):
        self.content = content
        # TODO ensure headers have case-insensitive keys to match HTTP
        self.headers = {} if headers is None else headers

    @staticmethod
    def validate_execution_locals(execution):
        for key in ['__path__', '__metadata_path__']:
            if key not in execution.locals:
                raise ValueError("execution.locals did not provide '%s'" % key)
        return True

    @classmethod
    def restore_from_disk(cls, execution):
        cls.validate_execution_locals(execution)
        return cls(
            content=execution.locals['__path__'].read_bytes(),
            headers=json.loads(execution.locals['__metadata_path__'].read_text(
                encoding='utf8')),
        )

    @property
    def content(self):
        return vars(self)['content']

    @content.setter
    def content(self, value):
        if isinstance(value, bytes):
            vars(self)['content'] = value
        else:
            vars(self)['content'] = bytes(value, encoding='utf8')

    def store_to_disk(self, execution):
        self.validate_execution_locals(execution)
        checked_write_bytes(execution.locals, '__path__', self.content)
        headers = bytes(json.dumps(self.headers), encoding='utf8')
        checked_write_bytes(execution.locals, '__metadata_path__', headers)


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
