"""Kalman filter for the location of the vehicle."""

import itertools
import sys
import time


class LocationFilter(object):
    """Kalman filter for the location of the vehicle."""

    # http://robotsforroboticists.com/kalman-filtering/ is a great reference
    def __init__(self, x_m, y_m):
        # x meters, y meters
        # x m, y m, x delta_m_s, y delta_m_s
        self._estimates = [[x_m], [y_m], [0.0], [0.0]]  # x
        self._observer_matrix = [  # H
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ]
        # This will be populated as the filter runs
        # TODO: Ideally, this should be initialized to those values, for
        # right now, identity matrix is fine.
        self._covariance_matrix = [  # P
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ]
        self._measurement_noise = [  # R
            [2.0, 0.0, 0.0, 0.0],
            [0.0, 2.0, 0.0, 0.0],
            [0.0, 0.0, 0.1, 0.0],
            [0.0, 0.0, 0.0, 0.1]
        ]
        self._process_noise = [  # Q
            [0.1, 0.0, 0.0, 0.0],
            [0.0, 0.1, 0.0, 0.0],
            [0.0, 0.0, 0.1, 0.0],
            [0.0, 0.0, 0.0, 0.1],
        ]
        self._identity = [
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ]

        self._last_observation_s = time.time()

    def update_location(self, x_meters, y_meters):
        """Update the state estimation using the provided GPS measurement."""
        measurements = [[x_meters], [y_meters], [0.0], [0.0]]  # z

        # Depending on what sensor measurements we've gotten, switch between
        # observer (H) matrices and measurement noise (R) matrices
        self._observer_matrix = [
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0]
        ]

        # GPS updates don't rely on time, so ignore time_diff_s
        self._update(measurements, 0.0)

    def update_location_delta(self, delta_x_m_s, delta_y_m_s):
        """Update the state estimation using the provided location delta
        per second measurement.
        """
        measurements = [[0.0], [0.0], [delta_x_m_s], [delta_y_m_s]]  # z

        # Depending on what sensor measurements we've gotten, switch between
        # observer (H) matrices and measurement noise (R) matrices
        self._observer_matrix = [
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ]

        now = time.time()
        time_diff_s = now - self._last_observation_s
        self._last_observation_s = now

        self._update(measurements, time_diff_s)

    def _update(self, measurements, time_diff_s):
        """Runs the Kalman update using the provided measurements."""
        # Prediction step
        # x = A * x
        transition = [  # A
            [1.0, 0.0, time_diff_s, 0.0],
            [0.0, 1.0, 0.0, time_diff_s],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
        self._estimates = self._multiply(transition, self._estimates)
        #print('1. A={}'.format(transition))
        #print('   P={}'.format(self._covariance_matrix))
        #print('   x={}'.format(self._estimates))
        #print('2. H={}'.format(self._observer_matrix))
        #print('   z={}'.format(measurements))
        #print('3. x={}'.format(self._estimates))

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
        h_mult_x = self._multiply(self._observer_matrix, self._estimates)
        negative_h_mult_x = [
            [-value for value in row]
            for row in h_mult_x
        ]
        zhx = self._add(
            measurements,
            negative_h_mult_x
        )
        #print('6. zhx={}'.format(zhx))

        self._estimates = \
            self._add(
                self._estimates,
                self._multiply(
                    kalman_gain,
                    zhx
                )
            )

        #print('6. x={}'.format(self._estimates))

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

    def estimated_location(self):
        """Returns the estimated true location."""
        return (self._estimates[0][0], self._estimates[1][1])

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
            LocationFilter._dimensions(matrix1)[1]
            != LocationFilter._dimensions(matrix2)[0]
        ):
            raise ValueError(
                'Mismatched matrices: {} * {}'.format(matrix1, matrix2)
            )

        out = []
        for row in range(LocationFilter._dimensions(matrix1)[0]):
            out.append([])
            for column in range(LocationFilter._dimensions(matrix2)[1]):
                out[-1].append(0.0)
                for i in range(LocationFilter._dimensions(matrix1)[1]):
                    out[-1][-1] += matrix1[row][i] * matrix2[i][column]
        return out

    @staticmethod
    def _add(matrix1, matrix2):
        """Adds two matrices."""
        if (
            LocationFilter._dimensions(matrix1)
            != LocationFilter._dimensions(matrix2)
        ):
            raise ValueError(
                'Mismatched matrices: {} * {}'.format(matrix1, matrix2)
            )

        dim = LocationFilter._dimensions(matrix1)
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
        dim = LocationFilter._dimensions(matrix)
        if dim[0] != dim[1] or dim[1] != 4:
            raise ValueError('Only 4x4 matrices supported')

        m = list(itertools.chain.from_iterable(matrix))  # pylint: disable=invalid-name
        inv = [0] * 16

        inv[0] = m[5]  * m[10] * m[15] - \
                 m[5]  * m[11] * m[14] - \
                 m[9]  * m[6]  * m[15] + \
                 m[9]  * m[7]  * m[14] + \
                 m[13] * m[6]  * m[11] - \
                 m[13] * m[7]  * m[10]

        inv[4] = -m[4]  * m[10] * m[15] + \
                  m[4]  * m[11] * m[14] + \
                  m[8]  * m[6]  * m[15] - \
                  m[8]  * m[7]  * m[14] - \
                  m[12] * m[6]  * m[11] + \
                  m[12] * m[7]  * m[10]

        inv[8] = m[4]  * m[9] * m[15] - \
                 m[4]  * m[11] * m[13] - \
                 m[8]  * m[5] * m[15] + \
                 m[8]  * m[7] * m[13] + \
                 m[12] * m[5] * m[11] - \
                 m[12] * m[7] * m[9]

        inv[12] = -m[4]  * m[9] * m[14] + \
                   m[4]  * m[10] * m[13] + \
                   m[8]  * m[5] * m[14] - \
                   m[8]  * m[6] * m[13] - \
                   m[12] * m[5] * m[10] + \
                   m[12] * m[6] * m[9]

        inv[1] = -m[1]  * m[10] * m[15] + \
                  m[1]  * m[11] * m[14] + \
                  m[9]  * m[2] * m[15] - \
                  m[9]  * m[3] * m[14] - \
                  m[13] * m[2] * m[11] + \
                  m[13] * m[3] * m[10]

        inv[5] = m[0]  * m[10] * m[15] - \
                 m[0]  * m[11] * m[14] - \
                 m[8]  * m[2] * m[15] + \
                 m[8]  * m[3] * m[14] + \
                 m[12] * m[2] * m[11] - \
                 m[12] * m[3] * m[10]

        inv[9] = -m[0]  * m[9] * m[15] + \
                  m[0]  * m[11] * m[13] + \
                  m[8]  * m[1] * m[15] - \
                  m[8]  * m[3] * m[13] - \
                  m[12] * m[1] * m[11] + \
                  m[12] * m[3] * m[9]

        inv[13] = m[0]  * m[9] * m[14] - \
                  m[0]  * m[10] * m[13] - \
                  m[8]  * m[1] * m[14] + \
                  m[8]  * m[2] * m[13] + \
                  m[12] * m[1] * m[10] - \
                  m[12] * m[2] * m[9]

        inv[2] = m[1]  * m[6] * m[15] - \
                 m[1]  * m[7] * m[14] - \
                 m[5]  * m[2] * m[15] + \
                 m[5]  * m[3] * m[14] + \
                 m[13] * m[2] * m[7] - \
                 m[13] * m[3] * m[6]

        inv[6] = -m[0]  * m[6] * m[15] + \
                  m[0]  * m[7] * m[14] + \
                  m[4]  * m[2] * m[15] - \
                  m[4]  * m[3] * m[14] - \
                  m[12] * m[2] * m[7] + \
                  m[12] * m[3] * m[6]

        inv[10] = m[0]  * m[5] * m[15] - \
                  m[0]  * m[7] * m[13] - \
                  m[4]  * m[1] * m[15] + \
                  m[4]  * m[3] * m[13] + \
                  m[12] * m[1] * m[7] - \
                  m[12] * m[3] * m[5]

        inv[14] = -m[0]  * m[5] * m[14] + \
                   m[0]  * m[6] * m[13] + \
                   m[4]  * m[1] * m[14] - \
                   m[4]  * m[2] * m[13] - \
                   m[12] * m[1] * m[6] + \
                   m[12] * m[2] * m[5]

        inv[3] = -m[1] * m[6] * m[11] + \
                  m[1] * m[7] * m[10] + \
                  m[5] * m[2] * m[11] - \
                  m[5] * m[3] * m[10] - \
                  m[9] * m[2] * m[7] + \
                  m[9] * m[3] * m[6]

        inv[7] = m[0] * m[6] * m[11] - \
                 m[0] * m[7] * m[10] - \
                 m[4] * m[2] * m[11] + \
                 m[4] * m[3] * m[10] + \
                 m[8] * m[2] * m[7] - \
                 m[8] * m[3] * m[6]

        inv[11] = -m[0] * m[5] * m[11] + \
                   m[0] * m[7] * m[9] + \
                   m[4] * m[1] * m[11] - \
                   m[4] * m[3] * m[9] - \
                   m[8] * m[1] * m[7] + \
                   m[8] * m[3] * m[5]

        inv[15] = m[0] * m[5] * m[10] - \
                  m[0] * m[6] * m[9] - \
                  m[4] * m[1] * m[10] + \
                  m[4] * m[2] * m[9] + \
                  m[8] * m[1] * m[6] - \
                  m[8] * m[2] * m[5]

        determinant = m[0] * inv[0] + m[1] * inv[4] \
            + m[2] * inv[8] + m[3] * inv[12]

        if determinant == 0:
            raise ZeroDivisionError('Determinant is 0')

        determinant = 1.0 / determinant

        inverse = []
        for i in range(0, 4):
            inverse.append([])
            for j in range(0, 4):
                inverse[-1].append(inv[i * 4 + j] * determinant)
        return inverse

    @staticmethod
    def _transpose(matrix):
        """Transposes a matrix."""
        dim = LocationFilter._dimensions(matrix)
        if dim[0] != dim[1] or dim[1] != 4:
            raise ValueError('Only 4x4 matrices supported')

        if sys.version_info.major == 3:
            new_matrix = matrix.copy()
        else:
            import copy
            new_matrix = copy.deepcopy(matrix)
        for p_1 in range(len(matrix)):
            for p_2 in range(len(matrix)):
                if p_1 == p_2:
                    continue
                new_matrix[p_1][p_2], new_matrix[p_2][p_1] = \
                        new_matrix[p_2][p_1], new_matrix[p_1][p_2]
        return new_matrix
