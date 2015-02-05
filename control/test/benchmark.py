"""Benchmarks the parts of the system."""

import time
import timeit

from control.chase_waypoint_generator import ChaseWaypointGenerator
from control.command import Command
from control.kml_waypoint_generator import KmlWaypointGenerator
from control.location_filter import LocationFilter
from control.telemetry import Telemetry
from control.test.dummy_driver import DummyDriver
from control.test.dummy_logger import DummyLogger
from control.test.dummy_telemetry_data import DummyTelemetryData


def benchmark_location_filter_update_gps():
    location_filter = LocationFilter(0.0, 0.0, 0.0)
    iterations = 100
    start = time.time()
    for _ in range(iterations):
        location_filter.update_gps(
            100.0,
            100.0,
            1.0,
            1.0,
            20.0,
            4.5
        )
    end = time.time()
    print(
        '{} iterations of LocationFilter.update_gps, each took {:.5}'.format(
            iterations,
            (end - start) / float(iterations)
        )
    )


def benchmark_location_filter_update_compass():
    location_filter = LocationFilter(0.0, 0.0, 0.0)
    iterations = 100
    start = time.time()
    for _ in range(iterations):
        location_filter.update_compass(20.0)
    end = time.time()
    print(
        '{} iterations of LocationFilter.update_compass, each took {:.5}'.format(
            iterations,
            (end - start) / float(iterations)
        )
    )


def benchmark_location_filter_update_dead_reckoning():
    location_filter = LocationFilter(0.0, 0.0, 0.0)
    iterations = 1000
    start = time.time()
    for _ in range(iterations):
        location_filter.update_dead_reckoning()
    end = time.time()
    print(
        '{} iterations of LocationFilter.update_dead_reckoning, each took {:.5}'.format(
            iterations,
            (end - start) / float(iterations)
        )
    )


def benchmark_command_run_course_iterator():
    logger = DummyLogger()
    telemetry = Telemetry(logger)
    waypoint_generator = KmlWaypointGenerator(
        logger,
        'control/paths/solid-state-depot.kmz'
    )
    driver = DummyDriver(telemetry, logger)
    command = Command(telemetry, driver, waypoint_generator, logger)

    iterations = 250
    start = time.time()
    iterator = command._run_course_iterator()
    for step in zip(range(iterations), iterator):
        pass
    assert step[0] == iterations - 1

    end = time.time()
    print(
        '{} iterations of Command._run_course_iterator, each took {:.5}'.format(
            iterations,
            (end - start) / float(iterations)
        )
    )


def main():
    benchmark_location_filter_update_gps()
    benchmark_location_filter_update_compass()
    benchmark_location_filter_update_dead_reckoning()
    benchmark_command_run_course_iterator()

if __name__ == '__main__':
    main()
