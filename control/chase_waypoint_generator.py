"""Implements the WaypointGenerator interface. Returns waypoints from a KML
file. All WaypointGenerator implementations should have two methods:
    get_current_waypoint(self, latitude, longitude) -> (float, float)
    reached(self, latitude, longitude) -> bool
    next(self)
    done(self) -> bool
This implements the "rabbit chase" algorithm.
"""

import math

from control.telemetry import Telemetry


class ChaseWaypointGenerator(object):
    """Generates waypoints using the 'rabbit chase' algorithm."""

    def __init__(self, logger, waypoints, distance_m=None):
        self._logger = logger

        if distance_m is None:
            self._distance_m = 2.0
        else:
            self._distance_m = distance_m

        self._waypoints = waypoints
        self._current_waypoint = 0

        self._last_latitude = None
        self._last_longitude = None

    def get_current_waypoint(self, latitude, longitude):
        """Returns the current waypoint."""
        if self._current_waypoint == 0:
            return self._waypoints[self._current_waypoint]
        elif len(self._waypoints) == 1:
            return self._waypoints[self._current_waypoint]
        else:
            current = self._waypoints[self._current_waypoint]
            previous = self._waypoints[self._current_waypoint - 1]
            distance_m = Telemetry.distance_m(
                current[0],
                current[1],
                latitude,
                longitude
            )
            if distance_m < self._distance_m:
                return self._waypoints[self._current_waypoint]

            # Find the point on the line segment from the previous waypoint to
            # the current waypoint that is self._distance_m away and that's in
            # the direction of the next waypoint
            intersections = self._circle_intersection(
                previous,
                current,
                (latitude, longitude),
                self._distance_m
            )
            if len(intersections) == 0:
                # Well, this is bad. I guess we could go for a tangent?
                self._logger.warn(
                    'No chase waypoint in range: {distance}'
                    ' from {point_1}-{point_2}, using tangent'.format(
                        distance=self._distance_m,
                        point_1=previous,
                        point_2=current
                    )
                )

                tangent_distance_m = self._tangent_distance_m(
                    (latitude, longitude),
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
                    (latitude, longitude),
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

    def reached(self, latitude, longitude):
        """Returns True if the current waypoint has been reached."""
        self._last_latitude = latitude
        self._last_longitude = longitude
        return Telemetry.distance_m(
            latitude,
            longitude,
            self._waypoints[0][0],
            self._waypoints[0][1]
        ) < 1.5

    def next(self):
        """Goes to the next waypoint."""
        self._current_waypoint += 1

    def done(self):
        """Returns True if the course is done and there are no remaining
        waypoints.
        """
        return self._current_waypoint == len(self._waypoints)

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
