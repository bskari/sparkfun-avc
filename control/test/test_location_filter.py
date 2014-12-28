"""Tests the location Kalman Filter."""

from telemetry import Telemetry
import unittest

from location_filter import LocationFilter

#pylint: disable=protected-access
#pylint: disable=too-many-public-methods


class TestLocationFilter(unittest.TestCase):
    """Tests the location Kalman filter."""

    def test_multiply(self):
        """Test the matrix multiply method."""
        with self.assertRaises(TypeError):
            LocationFilter._multiply(0, 0)

        with self.assertRaises(ValueError):
            LocationFilter._multiply(
                [[1, 1]],
                [[1, 1]]
            )

        with self.assertRaises(ValueError):
            LocationFilter._multiply(
                [[1, 1]],
                [[1, 1], [1, 1], [1, 1]]
            )

        self.assertEqual(
            LocationFilter._multiply(
                [[1, 2]],
                [[2, 3],
                 [5, 8]]
            ),
            [[2 + 10, 3 + 16]]
        )

        self.assertEqual(
            LocationFilter._multiply(
                [[1, 2, 4],
                 [3, 7, 8]],
                [[2, 0, 1, 4, 6],
                 [1, 1, 1, 1, 1],
                 [5, 3, 8, 9, 7]]
            ),
            [[24, 14, 35, 42, 36],
             [53, 31, 74, 91, 81]]
        )

    def test_add(self):
        """test the matrix addition method."""
        with self.assertRaises(TypeError):
            LocationFilter._add(0, 0)

        with self.assertRaises(ValueError):
            LocationFilter._add(
                [[1, 1, 1]],
                [[1, 1]]
            )

        with self.assertRaises(ValueError):
            LocationFilter._add(
                [[1, 1]],
                [[1, 1], [1, 1], [1, 1]]
            )

        self.assertEqual(
            LocationFilter._add(
                [[1, 2]],
                [[3, 0]],
            ),
            [[4, 2]]
        )

        self.assertEqual(
            LocationFilter._add(
                [[1, 2],
                 [3, 0]],
                [[3, 0],
                 [4, 1]]
            ),
            [[4, 2],
             [7, 1]]
        )

    def test_inverse(self):
        """Tests the matrix inverse method."""
        with self.assertRaises(ValueError):
            LocationFilter._inverse(
                [[1, 2, 3],
                 [1, 2, 3],
                 [1, 2, 3]]
            )

        def assert_almost_equal(matrix1, matrix2):
            """Matrix version of unittest.assertAlmostEqual."""
            for row1, row2 in zip(matrix1, matrix2):
                for item1, item2 in zip(row1, row2):
                    self.assertAlmostEqual(item1, item2)

        test = [
            [2, 3, 4, 5],
            [1, 4, 2, 6],
            [4, 2, 8, 5],
            [5, 4, 6, 3]
        ]
        identity = [
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ]
        assert_almost_equal(
            LocationFilter._multiply(
                test,
                LocationFilter._inverse(test)
            ),
            identity
        )
        assert_almost_equal(
            LocationFilter._multiply(
                LocationFilter._inverse(test),
                test
            ),
            identity
        )

    def test_estimate_gps(self):
        """Tests that the estimating of the locations via GPS is sane."""
        # I'm not sure how to independently validate these tests for accuracy.
        # The best I can think of is to do some sanity tests.
        # TODO
        return
        for initial_location in range(0, 360, 30):
            location_filter = LocationFilter(initial_location)

            self.assertEqual(
                location_filter.estimated_location(),
                initial_location
            )

            for location in range(15, 360, 30):
                # Change this just to make stuff converge faster
                location_filter._measurement_noise = [[0.001, 0], [0, 0.001]]

                for _ in range(5):
                    location_filter.update_location(location)
                self.assertAlmostEqual(
                    location_filter.estimated_location(),
                    location,
                    2
                )

    def test_estimate(self):
        """Tests that the estimating of the locations via both is sane."""
        # TODO
        return
        initial_x = 100.0
        initial_y = 1000.0
        location_filter = LocationFilter(initial_x, initial_y)

        self.assertEqual(location_filter.estimated_location(), initial_location)

        update_hz = 10

        # Turn
        location_d_s = 20.0
        turn_time_s = 5
        measurements = [[0.0,], [location_d_s,],]  # z
        location_filter._observer_matrix = [[0, 0], [0, 1]]

        for _ in range(turn_time_s * update_hz):
            location_filter._update(measurements, 1.0 / update_hz)
        self.assertAlmostEqual(
            location_filter.estimated_location(),
            initial_location + location_d_s * turn_time_s,
            2
        )
        # Introduce some error
        actual_location = Telemetry.wrap_degrees(
            initial_location + location_d_s * turn_time_s - 10
        )

        # And now straight
        straight_time_s = 5
        for _ in range(straight_time_s * update_hz):
            # No turn
            measurements = [[0.0,], [0.0,],]  # z
            location_filter._observer_matrix = [[0, 0], [0, 1]]
            location_filter._update(measurements, 1.0 / update_hz)

            # GPS location
            measurements = [[actual_location,], [0.0,],]  # z
            location_filter._observer_matrix = [[1, 0], [0, 0]]
            location_filter._update(measurements, 1.0 / update_hz)

        self.assertAlmostEqual(
            location_filter.estimated_location(),
            actual_location,
            1
        )
