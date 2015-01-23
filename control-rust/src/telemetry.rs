use std::f32;

use telemetry_message::TelemetryMessage;

/**
 * Provides Telemetry data, possibly filtered to be more accurate.
 */
pub trait Telemetry {
    /**
     * Returns the raw sensor readings.
     */
    fn get_raw_data(&self) -> &TelemetryMessage;

    /**
     * Returns the (possibly filtered) telemetry data.
     */
    fn get_data(&self) -> &TelemetryMessage;

    /**
     * End point for processing commands executed by the Command module.
     */
    fn process_drive_command(&mut self, throttle:f32, steering:f32) -> ();

    /**
     * Processes a telemetry message.
     */
    fn handle_message(&self, message:&TelemetryMessage) -> ();

    /**
     * Returns true if the car is stopped.
     */
    fn is_stopped(&self) -> bool;
}


/**
 * Rotates a point a number of degrees clockwise around the origin.
 */
pub fn rotate_degrees_clockwise(point:(f32, f32), degrees:f32) -> (f32, f32) {
    let (pt_x, pt_y) = point;
    let (sine, cosine) = (-degrees).to_radians().sin_cos();

    (pt_x * cosine - pt_y * sine, pt_x * sine + pt_y * cosine)
}


/**
 * Returns the equatorial radius of the Earth in meters. I don't know how to
 * define constants in Rust.
 */
fn equatorial_radius_m() -> f32 {
    6378.1370 * 1000.0
}


/**
 * Returns the number of meters per degree of latitude. I don't know how to
 * define constants in Rust.
 */
fn m_per_latitude_d() -> f32{
    equatorial_radius_m() * f32::consts::PI_2 / 360.0
}


/**
 * Returns the number of meters per degree longitude at a given latitude.
 */
fn latitude_d_to_m_per_longitude_d(latitude_d: f32) -> f32 {
    let radius_m = latitude_d.to_radians().cos() * equatorial_radius_m();
    let circumference_m = f32::consts::PI_2 * radius_m;
    circumference_m / 360.0
}


/**
 * Determines if the vehicle facing a heading in degrees needs to turn left to
 * left to reach a goal heading in degrees.
 */
fn is_turn_left(heading_d: f32, goal_heading_d: f32) -> bool {
    let (pt_1_0, pt_1_1) = rotate_degrees_clockwise((1.0f32, 0.0f32), heading_d);
    let (pt_2_0, pt_2_1) = rotate_degrees_clockwise((1.0f32, 0.0f32), goal_heading_d);
    let cross_product = pt_1_0 * pt_2_1 - pt_1_1 * pt_2_0;
    if cross_product > 0.0 {
        return true;
    }
    return false;
}


/**
 * Computes the relative degrees from the first waypoint to the second, where
 * north is 0.
 */
fn relative_degrees(x_1: f32, y_1: f32, x_2: f32, y_2: f32) -> f32 {
    let relative_x_m = x_2 - x_1;
    let relative_y_m = y_2 - y_1;
    if relative_x_m == 0.0 {
        if relative_y_m > 0.0 {
            return 0.0;
        }
        return 180.0;
    }

    let degrees = (relative_y_m / relative_x_m).atan().to_degrees();
    if relative_x_m > 0.0 {
        return 90.0 - degrees;
    } else {
        return 270.0 - degrees;
    }
}


/**
 * Wraps degrees to be in [0..360).
 */
pub fn wrap_degrees(degrees: f32) -> f32 {
    let dividend = (degrees / 360.0).floor();
    (degrees - dividend * 360.0) % 360.0
}


/**
 * Calculates the absolute difference in degrees between two headings.
 */
fn difference_d(heading_1_d: f32, heading_2_d: f32) -> f32 {
    let wrap_1_d = wrap_degrees(heading_1_d);
    let wrap_2_d = wrap_degrees(heading_2_d);
    let mut diff_d = (wrap_1_d - wrap_2_d).abs();
    if diff_d > 180.0 {
        diff_d = 360.0 - diff_d;
    }
    diff_d
}


