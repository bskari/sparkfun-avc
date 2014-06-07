"""Class to control the RC car."""

import collections
import math
import threading
import time

from dune_warrior import command
from telemetry import Telemetry

# pylint: disable=superfluous-parens


class Command(threading.Thread):
    """Processes telemetry data and controls the RC car."""

    def __init__(
        self,
        telemetry,
        send_socket,
        commands,
        logger,
        sleep_time_milliseconds=None
    ):
        """Create the Command thread. send_socket is just a wrapper around
        some other kind of socket that has a simple "send" method.
        """
        super(Command, self).__init__()

        self._valid_commands = {'start', 'stop'}
        self._telemetry = telemetry
        if sleep_time_milliseconds is None:
            self._sleep_time_seconds = .02
        else:
            self._sleep_time_seconds = sleep_time_milliseconds / 1000.0
        self._send_socket = send_socket
        self._commands = commands
        self._logger = logger
        self._run = True
        self._run_course = False
        self._start_time = None
        self._last_iteration_seconds = None
        self._waypoints = collections.deque()
        self._last_command = None

    def handle_message(self, message):
        """Handles command messages, e.g. 'start' or 'stop'."""
        if 'command' not in message:
            self._logger.info('No command in command message')
            return

        if message['command'] not in self._valid_commands:
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
        m_per_d_longitude = Telemetry.latitude_to_m_per_d_longitude(position_d[0])

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
        try:
            while self._run:

                while self._run and not self._run_course:
                    time.sleep(self._sleep_time_seconds)

                if not self._run:
                    return

                self._logger.info('Running course iteration')

                self._waypoints = collections.deque([
                    # In front of the Hacker Space
                    (40.041384, -105.249758),
                    (40.021411, -105.250189),
                ])

                while self._run and self._run_course:
                    self._last_iteration_seconds = time.time()
                    self._run_course_iteration()
                    time.sleep(self._sleep_time_seconds)
                self._logger.info('Stopping course')

        except Exception as exception:
            self._logger.warning('Command thread had exception, ignoring: ' + str(exception))

    def _run_course_iteration(self):
        """Runs a single iteration of the course navigation loop."""
        speed = 0.25
        # Drive straight for 2 seconds at the start to get GPS bearing
        if time.time() < self._start_time + 2:
            self.send_command(1.0, 0.0)
            return

        telemetry = self._telemetry.get_data()
        current_waypoint = self._waypoints[0]
        distance = Telemetry.distance_m(
            telemetry['latitude'],
            telemetry['longitude'],
            current_waypoint[0],
            current_waypoint[1]
        )
        if distance < 0.5:
            self._logger.info('Reached ' + str(current_waypoint))
            self._waypoints.popleft()
            if len(self._waypoints) == 0:
                self._logger.info('Stopping')
                self.send_command(0.0, 0.0)
            else:
                # I know I shouldn't use recursion here, but I'm lazy
                self._run_course_iteration()
            return

        degrees = Telemetry.relative_degrees(
            telemetry['latitude'],
            telemetry['longitude'],
            current_waypoint[0],
            current_waypoint[1]
        )
        self._logger.debug(
            '{latitude_1} {longitude_1} to {latitude_2} {longitude_2} is {degrees}'.format(
                latitude_1=telemetry['latitude'],
                longitude_1=telemetry['longitude'],
                latitude_2=current_waypoint[0],
                longitude_2=current_waypoint[1],
                degrees=degrees,
            )
        )


        if 'bearing' not in telemetry:
            if 'heading' not in telemetry:
                return
            heading_d = telemetry['heading']
        else:
            heading_d = telemetry['bearing']

        diff_d = abs(heading_d - degrees)
        if diff_d > 180.0:
            diff_d -= 180.0

        self._logger.debug(
            'My heading: {heading}, goal heading: {goal}'.format(
                heading=heading_d,
                goal=degrees,
            )
        )
        if diff_d < 10.0:
            self.send_command(speed, 0.0)
            return

        turn = min(diff_d / 20.0, 1.0)
        if Telemetry.is_turn_left(heading_d, degrees):
            turn = -turn
        self.send_command(speed, turn)

    def run_course(self):
        """Starts the RC car running the course."""
        self._start_time = time.time()
        self._run_course = True

    def stop(self):
        """Stops the RC car from running the course."""
        self.send_command(0.0, 0.0)
        self._run_course = False

    def kill(self):
        """Kills the thread."""
        self._run = False

    def send_command(self, throttle, turn):
        """Sends a command to the RC car. Throttle should be a float between
        -1.0 for reverse and 1.0 for forward. Turn should be a float between
        -1.0 for left and 1.0 for right.
        """
        assert -1.0 <= throttle <= 1.0, 'Bad throttle in command'
        assert -1.0 <= turn <= 1.0, 'Bad turn in command'

        self._telemetry.process_drive_command(throttle, turn)

        throttle = int(throttle * 16.0 + 16.0)
        throttle = min(throttle, 31)
        # Turning too sharply causes the servo to push harder than it can go,
        # so limit this
        # Add 33 instead of 32 because the car drifts left
        turn = int(turn * 24.0 + 33.0)
        turn = min(turn, 57)
        turn = max(turn, 8)

        if self._last_command is not None:
            last_command = self._last_command
            if last_command[0] == throttle and last_command[1] == turn:
                return
        self._last_command = (throttle, turn)
        self._logger.debug(
            'throttle:{throttle} turn:{turn} time:{time}'.format(
                throttle=throttle,
                turn=turn,
                time=time.time()
            )
        )

        self._send_socket.send(command(throttle, turn))
