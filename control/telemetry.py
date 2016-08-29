"""Telemetry class that takes raw sensor data and filters it to remove noise
and provide more accurate telemetry data.
"""
from pykml import parser
import collections
import json
import math
import os
import re
import threading

from control.location_filter import LocationFilter
from control.synchronized import synchronized
from messaging import config
from messaging.message_consumer import consume_messages
from messaging.async_logger import AsyncLogger

#pylint: disable=invalid-name

# Sparkfun HQ
CENTRAL_LATITUDE = 40.091244
CENTRAL_LONGITUDE = -105.185276

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
    HISTORICAL_SPEED_READINGS_COUNT = 10

    def __init__(self, kml_file_name=None):
        self._data = {}
        self._logger = AsyncLogger()
        self._speed_history = collections.deque()
        self._lock = threading.Lock()

        # TODO: For the competition, just hard code the compass. For now, the
        # Kalman filter should start reading in values and correct quickly.
        self._location_filter = LocationFilter(0.0, 0.0, 0.0)
        self._estimated_steering = 0.0
        self._estimated_throttle = 0.0

        self._target_steering = 0.0
        self._target_throttle = 0.0

        self._ignored_points = collections.defaultdict(lambda: 0)
        self._ignored_points_thresholds = collections.defaultdict(lambda: 10)

        consume = lambda: consume_messages(
            config.TELEMETRY_EXCHANGE,
            self._handle_message
        )
        thread = threading.Thread(target=consume)
        thread.name = '{}:consume_messages:{}'.format(
            self.__class__.__name__,
            config.TELEMETRY_EXCHANGE
        )
        thread.start()

        self._course_m = None
        try:
            if kml_file_name is not None:
                self.load_kml_from_file_name(kml_file_name)
                self._logger.info(
                    'Loaded {} course points and {} inner objects'.format(
                        len(self._course_m['course']),
                        len(self._course_m['inner'])
                    )
                )
            else:
                self._course_m = None

            if self._course_m is not None:
                if len(self._course_m['course']) == 0:
                    self._logger.warn(
                        'No course defined for {}'.format(kml_file_name)
                    )
                if len(self._course_m['inner']) == 0:
                    self._logger.warn(
                        'No inner obstacles defined for {}'.format(kml_file_name)
                    )
        except Exception as e:
            self._logger.error('Unable to load course file: {}'.format(e))

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
                x=round(values['x_m'], 3),
                y=round(values['y_m'], 3),
                heading=round(values['heading_d'], 3),
                speed=round(values['speed_m_s'], 3),
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

    def _handle_message(self, message):
        """Stores telemetry data from messages received from some source."""
        message = json.loads(message)
        device = message['device_id']
        if 'speed_m_s' in self._data:
            self._speed_history.append(self._data['speed_m_s'])
            while len(self._speed_history) > self.HISTORICAL_SPEED_READINGS_COUNT:
                self._speed_history.popleft()

        if 'compass_d' in message:
            self._update_estimated_drive()
            self._location_filter.update_compass(
                message['compass_d'],
                message['confidence']
            )

        if 'latitude_d' in message:
            point_d = (
                Telemetry.latitude_to_m_offset(message['latitude_d']),
                Telemetry.longitude_to_m_offset(message['longitude_d'])
            )
            if not self._m_point_in_course(point_d):
                self._ignored_points[device] += 1
                if self._ignored_points[device] > self._ignored_points_thresholds[device]:
                    self._logger.info(
                        'Dropped {} out of bounds points from {} in a row'.format(
                            self._ignored_points[device],
                            device
                        )
                    )
                    self._ignored_points[device] = 0
                    self._ignored_points_thresholds[device] += 10
                else:
                    self._logger.debug(
                        'Ignoring out of bounds point: {}'.format(point_d)
                    )
            else:
                self._ignored_points[device] = 0
                self._ignored_points_thresholds[device] = 10
                message['x_m'] = \
                    self.longitude_to_m_offset(message['longitude_d'])
                message['y_m'] = \
                    self.latitude_to_m_offset(message['latitude_d'])

                self._update_estimated_drive()
                self._location_filter.update_gps(
                    message['x_m'],
                    message['y_m'],
                    # The location filter supports accuracy in both directions,
                    # but TelemetryProducer only reports one right now. I don't
                    # think any of my sources report both right now.
                    message['accuracy_m'],
                    message['accuracy_m'],
                    message['heading_d'],
                    message['speed_m_s']
                )

            self._data = message
            self._logger.debug(json.dumps(message))

        if 'load_waypoints' in message:
            self.load_kml_from_file_name(message['load_waypoints'])

    @synchronized
    def is_stopped(self):
        """Determines if the RC car is moving."""
        if len(self._speed_history) < self.HISTORICAL_SPEED_READINGS_COUNT:
            return False

        if all((speed == 0.0 for speed in self._speed_history)):
            self._speed_history.clear()
            return True
        return False

    @synchronized
    def load_kml_from_file_name(self, kml_file_name):
        """Loads KML from a file name."""
        kml_file_name = 'paths' + os.sep + kml_file_name
        if kml_file_name.endswith('.kmz'):
            import zipfile
            with zipfile.ZipFile(kml_file_name) as archive:
                self._course_m = self._load_kml_from_stream(archive.open('doc.kml'))
        else:
            with open(kml_file_name) as stream:
                self._course_m = self._load_kml_from_stream(stream)

    def _update_estimated_drive(self):
        """Updates the estimations of the drive state, e.g. the current
        throttle and steering.
        """
        self._estimated_throttle = self._target_throttle
        self._estimated_steering = self._target_steering

        # Also tell the location filter that we've changed
        if self._estimated_throttle != self._target_throttle:
            self._location_filter.manual_throttle(
                self._estimated_throttle * MAX_SPEED_M_S
            )
        # Values for Tamiya Grasshopper, from observation. This is at .5
        # throttle, but we turn faster at higher speeds.
        BASE_MAX_TURN_RATE_D_S = 150.0
        # We always update the steering change, because we don't have sensors
        # to get estimates for it from other sources for our Kalman filter
        self._location_filter.manual_steering(
            self._estimated_steering * BASE_MAX_TURN_RATE_D_S
        )

    def _load_kml_from_stream(self, kml_stream):
        """Loads the course boundaries from a KML file."""
        course = collections.defaultdict(lambda: [])

        def get_child(element, tag_name):
            """Returns the child element with the given tag name."""
            try:
                return getattr(element, tag_name)
            except AttributeError:
                raise ValueError('No {tag} element found'.format(tag=tag_name))

        root = parser.parse(kml_stream).getroot()
        if 'kml' not in root.tag:
            self._logger.warn('Not a KML file')
            return None

        document = get_child(root, 'Document')
        for placemark in document.iterchildren():
            if not placemark.tag.endswith('Placemark'):
                continue

            try:
                polygon = get_child(placemark, 'Polygon')
            except ValueError:
                # The KML also includes Path elements; those are fine
                continue

            bound = get_child(polygon, 'outerBoundaryIs')
            ring = get_child(bound, 'LinearRing')
            coordinates = get_child(ring, 'coordinates')
            waypoints = []
            text = coordinates.text.strip()
            for csv in re.split(r'\s', text):
                (
                    longitude,
                    latitude,
                    altitude  # pylint: disable=unused-variable
                ) = csv.split(',')

                waypoints.append((
                    Telemetry.latitude_to_m_offset(float(latitude)),
                    Telemetry.longitude_to_m_offset(float(longitude)),
                ))

            if str(placemark.name).startswith('course'):
                course['course'] = waypoints
            elif str(placemark.name).startswith('inner'):
                course['inner'].append(waypoints)

        return course

    def _m_point_in_course(self, point_m):
        if self._course_m is None:
            return True
        if not self.point_in_polygon(point_m, self._course_m['course']):
            return False
        for inner in self._course_m['inner']:
            if self.point_in_polygon(point_m, inner):
                return False
        return True

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

    @staticmethod
    def intersects(a, b, c, d):
        """Returns True if two line segments intersect."""
        def ccw(a, b, c):
            return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])

        return ccw(a, c, d) != ccw(b, c, d) and ccw(a, b, c) != ccw(a, b, d)

    @staticmethod
    def point_in_polygon(point, polygon):
        """Returns true if a point is strictly inside of a simple polygon."""
        min_x = min(p[0] for p in polygon)
        min_y = min(p[1] for p in polygon)
        # To avoid degenerate parallel cases, put some arbitrary numbers here
        outside = (min_x - .029238029833, min_y - .0132323872)

        inside = False

        next_point = iter(polygon)
        next(next_point)
        for p1, p2 in zip(polygon, next_point):
            if Telemetry.intersects(outside, point, p1, p2):
                inside = not inside
        if Telemetry.intersects(outside, point, polygon[-1], polygon[0]):
            inside = not inside

        return inside
