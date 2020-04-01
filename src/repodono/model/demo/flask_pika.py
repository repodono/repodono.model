"""
Demo flask helpers

This really should be moved to a dedicated flask integration package.
"""

import json

from werkzeug.routing import Map
from flask import (
    abort,
    request,
    Response as FlaskResponse,
)

from repodono.model.urimatch_flask import URITemplateRule
from repodono.model.exceptions import ExecutionNoResultError

from repodono.model.http import Response
from repodono.model.demo.pika_sender import create_connection_channel


def configure_app(app, config):
    def endpoint(**kwargs):
        execution = config.request_execution(
            request.endpoint, kwargs, request.headers)

        try:
            response = Response.restore_from_disk(execution)
        except OSError:
            connection, channel, sender = create_connection_channel(config)
            payload = json.dumps({
                "route": request.endpoint,
                "mapping": kwargs,
                "bucket_mapping": dict(request.headers),
            })
            response = sender(payload, execution)

        # TODO sender should disambiguate between timeout or no
        # response
        if response is None:
            abort(404)

        return FlaskResponse(
            response.content, mimetype=response.headers['content-type'])

    # XXX the provided endpoint_keys must have already been sorted.
    url_map = Map([
        URITemplateRule(endpoint, endpoint=endpoint)
        for endpoint in config.endpoint_keys
    ])
    view_functions = {
        endpoint_key: endpoint for endpoint_key in config.endpoint_keys
    }

    app.url_map = url_map
    app.view_functions.update(view_functions)

    return app


if __name__ == '__main__':
    import sys
    from flask import Flask
    from repodono.model.config import Configuration

    if len(sys.argv) < 2:
        sys.stderr.write('usage: %s <config.toml>\n' % sys.argv[0])
        sys.exit(1)

    with open(sys.argv[1]) as fd:
        config = Configuration.from_toml(fd.read())

    settings = config.get('settings', {})
    flask_settings = settings.get('flask', {})
    name = flask_settings.get('flask_name', __name__)
    port = int(flask_settings.get('port', 9000))
    debug = flask_settings.get('debug', False)
    app = Flask(name)
    configure_app(app, config)
    app.run(port=port, debug=debug)
