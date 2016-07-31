"""All of the various RabbitMQ message producers."""

from messaging import config
from messaging.message_producer import MessageProducer
from messaging.singleton_mixin import SingletonMixin


class CommandProducer(SingletonMixin):
    """Forwards commands."""

    def __init__(self):
        super(CommandProducer, self).__init__()
        self._producer = MessageProducer(config.COMMAND_EXCHANGE)

    def _send(self, command):
        """Sends a command."""
        self._producer.publish(command)

    def start(self):
        """Send the start command."""
        self._send('start')

    def stop(self):
        """Send the stop command."""
        self._send('stop')

    def reset(self):
        """Send the reset command."""
        self._send('reset')

    def calibrate_compass(self):
        """Send the calibrate_compass command."""
        self._send('calibrate-compass')
