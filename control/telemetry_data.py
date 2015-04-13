"""TelemetryData interface that feeds raw readings from the GPS module to a
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
import serial
import threading
import time


class TelemetryData(threading.Thread):
    """Reader of GPS module that implements the TelemetryData interface."""
    def __init__(
        self,
        telemetry,
        logger,
    ):
        """Create the TelemetryData thread."""
        super(TelemetryData, self).__init__()

        self._telemetry = telemetry
        self._logger = logger
        self._run = True
        self._iterations = 0

        self._driver = None
        self._serial = serial.Serial('/dev/ttyAMA0', 115200)

    def run(self):
        """Run in a thread, hands raw telemetry readings to telemetry
        instance.
        """
        from control.telemetry import Telemetry
        while self._run:
            # This blocks until a new mesage is received
            line = self._serial.readline().decode('utf-8')
            if not line.startswith('$GPRMC'):
                continue
            parts = line.split(',')
            latitude_str = parts[3]
            longitude_str = parts[5]
            latitude = float(latitude_str[0:2]) + float(latitude_str[2:]) / 60.0
            longitude = float(longitude_str[0:3]) + float(longitude_str[3:]) / 60.0
            if parts[4] == 'S':
                latitude = -latitude
            if parts[6] == 'W':
                longitude = -longitude
            speed_knots = float(parts[7])
            speed_m_s = speed_knots * 0.514444444
            course = float(parts[8])

            self._logger.debug(
                'lat: {}, long: {}, speed: {}, course: {}'.format(
                    latitude,
                    longitude,
                    speed_m_s,
                    course
                )
            )

            self._telemetry.handle_message({
                'x_m': Telemetry.longitude_to_m_offset(longitude),
                'y_m': Telemetry.latitude_to_m_offset(latitude),
                # TODO: Parse other messages to estimate these
                'x_accuracy_m': 1.0,
                'y_accuracy_m': 1.0,
                'gps_d': course,
                'speed_m_s': speed_m_s,
            })

    def kill(self):
        """Stops any data collection."""
        self._run = False

    def set_driver(self, driver):
        """Allow accessing a driver method so that we can do simulation of
        driving events, e.g. turning on throttle causes the car to move.
        """
        self._driver = driver
