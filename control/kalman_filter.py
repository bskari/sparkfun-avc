"""Kalman filter, used to estimate the true values from noisy sensor data."""
import collections

class KalmanFilter(object):
    """Kalman filter, used to estimate the true values from noisy sensor
    data.
    """
    def __init__(
        self,
        initial_estimates,
        process_error_covariances,
        measurement_error_covariances,
        transition_matrix,
        observation_matrix,
        initial_time=None,
        control_matrix=None
    ):
        self._estimates = self._to_matrix(initial_estimates)
        self._process_error_covariances = self._to_matrix(
            process_error_covariances
        )
        self._measurement_error_covariances = self._to_matrix(
            measurement_error_covariances
        )
        self._transition_matrix = transition_matrix
        self._observation_matrix = observation_matrix
        if initial_time is None:
            initial_time = 0.0
        else:
            self._last_time = initial_time
        self._control_matrix = control_matrix

    def predict(self, measurements, control_state=None):
        """Returns a prediction of the values."""
        measurements = self._to_matrix(measurements)

        predicted_state = self._matrix_multiply(
            self._transition_matrix,
            self._estimates
        )
        if self._control_matrix is not None:
            assert control_state is not None
            predicted_state = self._add(
                predicted_state,
                self._matrix_multiply(
                    self._control_matrix,
                    control_state
                )
            )

        predicted_covariance = self._add(
            self._matrix_multiply(
                self._matrix_multiply(
                    self._transition_matrix,
                    self._measurement_error_covariances
                ),
                self._transpose(self._transition_matrix)
            ),
            self._process_error_covariances
        )

        innovation = self._subtract(
            measurements,
            self._matrix_multiply(
                self._observation_matrix,
                predicted_state
            )
        )

        innovation_covariance = self._add(
            self._matrix_multiply(
                self._matrix_multiply(
                    self._observation_matrix,
                    predicted_covariance
                ),
                self._transpose(self._observation_matrix)
            ),
            self._measurement_error_covariances
        )

        kalman_gain = self._matrix_multiply(
            self._matrix_multiply(
                predicted_covariance,
                self._transpose(self._observation_matrix)
            ),
            self._inverse(innovation_covariance)
        )

        self._estimates = self._add(
            predicted_state,
            self._matrix_multiply(
                kalman_gain,
                innovation
            )
        )

        self._process_error_covariances = self._matrix_multiply(
            self._subtract(
                self._identity(len(kalman_gain)),
                self._matrix_multiply(
                    kalman_gain,
                    self._observation_matrix
                )
            ),
            predicted_covariance
        )

        return self._estimates[0]

    @staticmethod
    def _matrix_multiply(matrix1, matrix2):
        """Multiplies two matrices."""
        assert len(matrix1[0]) == len(matrix2)
        result = []
        for row in range(len(matrix1)):
            sum_ = 0.0
            result_column = []
            for column in range(len(matrix2[0])):
                for index in range(len(matrix1[0])):
                    value1 = matrix1[row][index]
                    value2 = matrix2[index][column]
                    sum_ += value1 * value2
                result_column.append(sum_)
            result.append(result_column)
        return result

    @staticmethod
    def _scalar_multiply(scalar, matrix):
        """Multiplies a matrix by a scalar value."""
        return_value = []
        for row in matrix:
            return_value.append([])
            for value in row:
                return_value[-1].append(scalar * value)
        return return_value

    @staticmethod
    def _transpose(matrix):
        """Transposes a matrix."""
        return_value = []
        for column in range(len(matrix[0])):
            return_row = []
            for row in range(len(matrix)):
                return_row.append(matrix[row][column])
            return_value.append(return_row)
        return return_value

    @staticmethod
    def _add(matrix1, matrix2):
        """Adds two matrices."""
        matrix = []
        for row_index in range(len(matrix1)):
            matrix.append([])
            for column_index in range(len(matrix1[row_index])):
                matrix[column_index].append(
                    matrix1[column_index][row_index] +
                    matrix2[column_index][row_index]
                )
        return matrix

    @staticmethod
    def _subtract(matrix1, matrix2):
        """Subtracts two matrices."""
        return KalmanFilter._add(
            matrix1,
            KalmanFilter._scalar_multiply(
                -1.0,
                matrix2
            )
        )

    @staticmethod
    def _determinant(matrix):
        """Calculates the determinant of a matrix."""
        m = matrix
        if len(m) == 1:
            return m[0][0]
        if len(m) == 2:
            return m[0][0] * m[1][1] - m[0][1] * m[1][0]
        sub_arrays = []
        for array in range(len(m)):
            sub_arrays.append([])
            for row in range(1, len(m)):
                sub_arrays[array].append(m[row][:array] + m[row][array + 1:])
        sum_ = 0.0
        add_or_subtract = 1
        for i in range(len(sub_arrays)):
            sum_ += add_or_subtract * m[0][i] * KalmanFilter._determinant(sub_arrays[i])
            add_or_subtract *= -1
        return sum_

    @staticmethod
    def _inverse(matrix):
        """Inverts a matrix."""
        m = matrix
        if len(m) == 1:
            return ((1.0 / m[0][0],),)
        if len(m) == 2:
            determinant = self._determinant(m)
            return_value = [
                [m[1][1], -m[0][1]],
                [-m[1][0], m[0][0]]
            ]
            return KalmanFilter._scalar_multiply(
                1.0 / determinant,
                return_value
            )
        raise NotImplementedError(
            'Inverse only supported for 1x1 and 2x2 matrices'
        )

    @staticmethod
    def _identity(size):
        """Returns an identity matrix."""
        matrix = []
        for index in range(size):
            matrix.append([0.0] * size)
            matrix[-1][index] = 1.0
        return matrix

    @staticmethod
    def _to_matrix(vector_or_matrix):
        if isinstance(vector_or_matrix[0], collections.Iterable):
            return vector_or_matrix
        return (vector_or_matrix,)
