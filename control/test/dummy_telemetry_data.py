"""Dummy class for TelemetryData interface that feeds raw readings to a
telemetry object.  A TelemetryData should have two methods:
    run(self)
    kill(self)
The TelemetryData should call telemetry.handle_message(message) with a
dictionary containing the most recent readings with entries for at least
latitude, longitude, heading, bearing, accelerometer, gyro, speed, time, etc.
"""

import math
import threading
import time


MAX_SPEED_M_S = 11.0
TURN_D_S = 90.0
SLEEP_TIME_S = 0.5


class DummyTelemetryData(threading.Thread):
    """Dummy class that implements the TelemetryData interface."""
    def __init__(
        self,
        telemetry,
        logger
    ):
        """Create the TelemetryData thread."""
        super(DummyTelemetryData, self).__init__()

        self._telemetry = telemetry
        self._logger = logger
        self._run = True

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
                time.sleep(SLEEP_TIME_S)
            except Exception:  # pylint: disable=broad-except
                pass

            speed_m_s = 0.0
            if self._driver is not None:
                speed_m_s = self._driver.get_throttle() * MAX_SPEED_M_S
                point_m = (0.0, speed_m_s * SLEEP_TIME_S)
                offset_m = Telemetry.rotate_radians_clockwise(
                    point_m,
                    math.radians(self._heading_d)
                )
                self._x_m += offset_m[0]
                self._y_m += offset_m[1]

                self._heading_d += self._driver.get_turn() * TURN_D_S * SLEEP_TIME_S
                self._heading_d = Telemetry.wrap_degrees(self._heading_d)

            self._telemetry.handle_message({
                'x_m': self._x_m,
                'y_m': self._y_m,
                'x_accuracy_m': 2.0,
                'y_accuracy_m': 2.0,
                'speed_m_s': speed_m_s,
                'heading_d': self._heading_d,
                'bearing_d': self._heading_d,
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
