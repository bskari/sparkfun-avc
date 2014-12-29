"""Tests the location Kalman Filter."""

import math
import numpy
import unittest

from location_filter import LocationFilter
from telemetry import Telemetry

#pylint: disable=protected-access
#pylint: disable=too-many-public-methods


class TestLocationFilter(unittest.TestCase):
    """Tests the location Kalman filter."""

    def test_estimate_gps(self):
        """Tests that the estimating of the locations via GPS is sane."""
        # I'm not sure how to independently validate these tests for accuracy.
        # The best I can think of is to do some sanity tests.
        for coordinates in ((100, 200), (200, 100), (300, 300), (50, 50)):
            location_filter = LocationFilter(coordinates[0], coordinates[1])

            self.assertEqual(
                location_filter.estimated_location(),
                coordinates
            )

            new_coordinates = (150, 150)

            for _ in range(5):
                location_filter.update_gps(
                    new_coordinates[0],
                    new_coordinates[1],
                    x_accuracy_m=0.1,
                    y_accuracy_m=0.1,
                    heading_d=0,
                    speed_m_s=0
                )
            for estimated, expected in zip(
                location_filter.estimated_location(),
                new_coordinates
            ):
                self.assertAlmostEqual(estimated, expected, 2)

    def test_estimate_constant_speed(self):
        """Tests that the estimating of the locations via dead reckoning at a
        constant speed is sane.
        """
        # I'm not sure how to independently validate these tests for accuracy.
        # The best I can think of is to do some sanity tests.
        start_coordinates = (100, 200)
        location_filter = LocationFilter(
            start_coordinates[0],
            start_coordinates[1]
        )

        self.assertEqual(
            location_filter.estimated_location(),
            start_coordinates
        )

        direction_d = 32.0
        speed_m_s = 1.0
        location_filter._estimates[2].itemset(0, direction_d)

        # Use this to set the speed
        location_filter.update_gps(
            start_coordinates[0],
            start_coordinates[1],
            0.1,
            0.1,
            direction_d,
            speed_m_s
        )

        for estimated, expected in zip(
            location_filter.estimated_location(),
            start_coordinates
        ):
            self.assertAlmostEqual(estimated, expected, 1)

        measurements = numpy.matrix(  # pylint: disable=no-member
            [0.0, 0.0, direction_d, 0.0, 0.0, 0.0]
        ).transpose()  # z

        seconds = 5
        for _ in range(seconds):
            print(location_filter.estimated_location())
            print(location_filter.estimated_heading())
            location_filter._update(
                measurements,
                location_filter.COMPASS_OBSERVER_MATRIX,
                location_filter.COMPASS_MEASUREMENT_NOISE,
                time_diff_s=1.0
            )

        offset = Telemetry.rotate_radians_clockwise(
            (0.0, speed_m_s * seconds),
            math.radians(direction_d)
        )
        new_coordinates = [s + o for s, o in zip(start_coordinates, offset)]

        for estimated, expected in zip(
            location_filter.estimated_location(),
            new_coordinates
        ):
            self.assertAlmostEqual(estimated, expected, 2)

    def test_estimate(self):
        """Tests that the estimating of the locations via both is sane."""
        initial_location = (100.0, 100.0)
        location_filter = LocationFilter(
            initial_location[0],
            initial_location[1]
        )

        self.assertEqual(location_filter.estimated_location(), initial_location)

        delta_m_s = 1.0

        location_filter._observer_matrix = [
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ]

        tick = 0.5
        for update in range(1, 5):
            measurements = [[0.0], [0.0], [delta_m_s], [delta_m_s]]
            location_filter._update(measurements, tick)
            for index in range(2):
                self.assertAlmostEqual(
                    location_filter.estimated_location()[index],
                    initial_location[index] + delta_m_s * update * tick,
                    2
                )
