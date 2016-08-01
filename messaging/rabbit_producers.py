"""All of the various RabbitMQ message producers."""

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
        """Kills the consumer end of RabbitMQ."""
        self._producer.publish('QUIT')


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
            timestamp_s
    ):
        """Sends a GPS reading."""
        self._producer.publish(json.dumps({
            'latitude_d': latitude_d,
            'longitude_d': longitude_d,
            'accuracy_m': accuracy_m,
            'bearing_d': bearing_d,
            'speed_m_s': speed_m_s,
            'timestamp_s': timestamp_s,
        }))

    def compass_reading(self, heading_d, confidence):
        """Sends a compass reading."""
        self._producer.publish(json.dumps({
            'heading_d': heading_d,
            'confidence': confidence,
        }))
