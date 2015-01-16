"""Tests the location Kalman Filter."""

import math
import numpy
import random
import unittest

from control.location_filter import LocationFilter
from control.telemetry import Telemetry

# pylint: disable=no-member
# pylint: disable=protected-access
# pylint: disable=too-many-public-methods


class TestLocationFilter(unittest.TestCase):
    """Tests the location Kalman filter."""

    def test_estimate_gps(self):
        """Tests that the estimating of the locations via GPS is sane."""
        # I'm not sure how to independently validate these tests for accuracy.
        # The best I can think of is to do some sanity tests.
        heading_d = 0.0
        for coordinates in ((100, 200), (200, 100), (300, 300), (50, 50)):
            location_filter = LocationFilter(
                coordinates[0],
                coordinates[1],
                heading_d
            )

            self.assertEqual(
                location_filter.estimated_location(),
                coordinates
            )

            new_coordinates = (150, 150)

            for _ in range(6):
                location_filter.update_gps(
                    new_coordinates[0],
                    new_coordinates[1],
                    x_accuracy_m=0.1,
                    y_accuracy_m=0.1,
                    heading_d=heading_d,
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
        start_coordinates_m = (100.0, 200.0)
        heading_d = 32.0
        location_filter = LocationFilter(
            start_coordinates_m[0],
            start_coordinates_m[1],
            heading_d
        )

        self.assertEqual(
            location_filter.estimated_location(),
            start_coordinates_m
        )

        speed_m_s = 1.8
        # This would normally naturally get set by running the Kalman filter;
        # we'll just manually set it now
        location_filter._estimates[3].itemset(0, speed_m_s)

        self.assertEqual(
            location_filter.estimated_location(),
            start_coordinates_m
        )

        measurements = numpy.matrix(  # pylint: disable=no-member
            [0.0, 0.0, heading_d, 0.0]
        ).transpose()  # z

        seconds = 5
        for _ in range(seconds):
            location_filter._update(
                measurements,
                location_filter.COMPASS_OBSERVER_MATRIX,
                location_filter.COMPASS_MEASUREMENT_NOISE,
                time_diff_s=1.0
            )

        offset = Telemetry.rotate_radians_clockwise(
            (0.0, speed_m_s * seconds),
            math.radians(heading_d)
        )
        new_coordinates = [s + o for s, o in zip(start_coordinates_m, offset)]

        for estimated, expected in zip(
            location_filter.estimated_location(),
            new_coordinates
        ):
            self.assertAlmostEqual(estimated, expected, 2)

    def test_estimate(self):
        """Tests that the estimating of the locations via both is sane."""
        start_coordinates_m = (100.0, 150.0)
        heading_d = 40.0
        location_filter = LocationFilter(
            start_coordinates_m[0],
            start_coordinates_m[1],
            heading_d
        )
        speed_m_s = 5.0
        # This would normally naturally get set by running the Kalman filter;
        # we'll just manually set it now
        location_filter._estimates[3].itemset(0, speed_m_s)

        self.assertEqual(
            location_filter.estimated_location(),
            start_coordinates_m
        )

        tick_s = 0.5

        step_m = speed_m_s * tick_s
        step_x_m, step_y_m = Telemetry.rotate_radians_clockwise(
            (0.0, step_m),
            math.radians(heading_d)
        )

        actual_x_m, actual_y_m = start_coordinates_m

        def check_estimates():
            self.assertLess(
                abs(location_filter.estimated_location()[0] - actual_x_m),
                0.5
            )
            self.assertLess(
                abs(location_filter.estimated_location()[1] - actual_y_m),
                0.5
            )

        for update in range(1, 21):
            actual_x_m += step_x_m
            actual_y_m += step_y_m

            # First update by compass
            measurements = numpy.matrix([0.0, 0.0, heading_d, 0.0]).transpose()
            location_filter._update(
                measurements,
                location_filter.COMPASS_OBSERVER_MATRIX,
                location_filter.COMPASS_MEASUREMENT_NOISE,
                tick_s
            )
            check_estimates()

            # Add some approximated GPS readings
            # We'll use very tight standard deviations to try to avoid random
            # test failures
            measurements = numpy.matrix([
                random.normalvariate(actual_x_m, 0.01),
                random.normalvariate(actual_y_m, 0.01),
                random.normalvariate(heading_d, 0.5),
                random.normalvariate(speed_m_s, speed_m_s * 0.1)
            ]).transpose()
            location_filter._update(
                measurements,
                location_filter.GPS_OBSERVER_MATRIX,
                location_filter.GPS_MEASUREMENT_NOISE,
                0.0  # Tick isn't used for GPS
            )
            check_estimates()
