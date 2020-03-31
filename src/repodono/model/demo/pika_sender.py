"""
Demo task runner and receiver function

This demonstrates how a minimum task runner may be implemented to accept
messages to generate output at the specific location.
"""

import json
import logging
import pika
from pathlib import Path
from time import time

logger = logging.getLogger()


def create_connection_channel(config):
    # TODO figure out a common specification which this "loading" may be
    # done in a manner that may be configured, exported/interrogated by
    # other processes.
    settings = config.get('settings', {})

    pika_settings = settings.get('pika', {})
    host = pika_settings.get('host', 'localhost')
    exchange = pika_settings.get('exchange', 'repodono')
    queue = pika_settings.get('queue', 'repodono.task')
    status = pika_settings.get('status', 'repodono.logs')
    timeout = float(pika_settings.get('timeout', 1))

    connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
    channel = connection.channel()
    channel.confirm_delivery()

    # exchange and queue for the status
    channel.exchange_declare(exchange=exchange, exchange_type='topic')
    q_name = channel.queue_declare(queue='', exclusive=True).method.queue
    channel.queue_bind(exchange=exchange, queue=q_name, routing_key=status)

    def sender(body, exe):
        # TODO figure out how to gracefully check existance of file.

        start_time = time()
        response = None
        logger.debug("sending %r" % body)
        channel.basic_publish(exchange='', routing_key=queue, body=body)

        # consume the return queue until the expected response
        for method, properties, body in channel.consume(
                queue=q_name, auto_ack=True, inactivity_timeout=timeout):
            if method is None:
                logger.warning(
                    "no response received after %s second(s)" % timeout)
                break
            logger.debug("received: [%r] %r" % (method.routing_key, body,))
            payload = json.loads(body)
            if payload['path'] == str(exe.locals['__path__']):
                # XXX this duplicates the initial response loading...
                channel.stop_consuming()
                if payload['success']:
                    response = Response.restore_from_disk(exe)
                    logger.info(
                        "response has length %d" % len(response.content))
                else:
                    logger.warning("response indicated failure")

        connection.close()
        logger.debug("acquired response after sending in %0.3fms", (
            time() - start_time) * 1000)
        return response

    return connection, channel, sender


def path_to_exe_payload(config, path):
    """
    This is a direct helper for the direct invocation below; for a
    typical application both the exe and payload would be provided by
    the framework itself.
    """

    routed = config.router(path)
    if routed is None:
        sys.stderr.write('path unroutable with config\n')
        sys.exit(1)
    route, mapping = routed
    bucket_mapping = {"Accept": "text/html"}
    payload_dict = {
        "route": route,
        "mapping": mapping,
        "bucket_mapping": bucket_mapping,
    }
    exe = config.request_execution(**payload_dict)
    return exe, json.dumps(payload_dict)


if __name__ == '__main__':
    import sys
    import json
    from repodono.model.config import Configuration
    from repodono.model.http import Response

    logger = logging.getLogger('repodono')
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    if len(sys.argv) < 3:
        sys.stderr.write('usage: %s <config.toml> [-f] <path>\n' % sys.argv[0])
        sys.stderr.write('\n')
        sys.stderr.write('  -f to force a message (ignores cache)\n')
        sys.exit(1)

    with open(sys.argv[1]) as fd:
        config = Configuration.from_toml(fd.read())

    force_msg = '-f' in sys.argv
    path = sys.argv[-1]
    exe, payload = path_to_exe_payload(config, path)

    start_time = time()
    if not force_msg:
        try:
            response = Response.restore_from_disk(exe)
        except OSError:
            # can't do this
            force_msg = True
        else:
            print("Cached response has length %d" % len(response.content))

    if force_msg:
        connection, channel, sender = create_connection_channel(config)
        sender(payload, exe)

    print("Total execution time after building exe/payload: %0.3fms" % (
        (time() - start_time) * 1000))
