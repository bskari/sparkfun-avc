/**
 * Provides waypoint data.
 */
pub trait WaypointGenerator {
    /**
     * Returns the current waypoint. We take in the current position so that we
     * can do fancy algorithms, like chase algorithms.
     */
    fn get_current_waypoint(&self, x_m: f32, y_m: f32) -> (f32, f32);

    /**
     * Returns the absolute position of the current waypoint.
     */
    fn get_current_raw_waypoint(&self, x_m: f32, y_m: f32) -> (f32, f32);
    
    /**
     * Moves to the next waypoint.
     */
    fn next(&self);

    /**
     * Returns true if the waypoint has been reached.
     */
    fn reached(&self, x_m: f32, y_m: f32) -> bool;

    /**
     * Returns true if there are no more waypoints.
     */
    fn done(&self) -> bool;
}
