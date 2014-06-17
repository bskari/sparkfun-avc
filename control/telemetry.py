"""Telemetry class that takes raw sensor data and filters it to remove noise
and provide more accurate telemetry data.
"""
import json
import math
import time

from estimated_compass import EstimatedCompass

#pylint: disable=invalid-name


class Telemetry(object):
    """Provides up to date telemetry data to other modules. This class will use
    the current command direction, anomalous value filtering and interpolation
    to provide more accurate readings than just raw data dumps.
    """
    EQUATORIAL_RADIUS_M = 6378.1370 * 1000
    M_PER_D_LATITUDE = EQUATORIAL_RADIUS_M * 2.0 * math.pi / 360.0

    def __init__(self, logger):
        self._data = {}
        self._past_length = 20
        self._logger = logger
        self._estimated_compass = EstimatedCompass()

    def get_raw_data(self):
        """Returns the raw most recent telemetry readings."""
        return self._data

    def get_data(self):
        """Returns the approximated telemetry data."""
        values = {
            'heading': self._estimated_compass.get_estimated_heading(
                self._data['heading']
            ),
            'accelerometer': self._data['accelerometer'],
        }

        if 'latitude' in self._data:
            values['latitude'] = self._data['latitude']
            values['longitude'] = self._data['longitude']

        if 'bearing' in self._data:
            values['bearing'] = self._data['bearing']

        return values

    def process_drive_command(self, throttle, turn):
        """Process a drive command. When the command module tells the car to do
        something (e.g. drive forward and left), that data should be integrated
        into the telemetry immediately, because GPS sensors and what not
        normally have a slight delay.
        """
        assert -1.0 <= throttle <= 1.0, 'Bad throttle in telemetry'
        assert -1.0 <= turn <= 1.0, 'Bad turn in telemetry'
        self._turn_time = time.time()
        self._turn_rate = turn
        if 'heading' in self._data:
            self._estimated_compass.process_drive_command(
                throttle,
                turn,
                self._data['heading']
            )

    def handle_message(self, message):
        """Stores telemetry data from messages received from the phone."""
        # The Android phone is mounted rotated 90 degrees, so we need to
        # rotate the compass heading
        if 'heading' in message:
            heading = message['heading'] - 90.0
            if heading < 0.0:
                heading += 360.0
            message['heading'] = heading

        self._data = message
        self._logger.debug(json.dumps(message))

    @staticmethod
    def rotate_radians_clockwise(point, radians):
        """Rotates the point by radians."""
        pt_x, pt_y = point
        cosine = math.cos(-radians)
        sine = math.sin(-radians)
        return (
            pt_x * cosine - pt_y * sine,
            pt_x * sine + pt_y * cosine
        )

    @classmethod
    def m_per_d_latitude(cls):
        """Returns the numbers of meters per degree of latitude."""
        return cls.M_PER_D_LATITUDE

    @classmethod
    def latitude_to_m_per_d_longitude(cls, latitude_d, cache=None):
        """Returns the number of meters per degree longitude at a given
        latitude.
        """
        def calculate(latitude_d):
            """Calculates the number of meters per degree longitude at a
            given latitude.
            """
            radius_m = \
                math.cos(math.radians(latitude_d)) * cls.EQUATORIAL_RADIUS_M
            circumference_m = 2.0 * math.pi * radius_m
            return circumference_m / 360.0

        if cache is not None and cache:
            return calculate(latitude_d)

        if 'cache' not in Telemetry.latitude_to_m_per_d_longitude.__dict__:
            Telemetry.latitude_to_m_per_d_longitude.__dict__['cache'] = [
                latitude_d,
                calculate(latitude_d)
            ]

        cache = Telemetry.latitude_to_m_per_d_longitude.cache
        if cache is not None and latitude_d - 0.1 < cache[0] < latitude_d + 0.1:
            return cache[1]
        cache[0] = latitude_d
        cache[1] = calculate(latitude_d)
        return cache[1]

    @classmethod
    def distance_m(
        cls,
        latitude_d_1,
        longitude_d_1,
        latitude_d_2,
        longitude_d_2
    ):
        """Returns the distance in meters between two waypoints in degrees."""
        diff_latitude_d = latitude_d_1 - latitude_d_2
        diff_longitude_d = longitude_d_1 - longitude_d_2
        diff_1_m = diff_latitude_d * cls.m_per_d_latitude()
        diff_2_m = (
            diff_longitude_d
            * Telemetry.latitude_to_m_per_d_longitude(latitude_d_1)
        )
        return math.sqrt(diff_1_m  ** 2.0 + diff_2_m ** 2.0)

    @staticmethod
    def is_turn_left(heading_d, goal_heading_d):
        """Determines if the vehicle facing a heading in degrees needs to turn
        left to reach a goal heading in degrees.
        """
        pt_1 = Telemetry.rotate_radians_clockwise(
            (1, 0),
            math.radians(heading_d)
        )
        pt_2 = Telemetry.rotate_radians_clockwise(
            (1, 0),
            math.radians(goal_heading_d)
        )
        pt_1 = list(pt_1) + [0]
        pt_2 = list(pt_2) + [0]
        cross_product = \
                pt_1[1] * pt_2[2] - pt_1[2] * pt_2[1] \
                + pt_1[2] * pt_2[0] - pt_1[0] * pt_2[2] \
                + pt_1[0] * pt_2[1] - pt_1[1] * pt_2[0]
        if cross_product > 0:
            return True
        return False

    @staticmethod
    def relative_degrees(
        latitude_d_1,
        longitude_d_1,
        latitude_d_2,
        longitude_d_2
    ):
        """Computes the relative degrees from the first waypoint to the second,
        where north is 0.
        """
        relative_y_m = float(latitude_d_2) - latitude_d_1
        relative_x_m = float(longitude_d_2) - longitude_d_1
        degrees = math.degrees(math.atan(relative_y_m / relative_x_m))
        if relative_x_m > 0.0:
            return 90.0 - degrees
        else:
            return 270.0 - degrees

    @staticmethod
    def acceleration_mss_velocity_ms_to_radius_m(
        acceleration_m_s_s,
        velocity_m_s
    ):
        """Converts the lateral acceleration force (accessible from the Android
        phone) and the car's velocity to the car's turn radius in meters.
        """
        # centripetal acceleration = velocity ^ 2 / radius
        return velocity_m_s ** 2 / acceleration_m_s_s

    @staticmethod
    def acceleration_mss_velocity_ms_to_ds(
        acceleration_m_s_s,
        velocity_m_s
    ):
        """Converts the lateral acceleration force (accessible from the Android
        phone) and the car's velocity to the car's turn rate in degrees per
        second.
        """
        radius_m = Telemetry.acceleration_mss_velocity_ms_to_radius_m(
            acceleration_m_s_s,
            velocity_m_s
        )
        circumference_m = 2 * math.pi * radius_m
        return circumference_m / float(velocity_m_s) * 360.0

    @staticmethod
    def wrap_degrees(degrees):
        """Wraps a degree value that's too high or too low."""
        dividend = int(degrees) // 360
        return (degrees + (dividend + 1) * 360.0) % 360.0

    @staticmethod
    def difference_d(heading_1_d, heading_2_d):
        """Calculates the absolute difference in degrees between two
        headings.
        """
        wrap_1_d = Telemetry.wrap_degrees(heading_1_d)
        wrap_2_d = Telemetry.wrap_degrees(heading_2_d)
        diff_d = abs(wrap_1_d - wrap_2_d)
        if diff_d > 180.0:
            diff_d = 360.0 - diff_d
        return diff_d
