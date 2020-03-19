"""
Demo task runner and receiver function

This demonstrates how a minimum task runner may be implemented to accept
messages to generate output at the specific location.
"""

import pika
from pathlib import Path


def create_connection_channel(config):
    # TODO figure out a common specification which this "loading" may be
    # done in a manner that may be configured, exported/interrogated by
    # other processes.
    settings = config.get('settings', {})

    pika_settings = config.get('pika_settings', {})
    host = pika_settings.get('host', 'localhost')
    exchange = pika_settings.get('exchange', 'repodono')
    queue = pika_settings.get('queue', 'repodono.task')
    status = pika_settings.get('status', 'repodono.logs')

    connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
    channel = connection.channel()
    channel.confirm_delivery()

    # exchange and queue for the status
    channel.exchange_declare(exchange=exchange, exchange_type='topic')
    q_name = channel.queue_declare(queue='', exclusive=True).method.queue
    channel.queue_bind(exchange=exchange, queue=q_name, routing_key=status)

    def sender(body, exe):
        # TODO figure out how to gracefully check existance of file.

        print("sending %r" % body)
        channel.basic_publish(exchange='', routing_key=queue, body=body)

        # consume the return queue until the expected response
        for method, properties, body in channel.consume(
                queue=q_name, auto_ack=True):
            print("received: [%r] %r" % (method.routing_key, body,))
            if str(body, encoding='utf8') == str(exe.locals['__path__']):
                # XXX this duplicates the initial response loading...
                channel.stop_consuming()
                response = Response.restore_from_disk(exe)
                print("response has length %d" % len(response.content))

        connection.close()

    return connection, channel, sender


def path_to_exe_payload(config, path):
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

    if len(sys.argv) < 3:
        sys.stderr.write('usage: %s <config.toml> [-f] <path>\n' % sys.argv[0])
        sys.stderr.write('\n')
        sys.stderr.write('  -f to force a message (ignores cache)\n')
        sys.exit(1)

    with open(sys.argv[1]) as fd:
        config = Configuration.from_toml(fd.read())

    flush = '-f' in sys.argv
    path = sys.argv[-1]
    exe, payload = path_to_exe_payload(config, path)

    if not flush:
        try:
            response = Response.restore_from_disk(exe)
        except OSError:
            # can't do this
            pass
        else:
            print("Cached response has length %d" % len(response.content))
            sys.exit(0)

    connection, channel, sender = create_connection_channel(config)
    sender(payload, exe)
