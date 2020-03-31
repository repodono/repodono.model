"""
Demo task runner and receiver function

This demonstrates how a minimum task runner may be implemented to accept
messages to generate output at the specific location.
"""

import json
import logging
import traceback

import pika

from time import time
from repodono.model.exceptions import ExecutionNoResultError

logger = logging.getLogger(__name__)


def build_receipt(success=False, path=None):
    result = {
        'success': success,
    }
    if path:
        result['path'] = path
    return json.dumps(result)


def create_connection_channel(config):
    settings = config.get('settings', {})

    pika_settings = settings.get('pika', {})
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

    def reject(delivery_tag, **kw):
        channel.basic_publish(
            exchange=exchange, routing_key=status,
            body=build_receipt(False, **kw)
        )
        channel.basic_reject(
            delivery_tag=delivery_tag, requeue=False)
        return False

    def ack(delivery_tag, **kw):
        channel.basic_publish(
            exchange=exchange, routing_key=status,
            body=build_receipt(True, **kw)
        )
        channel.basic_ack(delivery_tag=delivery_tag)
        return True

    def callback(ch, method, properties, body):
        logger.debug("received %r" % body)
        start_time = time()
        try:
            decoded = json.loads(body)
        except ValueError:
            logger.info("received invalid json")
            return reject(method.delivery_tag)

        try:
            # endpoint, kwargs, headers
            execution = config.request_execution(**decoded)
            path = str(execution.locals['__path__'])
        except Exception as e:
            logger.info("failed to request execution")
            traceback.print_exc()
            # reject execution failures for now.
            return reject(method.delivery_tag)

        try:
            result = execution()
        except ExecutionNoResultError:
            logger.debug("execution with received json produced no results")
            logger.debug("finished entire task in %0.3fms", (
                time() - start_time) * 1000)
            return reject(method.delivery_tag, path=path)
        except Exception as e:
            logger.exception("failed execution")
            # reject execution failures for now; alternatively option is
            # to requeue this somehow?
            return reject(method.delivery_tag, path=path)

        try:
            result.store_to_disk(execution)
            logger.debug("finished entire task in %0.3fms", (
                time() - start_time) * 1000)
        except ValueError:
            logger.exception("failed to serialise")
            return reject(method.delivery_tag, path=path)
        return ack(method.delivery_tag, path=path)

    def start():
        channel.basic_consume(
            queue=queue,
            on_message_callback=callback,
        )
        channel.start_consuming()

    return connection, channel, start


if __name__ == '__main__':
    import sys
    from repodono.model.config import Configuration
    from repodono.model.http import HttpExecution

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
        config = Configuration.from_toml(
            fd.read(), execution_class=HttpExecution)
    connection, channel, start = create_connection_channel(config)
    try:
        print('listener started...')
        start()
    except KeyboardInterrupt:
        print('quitting.')

