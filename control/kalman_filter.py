"""Kalman filter, used to estimate the true values from noisy sensor data."""
import collections
import numpy


class KalmanFilter(object):
    """Kalman filter, used to estimate the true values from noisy sensor
    data.
    """
    def __init__(
        self,
        transition_matrix,  # A
        observation_matrix,  # H
        state_estimate, # x
        process_covariance_estimate,  # P
        process_error_estimate,  # Q
        measurement_error_estimate,  # R
        control_matrix=None,  # B
    ):
        self._transition_matrix = self._to_matrix(transition_matrix)

        self._observation_matrix = self._to_matrix(observation_matrix)

        self._state_estimate = self._to_matrix(state_estimate)
        if len(self._state_estimate) == 1:
            self._state_estimate = numpy.transpose(self._state_estimate)

        self._process_covariance_estimate = self._to_matrix(process_covariance_estimate)

        self._process_error_estimate = self._to_matrix(process_error_estimate)

        self._measurement_error_estimate = self._to_matrix(measurement_error_estimate)

        if control_matrix is not None:
            self._control_matrix = self._to_matrix(control_matrix)
        else:
            self._control_matrix = None

    def predict(self, measurements, control_state=None):
        """Returns a prediction of the values."""
        predicted_state_estimate = self._transition_matrix * self._state_estimate
        if control_state is not None or self._control_matrix is not None:
            assert control_state is not None
            assert self._control_matrix is not None
            predicted_state_estimate += self._control_matrix * control_state

        predicted_covariance_estimate = (self._transition_matrix * self._process_covariance_estimate) * numpy.transpose(self._transition_matrix) + self._process_error_estimate

        if len(measurements) > 0:
            measurements = numpy.array([measurements]).transpose()
        innovation = measurements - self._observation_matrix * predicted_state_estimate
        innovation_covariance = self._observation_matrix * predicted_covariance_estimate * numpy.transpose(self._observation_matrix) + self._measurement_error_estimate

        kalman_gain = predicted_covariance_estimate * numpy.transpose(self._observation_matrix) * numpy.linalg.inv(innovation_covariance)
        self._state_estimate = predicted_state_estimate + kalman_gain * innovation

        # We need the size of the matrix so we can make an identity matrix
        size = self._process_covariance_estimate.shape[0]
        self._process_covariance_estimate = (numpy.eye(size) - kalman_gain * self._observation_matrix) * predicted_covariance_estimate

        return self._state_estimate

    @staticmethod
    def _to_matrix(vector_or_matrix):
        if isinstance(vector_or_matrix[0], collections.Iterable):
            return numpy.matrix(vector_or_matrix)
        return numpy.matrix((vector_or_matrix,))
