"""Tests the Kalman Filter."""

import unittest

from kalman_filter import KalmanFilter

#pylint: disable=protected-access
#pylint: disable=too-many-public-methods


class TestKalmanFilter(unittest.TestCase):
    """Tests the Kalman filter."""
    def test_matrix_multiply(self):
        """Tests matrix multiply."""
        matrix1 = [
            [1, 2, 3],
            [2, 3, 4]
        ]
        matrix2 = [
                [1],
                [0],
                [1]
        ]
        multiplied = KalmanFilter._matrix_multiply(matrix1, matrix2)
        self.assertEqual(
            multiplied,
            [
                [4],
                [6]
            ]
        )

    def test_scalar_multiply(self):
        """Tests scalar matrix multiply."""
        matrix1 = [
            [1, 2, 3],
            [4, 5, 6]
        ]
        matrix2 = KalmanFilter._scalar_multiply(3, matrix1)
        self.assertEqual(matrix2,
            [
                [3, 6, 9],
                [12, 15, 18]
            ]
        )

    def test_transpose(self):
        """Tests matrix transpose."""
        self.assertEqual(
            KalmanFilter._transpose(
                [[1, 2, 3]]
            ),
            [[1], [2], [3]]
        )
        self.assertEqual(
            KalmanFilter._transpose(
                [[1], [2], [3]],
            ),
            [[1, 2, 3]]
        )
        self.assertEqual(
            KalmanFilter._transpose(
                [[1, 2], [2, 3], [3, 4]],
            ),
            [[1, 2, 3], [2, 3, 4]]
        )

    def test_estimates(self):
        """Test the estimates of the Kalman filter. Use the gravity example
        provided in Lindsay Kleeman's "Understanding and Applying Kalman
        Filtering".
        """
        #def position_at_time(time):
        #    return 100.0 - 0.5 * (time ** 2.0)

        #def velocity_at_time(time):
        #    return -time

        kalman_filter = KalmanFilter(
            (100,),
            (1, 1)
        )

        expected_estimated_positions = (95.0, 99.63, 98.43, 95.21, 92.35, 87.68)
        expected_estimated_velocities = (1.0, 0.38, -1.16, -2.91, -3.70, -4.84)

        for position_velocity in zip(
            expected_estimated_positions,
            expected_estimated_velocities
        ):
            position, velocity = position_velocity
            estimated_position, estimated_velocity = \
                kalman_filter.predict((100.0,))
            self.assertAlmostEqual(estimated_position, position)
            self.assertAlmostEqual(estimated_velocity, velocity)
