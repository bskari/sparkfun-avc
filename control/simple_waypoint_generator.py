"""Implements the WaypointGenerator interface. Returns waypoints from a KML
file. All WaypointGenerator implementations should have two methods:
    get_current_waypoint(self, x_m, y_m) -> (float, float)
    get_raw_waypoint(self) -> (float, float)
    reached(self, x_m y_m) -> bool
    next(self)
    done(self) -> bool
    reset(self)
Note that implementers don't necessarily need to return the same current
waypoint per call; this should allow interfaces to implement other algorithms,
such as the "rabbit chase" method.
"""

from pykml import parser
import copy
import json
import math
import os
import re
import threading

from control.telemetry import Telemetry
from messaging import config
from messaging.async_logger import AsyncLogger
from messaging.message_consumer import consume_messages


class SimpleWaypointGenerator(object):
    """Loads and returns waypoints from a KML file."""

    def __init__(self, waypoints):
        self._logger = AsyncLogger()
        self._waypoints = copy.deepcopy(waypoints)
        self._current_waypoint_index = 0
        self._logger.info(
            'Loaded {length} waypoints'.format(
                length=len(self._waypoints)
            )
        )
        self._last_distance_m = float('inf')

        consume = lambda: consume_messages(
            config.WAYPOINT_EXCHANGE,
            self._handle_message
        )
        thread = threading.Thread(target=consume)
        thread.name = '{}:consume_messages:{}'.format(
            self.__class__.__name__,
            config.WAYPOINT_EXCHANGE
        )
        thread.start()

    def get_current_waypoint(self, x_m, y_m):  # pylint: disable=unused-argument
        """Returns the current waypoint."""
        if self._current_waypoint_index < len(self._waypoints):
            return self._waypoints[self._current_waypoint_index]
        raise ValueError('No waypoints left')

    def get_raw_waypoint(self):
        """Returns the raw waypoint. Should only be used with monitors."""
        if self._current_waypoint_index < len(self._waypoints):
            return self._waypoints[self._current_waypoint_index]
        # Return dummy data for the monitor
        return (0.0, 0.0)

    def reached(self, x_m, y_m):
        """Returns True if the current waypoint has been reached."""
        # I was having problems with the car driving in circles looking for the
        # waypoint, so instead of having a hard cutoff of 1.5 m, count the
        # waypoint as reached if the distance is < 3m and either the distance
        # starts increasing, or the car gets within 1m
        distance_m = math.sqrt(
            (x_m - self._waypoints[self._current_waypoint_index][0]) ** 2
            + (y_m - self._waypoints[self._current_waypoint_index][1]) ** 2
        )
        if distance_m < 1.0:
            return True
        if self._last_distance_m < 3.0 and distance_m > self._last_distance_m:
            # This will get overwritten next time
            self._last_distance_m = float('inf')
            return True

        self._last_distance_m = distance_m
        return False

    def next(self):
        """Goes to the next waypoint."""
        self._current_waypoint_index += 1

    def done(self):
        """Returns True if the course is done and there are no remaining
        waypoints.
        """
        return self._current_waypoint_index >= len(self._waypoints)

    def reset(self):
        """Resets the waypoints."""
        self._current_waypoint_index = 0

    def _handle_message(self, message):
        """Handles a message from the waypoint exchange."""
        message = json.loads(str(message))
        if 'command' not in message:
            self._logger.error('Invalid waypoint message: {}'.format(message))
            return
        if message['command'] == 'load' and 'file' in message:
            try:
                self._waypoints = self.get_waypoints_from_file_name(message['file'])
                self._current_waypoint_index = 0
            except Exception as exc:  # pylint: disable=broad-except
                self._logger.error(
                    'Unable to load waypoints from {}: {}'.format(
                        message['file'],
                        exc
                    )
                )
        else:
            self._logger.error(
                'Invalid waypoint exchange message: {}'.format(message)
            )

    @classmethod
    def get_waypoints_from_file_name(cls, kml_file_name):
        """Loads the KML waypoints from a file."""
        directory = 'paths' + os.sep
        if not kml_file_name.startswith(directory):
            kml_file_name = directory + kml_file_name
        if kml_file_name.endswith('.kmz'):
            import zipfile
            with zipfile.ZipFile(kml_file_name) as archive:
                kml_stream = archive.open('doc.kml')
                return cls._load_waypoints(kml_stream)
        else:
            with open(kml_file_name) as file_:
                return cls._load_waypoints(file_)

    @staticmethod
    def _load_waypoints(kml_stream):
        """Loads and returns the waypoints from a KML string."""

        def get_child(element, tag_name):
            """Returns the child element with the given tag name."""
            try:
                return getattr(element, tag_name)
            except AttributeError:
                raise ValueError('No {tag} element found'.format(tag=tag_name))

        root = parser.parse(kml_stream).getroot()
        if 'kml' not in root.tag:
            raise ValueError('Not a KML file')

        document = get_child(root, 'Document')
        placemark = get_child(document, 'Placemark')
        line_string = get_child(placemark, 'LineString')
        # Unlike all of the other tag names, "coordinates" is not capitalized
        coordinates = get_child(line_string, 'coordinates')

        waypoints = []
        text = coordinates.text.strip()
        for csv in re.split(r'\s', text):
            (
                longitude,
                latitude,
                altitude  # pylint: disable=unused-variable
            ) = csv.split(',')

            waypoints.append((
                Telemetry.longitude_to_m_offset(float(longitude), float(latitude)),
                Telemetry.latitude_to_m_offset(float(latitude))
            ))
        return waypoints
