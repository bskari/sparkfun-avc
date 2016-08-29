"""Kalman filter for the location of the vehicle."""

import math
import numpy
import time

# pylint: disable=no-member


class LocationFilter(object):
    """Kalman filter for the location of the vehicle."""
    MAX_SPEED_M_S = 11.0 * 5280 / 60 / 60 / 3.2808399  # 11 MPH

    GPS_OBSERVER_MATRIX = numpy.eye(4)  # H
    # Sometimes the web telemetry doesn't report heading and speed, so these
    # matrices ignore them
    GPS_NO_HEADING_OBSERVER_MATRIX = numpy.matrix([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 1]
    ])
    GPS_NO_SPEED_OBSERVER_MATRIX = numpy.matrix([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 0]
    ])
    GPS_NO_HEADING_SPEED_OBSERVER_MATRIX = numpy.matrix([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0]
    ])
    COMPASS_OBSERVER_MATRIX = numpy.matrix([  # H
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 0]
    ])
    SPEED_ESTIMATION_OBSERVER_MATRIX = numpy.matrix([  # H
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 1]
    ])


    GPS_MEASUREMENT_NOISE = numpy.matrix([  # R
        [0, 0, 0, 0],  # x_m will be filled in by the GPS accuracy
        [0, 0, 0, 0],  # y_m will be filled in by the GPS accuracy
        [0, 0, 5, 0],  # This degrees value is a guess
        [0, 0, 0, MAX_SPEED_M_S * 0.1]  # This speed value is a guess
    ])
    COMPASS_MEASUREMENT_NOISE = numpy.matrix([  # R
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        # This degrees value is a guess. It's kept artificially high because
        # I've observed a lot of local interference as I drove around before.
        [0, 0, 45, 0],
        [0, 0, 0, 0]
    ])
    # From the speed estimation, based on input throttle
    SPEED_ESTIMATION_MEASUREMENT_NOISE = numpy.matrix([  # R
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        # This is just a guess. I don't know if it should be greater or less
        # than the values from the GPS. Presumably the GPS will be more
        # accurate because I'm basing the speed estimations on imprecise
        # observations, but presumably it will take a few GPS measurements
        # before the speed updates, so maybe it will be more accurate at first?
        [0, 0, 0, 2.0]
    ])

    # http://robotsforroboticists.com/kalman-filtering/ is a great reference
    def __init__(self, x_m, y_m, heading_d=None):
        if heading_d is None:
            heading_d = 0.0
        self._estimates = numpy.matrix(
            # x m, y m, heading d, speed m/s
            [x_m, y_m, heading_d, 0.0]
        ).transpose()  # x

        # This will be populated as the filter runs
        # TODO: Ideally, this should be initialized to those values, for right
        # now, identity matrix is fine
        self._covariance_matrix = numpy.matrix([  # P
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ])
        # TODO: Tune this parameter for maximum performance
        self._process_noise = numpy.matrix([  # Q
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ])

        self._last_observation_s = time.time()
        self._estimated_turn_rate_d_s = 0.0

    def update_gps(
            self,
            x_m,
            y_m,
            x_accuracy_m,
            y_accuracy_m,
            heading_d,
            speed_m_s
    ):
        """Update the state estimation using the provided GPS measurement."""
        self.GPS_MEASUREMENT_NOISE[0].itemset(0, x_accuracy_m)
        self.GPS_MEASUREMENT_NOISE[1].itemset(1, y_accuracy_m)

        now = time.time()
        time_diff_s = now - self._last_observation_s
        self._last_observation_s = now

        if heading_d is None:
            if speed_m_s is None:
                matrix = self.GPS_NO_HEADING_SPEED_OBSERVER_MATRIX
            else:
                matrix = self.GPS_NO_HEADING_OBSERVER_MATRIX
        elif speed_m_s is None:
            matrix = self.GPS_NO_SPEED_OBSERVER_MATRIX
        else:
            matrix = self.GPS_OBSERVER_MATRIX

        measurements = numpy.matrix(
            [x_m, y_m, heading_d, speed_m_s]
        ).transpose()  # z

        self._update(
            measurements,
            matrix,
            self.GPS_MEASUREMENT_NOISE,
            time_diff_s
        )

    def update_compass(self, compass_d, confidence):
        """Update the heading estimation."""
        measurements = numpy.matrix(
            [0.0, 0.0, compass_d, 0.0]
        ).transpose()  # z

        now = time.time()
        time_diff_s = now - self._last_observation_s
        self._last_observation_s = now

        self.COMPASS_MEASUREMENT_NOISE[2].itemset(
            2,
            45 + 45 * (1.0 - confidence)
        )
        self._update(
            measurements,
            self.COMPASS_OBSERVER_MATRIX,
            self.COMPASS_MEASUREMENT_NOISE,
            time_diff_s
        )

    def update_dead_reckoning(self):
        """Update the dead reckoning position estimate."""
        now = time.time()
        time_diff_s = now - self._last_observation_s
        self._last_observation_s = now

        self._prediction_step(time_diff_s)

    def manual_throttle(self, speed_m_s):
        """Update the estimated speed based on throttle input."""
        measurements = numpy.matrix(
            [0.0, 0.0, 0.0, speed_m_s]
        ).transpose()  # z

        now = time.time()
        time_diff_s = now - self._last_observation_s
        self._last_observation_s = now

        self._update(
            measurements,
            self.SPEED_ESTIMATION_OBSERVER_MATRIX,
            self.SPEED_ESTIMATION_MEASUREMENT_NOISE,
            time_diff_s
        )

    def manual_steering(self, turn_d_s):
        """Update the estimated turn rate based on steering input."""
        self._estimated_turn_rate_d_s = turn_d_s

    def _update(
            self,
            measurements,
            observer_matrix,
            measurement_noise,
            time_diff_s
    ):
        """Runs the Kalman update using the provided measurements."""
        # Prediction step
        transition = self._prediction_step(time_diff_s)

        # Update uncertainty
        # P = A * P * A' + Q
        self._covariance_matrix = \
            transition * self._covariance_matrix * transition.transpose() \
            + self._process_noise

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

        # Determine innovation or residual and update our estimate
        # x = x + K * (z - H * x)
        zhx = measurements - observer_matrix * self._estimates
        heading_d = zhx[2].item(0)
        while heading_d > 180.0:
            heading_d -= 360.0
        while heading_d <= -180.0:
            heading_d += 360.0
        zhx[2].itemset(0, heading_d)

        self._estimates = self._estimates + kalman_gain * zhx
        from control.telemetry import Telemetry
        heading_d = Telemetry.wrap_degrees(self._estimates[2].item(0))
        self._estimates[2].itemset(0, heading_d)

        # Update the covariance
        # P = (I - K * H) * P
        self._covariance_matrix = (
            numpy.identity(len(kalman_gain)) - kalman_gain * observer_matrix
        ) * self._covariance_matrix

        assert len(self._estimates) == 4 and len(self._estimates[0]) == 1, \
            'Estimates should be size 4x1 but is {}x{} after update'.format(
                len(self._estimates),
                len(self._estimates[0])
            )

    def _prediction_step(self, time_diff_s):
        """Runs the prediction step and returns the transition matrix."""
        # x = A * x + B
        heading_r = math.radians(self.estimated_heading())
        from control.telemetry import Telemetry
        x_delta, y_delta = Telemetry.rotate_radians_clockwise(
            (0.0, time_diff_s),
            heading_r
        )
        speed_m_s = self.estimated_speed()
        transition = numpy.matrix([  # A
            [1.0, 0.0, 0.0, x_delta],
            [0.0, 1.0, 0.0, y_delta],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0]
        ])

        # Update heading estimate based on steering
        new_heading = Telemetry.wrap_degrees(
            self.estimated_heading()
            + self._estimated_turn_rate_d_s * time_diff_s
        )
        self._estimates.itemset(2, new_heading)

        # TODO: Add acceleration values

        self._estimates = transition * self._estimates
        return transition

    def estimated_location(self):
        """Returns the estimated true location in x and y meters."""
        return (self._estimates[0].item(0), self._estimates[1].item(0))

    def estimated_heading(self):
        """Returns the estimated true heading in degrees."""
        return self._estimates[2].item(0)

    def estimated_speed(self):
        """Returns the estimated speed in meters per second."""
        return self._estimates[3].item(0)
