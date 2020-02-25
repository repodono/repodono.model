"""
Demo task runner and receiver function

This demonstrates how a minimum task runner may be implemented to accept
messages to generate output at the specific location.
"""

import pika
import json


def create_connection_channel(config):
    settings = config.get('settings', {})
    pika_settings = config.get('pika_settings', {})
    host = pika_settings.get('host', 'localhost')
    queue = pika_settings.get('queue', 'repodono_demo')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
    channel = connection.channel()
    channel.queue_declare(queue=queue)

    def callback(ch, method, properties, body):
        print("Received %r" % body)
        try:
            decoded = json.loads(body)
        except ValueError:
            print("Error: received invalid JSON")
            return False

        # endpoint, kwargs, headers
        try:
            execution = config.request_execution(**decoded)
            result = execution()
        except Exception:
            print("Error: invalid message")
            return False

        result.store_to_disk(execution)

    def start():
        channel.basic_consume(
            queue=queue,
            on_message_callback=callback,
            auto_ack=True,
        )
        channel.start_consuming()

    return connection, channel, start


if __name__ == '__main__':
    import sys
    import logging
    from repodono.model.config import Configuration

    if len(sys.argv) < 2:
        sys.stderr.write('usage: %s <config.toml>\n' % sys.argv[0])
        sys.exit(1)

    logger = logging.getLogger('repodono')
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    with open(sys.argv[1]) as fd:
        config = Configuration.from_toml(fd.read())
    connection, channel, start = create_connection_channel(config)
    try:
        print('listener started...')
        start()
    except KeyboardInterrupt:
        print('quitting.')

