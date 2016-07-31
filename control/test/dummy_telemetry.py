"""Dummy class for Telemetry interface. A real Telemetry should have these
methods:
    get_raw_data(self)
    get_data(self)
    process_drive_command(self, throttle, turn)
    is_stopped(self)
    handle_message(self, data_dict)
"""

import math
import time

from control.telemetry import Telemetry
from messaging.rabbit_logger import RabbitMqLogger

# pylint: disable=too-many-instance-attributes


class DummyTelemetry(object):
    """Rough simulation of telemetry data."""
    MAX_SPEED_M_S = 4.7  # From observation

    def __init__(self, first_way_point):
        self._x_m, self._y_m = first_way_point
        self._logger = RabbitMqLogger()
        self._x_m -= 1000
        self._heading = 0.0
        self._last_command_time = time.time()
        self._throttle = 0.0
        self._turn = 0.0

        self.update_count = 1000

    def get_raw_data(self):
        """Returns the raw telemetry data."""
        raise NotImplementedError

    def get_data(self):
        """Returns the estimated telemetry data."""
        self._update_position()
        values = {
            'heading_d': self._heading,
            'x_m': self._x_m,
            'y_m': self._y_m,
            'accelerometer_m_s_s': [],
            'speed_m_s': self._throttle * self.MAX_SPEED_M_S,
        }
        return values

    def process_drive_command(self, throttle, turn):
        """Processes a drive command sent out by the command module."""
        self._throttle = throttle
        self._turn = turn

    def _update_position(self):
        """Updates the position using dead reckoning."""
        self.update_count -= 1

        diff_time_s = 1.0

        if self._throttle > 0.0:
            self._heading += self._turn * 30.0
            self._heading = Telemetry.wrap_degrees(self._heading)

            step_m = diff_time_s * self._throttle * self.MAX_SPEED_M_S
            point = (0, step_m)
            radians = math.radians(self._heading)
            point = Telemetry.rotate_radians_clockwise(point, radians)
            self._x_m += point[0]
            self._y_m += point[1]

    def is_stopped(self):  # pylint: disable=no-self-use
        """Returns True if the car is stopped."""
        return False

    def handle_message(self, data_dict):
        """Handles recent data from the Telemetry module. For the dummy class,
        we ignore messages.
        """
        pass
