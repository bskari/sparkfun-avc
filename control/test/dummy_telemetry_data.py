"""Dummy class for TelemetryData interface that feeds raw readings to a
telemetry object.  A TelemetryData should have two methods:
    run(self)
    kill(self)
The TelemetryData should call telemetry.handle_message(message) with a
dictionary containing the most recent readings with entries for at least
x_m, y_m, x_accuracy_m, y_accuracy_m, gps_d, speed_m_s for GPS readings, and
compass_d for compass readings. Optional parameters are time_s,
accelerometer_m_s_s, and magnetometer.
"""

import math
import random
import threading
import time


class DummyTelemetryData(threading.Thread):
    """Dummy class that implements the TelemetryData interface."""
    MAX_SPEED_M_S = 11.0
    TURN_D_S = 90.0
    SIGMA_M = 2.0
    SIGMA_COMPASS_D = 10.0
    SIGMA_GPS_D = 2.0
    SIGMA_M_S = 0.5

    def __init__(
        self,
        telemetry,
        logger,
        sleep_time_milliseconds=None
    ):
        """Create the TelemetryData thread."""
        super(DummyTelemetryData, self).__init__()

        self._telemetry = telemetry
        self._logger = logger
        self._run = True
        self._iterations = 0

        if sleep_time_milliseconds is None:
            self._sleep_time_s = 0.2
        else:
            self._sleep_time_s = sleep_time_milliseconds / 1000.0

        # We initialize these so that simulations and the like can set it
        # later, to provide simulated telemetry data
        self._driver = None
        self._x_m = 0.0
        self._y_m = 0.0
        self._heading_d = 0.0

    def run(self):
        """Run in a thread, hands raw telemetry readings to telemetry
        instance.
        """
        from control.telemetry import Telemetry
        # Normally, you'd have a loop that periodically checks for new readings
        # or that blocks until readings are received
        while self._run:
            try:
                time.sleep(self._sleep_time_s)
            except Exception:  # pylint: disable=broad-except
                pass

            speed_m_s = 0.0
            if self._driver is not None:
                speed_m_s = self._driver.get_throttle() * self.MAX_SPEED_M_S
                point_m = (0.0, speed_m_s * self.SLEEP_TIME_S)
                offset_m = Telemetry.rotate_radians_clockwise(
                    point_m,
                    math.radians(self._heading_d)
                )
                self._x_m += offset_m[0]
                self._y_m += offset_m[1]

                self._heading_d += \
                    self._driver.get_turn() * self.TURN_D_S * self.SLEEP_TIME_S
                self._heading_d = Telemetry.wrap_degrees(self._heading_d)

            self._iterations += 1
            if self._iterations % 5 == 0:
                gps_d = Telemetry.wrap_degrees(
                    random.normalvariate(self._heading_d, self.SIGMA_GPS_D)
                )
                self._telemetry.handle_message({
                    'x_m': random.normalvariate(self._x_m, self.SIGMA_M),
                    'y_m': random.normalvariate(self._y_m, self.SIGMA_M),
                    'x_accuracy_m': self.SIGMA_M,
                    'y_accuracy_m': self.SIGMA_M,
                    'speed_m_s': random.normalvariate(speed_m_s, self.SIGMA_M_S),
                    'gps_d': gps_d,
                    'accelerometer_m_s_s': (0.0, 0.0, 9.8),
                })
            else:
                compass_d = Telemetry.wrap_degrees(
                    random.normalvariate(
                        self._heading_d,
                        self.SIGMA_COMPASS_D
                    )
                )
                self._telemetry.handle_message({
                    'compass_d': compass_d,
                    'accelerometer_m_s_s': (0.0, 0.0, 9.8),
                })

    def kill(self):
        """Stops any data collection."""
        self._run = False

    def set_driver(self, driver):
        """Allow accessing a driver method so that we can do simulation of
        driving events, e.g. turning on throttle causes the car to move.
        """
        self._driver = driver
