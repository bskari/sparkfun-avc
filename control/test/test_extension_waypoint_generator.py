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

        # Project through tests
        points = ((0, 0), (0, 10), (10, 10), (10, 0), (0, 0), (5, 5), (5, 0), (5, -5), (0, 0))
        for partial in zip(points[:-1], points[1:]):
            generator = ExtensionWaypointGenerator(partial + (-100, -100))
            generator.next()
            position = partial[0]
            true_waypoint = partial[1]
            waypoint = generator.get_current_waypoint(
                partial[0][0],
                partial[0][1]
            )
            self.assertAlmostEqual(
                Telemetry.relative_degrees(
                    position[0],
                    position[1],
                    true_waypoint[0],
                    true_waypoint[1]
                ),
                Telemetry.relative_degrees(
                    position[0],
                    position[1],
                    waypoint[0],
                    waypoint[1]
                )
            )

            def distance(x1, y1, x2, y2):
                """Returns distance between 2 points."""
                return math.sqrt(
                    (x1 - x2) ** 2 + (y1 - y2) ** 2
                )

            self.assertLess(
                distance(
                    position[0],
                    position[1],
                    true_waypoint[0],
                    true_waypoint[1]
                ) + 1.0,
                distance(
                    position[0],
                    position[1],
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
