"""Logger that sends messages over Unix domain sockets."""

import json
import threading

from messaging import config
from messaging.message_consumer import consume_messages
from messaging.message_producer import MessageProducer
from messaging.singleton_mixin import SingletonMixin


class RabbitMqLogger(SingletonMixin):
    """Logger that sends messages over Unix domain sockets."""

    def __init__(self):
        super(RabbitMqLogger, self).__init__()
        self._producer = MessageProducer(config.LOGS_EXCHANGE)
        self.warning = self.warn

    def debug(self, message):
        """Forwards messages to debug log."""
        self._producer.publish(json.dumps({
            'level': 'debug',
            'message': message
        }))

    def info(self, message):
        """Forwards messages to info log."""
        self._producer.publish(json.dumps({
            'level': 'info',
            'message': message
        }))

    def warn(self, message):
        """Forwards messages to warn log."""
        self._producer.publish(json.dumps({
            'level': 'warn',
            'message': message
        }))

    def error(self, message):
        """Forwards messages to error log."""
        self._producer.publish(json.dumps({
            'level': 'error',
            'message': message
        }))

    def critical(self, message):
        """Forwards messages to critical log."""
        self._producer.publish(json.dumps({
            'level': 'critical',
            'message': message
        }))


class RabbitMqLoggerReceiver(object):
    """Class that handles RabbitMQ messages."""

    def __init__(self, logger):
        super(RabbitMqLoggerReceiver, self).__init__()
        self._message_type_to_logger = {
            'debug': logger.debug,
            'info': logger.info,
            'warn': logger.warn,
            'error': logger.error,
            'critical': logger.critical,
        }
        consume = lambda: consume_messages(config.LOGS_EXCHANGE, self._callback)
        self._thread = threading.Thread(target=consume)
        self._thread.name = '{}:consume_messages'.format(
            self.__class__.__name__
        )

    def start(self):
        """Starts the thread."""
        if not self._thread.is_alive():
            self._thread.start()

    def kill(self):
        """Kills the inner thread."""
        try:
            RabbitMqLogger()._producer.publish('QUIT')  # pylint: disable=protected-access
        except ValueError as error:
            # This might happen if we try to send a message after the logger has
            # been terminated
            print('While killing {}: {}'.format(self.__class__.__name__, error))

    def join(self):
        """Joins the inner thread."""
        self._thread.join()

    def _callback(self, json_data):
        """Callback that handles log messages."""
        data = json.loads(json_data)
        self._message_type_to_logger[data['level']](data['message'])
