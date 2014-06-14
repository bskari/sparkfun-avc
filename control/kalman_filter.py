"""Kalman filter, used to estimate the true values from noisy sensor data."""

class KalmanFilter(object):
    """Kalman filter, used to estimate the true values from noisy sensor
    data.
    """
    def __init__(
        self,
        initial_estimates,
        covariances,
        transition_matrix,
        update_matrix,
        initial_time
    ):
        self._estimates = initial_estimates
        self._covariances = covariances
        self._transition_matrix = transition_matrix
        self._update_matrix = self._transpose(update_matrix)
        self._last_time = initial_time

    def predict(self, estimates, absolute_time):
        """Returns a prediction of the values."""
        assert len(estimates) == len(self._estimates)
        time_diff = self._last_time - absolute_time
        self._estimates = \
            self._matrix_multiply(self._transition_matrix, estimates) \
            + self._update_matrix * time_diff

    def error_estimates(self):
        return [0.0]

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
