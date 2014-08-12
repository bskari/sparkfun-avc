"""Kalman filter, used to estimate the true values from noisy sensor data."""
import collections
import numpy


class KalmanFilter(object):
    """Kalman filter, used to estimate the true values from noisy sensor
    data.
    """
    def __init__(
        self,
        initial_estimates,  # Z_0
        process_error_covariances,  # Q
        measurement_error_covariances,  # R
        transition_matrix,  # A
        observation_matrix,  # H
        control_matrix=None  # B
    ):
        self._estimates = self._to_matrix(initial_estimates)
        if len(self._estimates[0]) > 1:
            self._estimates = self._transpose(self._estimates)

        self._process_error_covariances = self._to_matrix(
            process_error_covariances
        )
        if len(self._process_error_covariances[0]) > 1:
            self._process_error_covariances = self._transpose(
                self._process_error_covariances
            )

        self._measurement_error_covariances = self._to_matrix(
            measurement_error_covariances
        )
        if len(self._measurement_error_covariances[0]) > 1:
            self._measurement_error_covariances = self._transpose(
                self._measurement_error_covariances
            )

        self._transition_matrix = numpy.array(transition_matrix)
        self._observation_matrix = numpy.array(observation_matrix)
        if control_matrix is not None:
            self._control_matrix = numpy.array(control_matrix)
        else:
            self._control_matrix = None

    def predict(self, measurements, control_state=None):
        """Returns a prediction of the values."""
        # This process derived from http://greg.czerniak.info/guides/kalman1/
        measurements = self._to_matrix(measurements)
        if len(measurements[0]) > 1:
            measurements = self._transpose(measurements)

        import random; random.seed(0)
        import ipdb; ipdb.set_trace()
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
        return matrix1 * matrix2

    @staticmethod
    def _scalar_multiply(scalar, matrix):
        """Multiplies a matrix by a scalar value."""
        if isinstance(matrix, numpy.ndarray):
            return matrix * scalar
        return numpy.array(matrix) * scalar

    @staticmethod
    def _transpose(matrix):
        """Transposes a matrix."""
        return numpy.transpose(matrix)

    @staticmethod
    def _add(matrix1, matrix2):
        """Adds two matrices."""
        return matrix1 + matrix2

    @staticmethod
    def _subtract(matrix1, matrix2):
        """Subtracts two matrices."""
        return matrix1 - matrix2

    @staticmethod
    def _inverse(matrix):
        """Inverts a matrix."""
        if len(matrix) == 1:
            return matrix
        return numpy.linalg.inv(matrix)

    @staticmethod
    def _identity(size):
        """Returns an identity matrix."""
        return numpy.eye(size)

    @staticmethod
    def _to_matrix(vector_or_matrix):
        if isinstance(vector_or_matrix[0], collections.Iterable):
            return numpy.array(vector_or_matrix)
        return numpy.array((vector_or_matrix,))
