"""Tests the heading Kalman Filter."""

from telemetry import Telemetry
import unittest

from heading_filter import HeadingFilter

#pylint: disable=protected-access
#pylint: disable=too-many-public-methods


class TestHeadingFilter(unittest.TestCase):
    """Tests the heading Kalman filter."""

    def test_multiply(self):
        """Test the matrix multiply method."""
        with self.assertRaises(TypeError):
            HeadingFilter._multiply(0, 0)

        with self.assertRaises(ValueError):
            HeadingFilter._multiply(
                [[1, 1]],
                [[1, 1]]
            )

        with self.assertRaises(ValueError):
            HeadingFilter._multiply(
                [[1, 1]],
                [[1, 1], [1, 1], [1, 1]]
            )

        self.assertEqual(
            HeadingFilter._multiply(
                [[1, 2]],
                [[2, 3],
                 [5, 8]]
            ),
            [[2 + 10, 3 + 16]]
        )

        self.assertEqual(
            HeadingFilter._multiply(
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
            HeadingFilter._add(0, 0)

        with self.assertRaises(ValueError):
            HeadingFilter._add(
                [[1, 1, 1]],
                [[1, 1]]
            )

        with self.assertRaises(ValueError):
            HeadingFilter._add(
                [[1, 1]],
                [[1, 1], [1, 1], [1, 1]]
            )

        self.assertEqual(
            HeadingFilter._add(
                [[1, 2]],
                [[3, 0]],
            ),
            [[4, 2]]
        )

        self.assertEqual(
            HeadingFilter._add(
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
            HeadingFilter._inverse(
                [[1, 2, 3],
                 [1, 2, 3],
                 [1, 2, 3]]
            )

        def assert_almost_equal(matrix1, matrix2):
            """Matrix version of unittest.assertAlmostEqual."""
            for row1, row2 in zip(matrix1, matrix2):
                for item1, item2 in zip(row1, row2):
                    self.assertAlmostEqual(item1, item2)

        test = [[2, 3],
                [1, 4]]
        identity = [[1, 0],
                    [0, 1]]
        assert_almost_equal(
            HeadingFilter._multiply(
                test,
                HeadingFilter._inverse(test)
            ),
            identity
        )
        assert_almost_equal(
            HeadingFilter._multiply(
                HeadingFilter._inverse(test),
                test
            ),
            identity
        )

    def test_estimate_gps(self):
        """Tests that the estimating of the headings via GPS is sane."""
        # I'm not sure how to independently validate these tests for accuracy.
        # The best I can think of is to do some sanity tests.
        for initial_heading in range(0, 360, 30):
            heading_filter = HeadingFilter(initial_heading)

            self.assertEqual(
                heading_filter.estimated_heading(),
                initial_heading
            )

            for heading in range(15, 360, 30):
                # Change this just to make stuff converge faster
                heading_filter._measurement_noise = [[0.001, 0], [0, 0.001]]

                for _ in range(5):
                    heading_filter.update_heading(heading)
                self.assertAlmostEqual(
                    heading_filter.estimated_heading(),
                    heading,
                    2
                )

    def test_estimate_gps_rollover(self):
        """Tests that the estimation moves in the right direction around the
        0-360 rollover boundary.
        """
        # We also need to make sure that the estimation 'rolls over', i.e.
        # if we're at 350 degrees and start feeding it 10 degree measurements,
        # it increases instead of going down
        for initial_heading, measurement in ((350, 10), (10, 350)):
            heading_filter = HeadingFilter(initial_heading)
            heading_filter.update_heading(measurement)
            self.assertTrue(
                (
                    heading_filter.estimated_heading() > initial_heading
                    or heading_filter.estimated_heading() < measurement
                ),
                '{low} < {heading} < {high} but should not be'.format(
                    low=measurement,
                    heading=heading_filter.estimated_heading(),
                    high=initial_heading
                )
            )

    def test_estimate_turn(self):
        """Tests that the estimating of the headings via turning is sane."""
        # I'm not sure how to independently validate these tests for accuracy.
        # The best I can think of is to do some sanity tests.
        initial_heading = 100.0

        for heading_d_s in (1.0, -1.0):
            heading_filter = HeadingFilter(initial_heading)
            self.assertEqual(
                heading_filter.estimated_heading(),
                initial_heading
            )

            measurements = [[0.0,], [heading_d_s,],]  # z
            heading_filter._observer_matrix = [[0, 0], [0, 1]]

            updates = 20
            tick = 0.5
            for _ in range(updates):
                heading_filter._update(measurements, tick)
            self.assertAlmostEqual(
                heading_filter.estimated_heading(),
                initial_heading + heading_d_s * updates * tick,
                3
            )

    def test_estimate_turn_rollover(self):
        """Tests that the estimation moves in the right direction around the
        0-360 rollover boundary.
        """
        # We also need to make sure that the estimation 'rolls over', i.e.  if
        # we're at 350 degrees and start turning right, it increases instead of
        # going down
        for initial_heading, d_per_s in ((350, 1), (10, -1)):
            heading_filter = HeadingFilter(initial_heading)
            self.assertEqual(
                heading_filter.estimated_heading(),
                initial_heading
            )

            measurements = [[0.0,], [d_per_s,],]  # z
            heading_filter._observer_matrix = [[0, 0], [0, 1]]

            updates = 21  # Avoid 20 so we don't deal with 0-360 boundary
            tick = 0.5
            for _ in range(updates):
                heading_filter._update(measurements, tick)
            self.assertAlmostEqual(
                heading_filter.estimated_heading(),
                Telemetry.wrap_degrees(
                    initial_heading + d_per_s * updates * tick
                ),
                3
            )

    def test_estimate(self):
        """Tests that the estimating of the headings via both is sane."""
        # Scenario: turning with an estimated turn rate for 5 seconds, then
        # driving straight and getting GPS heading readings
        initial_heading = 100.0
        heading_filter = HeadingFilter(initial_heading)

        self.assertEqual(heading_filter.estimated_heading(), initial_heading)

        update_hz = 10

        # Turn
        heading_d_s = 20.0
        turn_time_s = 5
        measurements = [[0.0,], [heading_d_s,],]  # z
        heading_filter._observer_matrix = [[0, 0], [0, 1]]

        for _ in range(turn_time_s * update_hz):
            heading_filter._update(measurements, 1.0 / update_hz)
        self.assertAlmostEqual(
            heading_filter.estimated_heading(),
            initial_heading + heading_d_s * turn_time_s,
            2
        )
        # Introduce some error
        actual_heading = Telemetry.wrap_degrees(
            initial_heading + heading_d_s * turn_time_s - 10
        )

        # And now straight
        straight_time_s = 5
        for _ in range(straight_time_s * update_hz):
            # No turn
            measurements = [[0.0,], [0.0,],]  # z
            heading_filter._observer_matrix = [[0, 0], [0, 1]]
            heading_filter._update(measurements, 1.0 / update_hz)

            # GPS heading
            measurements = [[actual_heading,], [0.0,],]  # z
            heading_filter._observer_matrix = [[1, 0], [0, 0]]
            heading_filter._update(measurements, 1.0 / update_hz)

        self.assertAlmostEqual(
            heading_filter.estimated_heading(),
            actual_heading,
            1
        )
