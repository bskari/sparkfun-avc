"""Implements the WaypointGenerator interface. Returns waypoints from a KML
file. All WaypointGenerator implementations should have two methods:
    get_current_waypoint(self) -> (float, float)
    reached(self, latitude, longitude) -> bool
    next(self)
    done(self) -> bool
Note that implementers don't necessarily need to return the same current
waypoint per call; this should allow interfaces to implement other algorithms,
such as the "rabbit chase" method.
"""

from xml.etree import ElementTree
import collections
import zipfile

from telemetry import Telemetry


class KmlWaypointGenerator(object):
    """Loads and returns waypoints from a KML file."""

    def __init__(self, logger, kml_file_name):
        with zipfile.ZipFile(kml_file_name) as archive:
            kml_string = archive.open('doc.kml').read()
            self._waypoints = self._load_waypoints(kml_string)
            logger.info(
                'Loaded {length} waypoints'.format(
                    length=len(self._waypoints)
                )
            )

    def get_current_waypoint(self):
        """Returns the current waypoint."""
        if len(self._waypoints) > 0:
            return self._waypoints[0]
        raise ValueError('No waypoints left')

    def reached(self, latitude, longitude):
        """Returns True if the current waypoint has been reached."""
        return Telemetry.distance_m(
            latitude,
            longitude,
            self._waypoints[0][0],
            self._waypoints[0][1]
        ) < 1.5

    def next(self):
        """Goes to the next waypoint."""
        self._waypoints.popleft()

    def done(self):
        """Returns True if the course is done and there are no remaining
        waypoints.
        """
        return len(self._waypoints) == 0

    @staticmethod
    def _load_waypoints(kml_string):
        """Loads and returns the waypoints from a KML path file."""

        def get_child(element, tag_name):
            """Returns the child element with the given tag name."""
            for child in element:
                if tag_name in child.tag:
                    return child
            raise ValueError('No {tag} element found'.format(tag=tag_name))

        root = ElementTree.fromstring(kml_string)
        if 'kml' not in root.tag:
            raise ValueError('Not a KML file')

        document = get_child(root, 'Document')
        placemark = get_child(document, 'Placemark')
        line_string = get_child(placemark, 'LineString')
        # Unlike all of the other tag names, "coordinates" is not capitalized
        coordinates = get_child(line_string, 'coordinates')

        waypoints = collections.deque()
        text = coordinates.text.strip()
        for csv in text.split(' '):
            (
                longitude,
                latitude,
                altitude  # pylint: disable=unused-variable
            ) = csv.split(',')

            waypoints.append((float(latitude), float(longitude)))
        return waypoints
