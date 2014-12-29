"""Kalman filter for the location of the vehicle."""

import itertools
import math
import numpy
import sys
import time


class LocationFilter(object):
    """Kalman filter for the location of the vehicle."""
    GPS_OBSERVER_MATRIX = numpy.matrix([  # H
        [1, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0],
        [0, 0, 0, 0, 0, 0]
    ])
    COMPASS_OBSERVER_MATRIX = numpy.matrix([  # H
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0]
    ])

    GPS_MEASUREMENT_NOISE = numpy.matrix([  # R
        [0, 0, 0, 0, 0, 0],  # x_m will be filled in by the GPS accuracy
        [0, 0, 0, 0, 0, 0],  # y_m will be filled in by the GPS accuracy
        [0, 0, 5, 0, 0, 0],
        [0, 0, 0, 10, 0, 0],
        [0, 0, 0, 0, 0.1, 0],
        [0, 0, 0, 0, 0, 0.1]
    ])
    COMPASS_MEASUREMENT_NOISE = numpy.matrix([  # R
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 45, 0, 0, 0],
        [0, 0, 0, 5, 0, 0],
        [0, 0, 0, 0, 1, 0],
        [0, 0, 0, 0, 0, 0.5]
    ])

    MAX_SPEED_M_S = 11.0 * 5280 / 60 / 60 / 3.2808399  # 11 MPH
    # Assume constant acceleration until we hit the target speed
    ACCELERATION_M_S_S = 1.0  # TODO: Take measurements of this

    # http://robotsforroboticists.com/kalman-filtering/ is a great reference
    def __init__(self, x_m, y_m):
        self._estimates = numpy.matrix(
            # x m, y m, heading d, heading delta d/s, speed m/s, acceleration m/s^2
            [x_m, y_m, 0.0, 0.0, 0.0, 0.0]
        ).transpose()  # x

        # This will be populated as the filter runs
        # TODO: Ideally, this should be initialized to those values, for right
        # now, identity matrix is fine.
        self._covariance_matrix = numpy.matrix([  # P
            [1, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0],
            [0, 0, 0, 1, 0, 0],
            [0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 1]
        ])
        # TODO: Tune this parameter for maximum performance
        self._process_noise = numpy.matrix([  # Q
            [1, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0],
            [0, 0, 0, 1, 0, 0],
            [0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 1]
        ])
        self._accelerating = False
        self._acceleration = 0.0
        self._throttle = 0.0

        self._last_observation_s = time.time()

    def update_gps(self, x_m, y_m, x_accuracy_m, y_accuracy_m, heading_d, speed_m_s):
        """Update the state estimation using the provided GPS measurement."""
        measurements = numpy.matrix(
            [x_m, y_m, heading_d, 0.0, speed_m_s, 0.0]
        ).transpose()  # z

        # GPS updates don't rely on time, so ignore time_diff_s
        self.GPS_MEASUREMENT_NOISE[0].itemset(0, x_accuracy_m)
        self.GPS_MEASUREMENT_NOISE[1].itemset(1, y_accuracy_m)
        self._update(
            measurements,
            self.GPS_OBSERVER_MATRIX,
            self.GPS_MEASUREMENT_NOISE,
            0.0
        )

    def update_dead_reckoning(self, compass_d):
        """Update the heading estimation."""
        if self._accelerating:
            # If we've already hit the target speed, then acceleration = 0
            speed = self._estimates[4].item(0)
            target_speed = self._throttle * self.MAX_SPEED_M_S
            if (
                (self._acceleration > 0 and speed >= target_speed)
                or (self._acceleration < 0 and speed <= target_speed)
            ):
                self._accelerating = False
                self._acceleration = 0.0

        # TODO: This should be set according to the turn rate and the speed
        turn_d_s = 0.0

        measurements = numpy.matrix(
            [0.0, 0.0, compass_d, turn_d_s, 0.0, self._acceleration]
        ).transpose()  # z

        now = time.time()
        time_diff_s = now - self._last_observation_s
        self._last_observation_s = now

        self._update(
            measurements,
            self.COMPASS_OBSERVER_MATRIX,
            self.COMPASS_MEASUREMENT_NOISE,
            time_diff_s
        )

    def _update(
        self,
        measurements,
        observer_matrix,
        measurement_noise,
        time_diff_s
    ):
        """Runs the Kalman update using the provided measurements."""
        # Prediction step
        # x = A * x
        speed = self._estimates[5].item(0)
        heading_r = math.radians(self._estimates[2].item(0))
        x_delta = math.sin(heading_r)
        y_delta = math.cos(heading_r)
        transition = numpy.matrix([  # A
            [1.0, 0.0, 0.0, 0.0, x_delta, 0.0],
            [0.0, 1.0, 0.0, 0.0, y_delta, 0.0],
            [0.0, 0.0, 1.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1.0, 1.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
        ])
        self._estimates = transition * self._estimates
        #print('1. A=\n{}'.format(transition))
        #print('   P=\n{}'.format(self._covariance_matrix))
        #print('   x=\n{}'.format(self._estimates))
        #print('2. H=\n{}'.format(observer_matrix))
        #print('   z=\n{}'.format(measurements))
        #print('3. x=\n{}'.format(self._estimates))

        # Update uncertainty
        # P = A * P * A' + Q
        self._covariance_matrix = \
            transition * self._covariance_matrix * transition.transpose() \
            + self._process_noise
        #print('4. P=\n{}'.format(self._covariance_matrix))

        # Compute the Kalman gain
        # K = P * H' * inv(H * P * H' + R)
        hphtr = (
            observer_matrix
            * self._covariance_matrix
            * observer_matrix.transpose()
            + measurement_noise
        )
        try:
            hphtri = hphtr.getI()
        except numpy.linalg.linalg.LinAlgError:
            for diagonal_index in range(len(hphtr)):
                diagonal_value = hphtr[diagonal_index].item(diagonal_index)
                if diagonal_value == 0.0:
                    hphtr[diagonal_index].itemset(diagonal_index, 0.00001)
            hphtri = hphtr.getI()

        kalman_gain = \
                self._covariance_matrix * observer_matrix.transpose() * hphtri
        #print('5. K=\n{}'.format(kalman_gain))

        # Determine innovation or residual and update our estimate
        # x = x + K * (z - H * x)
        zhx = measurements - observer_matrix * self._estimates
        heading = zhx[2].item(0)
        while heading > 180.0:
            heading -= 360.0
        while heading <= -180.0:
            heading += 360.0
        zhx[2].itemset(0, heading)

        self._estimates = self._estimates + kalman_gain * zhx

        #print('6. x=\n{}'.format(self._estimates))

        # Update the covariance
        # P = (I - K * H) * P
        self._covariance_matrix = (
                numpy.identity(6) - kalman_gain * observer_matrix
        ) * self._covariance_matrix
        #print('7. P=\n{}'.format(self._covariance_matrix))

    def estimated_location(self):
        """Returns the estimated true location."""
        return (self._estimates[0].item(0), self._estimates[1].item(0))

    def estimated_heading(self):
        """Returns the estimated true heading."""
        return self._estimates[2][0]
