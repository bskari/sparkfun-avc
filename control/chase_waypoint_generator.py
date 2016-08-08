"""Implements the WaypointGenerator interface. Returns waypoints from a KML
file. All WaypointGenerator implementations should have two methods:
    get_current_waypoint(self, x_m, y_m) -> (float, float)
    get_raw_waypoint(self) -> (float, float)
    reached(self, x_m, y_m) -> bool
    next(self)
    done(self) -> bool
    reset(self)
This implements the "rabbit chase" algorithm.
"""

import copy
import math

from control.telemetry import Telemetry
from messaging.async_logger import AsyncLogger


class ChaseWaypointGenerator(object):
    """Generates waypoints using the 'rabbit chase' algorithm."""

    def __init__(self, waypoints, distance_m=None):
        self._logger = AsyncLogger()

        if distance_m is None:
            self._distance_m = 15.0
        else:
            self._distance_m = distance_m

        self._initial_waypoints = copy.deepcopy(waypoints)
        self._waypoints = copy.deepcopy(waypoints)
        self._current_waypoint = 0

        self._last_x_m = None
        self._last_y_m = None

    def get_current_waypoint(self, x_m, y_m):
        """Returns the current waypoint."""
        if self._current_waypoint == 0:
            return self._waypoints[self._current_waypoint]
        elif len(self._waypoints) == 1:
            return self._waypoints[self._current_waypoint]
        else:
            current = self._waypoints[self._current_waypoint]
            previous = self._waypoints[self._current_waypoint - 1]
            distance_m = math.sqrt(
                (current[0] - x_m) ** 2
                + (current[1] - y_m) ** 2
            )
            if distance_m < self._distance_m:
                return self._waypoints[self._current_waypoint]

            # Find the point on the line segment from the previous waypoint to
            # the current waypoint that is self._distance_m away and that's in
            # the direction of the next waypoint
            intersections = self._circle_intersection(
                previous,
                current,
                (x_m, y_m),
                self._distance_m
            )
            if len(intersections) == 0:
                # Well, this is bad. I guess we could go for a tangent?
                self._logger.warn(
                    'No chase waypoint in range: {distance}'
                    ' from {point_1}-{point_2}, using tangent'.format(
                        distance=round(self._distance_m, 3),
                        point_1=[round(i, 3) for i in previous],
                        point_2=[round(i, 3) for i in current],
                    )
                )

                tangent_distance_m = self._tangent_distance_m(
                    (x_m, y_m),
                    previous,
                    current
                )
                if tangent_distance_m == None:
                    self._logger.warn(
                        'Unable to compute tangent, falling back to waypoint'
                    )
                    return current

                intersections = self._circle_intersection(
                    previous,
                    current,
                    (x_m, y_m),
                    tangent_distance_m + 0.1  # Avoid floating point issues
                )

            waypoint = min(
                intersections,
                key=lambda point: Telemetry.distance_m(
                    current[0],
                    current[1],
                    point[0],
                    point[1]
                )
            )
            return waypoint

        raise ValueError('No waypoints left')

    def get_raw_waypoint(self):
        """Returns the raw waypoint. Should only be used with monitors."""
        if self._current_waypoint < len(self._waypoints):
            return self._waypoints[self._current_waypoint]
        return (0.0, 0.0)

    @staticmethod
    def _circle_intersection(point_1, point_2, circle_center, circle_radius):
        """Returns an iterable list of the points of intersection between a line
        and a circle, if any.
        """
        # http://mathworld.wolfram.com/Circle-LineIntersection.html
        x_1 = point_1[0] - circle_center[0]
        x_2 = point_2[0] - circle_center[0]
        y_1 = point_1[1] - circle_center[1]
        y_2 = point_2[1] - circle_center[1]
        d_x = x_2 - x_1
        d_y = y_2 - y_1
        d_r = math.sqrt(d_x ** 2 + d_y ** 2)
        determinant = x_1 * y_2 - x_2 * y_1

        discriminant = circle_radius ** 2 * d_r ** 2 - determinant ** 2
        if discriminant < 0:
            return ()

        root = math.sqrt(discriminant)
        d_r_2 = d_r ** 2
        x_1 = (determinant * d_y + d_x * root) / d_r_2
        x_2 = (determinant * d_y - d_x * root) / d_r_2
        y_1 = (-determinant * d_x + abs(d_y) * root) / d_r_2
        y_2 = (-determinant * d_x - abs(d_y) * root) / d_r_2

        # Degenerate case of a tangent line
        if x_1 == x_2 and y_1 == y_2:
            return ((x_1 + circle_center[0], y_1 + circle_center[1]),)

        return (
            (x_1 + circle_center[0], y_1 + circle_center[1]),
            (x_2 + circle_center[0], y_2 + circle_center[1])
        )

    def reached(self, x_m, y_m):
        """Returns True if the current waypoint has been reached."""
        self._last_x_m = x_m
        self._last_y_m = y_m
        return math.sqrt(
            (x_m - self._waypoints[self._current_waypoint][0]) ** 2 +
            (y_m - self._waypoints[self._current_waypoint][1]) ** 2
        ) < 1.5

    def next(self):
        """Goes to the next waypoint."""
        self._current_waypoint += 1

    def done(self):
        """Returns True if the course is done and there are no remaining
        waypoints.
        """
        return self._current_waypoint == len(self._waypoints)

    def reset(self):
        """Resets the waypoints."""
        self._waypoints = copy.deepcopy(self._initial_waypoints)
        self._current_waypoint = 0

    @staticmethod
    def _tangent_distance_m(point, line_point_1, line_point_2):
        """Calculates the distance from a point to a tangent between two
        other points.
        """
        # https://en.wikipedia.org/wiki/Distance_from_a_point_to_a_line
        y_0, x_0 = point
        y_1, x_1 = line_point_1
        y_2, x_2 = line_point_2
        denominator = math.sqrt((y_2 - y_1) ** 2 + (x_2 - x_1) ** 2)
        if denominator == 0:
            # If this happens, then the points are on top of each other
            return None

        return abs(
            (y_2 - y_1) * x_0 - (x_2 - x_1) * y_0
            + x_2 * y_1 - y_2 * x_1
        ) / denominator
