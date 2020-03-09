"""
Demo task runner and receiver function

This demonstrates how a minimum task runner may be implemented to accept
messages to generate output at the specific location.
"""

import pika
import json
import traceback


def create_connection_channel(config):
    settings = config.get('settings', {})

    pika_settings = config.get('pika_settings', {})
    host = pika_settings.get('host', 'localhost')
    exchange = pika_settings.get('exchange', 'repodono')
    queue = pika_settings.get('queue', 'repodono.task')
    status = pika_settings.get('status', 'repodono.logs')

    connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
    channel = connection.channel()
    channel.confirm_delivery()

    # the working queue
    channel.queue_declare(queue=queue)
    # exchange for the status
    channel.exchange_declare(exchange=exchange, exchange_type='topic')

    def callback(ch, method, properties, body):
        print("Received %r" % body)
        try:
            decoded = json.loads(body)
        except ValueError:
            print("Error: received invalid JSON")
            channel.basic_reject(
                delivery_tag=method.delivery_tag, requeue=False)
            return False

        # endpoint, kwargs, headers
        try:
            execution = config.request_execution(**decoded)
            result = execution()
        except Exception as e:
            print("Failed execution")
            traceback.print_exc()
            # reject execution failures for now.
            channel.basic_reject(
                delivery_tag=method.delivery_tag, requeue=False)
            return False

        try:
            result.store_to_disk(execution)
        except ValueError:
            print("Failed to serialise")
            traceback.print_exc()
            # reject execution failures for now.
            channel.basic_reject(
                delivery_tag=method.delivery_tag, requeue=False)
            return False

        channel.basic_publish(
            exchange=exchange, routing_key=status,
            body=str(execution.locals['__path__'])),
        channel.basic_ack(delivery_tag=method.delivery_tag)

    def start():
        channel.basic_consume(
            queue=queue,
            on_message_callback=callback,
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

