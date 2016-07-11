"""Logger that broadcasts to RabbitMQ."""

from messaging import config
import pika


class MessageProducer(object):
    """Message broker that sends to RabbitMQ."""

    def __init__(self, message_type, host=None):
        if host is None:
            host = 'localhost'

        self._exchange = message_type
        self._connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=host)
        )
        self._channel = self._connection.channel()
        self._channel.exchange_declare(
            exchange=self._exchange,
            exchange_type='fanout'
        )

    def publish(self, message):
        """Publishes a message."""
        self._channel.basic_publish(
            exchange=self._exchange,
            routing_key='',
            body=message
        )

    def kill(self):
        """Kills all listening consumers."""
        #self._channel.basic_publish(
        #    exchange=config.LOGS_EXCHANGE,
        #    routing_key='',
        #    body='QUIT'
        #)
        self._channel.cancel()
        self._connection.close()
