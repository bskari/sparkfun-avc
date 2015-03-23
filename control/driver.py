"""Drives the Tamiya Grasshopper."""
from RPIO import PWM


THROTTLE_GPIO_PIN = 18
THROTTLE_NEUTRAL_US = 1500
THROTTLE_DIFF = 500
THROTTLE_FORWARD_US = THROTTLE_NEUTRAL_US + THROTTLE_DIFF
THROTTLE_REVERSE_US = THROTTLE_NEUTRAL_US - THROTTLE_DIFF

STEERING_GPIO_PIN = 4
STEERING_NEUTRAL_US = 1650
STEERING_DIFF = 300
STEERING_LEFT_US = STEERING_NEUTRAL_US - STEERING_DIFF
STEERING_RIGHT_US = STEERING_NEUTRAL_US + STEERING_DIFF


class Driver(object):
    """Class that implements the Driver interface."""

    def __init__(self, telemetry, logger):
        self._telemetry = telemetry
        self._logger = logger
        PWM.set_loglevel(PWM.LOG_LEVEL_ERRORS)
        self._servo = PWM.Servo(subcycle_time_us=(1000000 // 50))
        self._throttle = 0.0
        self._steering = 0.0

        self._servo.set_servo(
            THROTTLE_GPIO_PIN,
            self._get_throttle(0.0)
        )
        self._servo.set_servo(
            STEERING_GPIO_PIN,
            self._get_steering(0.0)
        )
        self._max_throttle = 1.0

    def drive(self, throttle_percentage, steering_percentage):
        """Sends a command to the RC car. Throttle should be a float between
        -1.0 for reverse and 1.0 for forward. Turn should be a float between
        -1.0 for left and 1.0 for right.
        """
        assert -1.0 <= throttle_percentage <= 1.0
        assert -1.0 <= steering_percentage <= 1.0
        self._telemetry.process_drive_command(
            throttle_percentage,
            steering_percentage
        )
        self._logger.debug(
           'throttle = {throttle}, turn = {turn}'.format(
               throttle=throttle_percentage,
               turn=steering_percentage,
            )
        )
        self._throttle = throttle_percentage
        self._steering = steering_percentage

        self._logger.debug(
            'Throttle: {}, steering: {}'.format(
                throttle_percentage,
                steering_percentage
            )
        )

        if throttle_percentage > 0.0:
            throttle = min(self._max_throttle, throttle_percentage)
        else:
            throttle = max(-self._max_throttle, throttle_percentage)

        self._servo.set_servo(
            THROTTLE_GPIO_PIN,
            self._get_throttle(throttle)
        )
        self._servo.set_servo(
            STEERING_GPIO_PIN,
            self._get_steering(steering_percentage)
        )

    def get_throttle(self):
        """Returns the current throttle."""
        return self._throttle

    def get_turn(self):
        """Returns the current turn."""
        return self._steering

    @staticmethod
    def _get_throttle(percentage):
        """Returns the throttle value."""
        # Purposely limit the reverse in case we try to go back while still
        # rolling - prevent damage to the gear box
        if not (-0.25 <= percentage <= 1.0):
            raise ValueError('Bad throttle')
        return int(THROTTLE_NEUTRAL_US + THROTTLE_DIFF * percentage) // 10 * 10

    @staticmethod
    def _get_steering(percentage):
        """Returns the steering value."""
        if not (-1.0 <= percentage <= 1.0):
            raise ValueError('Bad steering')
        return int(STEERING_NEUTRAL_US + STEERING_DIFF * percentage) // 10 * 10

    def set_max_throttle(self, max_throttle):
        """Sets the maximum throttle."""
        self._max_throttle = min(1.0, max_throttle)
