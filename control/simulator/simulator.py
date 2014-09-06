"""Simulates the car with telemetry."""
import math
import mock
import time

from command import Command
from telemetry import Telemetry

# pylint: disable=missing-docstring
# pylint: disable=no-self-use
# pylint: disable=protected-access
# pylint: disable=superfluous-parens
# pylint: disable=too-few-public-methods


class FakeLogger(object):
    def debug(self, message):
        pass
    def info(self, message):
        print(message)
    def warning(self, message):
        print(message)
    def error(self, message):
        print(message)


class FakeSocket(object):
    def send(self, message):
        pass


class TelemetrySimulator(object):
    MAX_SPEED_M_S = 4.7  # From observation

    def __init__(self, first_way_point):
        self._latitude, self._longitude = first_way_point
        self._latitude -= 0.001
        self._heading = 0.0
        self._last_command_time = time.time()
        self._throttle = 0.0
        self._turn = 0.0

        self.update_count = 1000
        self.command = None

    def get_raw_data(self):
        raise NotImplementedError

    def get_data(self):
        # The Android phone is rotated, so we need to mess with heading before
        # we give it to the real Telemetry module to simulate the phone
        android_heading = Telemetry.wrap_degrees(-self._heading - 90)
        values = {
            'heading': android_heading,
            'latitude': self._latitude,
            'longitude': self._longitude,
            'accelerometer': [],
            'speed': self._throttle * self.MAX_SPEED_M_S,
        }
        return values

    def process_drive_command(self, throttle, turn):
        self._throttle = throttle
        self._turn = turn

    def _update_position(self):
        self.update_count -= 1
        if self.update_count <= 0:
            assert self.command is not None
            self.command.kill()

        diff_time_s = 1.0

        if self._throttle > 0.0:
            self._heading += self._turn * 20.0
            self._heading = Telemetry.wrap_degrees(self._heading)

            step_m = diff_time_s * self._throttle * self.MAX_SPEED_M_S
            point = (0, step_m / Telemetry.m_per_d_latitude())
            radians = math.radians(self._heading)
            point = Telemetry.rotate_radians_clockwise(point, radians)
            self._latitude += point[1]
            self._longitude += point[0]

    def is_stopped(self):
        return False


def main():
    """Main function."""
    fake_logger = FakeLogger()
    box = [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]
    waypoints = [(x * .001 + 10, y * .001 + 10) for x, y in box]

    fake_socket = FakeSocket()

    telemetry = Telemetry(fake_logger)
    telemetry_simulator = TelemetrySimulator(waypoints[0])
    original_telemetry_get_data = telemetry.get_data
    def call_and_return_original():
        telemetry.handle_message(telemetry_simulator.get_data())
        return original_telemetry_get_data()
    original_telemetry_process = telemetry.process_drive_command
    def call_both_processes(throttle, turn):
        original_telemetry_process(throttle, turn)
        telemetry_simulator.process_drive_command(throttle, turn)

    with mock.patch.object(
        telemetry,
        'get_data',
        new=call_and_return_original
    ):
        with mock.patch.object(
            telemetry,
            'process_drive_command',
            new=call_both_processes
        ):
            command = Command(
                telemetry,
                fake_socket,
                fake_logger,
                sleep_time_milliseconds=1,
                waypoints=waypoints,
            )
            telemetry_simulator.command = command
            command._wait = mock.Mock(
                side_effect=telemetry_simulator._update_position
            )
            command.run_course()
            command.run()


if __name__ == '__main__':
    main()
