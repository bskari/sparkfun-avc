"""Dummy class for TelemetryData interface that feeds raw readings to a
telemetry object.  A TelemetryData should have two methods:
    run(self)
    kill(self)
The TelemetryData should call telemetry.handle_message(message) with a
dictionary containing the most recent readings with entries for at least
latitude, longitude, heading, bearing, accelerometer, gyro, speed, time, etc.
"""

import threading
import time

# pylint: disable=broad-except


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

    def run(self):
        """Run in a thread, hands raw telemetry readings to telemetry
        instance.
        """
        # Normally, you'd have a loop that periodically checks for new readings
        # or that blocks until readings are received
        while self._run:
            try:
                time.sleep(0.1)
            except Exception:
                pass

            self._telemetry.handle_message({
                'x_m': 0.0,
                'y_m': 0.0,
                'x_accuracy_m': 2.0,
                'y_accuracy_m': 2.0,
                'speed_m_s': 0.0,
                'heading_d': 0.0,
                'bearing_d': 0.0,
                'accelerometer_m_s_s': (0.0, 0.0, 9.8),
            })

    def kill(self):
        """Stops any data collection."""
        self._run = False
