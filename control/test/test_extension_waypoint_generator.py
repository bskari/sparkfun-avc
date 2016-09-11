"""Tests the extension waypoint generator."""
import math
import unittest


# Patch out the logger
from messaging import async_logger
from control.test.dummy_logger import DummyLogger
async_logger.AsyncLogger = DummyLogger

from control.extension_waypoint_generator import ExtensionWaypointGenerator
from control.telemetry import Telemetry

#pylint: disable=invalid-name
#pylint: disable=protected-access
#pylint: disable=too-many-public-methods


class TestExtensionWaypointGenerator(unittest.TestCase):
    """Tests the ExtensionWaypointGenerator class."""
    OFFSETS = (
        (0, 0),
        (5, 0),
        (-6, 0),
        (0, 7),
        (0, -8),
        (1, 1),
        (1, -1),
        (-1, 1),
        (-1, -1),
    )

    def test_get_current_waypoint(self):
        """Tests the extension waypoint generation."""
        points = ((20, 20),)
        generator = ExtensionWaypointGenerator(points)
        # If there's only one point, always return it
        self.assertEqual(points[0], generator.get_current_waypoint(10, 10))
        self.assertEqual(points[0], generator.get_current_waypoint(19, 19))
        self.assertEqual(points[0], generator.get_current_waypoint(21, 19))
        self.assertEqual(points[0], generator.get_current_waypoint(21, 21))
        self.assertEqual(points[0], generator.get_current_waypoint(19, 21))

        points = ((19, 19), (20, 21), (-10, 20))
        generator = ExtensionWaypointGenerator(points)
        # If we are far away, just return the point
        self.assertEqual(points[0], generator.get_current_waypoint(-100, -100))
        self.assertEqual(points[0], generator.get_current_waypoint(100, -100))
        self.assertEqual(points[0], generator.get_current_waypoint(100, 100))
        self.assertEqual(points[0], generator.get_current_waypoint(-100, 100))
        generator.next()
        self.assertEqual(points[1], generator.get_current_waypoint(-100, -100))
        self.assertEqual(points[1], generator.get_current_waypoint(100, -100))
        self.assertEqual(points[1], generator.get_current_waypoint(100, 100))
        self.assertEqual(points[1], generator.get_current_waypoint(-100, 100))
        # If we are close, project through
        waypoint = generator.get_current_waypoint(points[1][0], points[1][1])
        self.assertAlmostEqual(
            math.sqrt(
                (points[1][0] - waypoint[0]) ** 2 +
                (points[1][1] - waypoint[1]) ** 2
            ),
            ExtensionWaypointGenerator.BEYOND_M
        )
        self.assertAlmostEqual(
            Telemetry.relative_degrees(
                points[1][0],
                points[1][1],
                points[2][0],
                points[2][1]
            ),
            Telemetry.relative_degrees(
                points[1][0],
                points[1][1],
                waypoint[0],
                waypoint[1]
            )
        )

    def test_reached(self):
        """Tests the reached waypoint algorithm."""
        points = ((19, 7), (20, 21), (-10, 20))
        generator = ExtensionWaypointGenerator(points)

        # Right on top should count as reached
        self.assertTrue(generator.reached(points[0][0], points[0][1]))
        self.assertTrue(generator.reached(points[0][0] + 0.5, points[0][1]))
        self.assertTrue(generator.reached(points[0][0] - 0.5, points[0][1]))
        self.assertTrue(generator.reached(points[0][0] - 0.5, points[0][1] + 0.5))
        self.assertTrue(generator.reached(points[0][0] + 0.5, points[0][1] + 0.5))

        # Getting close, then pulling away should count too
        offset = 4.0
        while offset > 1.0:
            self.assertFalse(generator.reached(points[0][0] - offset, points[0][1] - offset))
            offset -= 0.25
        self.assertTrue(generator.reached(points[0][0] - offset - 1.0, points[0][1] - offset))

        # But pulling away should not count if we are a long way away
        generator.next()
        offset = 20.0
        while offset > 10.0:
            self.assertFalse(generator.reached(points[1][0] - offset, points[1][1] - offset))
            offset -= 0.25
        self.assertFalse(generator.reached(points[1][0] - offset - 1.0, points[1][1] - offset))
