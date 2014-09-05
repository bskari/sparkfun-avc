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

    def _wait(self):
        """We just define this function separately so that it's easy to patch
        when testing.
        """
        time.sleep(self._sleep_time_seconds)

    def run(self):
        """Run in a thread, controls the RC car."""
        error_count = 0
        if self._waypoints is None or len(self._waypoints) == 0:
            self._logger.info('Resetting waypoints')
            self._waypoints = copy.deepcopy(self._base_waypoints)

        while self._run:
            try:
                while self._run and not self._run_course:
                    self._wait()

                if not self._run:
                    return

                self._logger.info('Running course iteration')

                run_iterator = self._run_iterator()
                while self._run and self._run_course and next(run_iterator):
                    self._wait()

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

    def _run_iterator(self):
        """Returns an iterator that drives everything."""
        course_iterator = self._run_course_iterator()
        while True:
            if self._telemetry.is_stopped():
                unstuck_iterator = self._unstuck_yourself_iterator(1.0)
                while next(unstuck_iterator):
                    yield True

                # Force the car to drive for a little while
                start = time.time()
                while (
                        self._run
                        and self._run_course
                        and time.time() < start + 3.0
                        and next(course_iterator)
                ):
                    yield True

            yield next(course_iterator)

    def _run_course_iterator(self):
        """Runs a single iteration of the course navigation loop."""
        while len(self._waypoints) > 0:
            current_waypoint = self._waypoints[0]
            telemetry = self._telemetry.get_data()

            distance_m = Telemetry.distance_m(
                telemetry['latitude'],
                telemetry['longitude'],
                current_waypoint[0],
                current_waypoint[1]
            )

            self._logger.debug(
                'Distance to goal: {distance}'.format(
                    distance=distance_m
                )
            )
            if distance_m < 1.5:
                self._logger.info('Reached ' + str(current_waypoint))
                self._waypoints.popleft()
                continue

            if distance_m > 3.0:
                speed = 1.0
            else:
                speed = 0.5

            degrees = Telemetry.relative_degrees(
                telemetry['latitude'],
                telemetry['longitude'],
                current_waypoint[0],
                current_waypoint[1]
            )

            heading_d = telemetry['heading']

            self._logger.debug(
                'My heading: {my_heading}, goal heading: {goal_heading}'.format(
                    my_heading=heading_d,
                    goal_heading=degrees,
                )
            )

            diff_d = Telemetry.difference_d(degrees, heading_d)
            if diff_d < 10.0:
                self.send_command(speed, 0.0)
                yield True
                continue
            elif diff_d > 90.0:
                turn = 1.0
            elif diff_d > 45.0:
                turn = 0.5
            else:
                turn = 0.25

            if Telemetry.is_turn_left(heading_d, degrees):
                turn = -turn
            self.send_command(speed, turn)
            yield True

        self._logger.info('No waypoints, stopping')
        self.send_command(0.0, 0.0)
        self.stop()
        yield False

    def run_course(self):
        """Starts the RC car running the course."""
        self._run_course = True

    def stop(self):
        """Stops the RC car from running the course."""
        self.send_command(0.0, 0.0)
        self._run_course = False

    def kill(self):
        """Kills the thread."""
        self._run = False

    def is_running_course(self):
        return self._run_course

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

    def _unstuck_yourself_iterator(self, seconds):
        """Commands the car to reverse and try to get off an obstacle."""
        start = time.time()
        turn_direction = 1.0 if random.randint(0, 1) == 0 else -1.0
        while time.time() < start + seconds:
            self.send_command(-.5, turn_direction)
            yield True
        yield False
