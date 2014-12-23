"""Dummy class for Driver interface. A real Driver should have three methods:
    drive(self, throttle_percentage, turn_percentage)
    get_throttle(self)
    get_turn(self)
"""

class DummyDriver(object):
    """Dummy class that implements the Driver interface."""

    def __init__(self, telemetry, logger):
        self._telemetry = telemetry
        self._logger = logger
        self._throttle = 0.0
        self._turn = 0.0

    def drive(self, throttle_percentage, turn_percentage):
        """Sends a command to the RC car. Throttle should be a float between
        -1.0 for reverse and 1.0 for forward. Turn should be a float between
        -1.0 for left and 1.0 for right.
        """
        assert -1.0 <= throttle_percentage <= 1.0
        assert -1.0 <= turn_percentage <= 1.0
        self._telemetry.process_drive_command(
            throttle_percentage,
            turn_percentage
        )
        self._logger.debug(
           'throttle = {throttle}, turn = {turn}'.format(
               throttle=throttle_percentage,
               turn=turn_percentage,
            )
        )

    def get_throttle(self):
        """Returns the current throttle."""
        return self._throttle

    def get_turn(self):
        """Returns the current turn."""
        return self._turn
