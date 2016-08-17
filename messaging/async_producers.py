"""All of the various asynchronous message producers."""

import json

from messaging import config
from messaging.message_producer import MessageProducer
from messaging.singleton_mixin import SingletonMixin


class CommandProducer(SingletonMixin):
    """Forwards commands."""

    def __init__(self):
        super(CommandProducer, self).__init__()
        self._producer = MessageProducer(config.COMMAND_EXCHANGE)

    def start(self):
        """Send the start command."""
        self._producer.publish('start')

    def stop(self):
        """Send the stop command."""
        self._producer.publish('stop')

    def reset(self):
        """Send the reset command."""
        self._producer.publish('reset')

    def calibrate_compass(self):
        """Send the calibrate_compass command."""
        self._producer.publish('calibrate-compass')

    def kill(self):
        """Kills the consumer end."""
        try:
            self._producer.publish('QUIT')
        except ValueError as error:
            # This might happen if we try to send a message after the logger has
            # been terminated
            print('While killing {}: {}'.format(self.__class__.__name__, error))


class TelemetryProducer(SingletonMixin):
    """Forwards telemetry messages."""

    def __init__(self):
        super(TelemetryProducer, self).__init__()
        self._producer = MessageProducer(config.TELEMETRY_EXCHANGE)

    def gps_reading(
            self,
            latitude_d,
            longitude_d,
            accuracy_m,
            bearing_d,
            speed_m_s,
            timestamp_s,
            device_id
    ):
        """Sends a GPS reading."""
        self._producer.publish(json.dumps({
            'latitude_d': latitude_d,
            'longitude_d': longitude_d,
            'accuracy_m': accuracy_m,
            'bearing_d': bearing_d,
            'speed_m_s': speed_m_s,
            'timestamp_s': timestamp_s,
            'device_id': device_id,
        }))

    def compass_reading(self, compass_d, confidence):
        """Sends a compass reading."""
        self._producer.publish(json.dumps({
            'compass_d': compass_d,
            'confidence': confidence,
            'device_id': device_id,
        }))


class CommandForwardProducer(SingletonMixin):
    """Forwards commands to another exchange."""
    # This is a complete hack. I couldn't figure out how to do multiple
    # consumers, but I only need it for one producer (command) and I only have
    # two consumers, so I'll just manually forward them. I know this is fragile
    # and tightly coupled, because handlers shouldn't need to or know about
    # forwarding messages.
    # TODO(skari): Implement multi consumer
    def __init__(self):
        super(CommandForwardProducer, self).__init__()
        self._producer = MessageProducer(config.COMMAND_FORWARDED_EXCHANGE)

    def forward(self, message):
        """Forwards the message."""
        self._producer.publish(message)

    def kill(self):
        """Kills the consumer end."""
        try:
            self._producer.publish('QUIT')
        except ValueError as error:
            # This might happen if we try to send a message after the logger has
            # been terminated
            print('While killing {}: {}'.format(self.__class__.__name__, error))
