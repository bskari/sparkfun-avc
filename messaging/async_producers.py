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

    def set_max_throttle(self, throttle):
        """Send the set max throttle command."""
        self._producer.publish('set-max-throttle={}'.format(throttle))


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
            heading_d,
            speed_m_s,
            timestamp_s,
            device_id
    ):
        """Sends a GPS reading."""
        self._producer.publish(json.dumps({
            'latitude_d': latitude_d,
            'longitude_d': longitude_d,
            'accuracy_m': accuracy_m,
            'heading_d': heading_d,
            'speed_m_s': speed_m_s,
            'timestamp_s': timestamp_s,
            'device_id': device_id,
        }))

    def compass_reading(self, compass_d, confidence, device_id):
        """Sends a compass reading."""
        self._producer.publish(json.dumps({
            'compass_d': compass_d,
            'confidence': confidence,
            'device_id': device_id,
        }))

    def accelerometer_reading(
            self,
            acceleration_g_x,
            acceleration_g_y,
            acceleration_g_z,
            device_id
    ):
        """Sends an accelerometer reading."""
        self._producer.publish(json.dumps({
            'acceleration_g_x': acceleration_g_x,
            'acceleration_g_y': acceleration_g_y,
            'acceleration_g_z': acceleration_g_z,
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


class WaypointProducer(SingletonMixin):
    """Forwards waypoint commands to another exchange."""
    def __init__(self):
        super(WaypointProducer, self).__init__()
        self._producer = MessageProducer(config.WAYPOINT_EXCHANGE)

    def load_kml_file(self, kml_file_name):
        """Loads some waypoints from a KML file."""
        self._producer.publish(
            json.dumps({
                'command': 'load',
                'file': kml_file_name
            })
        )
