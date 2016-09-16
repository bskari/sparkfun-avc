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
    BEYOND_M_2 = BEYOND_M ** 2

    def __init__(self, waypoints):
        super(ExtensionWaypointGenerator, self).__init__(waypoints)

    def get_current_waypoint(self, x_m, y_m):
        """Returns the current waypoint as projected BEYOND_M past."""
        return self._get_extended_waypoint(x_m, y_m)

    def next(self):
        """Goes to the next waypoint."""
        super(ExtensionWaypointGenerator, self).next()

    def reached(self, x_m, y_m):
        """Returns True if the current waypoint has been reached."""
        if super(ExtensionWaypointGenerator, self).reached(x_m, y_m):
            return True
        # Because the car is trying to go for the extension, the car might
        # pass the actual waypoint and keep on driving, so check if it's close
        # to the extension as well
        current_waypoint = self.get_current_waypoint(x_m, y_m)
        distance_m_2 = (
            (x_m - current_waypoint[0]) ** 2
            + (y_m - current_waypoint[1]) ** 2
        )
        if distance_m_2 < self.BEYOND_M_2:
            return True
        return False

    def _get_extended_waypoint(self, x_m, y_m):
        """Returns the extended waypoint."""
        if self._current_waypoint_index == 0:
            return self._waypoints[0]
        if (
                self._current_waypoint_index >= 1
                and self._current_waypoint_index < len(self._waypoints)
        ):
            previous_waypoint_m = self._waypoints[
                self._current_waypoint_index - 1
            ]
            current_waypoint_m = self._waypoints[self._current_waypoint_index]

            degrees = Telemetry.relative_degrees(
                previous_waypoint_m[0],
                previous_waypoint_m[1],
                current_waypoint_m[0],
                current_waypoint_m[1]
            )
            distance_to_current_m = math.sqrt(
                (x_m - current_waypoint_m[0]) ** 2 +
                (y_m - current_waypoint_m[1]) ** 2
            )
            offset_m = Telemetry.rotate_degrees_clockwise(
                (0.0, self.BEYOND_M - distance_to_current_m),
                degrees
            )
            # TODO(2016-09-15): If we're coming at the waypoint from the
            # opposite direction, this will make the car drive past the point
            # before doubling back. Prevent that.
            return (
                current_waypoint_m[0] + offset_m[0],
                current_waypoint_m[1] + offset_m[1]
            )

        return self._waypoints[-1]
