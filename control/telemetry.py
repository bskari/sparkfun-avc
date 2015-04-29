"""Telemetry class that takes raw sensor data and filters it to remove noise
and provide more accurate telemetry data.
"""
import collections
import json
import math
import threading
import time

from control.location_filter import LocationFilter
from control.synchronized import synchronized

#pylint: disable=invalid-name

# Sparkfun HQ
CENTRAL_LATITUDE = 40.091244
CENTRAL_LONGITUDE = -105.185276

# Values for Tamiya Grasshopper, from observation
BASE_MAX_TURN_RATE_D_S = 100.0
# We overestimate this because the compass takes a little while to update, and
# it keeps causing the car to oversteer. This should compensate.
MAX_TURN_RATE_D_S = BASE_MAX_TURN_RATE_D_S * 1.3
# The turn rate when steering is -1.0 or 1.0
# Time it takes to turn from steering -1.0 to 1.0
FULL_TURN_TIME_S = 1.0
STEERING_CHANGE_PER_S = 1.0 / FULL_TURN_TIME_S
# Time to go from 0 to top speed at throttle 1.0
ZERO_TO_TOP_S = 5.0
THROTTLE_CHANGE_PER_S = 1.0 / ZERO_TO_TOP_S
MAX_SPEED_M_S = 4.5


