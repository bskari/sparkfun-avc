"""Implements the WaypointGenerator interface. Returns waypoints from a KML
file. All WaypointGenerator implementations should have two methods:
    get_current_waypoint(self, x_m, y_m) -> (float, float)
    get_raw_waypoint(self) -> (float, float)
    reached(self, x_m, y_m) -> bool
    next(self)
    done(self) -> bool
    reset(self)
This implements an extension of the goal beyond the actual waypoint to try to
reduce oscillating.
"""

import math

from control.telemetry import Telemetry
from control.simple_waypoint_generator import SimpleWaypointGenerator


class ExtensionWaypointGenerator(SimpleWaypointGenerator):
    """Generates waypoints extending through the actual waypoint to try to
    reduce oscillating.
    """

    BEYOND_M = 5.0

    def __init__(self, waypoints):
        super(ExtensionWaypointGenerator, self).__init__(waypoints)

    def get_current_waypoint(self, x_m, y_m):
        """Returns the current waypoint."""
        if len(self._waypoints) == 1:
            return self._waypoints[0]
        elif len(self._waypoints) > 1:
            current_waypoint_m = self._waypoints[0]
            distance_m = math.sqrt(
                (current_waypoint_m[0] - x_m) ** 2
                + (current_waypoint_m[1] - y_m) ** 2
            )
            if distance_m > self.BEYOND_M:
                return current_waypoint_m
            past_m = self.BEYOND_M - distance_m
            next_waypoint_m = self._waypoints[1]

            degrees = Telemetry.relative_degrees(
                current_waypoint_m[0],
                current_waypoint_m[1],
                next_waypoint_m[0],
                next_waypoint_m[1]
            )
            offset_m = Telemetry.rotate_degrees_clockwise(
                (0.0, past_m),
                degrees
            )
            return (
                current_waypoint_m[0] + offset_m[0],
                current_waypoint_m[1] + offset_m[1]
            )

        raise ValueError('No waypoints left')
