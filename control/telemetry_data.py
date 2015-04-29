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

        self._calibrate_compass_end_time = None
        self._nmea_mode = True
        self._last_compass_heading_d = 0.0

    def run(self):
        """Run in a thread, hands raw telemetry readings to telemetry
        instance.
        """
        while self._run:
            try:
                self._run_inner()
            except EnvironmentError as env:
                self._logger.debug('Failed to switch mode: {}'.format(env))
                # Maybe resetting the module mode will help
                try:
                    if self._nmea_mode:
                        switch_to_nmea_mode(self._serial)
                    else:
                        switch_to_binary_mode(self._serial)
                except:
                    pass
            except Exception as exc:  # pylint: disable=broad-except
                self._logger.warn(
                    'Telemetry data caught exception: {}'.format(
                        exc
                    )
                )

    def _run_inner(self):
        """Inner part of run."""
        binary_count = 0
        while self._run:
            if self._calibrate_compass_end_time is not None:
                self._calibrate_compass()

            # NMEA mode
            if self._nmea_mode:
                if self._get_gprc():
                    switch_to_binary_mode(self._serial)
                    self._nmea_mode = False
            else:
                if self._get_binary():
                    binary_count += 1
                    if binary_count >= 3:
                        switch_to_nmea_mode(self._serial)
                        self._nmea_mode = True
                        binary_count = 0

    def _get_gprc(self):
        """Gets and processes a single GPRC message."""
        # This blocks until a new message is received
        line = self._serial.readline()
        try:
            line = line.decode('utf-8')
        except:
            raise EnvironmentError('Not a UTF-8 message')

        # TODO: Configure the module so that it only puts out GPRMC messages
        if line.startswith('$GPRMC'):
            self._handle_gprmc(line)
            return True
        return False

    def _get_binary(self):
        """Gets and processes a single binary message."""
        try:
            message = get_message(self._serial, 1000)
        except ValueError:
            self._logger.error('No binary message received')
            return False

        parsed = parse_binary(message)
        if parsed is None:
            if message[0] == '$':
                throw
            return False
        self._handle_binary(parsed)
        return True

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
        # Below a certain speed, the module uses the compass to determine
        # course, which is not calibrated, so we need to use our own value.
        if speed_m_s < COMPASS_SPEED_CUTOFF_M_S:
            course = self._last_compass_heading_d

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
        self._last_compass_heading_d = Telemetry.wrap_degrees(
            270.0 - math.degrees(
                math.atan2(flux_y, flux_x)
            ) - 8.666  # Boulder declination
        )
        # TODO: Drop messages that are several standard deviations off
        self._telemetry.handle_message({
            # TODO: We need to tell the system how confident we are
            'compass_d': self._last_compass_heading_d
        })

    def kill(self):
        """Stops any data collection."""
        self._run = False

    def calibrate_compass(self, seconds):
        """Requests that the car calibrate the compasss."""
        self._calibrate_compass_end_time = time.time() + seconds

    def _calibrate_compass(self):
        """Calibrates the compass."""
        self._logger.info('Calibrating compass; setting to binary mode')
        switch_to_binary_mode(self._serial)
        self._nmea_mode = False
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
        self._nmea_mode = True
