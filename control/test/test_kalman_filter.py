"""Tests the Kalman Filter."""

import random
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
        self.assertEqual(
            matrix2,
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

    def test_determinant(self):
        """Tests matrix determinant."""
        self.assertEqual(KalmanFilter._determinant([[2]]), 2)
        self.assertEqual(KalmanFilter._determinant([[3, 8], [4, 6]]), -14)
        self.assertEqual(
            KalmanFilter._determinant(
                [
                    [6, 1, 1],
                    [4, -2, 5],
                    [2, 8, 7],
                ]
            ),
            -306
        )
        self.assertEqual(
            KalmanFilter._determinant(
                [
                    [3, 0, 2, -1],
                    [1, 2, 0, -2],
                    [4, 0, 6, -3],
                    [5, 0, 2, 0],
                ]
            ),
            20
        )

    def test_linear_estimates_constant_observation(self):
        """Test the estimates of the Kalman filter. Use the voltage example
        from http://bilgin.esme.org/BitsBytes/KalmanFilterforDummies.aspx .
        """
        constant_observation = 1.0

        process_error_covariances = (0.0001,)  # We don't have an input process
        measurement_error_covariances = (0.1,)
        transition_matrix = ((1.0,),)  # Voltage(t) = Voltage(t-1)
        observation_matrix = ((1.0,),)
        # We'll purposely set this high to show how resilient the filter is
        initial_estimates = (3.0 * constant_observation,)

        filter_ = KalmanFilter(
            initial_estimates,
            process_error_covariances,
            measurement_error_covariances,
            transition_matrix,
            observation_matrix
        )
        # Feed it constant values
        for _ in range(20):
            filter_.predict((constant_observation,))
        estimated_voltage = filter_.predict((constant_observation,))[0]
        self.assertAlmostEqual(estimated_voltage, constant_observation)

    def test_linear_estimates_normal_observation(self):
        """Test the estimates of the Kalman filter with noisy readings. Use the
        voltage example from
        http://bilgin.esme.org/BitsBytes/KalmanFilterforDummies.aspx .
        """
        constant_observation = 1.0
        voltage_error_std_dev = 0.1

        process_error_covariances = (0.0001,)  # We don't have an input process
        measurement_error_covariances = (voltage_error_std_dev,)
        transition_matrix = ((1.0,),)  # Voltage(t) = Voltage(t-1)
        observation_matrix = ((1.0,),)
        # We'll purposely set this high to show how resilient the filter is
        initial_estimates = (3.0 * constant_observation,)

        filter_ = KalmanFilter(
            initial_estimates,
            process_error_covariances,
            measurement_error_covariances,
            transition_matrix,
            observation_matrix
        )
        # Feed it values with normal error
        for _ in range(20):
            filter_.predict((random.gauss(constant_observation, voltage_error_std_dev),))
        estimated_voltage = filter_.predict((constant_observation,))[0]

        # Because we have a lot of noise, we can't use assertAlmostEqual
        self.assertTrue(constant_observation - voltage_error_std_dev < estimated_voltage)
        self.assertTrue(estimated_voltage < constant_observation + voltage_error_std_dev)

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


if __name__ == '__main__':
    unittest.main()
