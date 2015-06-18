"""Class to control the RC car."""

import math
import random
import sys
import threading
import time
import traceback

from control.telemetry import Telemetry


class Command(threading.Thread):  # pylint: disable=too-many-instance-attributes
    """Processes telemetry data and controls the RC car."""
    VALID_COMMANDS = {'start', 'stop', 'reset', 'calibrate-compass'}
    NEUTRAL_TIME_1_S = 1.0
    REVERSE_TIME_S = 0.25
    NEUTRAL_TIME_2_S = 0.25

    def __init__(  # pylint: disable=too-many-arguments
            self,
            telemetry,
            driver,
            waypoint_generator,
            logger,
            sleep_time_milliseconds=None,
    ):
        """Create the Command thread."""
        super(Command, self).__init__()

        self._telemetry = telemetry
        if sleep_time_milliseconds is None:
            self._sleep_time_seconds = .02
        else:
            self._sleep_time_seconds = sleep_time_milliseconds / 1000.0
        self._driver = driver
        self._logger = logger
        self._run = True
        self._run_course = False
        self._waypoint_generator = waypoint_generator

        self._last_command = None
        self._sleep_time = None
        self._wake_time = None
        self._telemetry_data = None
        self._start_time = None

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
        elif message['command'] == 'reset':
            self.reset()
        elif message['command'] == 'calibrate-compass':
            if 'seconds' in message:
                self.calibrate_compass(message['seconds'])
            else:
                self.calibrate_compass(10)

    def set_telemetry_data(self, telemetry_data):
        """Sets the telemetry data. Needed for compass calibration."""
        self._telemetry_data = telemetry_data

    def _wait(self):
        """We just define this function separately so that it's easy to patch
        when testing.
        """
        self._sleep_time = time.time()
        if self._wake_time is not None:
            time_awake = self._sleep_time - self._wake_time
        else:
            time_awake = 0.0
        time.sleep(max(self._sleep_time_seconds - time_awake, 0.0))
        self._wake_time = time.time()

    def run(self):
        """Run in a thread, controls the RC car."""
        error_count = 0
        if self._waypoint_generator.done():
            self._logger.info('All waypoints reached')
            return

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
                self._driver.drive(0.0, 0.0)

            except Exception as exception:  # pylint: disable=broad-except
                trace_back = sys.exc_info()[2]
                traces = traceback.extract_tb(trace_back)

                # Find the last local file
                for index in range(len(traces) - 1, -1, -1):
                    file_name, line_number, function_name, _ = traces[index]
                    if file_name.endswith('.py'):
                        break

                trace = '{file_}:{line} {function}'.format(
                    file_=file_name,
                    line=line_number,
                    function=function_name
                )
                self._logger.warning(
                    'Command thread had exception from {trace}, ignoring:'
                    ' {type_}:{message}'.format(
                        trace=trace,
                        type_=str(type(exception)),
                        message=str(exception),
                    )
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
            if (
                self._telemetry.is_stopped()
                and self._start_time is not None
                and time.time() - self._start_time < 2.0
            ):
                self._logger.info(
                    'RC car is not moving according to speed history, reversing'
                )
                unstuck_iterator = self._unstuck_yourself_iterator(3.0)
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
        while not self._waypoint_generator.done():
            telemetry = self._telemetry.get_data()
            current_waypoint = self._waypoint_generator.get_current_waypoint(
                telemetry['x_m'],
                telemetry['y_m']
            )

            distance_m = math.sqrt(
                (telemetry['x_m'] - current_waypoint[0]) ** 2
                + (telemetry['y_m'] - current_waypoint[1]) ** 2
            )

            self._logger.debug(
                'Distance to goal {waypoint}: {distance}'.format(
                    waypoint=[round(i, 3) for i in current_waypoint],
                    distance=round(distance_m, 3),
                )
            )
            # We let the waypoint generator tell us if a waypoint has been
            # reached so that it can do fancy algorithms, like "rabbit chase"
            if self._waypoint_generator.reached(
                    telemetry['x_m'],
                    telemetry['y_m']
            ):
                self._logger.info(
                    'Reached {}'.format(
                        [round(i, 3) for i in current_waypoint]
                    )
                )
                self._waypoint_generator.next()
                continue

            if distance_m > 10.0 or distance_m / telemetry['speed_m_s'] > 2.0:
                throttle = 1.0
            else:
                throttle = 0.5

            degrees = Telemetry.relative_degrees(
                telemetry['x_m'],
                telemetry['y_m'],
                current_waypoint[0],
                current_waypoint[1]
            )

            heading_d = telemetry['heading_d']

            self._logger.debug(
                'My heading: {my_heading}, goal heading: {goal_heading}'.format(
                    my_heading=round(heading_d, 3),
                    goal_heading=round(degrees, 3),
                )
            )

            diff_d = Telemetry.difference_d(degrees, heading_d)
            if diff_d < 10.0:
                # We want to keep turning until we pass the point
                is_left = Telemetry.is_turn_left(heading_d, degrees)
                while diff_d < 10.0:
                    yield True
                    telemetry = self._telemetry.get_data()
                    degrees = Telemetry.relative_degrees(
                        telemetry['x_m'],
                        telemetry['y_m'],
                        current_waypoint[0],
                        current_waypoint[1]
                    )
                    heading_d = telemetry['heading_d']
                    diff_d = Telemetry.difference_d(degrees, heading_d)

                    if self._waypoint_generator.reached(
                            telemetry['x_m'],
                            telemetry['y_m']
                    ):
                        self._logger.info(
                            'Reached {}'.format(
                                [round(i, 3) for i in current_waypoint]
                            )
                        )
                        self._waypoint_generator.next()
                        break
                    if Telemetry.is_turn_left(heading_d, degrees) != is_left:
                        break

                self._driver.drive(throttle, 0.0)
                yield True
                continue
            elif diff_d > 90.0:
                turn = 1.0
            elif diff_d > 45.0:
                turn = 0.5
            else:
                turn = 0.25

            # Turning while going fast causes the car to roll over
            if telemetry['speed_m_s'] > 7.0 or throttle >= 0.75:
                turn = max(turn, 0.25)
            elif telemetry['speed_m_s'] > 4.0 or throttle >= 0.5:
                turn = max(turn, 0.5)

            if Telemetry.is_turn_left(heading_d, degrees):
                turn = -turn
            self._driver.drive(throttle, turn)
            yield True

        self._logger.info('No waypoints, stopping')
        self._driver.drive(0.0, 0.0)
        self.stop()
        yield False

    def calibrate_compass(self, seconds):
        """Calibrates the compass."""
        # Don't calibrate while driving
        if self._run_course:
            self._logger.warn("Can't configure compass while running")
            return
        if self._telemetry_data is None:
            self._logger.error(
                'Unable to configure compass: telemetry_data is None'
            )
            return

        start = time.time()
        self._driver.drive(0.5, 1.0)
        self._telemetry_data.calibrate_compass(seconds)
        try:
            while (
                    self._run
                    and not self._run_course
                    and time.time() < start + seconds
            ):
                time.sleep(0.1)
        except:  # pylint: disable=bare-except
            pass
        self._driver.drive(0.0, 0.0)

    def run_course(self):
        """Starts the RC car running the course."""
        self._run_course = True
        self._start_time = time.time()

    def stop(self):
        """Stops the RC car from running the course."""
        self._driver.drive(0.0, 0.0)
        self._run_course = False

    def reset(self):
        """Resets the waypoints for the RC car."""
        if self.is_running_course():
            self._logger.warn('Tried to reset the course while running')
            return
        self._waypoint_generator.reset()

    def kill(self):
        """Kills the thread."""
        self._run = False

    def is_running_course(self):
        """Returns True if we're currently navigating the course."""
        return self._run_course

    def _unstuck_yourself_iterator(self, seconds):
        """Commands the car to reverse and try to get off an obstacle."""
        # The ESC requires us to send neutral throttle for a bit, then send
        # reverse, then neutral, then reverse again (which will actually drive
        # the car in reverse)

        start = time.time()
        while time.time() < start + self.NEUTRAL_TIME_1_S:
            self._driver.drive(0.0, 0.0)
            yield True

        start = time.time()
        while time.time() < start + self.REVERSE_TIME_S:
            self._driver.drive(-0.5, 0.0)
            yield True

        start = time.time()
        while time.time() < start + self.NEUTRAL_TIME_2_S:
            self._driver.drive(0.0, 0.0)
            yield True

        turn_direction = 1.0 if random.randint(0, 1) == 0 else -1.0
        start = time.time()
        while time.time() < start + seconds:
            self._driver.drive(-.5, turn_direction)
            yield True
        yield False
