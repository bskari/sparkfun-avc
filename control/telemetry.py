"""Telemetry class that takes raw sensor data and filters it to remove noise
and provide more accurate telemetry data.
"""
import math


class Telemetry(object):
    """Provides up to date telemetry data to other modules. This class will use
    the current command direction, anomalous value filtering and interpolation
    to provide more accurate readings than just raw data dumps.
    """
    EQUATORIAL_RADIUS_M = 6378.1370 * 1000
    M_PER_D_LATITUDE = EQUATORIAL_RADIUS_M * 2.0 * math.pi / 360.0

    def __init__(self):
        self._data = {}

    def get_raw_data(self):
        """Returns the raw most recent telemetry readings."""
        return self._data

    def get_data(self):
        """Returns the approximated telemetry data."""
        return self.get_raw_data()

    def process_drive_command(self, throttle, turn):
        """Process a drive command. When the command module tells the car to do
        something (e.g. drive forward and left), that data should be integrated
        into the telemetry immediately, because GPS sensors and what not
        normally have a slight delay.
        """
        assert -1.0 <= throttle <= 1.0
        assert -1.0 <= turn <= 1.0

    def handle_message(self, message):
        """Stores telemetry data from messages received from the phone."""
        #import json; print(json.dumps(message, sort_keys=True, indent=1))
        self._data = message

    @staticmethod
    def rotate_radians(point, radians):
        """Rotates the point by radians."""
        pt_x, pt_y = point
        cosine = math.cos(radians)
        sine = math.sin(radians)
        return (
            pt_x * cosine - pt_y * sine,
            pt_x * sine + pt_y * cosine
        )

    @classmethod
    def latitude_to_m_per_d_longitude(cls, latitude_d):
        """Returns the number of meters per degree longitude at a given
        latitude.
        """
        if 'cache' not in Telemetry.latitude_to_m_per_d_longitude.__dict__:
            Telemetry.latitude_to_m_per_d_longitude.__dict__['cache'] = None

        cache = Telemetry.latitude_to_m_per_d_longitude.cache
        if cache is not None and latitude_d - 1.0 < cache[0] < latitude_d + 1.0:
            return cache[1]

        # Assume the Earth is a perfect sphere
        radius_m = \
            math.cos(math.radians(latitude_d)) * cls.EQUATORIAL_RADIUS_M
        circumference_m = 2.0 * math.pi * radius_m
        cache = (latitude_d, circumference_m / 360.0)
        return circumference_m / 360.0

    @classmethod
    def distance_m(cls, latitude_d_1, longitude_d_1, latitude_d_2, longitude_d_2):
        """Returns the distance in meters between two waypoints in degrees."""
        diff_latitude_d = latitude_d_1 - latitude_d_2
        diff_longitude_d = longitude_d_1 - longitude_d_2
        diff_1_m = diff_latitude_d * cls.M_PER_D_LATITUDE
        diff_2_m = (
            diff_longitude_d
            * Telemetry.latitude_to_m_per_d_longitude(latitude_d_1)
        )
        return math.sqrt(diff_1_m  ** 2.0 + diff_2_m ** 2.0)

    @staticmethod
    def is_turn_left(heading_d, goal_heading_d):
        pt_1 = Telemetry.rotate_radians((1, 0), math.radians(heading_d))
        pt_2 = Telemetry.rotate_radians((1, 0), math.radians(goal_heading_d))
        pt_1 = list(pt_1) + [0]
        pt_2 = list(pt_2) + [0]
        cross_product = \
                pt_1[1] * pt_2[2] - pt_1[2] * pt_2[1] \
                + pt_1[2] * pt_2[0] - pt_1[0] * pt_2[2] \
                + pt_1[0] * pt_2[1] - pt_1[1] * pt_2[0]
        if cross_product > 0:
            return True
        return False
