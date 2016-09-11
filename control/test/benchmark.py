"""Benchmarks the parts of the system."""

import time

from control.command import Command
from control.simple_waypoint_generator import SimpleWaypointGenerator
from control.location_filter import LocationFilter
from control.telemetry import Telemetry
from control.test.dummy_driver import DummyDriver
from control.test.dummy_logger import DummyLogger

# pylint: disable=invalid-name
# pylint: disable=protected-access
# pylint: disable=line-too-long


def benchmark_location_filter_update_gps():
    """Benchmark the location filter GPS update."""
    location_filter = LocationFilter(0.0, 0.0, 0.0)
    iterations = 100
    start = time.time()
    for _ in range(iterations):
        location_filter.update_gps(100.0, 100.0, 1.0, 1.0, 20.0, 4.5)
    end = time.time()
    print(
        '{} iterations of LocationFilter.update_gps, each took {:.5}'.format(
            iterations,
            (end - start) / float(iterations)
        )
    )


def benchmark_location_filter_update_compass():
    """Benchmark the location filter compass update."""
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
    """Benchmark the location filter with dead reckoning and no other input."""
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
    """Benchmark the logic for driving the car."""
    logger = DummyLogger()
    telemetry = Telemetry(logger)
    waypoint_generator = SimpleWaypointGenerator(
        SimpleWaypointGenerator.get_waypoints_from_file_name(
            'paths/solid-state-depot.kmz'
        )
    )
    driver = DummyDriver(telemetry, logger)
    command = Command(telemetry, driver, waypoint_generator, logger)

    iterations = 250
    start = time.time()
    iterator = command._run_course_iterator()
    step = None
    for step in zip(range(iterations), iterator):
        pass
    assert step is not None
    assert step[0] == iterations - 1

    end = time.time()
    print(
        '{} iterations of Command._run_course_iterator, each took {:.5}'.format(
            iterations,
            (end - start) / float(iterations)
        )
    )


def main():
    """Runs all the benchmarks."""
    benchmark_location_filter_update_gps()
    benchmark_location_filter_update_compass()
    benchmark_location_filter_update_dead_reckoning()
    benchmark_command_run_course_iterator()

if __name__ == '__main__':
    main()
