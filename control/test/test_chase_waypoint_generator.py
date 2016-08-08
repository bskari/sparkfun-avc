"""Tests the Telemetry class."""
import math
import unittest

# Patch out the logger
from messaging import async_logger
from control.test.dummy_logger import DummyLogger
async_logger.AsyncLogger = DummyLogger

from control.chase_waypoint_generator import ChaseWaypointGenerator

#pylint: disable=invalid-name
#pylint: disable=protected-access
#pylint: disable=too-many-public-methods


class TestChaseWaypointGenerator(unittest.TestCase):
    """Tests the ChaseWaypointGenerator class."""
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

    def test_circle_intersection_none(self):
        """Tests circle line intersection none case."""
        intersections = ChaseWaypointGenerator._circle_intersection(
            (-5, 0),
            (5, 0),
            (0, -10),
            9
        )
        self.assertEqual(len(intersections), 0)

    def test_circle_intersection_degenerate(self):
        """Tests circle line intersection degenerate case."""


    def test_circle_intersection_dual(self):
        """Tests circle line intersection two points case."""

        def _almost_equal_set_of_points(list_1, list_2, offset):
            """Tests a set of points for approximate equality."""
            for point_1 in list_1:
                matched = False
                for point_2 in list_2:
                    point_2 = self._add(point_2, offset)
                    if (
                            abs(point_1[0] - point_2[0]) < 0.00001
                            and abs(point_1[1] - point_2[1]) < 0.00001
                    ):
                        matched = True
                        break
                if not matched:
                    return False
            return True

        for p_1, p_2, circle, radius, expected in (
                # Vertical
                ((0, -10), (0, 10), (0, 0), 1, ((0, -1), (0, 1))),
                # Horizontal
                ((-3, 0), (300, 0), (0, 0), 2, ((2, 0), (-2, 0))),
        ):
            for offset in self.OFFSETS:
                intersections = ChaseWaypointGenerator._circle_intersection(
                    self._add(p_1, offset),
                    self._add(p_2, offset),
                    self._add(circle, offset),
                    radius
                )
                self.assertEqual(len(intersections), 2)
                self.assertTrue(
                    _almost_equal_set_of_points(
                        intersections,
                        expected,
                        offset
                    ),
                    'Calculated {}, expected {}'.format(intersections, expected)
                )

                intersections = ChaseWaypointGenerator._circle_intersection(
                    self._add(p_1, offset),
                    self._add(p_2, offset),
                    self._add(circle, offset),
                    radius
                )
                self.assertEqual(len(intersections), 2)
                self.assertTrue(
                    _almost_equal_set_of_points(
                        intersections,
                        expected,
                        offset
                    ),
                    'Calculated {}, expected {}'.format(intersections, expected)
                )

        # Diagonal
        # This case is degenerate itself, because it relies on floating point
        p_1, p_2, circle, radius, expected = (
            (-2, 0), (0, 2), (0, 0), math.sqrt(2), (-1, 1)
        )
        intersections = ChaseWaypointGenerator._circle_intersection(
            p_1,
            p_2,
            circle,
            radius
        )
        self.assertGreaterEqual(len(intersections), 1)
        for intersection in intersections:
            for value, expected_value in zip(intersection, expected):
                self.assertAlmostEqual(value, expected_value)

    @staticmethod
    def _add(point_1, point_2):
        """Adds two points."""
        return (point_1[0] + point_2[0], point_1[1] + point_2[1])

    def test_tangent_distance_m(self):
        """Tests the tangent distance calculation."""
        for point, line_point_1, line_point_2, expected in (
                ((0, 0), (0, 1), (1, 0), math.sqrt(2) * 0.5),
                ((0, 0), (0, 2), (2, 0), math.sqrt(8) * 0.5),
                ((0, 0), (-2, 0), (0, 2), math.sqrt(8) * 0.5),
                ((0, 0), (-2, 0), (-1, 1), math.sqrt(8) * 0.5),
                ((0, 0), (-2, 0), (0, 1), 0.8944271909),
        ):
            for offset in self.OFFSETS:
                distance_m = ChaseWaypointGenerator._tangent_distance_m(
                    self._add(point, offset),
                    self._add(line_point_1, offset),
                    self._add(line_point_2, offset)
                )
                self.assertAlmostEqual(distance_m, expected)

                distance_m = ChaseWaypointGenerator._tangent_distance_m(
                    self._add(point, offset),
                    self._add(line_point_2, offset),
                    self._add(line_point_1, offset)
                )
                self.assertAlmostEqual(distance_m, expected)

    def test_get_current_waypoint(self):
        """Tests the chase waypoint generation."""
        points = ((20, 20),)
        generator = ChaseWaypointGenerator(points)
        self.assertEqual(points[0], generator.get_current_waypoint(19, 19))

        points = ((20, 20), (21, 21))
        generator = ChaseWaypointGenerator(points)
        self.assertEqual(points[0], generator.get_current_waypoint(19, 19))

        points = ((0, 0), (0, 1), (0, 2), (0, 3))
        generator = ChaseWaypointGenerator(points)
        generator._current_waypoint = len(points) // 2
        waypoint = generator.get_current_waypoint(-1, 0.5)
        self.assertEqual(waypoint[0], 0)
        waypoint = generator.get_current_waypoint(0.00000001, 0.5)
        self.assertAlmostEqual(waypoint[0], 0)
        self.assertGreater(waypoint[1], 0.5)
