"""Telemetry class that takes raw sensor data and filters it to remove noise
and provide more accurate telemetry data.
"""
import time


class Telemetry(object):
    def __init__(self):
        self._valid_commands = {
            'idle',
            'forward', 'forward-left', 'forward-right',
            'reverse', 'reverse-left', 'reverse-right'
        }

    def get_position(self):
        """Returns just the latitude/longitude position."""
        return (40.02139, -105.25008) # Solid State Depot

    def get_heading(self):
        """Returns the heading of the RC car in degrees, where 0 is true
        north.
        """
        return 0.0

    def get_speed(self):
        """Returns the speed of the RC car in meters per second."""
        return 0.5

    def get_raw_data(self):
        """Returns the raw most recent telemetry readings."""
        return {
            'acceleration': {
                'x': 0.0,
                'y': 0.0,
                'z': -9.8
            },
            'heading': 0.0,
            'speed': 0.5,
            'position': {
                'latitude': 40.02139,
                'longitude': -105.25008
            },
            'timestamp': time.time(),
        }

    def process_drive_command(self, comand):
        """Process a drive command. When the command module tells the car to do
        something (e.g. drive forward and left), that data should be integrated
        into the telemetry immediately, because GPS sensors and what not
        normally have a slight delay.
        """
        # TODO: Do something useful with this command
        assert command in self._valid_commands

    def handle_message(self, message):
        # TODO: Process the message and stop using test data
        pass