#[cfg(test)]
mod tests {
    use std::f32;
    use super::difference_d;
    use super::equatorial_radius_m;
    use super::is_turn_left;
    use super::latitude_d_to_m_per_longitude_d;
    use super::relative_degrees;
    use super::rotate_degrees_clockwise;
    use super::wrap_degrees;


    fn assert_approx_eq(value_1:f32, value_2:f32) -> () {
        // Yeah, I know this is bad, see
        // http://randomascii.wordpress.com/2012/02/25/comparing-floating-point-numbers-2012-edition/

        // This is the best we can do with f32
        let tolerance: f32 = 0.00001;
        let diff = (value_1 - value_2).abs();
        assert!(diff < tolerance, "{} < {} failed", diff, tolerance);
    }


    fn test_rotate(point:(f32, f32), degrees:f32, expected_point:(f32, f32)) -> () {
        let new_point = rotate_degrees_clockwise(point, degrees);
        let (p_1, p_2) = new_point;
        let (ep_1, ep_2) = expected_point;
        assert_approx_eq(p_1, ep_1);
        assert_approx_eq(p_2, ep_2);
    }

    #[test]
    fn test_rotate_degrees_clockwise() {
        let base_x = 1.0f32;
        let base_y = 0.0f32;
        let base = (base_x, base_y);

        test_rotate(base, 0.0, base);
        test_rotate(base, 90.0, (base_y, -base_x));
        test_rotate(base, 180.0, (-base_x, base_y));
        test_rotate(base, 270.0, (base_y, base_x));
        test_rotate(base, 360.0, base);

        test_rotate(base, -90.0, (base_y, base_x));
        test_rotate(base, -180.0, (-base_x, base_y));
        test_rotate(base, -270.0, (base_y, -base_x));
        test_rotate(base, -360.0, base);

        test_rotate(base, 720.0, base);
        test_rotate(base, -720.0, base);

        let skewed_x = 1.0;
        let skewed_y = 2.0;
        let skewed = (skewed_x, skewed_y);

        test_rotate(skewed, 0.0, skewed);
        test_rotate(skewed, 90.0, (skewed_y, -skewed_x));
        test_rotate(skewed, 180.0, (-skewed_x, -skewed_y));
        test_rotate(skewed, 270.0, (-skewed_y, skewed_x));
        test_rotate(skewed, 360.0, skewed);

        test_rotate(skewed, -90.0, (-skewed_y, skewed_x));
        test_rotate(skewed, -180.0, (-skewed_x, -skewed_y));
        test_rotate(skewed, -270.0, (skewed_y, -skewed_x));
        test_rotate(skewed, -360.0, skewed);

        test_rotate(skewed, 720.0, skewed);
        test_rotate(skewed, -720.0, skewed);
    }

    #[test]
    fn test_latitude_d_to_m_per_longitude_d_spherical() {
        // Assume Earth is a sphere
        assert_approx_eq(
            equatorial_radius_m() * f32::consts::PI_2 / 360.0,
            latitude_d_to_m_per_longitude_d(0.0)
        );

        // Should be symmetrical
        for degrees in range(0i32, 85) {
            assert_approx_eq(
                latitude_d_to_m_per_longitude_d(degrees as f32),
                latitude_d_to_m_per_longitude_d(-degrees as f32)
            );
        }

        // At the poles, should be 0
        let diff = (latitude_d_to_m_per_longitude_d(90.0)).abs();
        assert!(diff < 0.01);
    }

    #[test]
    #[should_fail]  // We're using a less accurate spherical method right now
    fn test_latitude_d_to_m_per_longitude_d_oblong() {
        // Known values, from http://www.csgnetwork.com/degreelenllavcalc.html
        // M_PER_D_LATITUDE = 111319.458,
        assert_approx_eq(
            // Boulder
            latitude_d_to_m_per_longitude_d(40.08),
            85294.08886768305,
        );
    }

