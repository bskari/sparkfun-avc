"""Class to control the RC car."""

import collections
import copy
import math
import threading
import time
import random

from dune_warrior import command
from telemetry import Telemetry

# pylint: disable=superfluous-parens
# pylint: disable=broad-except


class Command(threading.Thread):
    """Processes telemetry data and controls the RC car."""
    VALID_COMMANDS = {'start', 'stop'}
    STRAIGHT_TIME_S = 1.0
    MIN_RUN_TIME_S = 3.0

    def __init__(
        self,
        telemetry,
        send_socket,
        logger,
        sleep_time_milliseconds=None,
        waypoints=None
    ):
        """Create the Command thread. send_socket is just a wrapper around
        some other kind of socket that has a simple "send" method.
        """
        super(Command, self).__init__()

        self._telemetry = telemetry
        if sleep_time_milliseconds is None:
            self._sleep_time_seconds = .02
        else:
            self._sleep_time_seconds = sleep_time_milliseconds / 1000.0
        self._send_socket = send_socket
        self._logger = logger
        self._run = True
        self._run_course = False
        if waypoints is None:
            self._base_waypoints = collections.deque((
                # In front of the Hacker Space
                (40.021391, -105.249860),
                (40.021394, -105.250176),
            ))
        else:
            self._base_waypoints = collections.deque(waypoints)
        self._waypoints = None
        self._last_command = None
        self._crash_time = None
        self._reverse_turn_direction = 1
        self._turn_time = None
        self._turn_duration_s = None
        self._run_time = None

    def handle_message(self, message):
        """Handles command messages, e.g. 'start' or 'stop'."""
        if 'command' not in message:
            self._logger.info('No command in command message')
            return

        if message['command'] not in self.VALID_COMMANDS:
            self._logger.warning(
                'Unknown command: "{command}"'.format(
                    command=message['command']
                )
            )
            return

        if message['command'] == 'start':
            self.run_course()
        elif message['command'] == 'stop':
            self.stop()

    @staticmethod
    def _generate_test_waypoints(position_d, meters, points_count):
        """Generates a generator of test waypoints originating from the current
        position.
        """
        m_per_d_longitude = Telemetry.latitude_to_m_per_d_longitude(
            position_d[0]
        )

        step_d = 360.0 / points_count
        step_r = math.radians(step_d)

        step_m = (meters, 0.0)
        last_waypoint_d = (
            position_d[0] + step_m[1] / Telemetry.M_PER_D_LATITUDE,
            position_d[1] + step_m[0] / m_per_d_longitude
        )
        waypoints = collections.deque()
        for _ in range(4):
            waypoints.append(last_waypoint_d)
            step_m = Telemetry.rotate_radians_clockwise(step_m, step_r)
            last_waypoint_d = (
                last_waypoint_d[0] + step_m[1] / Telemetry.M_PER_D_LATITUDE,
                last_waypoint_d[1] + step_m[0] / m_per_d_longitude
            )

        return waypoints

    def run(self):
        """Run in a thread, controls the RC car."""
        error_count = 0
        if self._waypoints is None or len(self._waypoints) == 0:
            self._logger.info('Resetting waypoints')
            self._waypoints = copy.deepcopy(self._base_waypoints)

        while self._run:
            try:
                while self._run and not self._run_course:
                    time.sleep(self._sleep_time_seconds)

                if not self._run:
                    return

                self._logger.info('Running course iteration')

                while self._run and self._run_course:
                    self._run_course_iteration()
                    time.sleep(self._sleep_time_seconds)
                self._logger.info('Stopping course')
                self.send_command(0.0, 0.0)

            except Exception as exception:
                self._logger.warning(
                    'Command thread had exception, ignoring: ' \
                        + str(type(exception)) + ':' + str(exception)
                )
                error_count += 1
                if error_count > 10:
                    self._logger.warning('Too many exceptions, pausing')
                    self.stop()

                    for _ in range(10):
                        # If we want to kill the thread or continue running the
                        # course again, then stop the pause
                        if not self._run or self._run_course:
                            break
                        time.sleep(0.5)

                    self.run_course()
                    self._logger.warning('Restarting after pause')
                    error_count = 0

    def _run_course_iteration(self):
        """Runs a single iteration of the course navigation loop."""
        now = time.time()
        telemetry = self._telemetry.get_data()
        if self._run_time + self.MIN_RUN_TIME_S < now and self._crash_time is None and self._telemetry.is_stopped():
            self._crash_time = time.time()
            if random.randint(0, 1) > 0:
                self._reverse_turn_direction *= -1
        if self._run_time + self.MIN_RUN_TIME_S < now and self._crash_time is not None:
            if now - self._crash_time > 2:
                self._crash_time = None
                self._run_time = now
                # Also force the car to drive for a little while
                self._turn_time = now
                self._turn_duration_s = 0.0
            else:
                self.unstuck_yourself()
            return

        if len(self._waypoints) == 0:
            self._logger.info('No waypoints, stopping')
            self.send_command(0.0, 0.0)
            self.stop()
            return
        current_waypoint = self._waypoints[0]

        distance_m = Telemetry.distance_m(
            telemetry['latitude'],
            telemetry['longitude'],
            current_waypoint[0],
            current_waypoint[1]
        )

        if distance_m < 3.0:
            self._logger.info('Reached ' + str(current_waypoint))
            self._waypoints.popleft()
            if len(self._waypoints) == 0:
                self._logger.info('Stopping')
                self.send_command(0.0, 0.0)
                self.stop()
            else:
                # I know I shouldn't use recursion here, but I'm lazy
                self._run_course_iteration()
            return

        if distance_m > 10.0:
            speed = 0.5
            turn = 0.5
        else:
            speed = 0.25
            turn = 0.5

        degrees = Telemetry.relative_degrees(
            telemetry['latitude'],
            telemetry['longitude'],
            current_waypoint[0],
            current_waypoint[1]
        )

        heading_d = telemetry['heading']

        if self._turn_time is not None:
            if self._turn_time + self._turn_duration_s > now:
                # Just keep on turning
                return
            if self._turn_time + self._turn_duration_s + self.STRAIGHT_TIME_S > now:
                self.send_command(speed, 0.0)
                return

        # Otherwise figure out how long to turn for
        diff_d = Telemetry.difference_d(heading_d, degrees)

        self._logger.debug(
            'my heading: {heading}, goal heading: {goal},'
            ' distance: {distance}'.format(
                heading=heading_d,
                goal=degrees,
                distance=distance_m,
            )
        )
        if diff_d < 20.0:
            self.send_command(speed, 0.0)
            return

        if Telemetry.is_turn_left(heading_d, degrees):
            turn = -turn
        self._turn_time = now
        # We can overestimate this because it'll just turn again
        self._turn_duration_s = diff_d / 60.0
        self.send_command(speed, turn)

    def run_course(self):
        """Starts the RC car running the course."""
        self._run_course = True
        self._run_time = time.time()

    def stop(self):
        """Stops the RC car from running the course."""
        self.send_command(0.0, 0.0)
        self._run_course = False

    def kill(self):
        """Kills the thread."""
        self._run = False

    def send_command(self, throttle_percentage, turn_percentage):
        """Sends a command to the RC car. Throttle should be a float between
        -1.0 for reverse and 1.0 for forward. Turn should be a float between
        -1.0 for left and 1.0 for right.
        """
        assert -1.0 <= throttle_percentage <= 1.0, 'Bad throttle in command'
        assert -1.0 <= turn_percentage <= 1.0, 'Bad turn in command'

        throttle = int(throttle_percentage * 16.0 + 16.0)
        throttle = min(throttle, 31)
        # Turning too sharply causes the servo to push harder than it can go,
        # so limit this
        # Add 33 instead of 32 because the car drifts left
        turn = int(turn_percentage * 24.0 + 33.0)
        turn = min(turn, 57)
        turn = max(turn, 8)

        if self._last_command == (throttle, turn):
            return
        self._last_command = (throttle, turn)

        self._telemetry.process_drive_command(
            throttle_percentage,
            turn_percentage
        )
        self._logger.debug(
            'throttle:{throttle} turn:{turn}'.format(
                throttle=throttle,
                turn=turn,
                time=time.time()
            )
        )

        self._send_socket.send(command(throttle, turn))

    def unstuck_yourself(self):
        """commands the car to reverse and try to get off an obstacle"""
        self.send_command(-.5, self._reverse_turn_direction)
