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

import datetime
import math
import numpy
import pytz
import threading
import time

from control.sup800f import get_message
from control.sup800f import parse_binary
from control.sup800f import switch_to_binary_mode
from control.sup800f import switch_to_nmea_mode
from control.telemetry import Telemetry
from messaging import config
from messaging.async_logger import AsyncLogger
from messaging.async_producers import TelemetryProducer
from messaging.message_consumer import consume_messages


# Below this speed, the GPS module uses the compass to compute heading, if the
# compass is calibrated
COMPASS_SPEED_CUTOFF_KM_HOUR = 10.0
COMPASS_SPEED_CUTOFF_M_S = COMPASS_SPEED_CUTOFF_KM_HOUR * 1000.0 / 3600.0


class Sup800fTelemetry(threading.Thread):
    """Reader of GPS module that implements the TelemetryData interface."""
    def __init__(self, serial):
        """Create the TelemetryData thread."""
        super(Sup800fTelemetry, self).__init__()
        self.name = self.__class__.__name__

        self._telemetry = TelemetryProducer()
        self._serial = serial
        self._logger = AsyncLogger()
        self._run = True
        self._iterations = 0
        # These initial measurements are from a calibration observation
        self._compass_offsets = (-11.87, -5.97)
        self._magnitude_mean = 353.310
        self._magnitude_std_dev = 117.918

        self._calibrate_compass_end_time = None
        self._nmea_mode = True
        self._last_compass_heading_d = 0.0
        self._dropped_compass_messages = 0
        self._dropped_threshold = 10

        self._hdop = 5.0

        def handle_message(message):
            """Handles command messages. Only cares about calibrate compass;
            other messages are ignored.
            """
            if message == 'calibrate-compass':
                self.calibrate_compass(10)

        consume = lambda: consume_messages(
            config.COMMAND_FORWARDED_EXCHANGE,
            handle_message
        )
        thread = threading.Thread(target=consume)
        thread.name = '{}:consume_messages:{}'.format(
            self.__class__.__name__,
            config.COMMAND_FORWARDED_EXCHANGE
        )
        thread.start()

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

        if line.startswith('$GPRMC'):
            self._handle_gprmc(line)
            return True
        elif line.startswith('$GPGSA'):
            self._handle_gpgsa(line)
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
            return False
        self._handle_binary(parsed)
        return True

    @staticmethod
    def _timestamp(dt):
        """Computes the Unix timestamp from a datetime object. This is needed
        because Python < 3.2 doesn't have .timestamp built in.
        """
        return (dt - datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)) \
            / datetime.timedelta(seconds=1)

    def _handle_gprmc(self, gprmc_message):
        """Handles GPRMC (recommended minimum specific GNSS data) messages."""
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

        time_ = parts[1]
        hours = int(time_[0:2])
        minutes = int(time_[2:4])
        seconds = float(time_[4:])
        date = parts[9]
        day = int(date[0:2])
        month = int(date[2:4])
        year = int(date[4:]) + 2000
        # datetime doesn't do float seconds, so we need to fudge it later
        datetime_ = datetime.datetime(
            year,
            month,
            day,
            hours,
            minutes,
            0,
            tzinfo=pytz.utc
        )
        timestamp_s = self._timestamp(datetime_) + seconds

        self._telemetry.gps_reading(
            latitude,
            longitude,
            self._hdop * 5.0,  # This is a guess. Smaller HDOP is more precise.
            course,
            speed_m_s,
            timestamp_s,
            'sup800f'
        )

    def _handle_gpgsa(self, gpgsa_message):
        """Handles GSA (GNSS DOP and active satellites) messages."""
        # $GPGSA,A,3,23,03,26,09,27,16,22,31,,,,,1.9,1.1,1.5*31\r\n
        # type, mode M=manual or A=automatic, fix type 1=N/A 2=2D 3=3D,
        # satellites used 1-12, PDOP, HDOP, VDOP + checksum
        parts = gpgsa_message.split(',')
        #pdop = float(parts[-3])
        hdop = float(parts[-2])
        #vdop = float(parts[-1].split('*')[0])
        self._hdop = hdop

    def _handle_binary(self, message):
        """Handles properietary SUP800F binary messages."""
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
            ) + 8.666  # Boulder declination
        )
        magnitude = flux_x ** 2 + flux_y ** 2
        std_devs_away = abs(
            self._magnitude_mean - magnitude
        ) / self._magnitude_std_dev
        # In a normal distribution, 95% of readings should be within 2 std devs
        if std_devs_away > 2.0:
            self._dropped_compass_messages += 1
            if self._dropped_compass_messages > self._dropped_threshold:
                self._logger.warn(
                    'Dropped {} compass messages in a row, std dev = {}'.format(
                        self._dropped_compass_messages,
                        round(std_devs_away, 3)
                    )
                )
                self._dropped_compass_messages = 0
                self._dropped_threshold += 10
            return
        self._dropped_compass_messages = 0
        self._dropped_threshold = 10

        if std_devs_away > 1.0:
            confidence = 2.0 - std_devs_away
        else:
            confidence = 1.0

        self._telemetry.compass_reading(
            self._last_compass_heading_d,
            confidence,
            'sup800f'
        )

    def kill(self):
        """Stops any data collection."""
        self._run = False

    def calibrate_compass(self, seconds):
        """Requests that the car calibrate the compasss."""
        if self._calibrate_compass_end_time is None:
            self._calibrate_compass_end_time = time.time() + seconds
        else:
            self._logger.warn('Compass is already being calibrated')

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
