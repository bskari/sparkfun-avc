"""Telemetry class that takes raw sensor data and filters it to remove noise
and provide more accurate telemetry data.
"""
import collections
import json
import math


class Telemetry(object):
    """Provides up to date telemetry data to other modules. This class will use
    the current command direction, anomalous value filtering and interpolation
    to provide more accurate readings than just raw data dumps.
    """
    EQUATORIAL_RADIUS_M = 6378.1370 * 1000
    M_PER_D_LATITUDE = EQUATORIAL_RADIUS_M * 2.0 * math.pi / 360.0

    def __init__(self, logger):
        self._data = {}
        self._past_latitude_longitude = collections.deque()
        self._past_length = 20
        self._logger = logger

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
        # The Android phone is mounted rotated 90 degrees, so we need to
        # rotate the compass heading
        if 'heading' in message:
            heading = message['heading'] - 90.0
            if heading < 0.0:
                heading += 360.0
            message['heading'] = heading

        try:
            # Android is not calculating this itself, so let's do it
            if 'bearing' not in message or message['bearing'] == 0.0:
                if message['bearing'] == 0.0:
                    del message['bearing']
                for index in range(len(self._past_latitude_longitude) - 1, -1, -1):
                    distance_m = self.distance_m(
                        self._past_latitude_longitude[index]['latitude'],
                        self._past_latitude_longitude[index]['longitude'],
                        message['latitude'],
                        message['longitude']
                    )
                    if distance_m > 0.5:
                        message['bearing'] = self.relative_degrees(
                            self._past_latitude_longitude[index]['latitude'],
                            self._past_latitude_longitude[index]['longitude'],
                            message['latitude'],
                            message['longitude']
                        )
                        self._logger.debug(
                            'Computed {bearing} from {latitude_1} {longitude_1} to {latitude_2} {longitude_2}'.format(
                                bearing=message['bearing'],
                                latitude_1=self._past_latitude_longitude[0]['latitude'],
                                longitude_1=self._past_latitude_longitude[0]['longitude'],
                                latitude_2=message['latitude'],
                                longitude_2=message['longitude'],
                            )
                        )
                        break
        except:
            pass

        self._data = message
        self._logger.debug(json.dumps(message))

        if 'latitude' in message and 'longitude' in message:
            if (
                len(self._past_latitude_longitude) == 0 or
                (
                    message['latitude'] != self._past_latitude_longitude[0]['latitude'] and
                    message['longitude'] != self._past_latitude_longitude[0]['longitude']
                )
            ):
                self._past_latitude_longitude.appendleft({
                    'latitude': message['latitude'],
                    'longitude': message['longitude'],
                    'timestamp': message['timestamp']
                })

        if len(self._past_latitude_longitude) > self._past_length:
            self._past_latitude_longitude.pop()

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
        return cls.M_PER_D_LATITUDE

    @classmethod
    def latitude_to_m_per_d_longitude(cls, latitude_d, cache=None):
        """Returns the number of meters per degree longitude at a given
        latitude.
        """
        def calculate(latitude_d):
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
    def distance_m(cls, latitude_d_1, longitude_d_1, latitude_d_2, longitude_d_2):
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
        pt_1 = Telemetry.rotate_radians_clockwise((1, 0), math.radians(heading_d))
        pt_2 = Telemetry.rotate_radians_clockwise((1, 0), math.radians(goal_heading_d))
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
