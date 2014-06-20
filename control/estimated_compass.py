"""Estimates readings from the compass, because it's slow to update."""

import time


class EstimatedCompass(object):
    """Estimates readings from the compass, because it's slow to update."""
    DEAD_TIME_S = 0.25
    COMPASS_TRAVEL_RATE_D_S = 90.0

    def __init__(self, logger):
        self._logger = logger

        self._turn_time = None
        self._update_time = None
        self._last_turn = 0
        self._turn = 0
        self._throttle = 0
        self._estimated_compass = None
        self._estimated_heading = None
        self._delay = False
        self._compass_turning = False

    def process_drive_command(self, throttle, turn, compass_heading):
        """Takes into account the vehicle's turn."""
        self._throttle = throttle
        self._turn = turn

        now = time.time()
        self._turn_time = now
        self._update_time = now

        if turn > 0.1 or turn < -0.1:
            # If we're switching directions, then we need to delay
            if (
                self._last_turn is None
                or self._last_turn == 0
                or (self._last_turn > 0.0 and turn < 0.0)
                or (self._last_turn < 0.0 and turn > 0.0)
            ):
                self._delay = True
                self._logger.debug('Delaying compass estimate')

            if not self._compass_turning is None:
                self._estimated_heading = compass_heading
            self._compass_turning = True
            self._estimated_compass = compass_heading

    def get_estimated_heading(self, compass_heading):
        """Returns the estimated heading. If the car has been driving straight
        for a while, this should return the plain compass heading.
        """
        # Because the compass takes so long to update, we'll need to guess the
        # true heading and then incorporate real values once it's had a chance
        # to catch up. Let's assume the compass is dead for .25 seconds then
        # travels 90 degrees per second, and that the car turns 90 degrees per
        # second. The latter formula should take into account the car's speed
        # and turn rate, but we'll have to take more observations to tweak it.
        if not self._compass_turning:
            self._logger.debug(
                'Compass not turning, returning {raw}'.format(
                    raw=compass_heading
                )
            )
            return compass_heading

        now = time.time()
        time_diff_s = now - self._update_time
        self._update_time = now

        # Import here to prevent circular imports
        from telemetry import Telemetry

        self._estimated_heading = Telemetry.wrap_degrees(
            self._estimated_heading + self._car_turn_rate_d_s() * time_diff_s
        )

        if self._delay:
            if (
                self._turn_time is not None
                and self._turn_time + EstimatedCompass.DEAD_TIME_S < now
            ):
                self._delay = False
                self._logger.debug('Done delaying compass estimate')
        else:
            step_d = self._compass_turn_rate_d_s() * time_diff_s
            self._estimated_compass += step_d

            if Telemetry.difference_d(
                self._estimated_compass,
                self._estimated_heading
            ) < abs(step_d):
                self._logger.debug('Compass done turning')
                self._compass_turning = False

        self._logger.debug(
            'Estimated heading: {estimated}, estimated compass: {compass},'
            ' raw compass: {raw}'.format(
                estimated=self._estimated_heading,
                compass=self._estimated_compass,
                raw=compass_heading,
            )
        )
        return self._estimated_heading

    def _car_turn_rate_d_s(self):
        """Returns the approximate turn rate of the car in degrees per second
        for the given speed and turn value.
        """
        # In 4 seconds: (throttle, turn)
        # (0.25, 0.25) => ?? Noisy data, maybe just assume 90 from observation
        # (0.25, 0.50) => 126 (62 to 188)
        # (0.25, 0.75) => 287 (53 to 340)
        # (0.25, 1.00) => 343 (43 to 26)
        # (0.50, 0.25) => crashed
        # (0.50, 0.50) => 172 (37 to 209)
        # (0.50, 0.75) => 388 (23 to 51)
        # (0.50, 1.00) => 545 (45 to 230)
        # (0.75, 0.25) => crashed?
        # (0.75, 0.50) => 178 (155 to 333)
        # (0.75, 0.75) => 410 (146 to 196)
        # (0.75, 1.00) => 441 (178 to 259)
        # Note that for the next measurement, the car was drifting left more
        # when it was supposed to be going straight then it was when it was
        # supposed to be turning right, sooooo this migth be way off
        # (1.00, 0.25) => 45 (180 to 225)
        # (1.00, 0.50) => 180 (323 to 142)
        # (1.00, 0.75) => 330 (310 to 280)
        # (1.00, 1.00) => 320 (320 to 280)

        # Linear least squares regression gives us -32.42961301, 443.08020191
        throttle_multiplier = -32.42961301 / 4.0
        turn_multiplier = 443.08020191 / 4.0
        return self._throttle * throttle_multiplier + self._turn * turn_multiplier

    def _compass_turn_rate_d_s(self):
        """Returns the approximate turn rate of the compass in degrees per
        second for the given speed and turn value.
        """
        # TODO: Validate this with some observations of the compass
        if self._turn < 0.0:
            return -self.COMPASS_TRAVEL_RATE_D_S
        return self.COMPASS_TRAVEL_RATE_D_S
