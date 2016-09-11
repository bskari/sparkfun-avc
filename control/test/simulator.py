"""Simulates the car with telemetry."""

import time

from control.command import Command
from control.simple_waypoint_generator import SimpleWaypointGenerator
from control.test.dummy_driver import DummyDriver
from control.test.dummy_logger import DummyLogger
from control.test.dummy_telemetry import DummyTelemetry

# pylint: disable=missing-docstring
# pylint: disable=no-self-use
# pylint: disable=protected-access
# pylint: disable=too-few-public-methods


def main():
    """Main function."""
    logger = DummyLogger()
    box = [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]
    waypoint_generator = SimpleWaypointGenerator(
        SimpleWaypointGenerator.get_waypoints_from_file_name(
            'control/paths/solid-state-depot.kmz'
        )
    )
    waypoint_generator._waypoints.clear()
    for x, y in ((x_ * .005 + 10, y_ * .005 + 10) for x_, y_ in box):
        waypoint_generator._waypoints.append((x, y))

    telemetry = DummyTelemetry(
        logger,
        waypoint_generator.get_current_waypoint(
            waypoint_generator._waypoints[0][0],
            waypoint_generator._waypoints[0][1]
        )
    )
    driver = DummyDriver(telemetry, logger)

    command = Command(
        telemetry,
        driver,
        waypoint_generator,
        logger,
        sleep_time_milliseconds=1,
    )
    command.run_course()
    command.start()

    while not waypoint_generator.done():
        time.sleep(0.1)
    command.kill()

if __name__ == '__main__':
    main()