class Telemetry(object):
    """Provides up to date telemetry data to other modules. This class will use
    the current command direction, anomalous value filtering and interpolation
    to provide more accurate readings than just raw data dumps.
    """
    EQUATORIAL_RADIUS_M = 6378.1370 * 1000
    M_PER_D_LATITUDE = EQUATORIAL_RADIUS_M * 2.0 * math.pi / 360.0
    HISTORICAL_SPEED_READINGS_COUNT = 20

    def __init__(self, logger):
        self._data = {}
        self._logger = logger
        self._speed_history = collections.deque()
        self._lock = threading.Lock()

        # TODO: For the competition, just hard code the compass. For now, the
        # Kalman filter should start reading in values and correct quickly.
        self._location_filter = LocationFilter(0.0, 0.0, 0.0)
        self._estimated_steering = 0.0
        self._target_steering = 0.0
        self._estimated_throttle = 0.0
        self._target_throttle = 0.0
        self._drive_time = None

    @synchronized
    def get_raw_data(self):
        """Returns the raw most recent telemetry readings."""
        return self._data

    @synchronized
    def get_data(self):
        """Returns the approximated telemetry data."""
        self._location_filter.update_dead_reckoning()
        values = {}
        for key in ('accelerometer_m_s_s',):  # Left as a loop if we want more later
            if key in self._data:
                values[key] = self._data[key]

        values['speed_m_s'] = self._location_filter.estimated_speed()
        values['heading_d'] = self._location_filter.estimated_heading()
        x_m, y_m = self._location_filter.estimated_location()
        values['x_m'], values['y_m'] = x_m, y_m
        self._logger.debug(
            'Estimates: x m {x}, y m {y}, heading d {heading},'
            ' speed m/s^2 {speed}'.format(
                x=values['x_m'],
                y=values['y_m'],
                heading=values['heading_d'],
                speed=values['speed_m_s'],
            )
        )
        return values

    @synchronized
    def process_drive_command(self, throttle, steering):
        """Process a drive command. When the command module tells the car to do
        something (e.g. drive forward and left), that data should be integrated
        into the telemetry immediately, because GPS sensors and what not
        normally have a slight delay.
        """
        assert -1.0 <= throttle <= 1.0, 'Bad throttle in telemetry'
        assert -1.0 <= steering <= 1.0, 'Bad steering in telemetry'

        self._target_steering = steering
        self._target_throttle = throttle
        self._drive_time = time.time()

    @synchronized
    def handle_message(self, message):
        """Stores telemetry data from messages received from some source."""
        if 'speed_m_s' in self._data:
            self._speed_history.append(self._data['speed_m_s'])
            while len(self._speed_history) > self.HISTORICAL_SPEED_READINGS_COUNT:
                self._speed_history.popleft()

        if 'compass_d' in message:
            self._update_estimated_drive()
            self._location_filter.update_compass(message['compass_d'])

        if 'x_m' in message:
            self._update_estimated_drive()
            self._location_filter.update_gps(
                message['x_m'],
                message['y_m'],
                message['x_accuracy_m'],
                message['y_accuracy_m'],
                message['gps_d'],
                message['speed_m_s']
            )

        self._data = message
        self._logger.debug(json.dumps(message))

    @synchronized
    def is_stopped(self):
        """Determines if the RC car is moving."""
        if len(self._speed_history) < self.HISTORICAL_SPEED_READINGS_COUNT:
            return False

        if all((speed == 0.0 for speed in self._speed_history)):
            self._logger.info(
                'RC car is not moving according to speed history'
            )
            self._speed_history.clear()
            return True
        return False

    def _update_estimated_drive(self):
        """Updates the estimations of the drive state, e.g. the current
        throttle and steering.
        """
        if self._drive_time is None:
            return
        now = time.time()
        diff_s = now - self._drive_time

        def updated(estimate, target, change_per_s):
            """Returns the updated value."""
            diff = abs(estimate - target)
            if diff == 0.0:
                return target
            total_change = change_per_s * diff_s
            if total_change > diff:
                return target
            if estimate < target:
                return estimate + total_change
            return estimate - total_change

        self._estimated_throttle = updated(
            self._estimated_throttle,
            self._target_throttle,
            THROTTLE_CHANGE_PER_S
        )
        self._estimated_steering = updated(
            self._estimated_steering,
            self._target_steering,
            STEERING_CHANGE_PER_S
        )

        # Also tell the location filter that we've changed
        if self._estimated_throttle != self._target_throttle:
            self._location_filter.manual_throttle(
                self._estimated_throttle * MAX_SPEED_M_S
            )
        # We always update the steering change, because we don't have sensors
        # to get estimates for it from other sources for our Kalman filter
        self._location_filter.manual_steering(
            self._estimated_steering * MAX_TURN_RATE_D_S
        )

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
        return math.sqrt(diff_1_m ** 2.0 + diff_2_m ** 2.0)

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
    def relative_degrees(x_m_1, y_m_1, x_m_2, y_m_2):
        """Computes the relative degrees from the first waypoint to the second,
        where north is 0.
        """
        relative_y_m = float(y_m_2) - y_m_1
        relative_x_m = float(x_m_2) - x_m_1
        if relative_x_m == 0.0:
            if relative_y_m > 0.0:
                return 0.0
            return 180.0

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

    @staticmethod
    def latitude_to_m_offset(latitude_d):
        """Returns the offset in meters for a given coordinate."""
        y_m = Telemetry.distance_m(latitude_d, 0.0, CENTRAL_LATITUDE, 0.0)
        if latitude_d > CENTRAL_LATITUDE:
            return y_m
        return -y_m

    @staticmethod
    def longitude_to_m_offset(longitude_d):
        """Returns the offset in meters for a given coordinate."""
        x_m = Telemetry.distance_m(0.0, longitude_d, 0.0, CENTRAL_LONGITUDE)
        if longitude_d > CENTRAL_LONGITUDE:
            return x_m
        return -x_m

    @staticmethod
    def distance_to_waypoint(heading_d_1, heading_d_2, distance_travelled):
        """Calculates the distance to a waypoint, given two observed headings
        to the waypoint and distance travelled in a straight line between the
        two observations.
        """
        m_1 = math.tan(math.radians(90.0 - heading_d_1))
        m_2 = math.tan(math.radians(90.0 - heading_d_2))
        x = distance_travelled / (m_1 - m_2)
        hypotenuse = x / math.cos(math.radians(90.0 - heading_d_1))
        return hypotenuse

    @staticmethod
    def offset_from_waypoint(heading_d, offset_to_waypoint_d, distance):
        """Calculates the offset (x, y) from a waypoint, given the heading of
        the vehicle, the angle from the vehicle's heading to the waypoint, and
        the distance to the waypoint.
        """
        angle = Telemetry.wrap_degrees(180.0 + heading_d + offset_to_waypoint_d)
        return Telemetry.rotate_radians_clockwise(
            (0.0, distance),
            math.radians(angle)
        )
