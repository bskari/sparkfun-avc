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
                'latitude': 0.0,
                'longitude': 0.0,
                'speed': 0.0,
                'heading': 0.0,
                'bearing': 0.0,
                'accelerometer': (0.0, 0.0, 9.8),
            })

    def kill(self):
        """Stops any data collection."""
        self._run = False
