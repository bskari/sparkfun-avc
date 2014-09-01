"""Tests the Kalman Filter."""

import math
import numpy
import operator
import random
import unittest

from kalman_filter import KalmanFilter

#pylint: disable=protected-access
#pylint: disable=too-many-public-methods


class TestKalmanFilter(unittest.TestCase):
    """Tests the Kalman filter."""

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
        for _ in range(100):
            filter_.predict((constant_observation,))
        estimated_voltage = filter_.predict((constant_observation,))[0]
        self.assertAlmostEqual(estimated_voltage, constant_observation)

    def test_cannonball(self):
        """Test the cannonball example from
        http://greg.czerniak.info/guides/kalman1/
        """
        time_slice = 0.1
        process_error_covariances = (
            # Because we created the process, we can assume there is no error
            (0.0, 0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0, 0.0),
        )
        measurement_error_covariances = (
            (0.2, 0.0, 0.0, 0.0),
            (0.0, 0.2, 0.0, 0.0),
            (0.0, 0.0, 0.2, 0.0),
            (0.0, 0.0, 0.0, 0.2),
        )
        transition_matrix = (
            (1.0, time_slice, 0.0, 0.0),
            (0.0, 1.0, 0.0, 0.0),
            (0.0, 0.0, 1.0, time_slice),
            (0.0, 0.0, 0.0, 1.0),
        )
        observation_matrix = (
            (1.0, 0.0, 0.0, 0.0),
            (0.0, 1.0, 0.0, 0.0),
            (0.0, 0.0, 1.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        )
        initial_estimates = (
            0.0,
            100.0 * math.cos(math.pi / 4.0),
            # y should be 0, but we're going to set it way off to show how
            # resilient it is anyway
            500.0,
            100.0 * math.sin(math.pi / 4.0),
        )
        control_matrix = (
            (0.0, 0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0, 0.0),
            (0.0, 0.0, 1.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        )

        filter_ = KalmanFilter(
            transition_matrix,
            observation_matrix,
            initial_estimates,
            numpy.eye(4),
            process_error_covariances,
            measurement_error_covariances,
            control_matrix=control_matrix
        )

        class CannonBall(object):
            ANGLE = 45.0
            MUZZLE_VELOCITY = 100.0
            GRAVITY = [0.0, -9.81]

            def __init__(self, time_slice, noise_level):
                self._time_slice = time_slice
                self._noise_level = noise_level
                self._location = [0.0, 0.0]
                self._velocity = (
                    self.MUZZLE_VELOCITY * math.cos(math.radians(self.ANGLE)),
                    self.MUZZLE_VELOCITY * math.sin(math.radians(self.ANGLE))
                )

            def get_x(self):
                return self._location[0]

            def get_y(self):
                return self._location[1]

            def get_x_with_noise(self):
                return random.gauss(self.get_x(), self._noise_level)

            def get_y_with_noise(self):
                return random.gauss(self.get_y(), self._noise_level)

            def get_x_velocity(self):
                return self._velocity[0]

            def get_y_velocity(self):
                return self._velocity[1]

            # Increment through the next time_slice of the simulation
            def step(self):
                # We're gonna use this vector to timeslice everything
                time_slice_vector = (self._time_slice, self._time_slice)
                # Break gravitational force into a smaller time slice
                sliced_gravity = map(
                    operator.mul,
                    self.GRAVITY,
                    time_slice_vector
                )
                # The only force on the cannonball is gravity
                sliced_acceleration = sliced_gravity
                # Apply the acceleration to velocity
                self._velocity = map(
                    operator.add,
                    self._velocity,
                    sliced_acceleration
                )
                sliced_velocity = map(
                    operator.mul,
                    self._velocity,
                    time_slice_vector
                )
                # Apply the velocity to location
                self._location = map(
                    operator.add,
                    self._location,
                    sliced_velocity
                )
                # Cannonballs shouldn't go into the ground
                if self._location[1] < 0.0:
                    self._location[1] = 0.0

        error = 30.0
        cannon_ball = CannonBall(time_slice, error)
        # The control vector that adds acceleration to the kinematic equations
        # 0          =>  x(n+1) =  x(n+1)
        # 0          => vx(n+1) = vx(n+1)
        # -9.81*ts^2 =>  y(n+1) =  y(n+1) + 0.5*-9.81*ts^2
        # -9.81*ts   => vy(n+1) = vy(n+1) + -9.81*ts
        control_vector = [
            [0],
            [0],
            [0.5 * -9.81 * time_slice * time_slice],
            [-9.81 * time_slice]
        ]
        real_x = []
        real_y = []
        reading_x = []
        reading_y = []
        kalman_x = []
        kalman_y = []
        for _ in range(int(12.0 / time_slice)):
            cannon_ball.step()
            real_x.append(cannon_ball.get_x())
            real_y.append(cannon_ball.get_y())
            reading_x.append(cannon_ball.get_x_with_noise())
            reading_y.append(cannon_ball.get_y_with_noise())
            prediction = filter_.predict(
                (
                    reading_x[-1],
                    cannon_ball.get_x_velocity(),
                    reading_y[-1],
                    cannon_ball.get_y_velocity()
                ),
                control_state=control_vector
            )
            kalman_x.append(prediction[0].item())
            kalman_y.append(prediction[2].item())

        for cannon_x, predicted_x in zip(real_x[-5:], kalman_x[-5:]):
            self.assertTrue(abs(cannon_x - predicted_x) < error)
        for cannon_y, predicted_y in zip(real_y[-5:], kalman_y[-5:]):
            self.assertTrue(abs(cannon_y - predicted_y) < error)

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
            filter_.predict(
                [random.gauss(constant_observation, voltage_error_std_dev)]
            )
        estimated_voltage = filter_.predict((constant_observation,))[0]

        # Because we have a lot of noise, we can't use assertAlmostEqual
        self.assertTrue(constant_observation - voltage_error_std_dev < estimated_voltage)
        self.assertTrue(estimated_voltage < constant_observation + voltage_error_std_dev)

    def test_estimates(self):
        """Test the estimates of the Kalman filter. Use the gravity example
        provided in Lindsay Kleeman's "Understanding and Applying Kalman
        Filtering".
        """
        raise NotImplementedError
        def position_at_time(time):
            return 100.0 - 0.5 * (time ** 2.0)

        def velocity_at_time(time):
            return -time

        initial_estimates = (95.0, 1.0)
        # We don't have an input process
        process_error_covariances = ((0.00001, 0.0), (0.0, 0.00001))
        measurement_error_covariances = ((1.0, 0.0), (0.0, 1.0))
        transition_matrix = ((1.0, 1.0), (0.0, 2.0))
        observation_matrix = ((1.0, 1.0),)

        kalman_filter = KalmanFilter(
            initial_estimates,
            process_error_covariances,
            measurement_error_covariances,
            transition_matrix,
            observation_matrix
        )

        for time in xrange(1, 11):
            print(kalman_filter.predict(
                (position_at_time(time), velocity_at_time(time))
            ))


if __name__ == '__main__':
    unittest.main()
