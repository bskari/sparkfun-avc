"""Telemetry class that takes raw sensor data and filters it to remove noise
and provide more accurate telemetry data.
"""
import json


class Telemetry(object):
    """Provides up to date telemetry data to other modules. This class will use
    the current command direction, anomalous value filtering and interpolation
    to provide more accurate readings than just raw data dumps.
    """
    def __init__(self):
        self._data = {}

    def get_raw_data(self):
        """Returns the raw most recent telemetry readings."""
        return self._data

    def get_data(self):
        """Returns the approximated telemetry data."""
        return self.get_raw_data()

    def process_drive_command(self, throttle, turn):
        """Process a drive command. When the command module tells the car to do
        something (e.g. drive forward and left), that data should be integrated
        into the telemetry immediately, because GPS sensors and what not
        normally have a slight delay.
        """
        assert -1.0 <= throttle <= 1.0
        assert -1.0 <= turn <= 1.0

    def handle_message(self, message):
        """Stores telemetry data from messages received from the phone."""
        #print(json.dumps(message, sort_keys=True, indent=1))
        self._data = message
