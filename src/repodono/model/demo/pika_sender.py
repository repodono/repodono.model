"""
Demo task runner and receiver function

This demonstrates how a minimum task runner may be implemented to accept
messages to generate output at the specific location.
"""

import pika


def create_connection_channel(config):
    settings = config.get('settings', {})
    pika_settings = config.get('pika_settings', {})
    host = pika_settings.get('host', 'localhost')
    queue = pika_settings.get('queue', 'repodono_demo')
    routing_key = pika_settings.get('routing_key', 'repodono_demo')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
    channel = connection.channel()
    channel.queue_declare(queue=queue)

    def sender(body):
        print("sending %r" % body)
        channel.basic_publish(exchange='', routing_key=routing_key, body=body)

    return connection, channel, sender


if __name__ == '__main__':
    import sys
    from repodono.model.config import Configuration
    if len(sys.argv) < 3:
        sys.stderr.write('usage: %s <config.toml> <msg_json>\n' % sys.argv[0])
        sys.exit(1)

    with open(sys.argv[1]) as fd:
        config = Configuration.from_toml(fd.read())
    connection, channel, sender = create_connection_channel(config)
    sender(sys.argv[2])
