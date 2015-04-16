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

import serial
import threading

#pylint: disable=bad-builtin

# Below this speed, the GPS module uses the compass to compute heading, if the
# compass is calibrated
COMPASS_SPEED_CUTOFF_KM_HOUR = 10.0
COMPASS_SPEED_CUTOFF_M_S = COMPASS_SPEED_CUTOFF_KM_HOUR * 1000.0 / 3600.0


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
        self._compass_calibrated = False

        self._driver = None
        self._serial = serial.Serial('/dev/ttyAMA0', 115200)

    def run(self):
        """Run in a thread, hands raw telemetry readings to telemetry
        instance.
        """
        while self._run:
            # This blocks until a new message is received
            line = self._serial.readline().decode('utf-8')

            if line.startswith('$PSTI'):
                self._handle_psti(line)
            elif line.startswith('$GPRMC'):
                self._handle_gprmc(line)

    def _handle_psti(self, psti_message):
        """Handles PSTI (pitch, roll, yaw, pressure, temperature) messages."""
        if self._compass_calibrated:
            return
        self._compass_calibrated = psti_message.split(',')[2] == '1'
        if self._compass_calibrated:
            self._logger.info('Compass calibrated')

    def _handle_gprmc(self, gprmc_message):
        """Handles GPRMC (recommended minimum specific GNSS data) messages."""
        from control.telemetry import Telemetry
        parts = gprmc_message.split(',')
        latitude_str = parts[3]
        longitude_str = parts[5]

        decimal_index = latitude_str.find('.')
        latitude_degrees = float(latitude_str[:decimal_index - 2])
        latitude_minutes = float(latitude_str[decimal_index - 2:])

        decimal_index = longitude_str.find('.')
        longitude_degrees = float(longitude_str[:decimal_index - 2])
        longitude_minutes = float(longitude_str[decimal_index - 2:])

        latitude = latitude_degrees + latitude_minutes / 60.0
        longitude = longitude_degrees + longitude_minutes / 60.0
        if parts[4] == 'S':
            latitude = -latitude
        if parts[6] == 'W':
            longitude = -longitude
        speed_knots = float(parts[7])
        speed_m_s = speed_knots * 0.514444444
        course = float(parts[8])
        # I mounted the GPS module 90 degrees off, because it was easier and
        # more secure. Below a certain speed, the module uses the compass to
        # determine course, so we need to compensate. Above that speed, it
        # interpolates between GPS points and no rotation is necessary.
        if speed_m_s < COMPASS_SPEED_CUTOFF_M_S and self._compass_calibrated:
            course = Telemetry.wrap_degrees(course - 90.0)

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
