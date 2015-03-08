/**
 * Provides waypoint data.
 */
use telemetry::Point;
use telemetry::Meter;

pub trait WaypointGenerator {
    /**
     * Returns the current waypoint. We take in the current position so that we
     * can do fancy algorithms, like chase algorithms.
     */
    fn get_current_waypoint(&self, point: &Point) -> Point;

    /**
     * Returns the absolute position of the current waypoint.
     */
    fn get_current_raw_waypoint(&self, point: &Point) -> Point;

    /**
     * Moves to the next waypoint.
     */
    fn next(&mut self);

    /**
     * Returns true if the waypoint has been reached.
     */
    fn reached(&self, point: &Point) -> bool;

    /**
     * Returns true if there are no more waypoints.
     */
    fn done(&self) -> bool;

    /**
     * Returns the distance required to consider a waypoint as reached.
     */
    fn reach_distance(&self) -> Meter;
}
