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

import numpy
import math
import threading
import time

from control.sup800f import get_message
from control.sup800f import parse_binary
from control.sup800f import switch_to_binary_mode
from control.sup800f import switch_to_nmea_mode
from control.telemetry import Telemetry


# Below this speed, the GPS module uses the compass to compute heading, if the
# compass is calibrated
COMPASS_SPEED_CUTOFF_KM_HOUR = 10.0
COMPASS_SPEED_CUTOFF_M_S = COMPASS_SPEED_CUTOFF_KM_HOUR * 1000.0 / 3600.0


class TelemetryData(threading.Thread):
    """Reader of GPS module that implements the TelemetryData interface."""
    def __init__(
            self,
            telemetry,
            serial,
            logger,
    ):
        """Create the TelemetryData thread."""
        super(TelemetryData, self).__init__()

        self._telemetry = telemetry
        self._serial = serial
        self._logger = logger
        self._run = True
        self._iterations = 0
        # These initial measurements are from a calibration observation
        self._compass_offsets = (-4.43, -0.43)
        self._magnitude_mean = 353.310
        self._magnitude_std_dev = 117.918

        self._driver = None
        self._calibrate_compass_end_time = None
        self._mode = 'n'

    def run(self):
        """Run in a thread, hands raw telemetry readings to telemetry
        instance.
        """
        binary_count = 0
        while self._run:
            if self._calibrate_compass_end_time is not None:
                self._calibrate_compass()

            # This blocks until a new message is received
            try:
                if self._mode == 'n':
                    line = self._serial.readline().decode('utf-8')
                else:
                    data = get_message(self._serial, 10000)
            except Exception as exc:  # pylint: disable=broad-except
                self._logger.warn(
                    'Unable to read message: {}'.format(exc)
                )
                continue

            # NMEA mode
            if self._mode == 'n':
                if line.startswith('$GPRMC'):
                    self._handle_gprmc(line)
                    try:
                        switch_to_binary_mode(self._serial)
                    except RuntimeError as rte:
                        self._logger.error(
                            'Unable to switch to binary mode: {}'.format(
                                rte
                            )
                        )
                    self._mode = 'b'
            # Binary/compass mode
            elif self._mode == 'b':
                parsed = parse_binary(data)
                if parsed is None:
                    continue
                self._handle_binary(parsed)
                binary_count += 1
                if binary_count >= 3:
                    try:
                        switch_to_nmea_mode(self._serial)
                    except RuntimeError as rte:
                        self._logger.error(
                            'Unable to switch to NMEA mode: {}'.format(
                                rte
                            )
                        )
                    self._mode = 'n'
                    binary_count = 0
            else:
                self._logger.error('Unknown mode: {}',format(self._mode))


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
        if speed_m_s < COMPASS_SPEED_CUTOFF_M_S:
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

    def _handle_binary(self, message):
        if message is None:
            return
        flux_x = float(message.magnetic_flux_ut_x - self._compass_offsets[0])
        flux_y = float(message.magnetic_flux_ut_y - self._compass_offsets[1])
        if flux_x == 0.0:
            # TODO: Figure out what to do here
            return
        degrees = Telemetry.wrap_degrees(
            270.0 - math.degrees(
                math.atan2(flux_y, flux_x)
            )
        )
        self._logger.info(
            'x:{} y:{} heading:{} std devs:{}'.format(
                round(flux_x, 3),
                round(flux_y, 3),
                round(degrees, 3),
                round(
                    abs(
                        (
                            message.magnetic_flux_ut_x ** 2
                            + message.magnetic_flux_ut_y ** 2
                        ) - self._magnitude_mean
                    ) / self._magnitude_std_dev,
                    3
                )
            )
        )

    def kill(self):
        """Stops any data collection."""
        self._run = False

    def set_driver(self, driver):
        """Allow accessing a driver method so that we can do simulation of
        driving events, e.g. turning on throttle causes the car to move.
        """
        self._driver = driver

    def calibrate_compass(self, seconds):
        """Requests that the car calibrate the compasss."""
        self._calibrate_compass_end_time = time.time() + seconds

    def _calibrate_compass(self):
        """Calibrates the compass."""
        self._logger.info('Calibrating compass; setting to binary mode')
        switch_to_binary_mode(self._serial)
        self._mode = 'b'
        for _ in range(10):
            self._serial.readline()

        maxes = [-1000000.0] * 3
        mins = [1000000.0] * 3
        readings = []
        # We should be driving for this long
        while time.time() < self._calibrate_compass_end_time:
            data = get_message(self._serial)
            try:
                binary = parse_binary(data)
            except ValueError as ve:
                self._logger.info(
                    'Unable to parse binary message {}'.format(
                        data
                    )
                )
                continue
            # TODO: This should never be None, see comment in sup800f.py
            if binary is None:
                continue
            values = (
                binary.magnetic_flux_ut_x,
                binary.magnetic_flux_ut_y,
            )
            maxes = [max(a, b) for a, b in zip(maxes, values)]
            mins = [min(a, b) for a, b in zip(mins, values)]
            readings.append((
                binary.magnetic_flux_ut_x,
                binary.magnetic_flux_ut_y,
            ))

        self._compass_offsets = [
            (max_ + min_) * 0.5 for max_, min_ in zip(maxes, mins)
        ]
        self._logger.info(
            'Compass calibrated, offsets are {}'.format(
                [round(i, 2) for i in self._compass_offsets]
            )
        )
        total_magnitudes = numpy.array([
            (x - self._compass_offsets[0]) ** 2 +
            (y - self._compass_offsets[1]) ** 2
            for x, y in readings
        ])
        self._magnitude_mean = total_magnitudes.mean()
        self._magnitude_std_dev = total_magnitudes.std()
        self._logger.info(
            'Magnitudes mean: {}, standard deviation {}'.format(
                round(self._magnitude_mean, 3),
                round(self._magnitude_std_dev, 3)
            )
        )
        self._calibrate_compass_end_time = None
        switch_to_nmea_mode(self._serial)
        self._mode = 'n'
