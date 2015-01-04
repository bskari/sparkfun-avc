"""Class to control the RC car."""

import gc
import random
import sys
import threading
import time
import traceback

from telemetry import Telemetry


class Command(threading.Thread):  # pylint: disable=too-many-instance-attributes
    """Processes telemetry data and controls the RC car."""
    VALID_COMMANDS = {'start', 'stop'}
    STRAIGHT_TIME_S = 1.0
    MIN_RUN_TIME_S = 3.0

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
        gc.collect()  # Let's try to preemptvely avoid GC interruptions
        self._sleep_time = time.time()
        if self._wake_time is not None:
            time_awake = self._wake_time - self._sleep_time
        else:
            time_awake = 0.0
        time.sleep(self._sleep_time_seconds - time_awake)
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
        while not self._waypoint_generator.done():
            telemetry = self._telemetry.get_data()
            current_waypoint = self._waypoint_generator.get_current_waypoint(
                telemetry['latitude'],
                telemetry['longitude']
            )

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
            # We let the waypoint generator tell us if a waypoint has been
            # reached so that it can do fancy algorithms, like "rabbit chase"
            if self._waypoint_generator.reached(
                telemetry['latitude'],
                telemetry['longitude']
            ):
                self._logger.info('Reached ' + str(current_waypoint))
                self._waypoint_generator.next()
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
                self._driver.drive(speed, 0.0)
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
            self._driver.drive(speed, turn)
            yield True

        self._logger.info('No waypoints, stopping')
        self._driver.drive(0.0, 0.0)
        self.stop()
        yield False

    def run_course(self):
        """Starts the RC car running the course."""
        self._run_course = True

    def stop(self):
        """Stops the RC car from running the course."""
        self._driver.drive(0.0, 0.0)
        self._run_course = False

    def kill(self):
        """Kills the thread."""
        self._run = False

    def is_running_course(self):
        """Returns True if we're currently navigating the course."""
        return self._run_course

    def _unstuck_yourself_iterator(self, seconds):
        """Commands the car to reverse and try to get off an obstacle."""
        start = time.time()
        turn_direction = 1.0 if random.randint(0, 1) == 0 else -1.0
        while time.time() < start + seconds:
            self._driver.drive(-.5, turn_direction)
            yield True
        yield False
