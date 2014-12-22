"""Kalman filter for the heading of the vehicle."""

import sys
import time

from telemetry import Telemetry


class HeadingFilter(object):
    """Kalman filter for the heading of the vehicle."""

    def __init__(self, initial_heading_d):
        # Heading, heading delta (x)
        self._estimates_d = [[initial_heading_d], [0.0]] # x
        self._observer_matrix = [[1, 0], [0, 1]]  # H
        self._covariance_matrix = [[1000, 0,], [0, 1000]]  # P
        self._measurement_noise = [[3, 0], [0, 0.3]]  # R
        self._process_noise = [[0.01, 0], [0, 0.01]]  # Q
        self._identity = [[1, 0], [0, 1]]

        self._last_observation_s = time.time()

    def update_heading(self, heading_d):
        """Update the state estimation using the provided heading
        measurement.
        """
        measurements = [[heading_d,], [0.0,],]  # z

        # Depending on what sensor measurements we've gotten, switch between
        # observer (H) matrices and measurement noise (R) matrices
        self._observer_matrix = [[1, 0], [0, 0]]

        # GPS updates don't rely on time, so ignore time_diff_s
        self._update(measurements, 0.0)

    def update_heading_delta(self, heading_d_s):
        """Update the state estimation using the provided heading delta per
        second measurement.
        """
        measurements = [[0.0,], [heading_d_s,],]  # z

        # Depending on what sensor measurements we've gotten, switch between
        # observer (H) matrices and measurement noise (R) matrices
        self._observer_matrix = [[0, 0], [0, 1]]

        now = time.time()
        time_diff_s = now - self._last_observation_s
        self._last_observation_s = now

        self._update(measurements, time_diff_s)

    def _update(self, measurements, time_diff_s):
        """Runs the Kalman update using the provided measurements."""
        # Prediction step
        # x = A * x
        transition = [[1.0, time_diff_s], [0.0, 1.0]]  # A
        self._estimates_d = self._multiply(transition, self._estimates_d)
        #print('1. A={}'.format(transition))
        #print('   P={}'.format(self._covariance_matrix))
        #print('   x={}'.format(self._estimates_d))
        #print('2. H={}'.format(self._observer_matrix))
        #print('   z={}'.format(measurements))
        #print('3. x={}'.format(self._estimates_d))

        # Update uncertainty
        # P = A * P * A' + Q
        transition_t = self._transpose(transition)  # A'
        self._covariance_matrix = self._add(
            self._multiply(
                self._multiply(transition, self._covariance_matrix),
                transition_t
            ),
            self._process_noise
        )
        #print('4. P={}'.format(self._covariance_matrix))

        # Compute the Kalman gain
        # K = P * H' * inv(H * P * H' + R)
        observer_matrix_t = self._transpose(self._observer_matrix)
        kalman_gain = \
            self._multiply(
                self._multiply(
                    self._covariance_matrix,  # P
                    observer_matrix_t  # H'
                ),
                self._inverse(
                    self._add(
                        self._multiply(
                            self._multiply(
                                self._observer_matrix,  # H
                                self._covariance_matrix  # P
                            ),
                            observer_matrix_t  # H'
                        ),
                        self._measurement_noise  # R
                    )
                )
            )
        #print('5. K={}'.format(kalman_gain))

        # Determine innovation or residual and update our estimate
        # x = x + K * (z - H * x)
        h_mult_x = self._multiply(self._observer_matrix, self._estimates_d)
        negative_h_mult_x = [
            [-value for value in row]
            for row in h_mult_x
        ]
        zhx = self._add(
            measurements,
            negative_h_mult_x
        )
        if zhx[0][0] > 180.0:
            zhx[0][0] -= 360.0
        elif zhx[0][0] <= -180.0:
            zhx[0][0] += 360.0
        #print('6. zhx={}'.format(zhx))

        self._estimates_d = \
            self._add(
                self._estimates_d,
                self._multiply(
                    kalman_gain,
                    zhx
                )
            )

        #print('6. x={}'.format(self._estimates_d))

        # Update the covariance
        # P = (I - K * H) * P
        k_mult_h = self._multiply(kalman_gain, self._observer_matrix)
        negative_k_mult_h = [
            [-value for value in row]
            for row in k_mult_h
        ]
        self._covariance_matrix = self._multiply(
            self._add(
                self._identity,
                negative_k_mult_h
            ),
            self._covariance_matrix
        )
        #print('7. P={}'.format(self._covariance_matrix))

    def estimated_heading(self):
        """Returns the estimated true heading."""
        return Telemetry.wrap_degrees(self._estimates_d[0][0])

    @staticmethod
    def _dimensions(matrix):
        """Returns the dimensions of a matrix."""
        size1 = len(matrix)
        size2 = len(matrix[0])
        return (size1, size2)

    @staticmethod
    def _multiply(matrix1, matrix2):
        """Multiplies two matrices."""

        if (
            HeadingFilter._dimensions(matrix1)[1]
            != HeadingFilter._dimensions(matrix2)[0]
        ):
            raise ValueError(
                'Mismatched matrices: {} * {}'.format(matrix1, matrix2)
            )

        out = []
        for row in range(HeadingFilter._dimensions(matrix1)[0]):
            out.append([])
            for column in range(HeadingFilter._dimensions(matrix2)[1]):
                out[-1].append(0.0)
                for i in range(HeadingFilter._dimensions(matrix1)[1]):
                    out[-1][-1] += matrix1[row][i] * matrix2[i][column]
        return out

    @staticmethod
    def _add(matrix1, matrix2):
        """Adds two matrices."""
        if (
            HeadingFilter._dimensions(matrix1)
            != HeadingFilter._dimensions(matrix2)
        ):
            raise ValueError(
                'Mismatched matrices: {} * {}'.format(matrix1, matrix2)
            )

        dim = HeadingFilter._dimensions(matrix1)
        return [
            [
                matrix1[row][column] + matrix2[row][column]
                for column in range(dim[1])
            ]
            for row in range(dim[0])
        ]

    @staticmethod
    def _inverse(matrix):
        """Inverts a matrix."""
        dim = HeadingFilter._dimensions(matrix)
        if dim[0] != dim[1] or dim[1] != 2:
            raise ValueError('Only 2x2 matrices supported')

        determinant = float(
            matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]
        )
        return [
            [matrix[1][1] / determinant, -matrix[0][1] / determinant],
            [-matrix[1][0] / determinant, matrix[0][0] / determinant]
        ]

    @staticmethod
    def _transpose(matrix):
        """Transposes a matrix."""
        dim = HeadingFilter._dimensions(matrix)
        if dim[0] != dim[1] or dim[1] != 2:
            raise ValueError('Only 2x2 matrices supported')

        if sys.version_info.major == 3:
            new_matrix = matrix.copy()
        else:
            import copy
            new_matrix = copy.deepcopy(matrix)
        new_matrix[0][1], new_matrix[1][0] = new_matrix[1][0], new_matrix[0][1]
        return new_matrix
