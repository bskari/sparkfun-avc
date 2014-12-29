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
        for coordinates in ((100, 50), (200, 500)):
            location_filter = LocationFilter(coordinates[0], coordinates[1])

            self.assertEqual(
                location_filter.estimated_location(),
                coordinates
            )

            new_location = (150, 300)

            # Change this just to make stuff converge faster
            location_filter._measurement_noise = [
                [0.01, 0.0, 0.0, 0.0],
                [0.0, 0.01, 0.0, 0.0],
                [0.0, 0.0, 0.1, 0.0],
                [0.0, 0.0, 0.0, 0.1]
            ]
            for _ in range(5):
                location_filter.update_location(
                    new_location[0],
                    new_location[1]
                )
            for estimated, expected in zip(
                location_filter.estimated_location(),
                new_location
            ):
                self.assertAlmostEqual(estimated, expected, 2)

    def test_estimate_dead_reckoning(self):
        """Tests that the estimating of the locations via dead reckoning is sane."""
        # I'm not sure how to independently validate these tests for accuracy.
        # The best I can think of is to do some sanity tests.
        start_coordinates = (100, 100)
        location_filter = LocationFilter(
            start_coordinates[0],
            start_coordinates[1]
        )

        self.assertEqual(
            location_filter.estimated_location(),
            start_coordinates
        )

        new_location = (150, 300)

        # Change this just to make stuff converge faster
        location_filter._measurement_noise = [
            [0.01, 0.0, 0.0, 0.0],
            [0.0, 0.01, 0.0, 0.0],
            [0.0, 0.0, 0.1, 0.0],
            [0.0, 0.0, 0.0, 0.1]
        ]
        for _ in range(5):
            location_filter.update_location(
                new_location[0],
                new_location[1]
            )
        for estimated, expected in zip(
            location_filter.estimated_location(),
            new_location
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

        for seconds in range(1, 5):
            measurements = [[0.0], [0.0], [delta_m_s], [delta_m_s]]
            location_filter._update(measurements, 1.0)
            for index in range(2):
                self.assertAlmostEqual(
                    location_filter.estimated_location()[index],
                    initial_location[index] + seconds * delta_m_s,
                    2
                )
