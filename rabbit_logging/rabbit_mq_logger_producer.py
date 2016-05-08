"""Logger that broadcasts to RabbitMQ."""

from rabbit_logging import config
import json
import logging
import pika


class RabbitMqLoggerProducer(object):
    """Logger that broadcasts to RabbitMQ. This implements (some of) the
    logging.Logger interface.
    """

    def __init__(self):
        self._connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost')
        )
        self._channel = self._connection.channel()
        self._channel.exchange_declare(
            exchange=config.LOGS_EXCHANGE,
            type='fanout'
        )

    def debug(self, msg, *args, **kwargs):
        self.log(logging.DEBUG, msg, args, kwargs)

    def info(self, msg, *args, **kwargs):
        self.log(logging.INFO, msg, args, kwargs)

    def warning(self, msg, *args, **kwargs):
        self.log(logging.WARNING, msg, args, kwargs)

    def error(self, msg, *args, **kwargs):
        self.log(logging.ERROR, msg, args, kwargs)

    def critical(self, msg, *args, **kwargs):
        self.log(logging.CRITICAL, msg, args, kwargs)

    def log(self, level, msg, *args, **kwargs):
        message = {'level': level, 'msg': msg, 'args': args, 'kwargs': kwargs}
        self._channel.basic_publish(
            exchange=config.LOGS_EXCHANGE,
            routing_key='',
            body=json.dumps(message)
        )

    def kill(self):
        self._channel.cancel()
        self._connection.close()
