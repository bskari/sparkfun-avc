"""Tests the Telemetry class."""
import collections
import io
import math
import unittest
import zipfile

# Patch out the logger
from messaging import async_logger
from control.test.dummy_logger import DummyLogger
async_logger.AsyncLogger = DummyLogger

from control.simple_waypoint_generator import SimpleWaypointGenerator
from control.telemetry import Telemetry

# pylint: disable=protected-access
# pylint: disable=too-many-public-methods

KML_TEMPLATE = \
'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"
    xmlns:gx="http://www.google.com/kml/ext/2.2"
    xmlns:kml="http://www.opengis.net/kml/2.2"
    xmlns:atom="http://www.w3.org/2005/Atom">
<Document>
    <name>rally-1-loop.kmz</name>
    <Placemark>
        <name>Rally 1 loop</name>
        <styleUrl>#m_ylw-pushpin</styleUrl>
        <LineString>
            <tessellate>1</tessellate>
            <coordinates>
                                {}
            </coordinates>
        </LineString>
    </Placemark>
</Document>
</kml>
'''

class TestSimpleWaypointGenerator(unittest.TestCase):
    """Tests the SimpleWaypointGenerator class."""

    def test_load_waypoints(self):
        """Tests loading waypoints from a KML format file."""
        coordinates_long_lat = zip(range(10), range(10, 0, -1))
        coordinates_str = ' '.join((
            '{},{},50'.format(long, lat) for long, lat in coordinates_long_lat
        ))
        kml = KML_TEMPLATE.format(coordinates_str).encode('utf-8')
        kml_buffer = io.BytesIO(kml)
        waypoints = SimpleWaypointGenerator._load_waypoints(kml_buffer)
        for m_offset, long_lat in zip(waypoints, coordinates_long_lat):
            x_m_1, y_m_1 = m_offset
            long_, lat = long_lat
            x_m_2 = Telemetry.longitude_to_m_offset(long_)
            y_m_2 = Telemetry.latitude_to_m_offset(lat)
            self.assertEqual(x_m_1, x_m_2)
            self.assertEqual(y_m_1, y_m_2)

    def test_get_current_waypoint(self):
        """Tests the current waypoint."""
        waypoint_generator = self.make_generator()
        waypoint = (1.0, 1.0)
        waypoint_generator._waypoints = [waypoint, (2.0, 2.0)]
        self.assertEqual(
            waypoint_generator.get_current_waypoint(10000, 10000),
            waypoint
        )
        waypoint_generator._waypoints = []
        no_waypoints = lambda: waypoint_generator.get_current_waypoint(10, 10)
        self.assertRaises(ValueError, no_waypoints)

    def test_get_raw_waypoint(self):
        """Tests the raw waypoint."""
        waypoint_generator = self.make_generator()
        waypoint = (1.0, 1.0)
        waypoint_generator._waypoints = [waypoint, (2.0, 2.0)]
        self.assertEqual(
            waypoint_generator.get_raw_waypoint(),
            waypoint
        )
        waypoint_generator._waypoints = []
        # If there are no waypoints, just return dummy data for the monitor,
        # i.e. this should not throw
        fake_point = waypoint_generator.get_raw_waypoint()
        self.assertEqual(len(fake_point), 2)

    def test_reached(self):
        """Tests waypoints being reached."""
        waypoint_generator = self.make_generator()
        waypoint = (50, 50)
        waypoint_generator._waypoints = [waypoint, (200.0, 200.0)]

        # Still a long ways away
        self.assertFalse(
            waypoint_generator.reached(
                waypoint[0] + 100.0,
                waypoint[1] + 100.0,
            )
        )
        self.assertFalse(
            waypoint_generator.reached(
                waypoint[0],
                waypoint[1] + 100.0,
            )
        )
        self.assertFalse(
            waypoint_generator.reached(
                waypoint[0] + 100.0,
                waypoint[1]
            )
        )

        # If we are close, then it counts
        self.assertTrue(
            waypoint_generator.reached(
                waypoint[0],
                waypoint[1]
            )
        )
        self.assertTrue(
            waypoint_generator.reached(
                waypoint[0] + 0.5,
                waypoint[1]
            )
        )
        self.assertTrue(
            waypoint_generator.reached(
                waypoint[0],
                waypoint[1] + 0.5
            )
        )
        self.assertTrue(
            waypoint_generator.reached(
                waypoint[0] + 0.5,
                waypoint[1] + 0.5
            )
        )

        # If we get within a certain range, and keep getting closer, then start
        # getting farther away, then that counts
        distances = [math.sqrt(2.0 + i * 0.1) for i in range(30, 0, -1)]
        for d in distances:
            self.assertFalse(
                waypoint_generator.reached(
                    waypoint[0] + d,
                    waypoint[1] + d
                )
            )
        self.assertTrue(
            waypoint_generator.reached(
                waypoint[0] + distances[-2],
                waypoint[1] + distances[-2],
            )
        )

    def test_next(self):
        """Tests the next waypoint method."""
        waypoint_generator = self.make_generator()
        length = 3
        waypoint_generator._waypoints = collections.deque(
            (i, i) for i in range(length)
        )
        for i in range(length):
            self.assertEqual(
                (i, i),
                waypoint_generator.get_current_waypoint(100.0, 100.0)
            )
            waypoint_generator.next()
        no_waypoints = lambda: waypoint_generator.get_current_waypoint(10, 10)
        self.assertRaises(ValueError, no_waypoints)

    def test_done(self):
        """Tests the done method."""
        waypoint_generator = self.make_generator()
        waypoint_generator._waypoints = collections.deque([(5, 5)])
        self.assertFalse(waypoint_generator.done())
        waypoint_generator.next()
        self.assertTrue(waypoint_generator.done())

    @staticmethod
    def test_zipped_files_smoke():
        """The generator should also support zipped KML files (KMZ)."""
        # The generator always prepends 'paths/', so force it to drop to /tmp
        archive_file_name = '../../../../../tmp/test.kmz'
        with zipfile.ZipFile(archive_file_name, 'w') as archive:
            archive.write('paths/solid-state-depot.kml', 'doc.kml')
        SimpleWaypointGenerator.get_waypoints_from_file_name(archive_file_name)

    @staticmethod
    def make_generator():
        """Returns a KML waypoint generator."""
        return SimpleWaypointGenerator(
            SimpleWaypointGenerator.get_waypoints_from_file_name(
                'paths/solid-state-depot.kml'
            )
        )
