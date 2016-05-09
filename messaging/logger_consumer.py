"""Logger that receives from RabbitMQ."""

from messaging import config
import json
import logging
import pika
import threading


class LoggerConsumer(threading.Thread):
    """Logger that receives from RabbitMQ. This implements (some of) the
    logging.Logger interface.
    """

    def __init__(self, host=None):
        super(LoggerConsumer, self).__init__()

        self._handlers = []

        self._logger = logging.getLogger('sparkfun') 

        if host is None:
            host = 'localhost'
        self._connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=host)
        )
        self._channel = self._connection.channel()
        result = self._channel.queue_declare(exclusive=True)
        queue_name = result.method.queue
        self._channel.queue_bind(
            exchange=config.LOGS_EXCHANGE,
            queue=queue_name
        )
        self._channel.basic_consume(
            self._callback,
            queue=queue_name,
            no_ack=True
        )

    def addHandler(self, handler):
        """Adds a logging handler."""
        self._handlers.append(handler)

    def run(self):
        self._channel.start_consuming()

    def kill(self):
        self._channel.stop_consuming()

    def _callback(self, channel, method, properties, body):
        """Handles received messages."""
        body = json.loads(bytes.decode(body, 'utf8'))
        if 'quit' in body:
            channel.close()
            return
        record = self._logger.makeRecord(
            'sparkfun',
            body['level'],
            None,  # function
            None,  # line number
            body['msg'],
            body['args'],
            body['exc_info'] if 'exc_info' in body else None,
            body['extra'] if 'extra' in body else None,
            body['sinfo'] if 'sinfo' in body else None
        )

        for handler in self._handlers:
            handler.handle(record)
