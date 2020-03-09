"""
Demo task runner and receiver function

This demonstrates how a minimum task runner may be implemented to accept
messages to generate output at the specific location.
"""

import pika


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

    def status_callback(ch, method, properties, body):
        print("status: [%r] %r" % (method.routing_key, body,))

    channel.basic_consume(
        queue=q_name, on_message_callback=status_callback, auto_ack=True)

    # TODO
    # modification of RPC - have a channel that is common that broadcast
    # newly created resources, and the handler will stop listening when
    # received the appropriate message, and return the thing.
    def sender(body):
        print("sending %r" % body)
        channel.basic_publish(exchange='', routing_key=queue, body=body)

        # now await response
        # connection.process_data_events()

        # XXX
        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            pass

        connection.close()

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