    #[test]
    fn test_is_turn_left() {
        assert!(is_turn_left(1.0, 0.0));
        assert!(!is_turn_left(0.0, 1.0));

        assert!(is_turn_left(1.0, 359.0));
        assert!(!is_turn_left(359.0, 1.0));

        assert!(is_turn_left(1.0, 270.0));
        assert!(is_turn_left(0.0, 270.0));
        assert!(is_turn_left(359.0, 270.0));

        assert!(!is_turn_left(1.0, 90.0));
        assert!(!is_turn_left(0.0, 90.0));
        assert!(!is_turn_left(359.0, 90.0));
    }


    #[test]
    fn test_relative_degrees() {
        assert_approx_eq(relative_degrees(0.0, 0.0, 1.0, 1.0), 45.0);
        assert_approx_eq(relative_degrees(1.0, 1.0, 0.0, 0.0), 225.0);
        assert_approx_eq(relative_degrees(0.0, 0.0, 2.0, 2.0), 45.0);
        assert_approx_eq(relative_degrees(2.0, 2.0, 0.0, 0.0), 225.0);

        assert_approx_eq(relative_degrees(0.0, 0.0, -1.0, 1.0), 315.0);
        assert_approx_eq(relative_degrees(-1.0, 1.0, 0.0, 0.0), 135.0);
        assert_approx_eq(relative_degrees(0.0, 0.0, -2.0, 2.0), 315.0);
        assert_approx_eq(relative_degrees(-2.0, 2.0, 0.0, 0.0), 135.0);

        assert_approx_eq(relative_degrees(0.0, 0.0, 0.0, 1.0), 0.0);
        assert_approx_eq(relative_degrees(0.0, 1.0, 0.0, 0.0), 180.0);
        assert_approx_eq(relative_degrees(0.0, 0.0, 0.0, 2.0), 0.0);
        assert_approx_eq(relative_degrees(0.0, 2.0, 0.0, 0.0), 180.0);

        assert_approx_eq(relative_degrees(0.0, 0.0, 1.0, 0.0), 90.0);
        assert_approx_eq(relative_degrees(1.0, 0.0, 0.0, 0.0), 270.0);
        assert_approx_eq(relative_degrees(0.0, 0.0, 2.0, 0.0), 90.0);
        assert_approx_eq(relative_degrees(2.0, 0.0, 0.0, 0.0), 270.0);
    }


    #[test]
    fn test_wrap_degrees() {
        for d in range(0i32, 360) {
            assert_approx_eq(d as f32, wrap_degrees(d as f32));
        }

        assert_approx_eq(0.0, wrap_degrees(0.0));
        assert_approx_eq(0.0, wrap_degrees(360.0));
        assert_approx_eq(359.0, wrap_degrees(-1.0));
        assert_approx_eq(359.0, wrap_degrees(-361.0));
        assert_approx_eq(1.0, wrap_degrees(361.0));
        assert_approx_eq(1.0, wrap_degrees(721.0));
        assert_approx_eq(0.1, wrap_degrees(360.1));
        assert_approx_eq(0.1, wrap_degrees(0.1));
        assert_approx_eq(359.9, wrap_degrees(-0.1));
        assert_approx_eq(0.0, wrap_degrees(360.0));
    }


    #[test]
    fn test_difference_d() {
        assert_approx_eq(difference_d(359.0, 0.0), 1.0);
        assert_approx_eq(difference_d(0.0, 1.0), 1.0);
        assert_approx_eq(difference_d(359.0, 1.0), 2.0);
        assert_approx_eq(difference_d(360.0, 365.0), 5.0);
        assert_approx_eq(difference_d(-355.0, 365.0), 0.0);
        assert_approx_eq(difference_d(360.0, 0.0), 0.0);
        assert_approx_eq(difference_d(0.0, 360.0), 0.0);
        assert_approx_eq(difference_d(361.0, 1.0), 0.0);
        assert_approx_eq(difference_d(1.0, 361.0), 0.0);
        assert_approx_eq(difference_d(90.0 - 360.0, 90.0 + 360.0), 0.0);
    }
}
