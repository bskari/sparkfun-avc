use std::f32;
use std::iter::range_step;

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
    // So, sine and cosine appear to be messed up on Rust 0.13 on Raspberry Pi.
    // sin just returns the value, so we have to use our own implmenetation.
    let sine = degrees.sine_d();
    let cosine = degrees.cosine_d();
    (cosine * pt_x + sine * pt_y, -sine * pt_x + cosine * pt_y)
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
pub fn m_per_latitude_d() -> f32{
    equatorial_radius_m() * f32::consts::PI_2 / 360.0
}


/**
 * Returns the number of meters per degree longitude at a given latitude.
 */
pub fn latitude_d_to_m_per_longitude_d(latitude_d: f32) -> f32 {
    let radius_m = latitude_d.to_radians().cos() * equatorial_radius_m();
    let circumference_m = f32::consts::PI_2 * radius_m;
    circumference_m / 360.0
}


/**
 * Determines if the vehicle facing a heading in degrees needs to turn left to
 * left to reach a goal heading in degrees.
 */
pub fn is_turn_left(heading_d: f32, goal_heading_d: f32) -> bool {
    let (pt_1_0, pt_1_1) = rotate_degrees_clockwise((0.0f32, 1.0f32), heading_d);
    let (pt_2_0, pt_2_1) = rotate_degrees_clockwise((0.0f32, 1.0f32), goal_heading_d);
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
pub fn relative_degrees(x_1: f32, y_1: f32, x_2: f32, y_2: f32) -> f32 {
    let relative_x_m = x_2 - x_1;
    let relative_y_m = y_2 - y_1;
    if relative_x_m == 0.0 {
        if relative_y_m > 0.0 {
            return 0.0;
        }
        return 180.0;
    }

    let degrees = (relative_y_m / relative_x_m).arc_tan();
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
    // TODO: floor doesn't appear to actually return the floor of a value, so
    // uh, we need to do this weird thing instead
    let dividend = (degrees / 360.0) as i32;
    let mut return_value = degrees - dividend as f32 * 360.0;
    while return_value < 0.0 {
        return_value += 360.0;
    }
    while return_value >= 360.0 {
        return_value -= 360.0;
    }
    return return_value;
}


/**
 * Calculates the absolute difference in degrees between two headings.
 */
pub fn difference_d(heading_1_d: f32, heading_2_d: f32) -> f32 {
    let wrap_1_d = wrap_degrees(heading_1_d);
    let wrap_2_d = wrap_degrees(heading_2_d);
    let mut diff_d = (wrap_1_d - wrap_2_d).abs();
    if diff_d > 180.0 {
        diff_d = 360.0 - diff_d;
    }
    diff_d
}


/**
 * Sine, cosine, and powi appear to be broken for this build of Rust 0.12 on
 * Raspberry Pi, so I wrote my own! Taylor series expansion.
 */
trait MyTrig {
    fn pow_i(&self, exponent: i32) -> f32;
    fn sine_d(&self) -> f32;
    fn cosine_d(&self) -> f32;
    fn arc_tan(&self) -> f32;
}
impl MyTrig for f32 {
    fn pow_i(&self, exponent: i32) -> f32 {
        // TODO: Maybe do a divide and conquer if we use any large exponents
        let mut value = *self;
        for _ in range(1, exponent) {
            value *= *self;
        }
        return value;
    }
    fn sine_d(&self) -> f32 {
        let mut degrees = wrap_degrees(*self);
        if degrees > 180.0 {
            degrees = 180.0 - degrees;
        }

        // TODO: sine is cyclic every 45 degrees, so we could reduce
        // the required computations even more here by playing tricks
        if degrees > 90.0 {
            degrees = 180.0 - degrees;
        } else if degrees < -90.0 {
            degrees = -180.0 - degrees;
        }
        let pi: f32 = 3.14159265358979323846264338327950288419;
        let radians: f32 = degrees * pi / 180.0;
        radians
            - radians.pow_i(3) / 6f32 // factorial(3)
            + radians.pow_i(5) / 120f32 // factorial(5)
            - radians.pow_i(7) / 5040f32 // factorial(7)
            + radians.pow_i(9) / 362880f32 // factorial(9)
    }

    fn cosine_d(&self) -> f32 {
        (90.0 - *self).sine_d()
    }

    fn arc_tan(&self) -> f32 {
        let pi: f32 = 3.14159265358979323846264338327950288419;

        return *self
            - 1.0 / (3.0 / *self)
            + 1.0 / (5.0 / (*self).pow_i(5))
            - 1.0 / (7.0 / (*self).pow_i(7))
            ;

        /*
        if target < 1.0 {
            value = target
                + target.pow_i(3) / 3f32
                - 2.0 * target.pow_i(5) / 15f32
                + 17.0 * target.pow_i(7) / 315f32
                ;
        } else {
            value = 0.5 * pi
                - 1.0 /target 
                + 1.0 / (3.0 * target.pow_i(3))
                - 1.0 / (5.0 * target.pow_i(5))
                + 1.0 / (7.0 * target.pow_i(7))
                ;
        }
        if negative {
            -value * 180.0 / pi
        } else {
            value * 180.0 / pi
        }
        */
    }
}
#[test]
fn test_sine_d() {
    assert!((0.0f32.sine_d() - 0.0f32).abs() < 0.0001f32);
    assert!((1.0f32.sine_d() - 0.01745f32).abs() < 0.00001f32);
    assert!((5.0f32.sine_d() - 0.08716f32).abs() < 0.00001f32);
    assert!((20.0f32.sine_d() - 0.34202f32).abs() < 0.00001f32);
    assert!((45.0f32.sine_d() - 0.70711f32).abs() < 0.00001f32);
    assert!((60.0f32.sine_d() - 0.86603f32).abs() < 0.00001f32);
    assert!((90.0f32.sine_d() - 1.0f32).abs() < 0.00001f32);
    assert!((180.0f32.sine_d() - 0.0f32).abs() < 0.00001f32);
    assert!((270.0f32.sine_d() - -1.0f32).abs() < 0.00001f32);
    assert!((360.0f32.sine_d() - 0.0f32).abs() < 0.00001f32);
    assert!((720.0f32.sine_d() - 0.0f32).abs() < 0.00001f32);
    assert!((1080.0f32.sine_d() - 0.0f32).abs() < 0.00001f32);
    assert!((-45.0f32.sine_d() - -0.70711f32).abs() < 0.00001f32);
    assert!((-90.0f32.sine_d() - -1.0f32).abs() < 0.00001f32);
    assert!((-180.0f32.sine_d() - 0.0f32).abs() < 0.0001f32);
    assert!((-270.0f32.sine_d() - 1.0f32).abs() < 0.00001f32);
    assert!((-360.0f32.sine_d() - 0.0f32).abs() < 0.00001f32);
    assert!((-720.0f32.sine_d() - 0.0f32).abs() < 0.00001f32);
    assert!((-1080.0f32.sine_d() - 0.0f32).abs() < 0.00001f32);
}
#[test]
fn test_cosine_d() {
    assert!((0.0f32.cosine_d() - 1.0f32).abs() < 0.0001f32);
    assert!((45.0f32.cosine_d() - 0.70711f32).abs() < 0.00001f32);
    assert!((90.0f32.cosine_d() - 0.0f32).abs() < 0.00001f32);
    assert!((180.0f32.cosine_d() - -1.0f32).abs() < 0.00001f32);
    assert!((270.0f32.cosine_d() - 0.0f32).abs() < 0.00001f32);
    assert!((360.0f32.cosine_d() - 1.0f32).abs() < 0.00001f32);
    assert!(((-90.0f32).cosine_d() - 0.0f32).abs() < 0.00001f32);
    assert!(((-180.0f32).cosine_d() - -1.0f32).abs() < 0.00001f32);
    assert!(((-270.0f32).cosine_d() - 0.0f32).abs() < 0.00001f32);
    assert!(((-360.0f32).cosine_d() - 1.0f32).abs() < 0.00001f32);
}
#[test]
fn test_arc_tan() {
    // Expected values computed in Python from range_step(-5, 5.1, 0.1)
    let values: Vec<f32> = vec![-5.00, -4.90, -4.80, -4.70, -4.60, -4.50, -4.40, -4.30, -4.20, -4.10, -4.00, -3.90, -3.80, -3.70, -3.60, -3.50, -3.40, -3.30, -3.20, -3.10, -3.00, -2.90, -2.80, -2.70, -2.60, -2.50, -2.40, -2.30, -2.20, -2.10, -2.00, -1.90, -1.80, -1.70, -1.60, -1.50, -1.40, -1.30, -1.20, -1.10, -1.00, -0.90, -0.80, -0.70, -0.60, -0.50, -0.40, -0.30, -0.20, -0.10, 0.00, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00, 1.10, 1.20, 1.30, 1.40, 1.50, 1.60, 1.70, 1.80, 1.90, 2.00, 2.10, 2.20, 2.30, 2.40, 2.50, 2.60, 2.70, 2.80, 2.90, 3.00, 3.10, 3.20, 3.30, 3.40, 3.50, 3.60, 3.70, 3.80, 3.90, 4.00, 4.10, 4.20, 4.30, 4.40, 4.50, 4.60, 4.70, 4.80, 4.90, 5.00];
    let expected_d: Vec<f32> = vec![-78.69f32, -78.47, -78.23, -77.99, -77.74, -77.47, -77.20, -76.91, -76.61, -76.29, -75.96, -75.62, -75.26, -74.88, -74.48, -74.05, -73.61, -73.14, -72.65, -72.12, -71.57, -70.97, -70.35, -69.68, -68.96, -68.20, -67.38, -66.50, -65.56, -64.54, -63.43, -62.24, -60.95, -59.53, -57.99, -56.31, -54.46, -52.43, -50.19, -47.73, -45.00, -41.99, -38.66, -34.99, -30.96, -26.57, -21.80, -16.70, -11.31, -5.71, 0.00, 5.71, 11.31, 16.70, 21.80, 26.57, 30.96, 34.99, 38.66, 41.99, 45.00, 47.73, 50.19, 52.43, 54.46, 56.31, 57.99, 59.53, 60.95, 62.24, 63.43, 64.54, 65.56, 66.50, 67.38, 68.20, 68.96, 69.68, 70.35, 70.97, 71.57, 72.12, 72.65, 73.14, 73.61, 74.05, 74.48, 74.88, 75.26, 75.62, 75.96, 76.29, 76.61, 76.91, 77.20, 77.47, 77.74, 77.99, 78.23, 78.47, 78.69];
    for index in range(0u32, values.len() as u32) {
        let value = values[index as uint].arc_tan();
        let expected = expected_d[index as uint];
        println!("value {}, expected {}, diff {}", value, expected, (value - expected).abs());
    }
    assert!(false);
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
        assert!(approx_eq(value_1, value_2));
    }
    fn approx_eq(value_1:f32, value_2:f32) -> bool {
        // Yeah, I know this is bad, see
        // http://randomascii.wordpress.com/2012/02/25/comparing-floating-point-numbers-2012-edition/

        // This is the best we can do with f32
        let tolerance: f32 = 0.00001;
        let diff = (value_1 - value_2).abs();
        diff < tolerance
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
        let base_x = 0.0f32;
        let base_y = 1.0f32;
        let base = (base_x, base_y);

        test_rotate(base, 0.0, base);
        test_rotate(base, 45.0, (0.707106781f32, 0.707106781f32));
        test_rotate(base, 90.0, (base_y, -base_x));
        test_rotate(base, 180.0, (-base_x, -base_y));
        test_rotate(base, 270.0, (-base_y, base_x));
        test_rotate(base, 360.0, base);

        let (x_359, y_359) = rotate_degrees_clockwise(base, 359.0);
        assert!(-0.9 < x_359 && x_359 < base_x);
        assert!(y_359 > base_y && base_y > 0.9);

        test_rotate(base, -90.0, (-base_y, base_x));
        test_rotate(base, -180.0, (base_x, -base_y));
        test_rotate(base, -270.0, (base_y, base_x));
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
        println!("{}", relative_degrees(0.0, 0.0, 1.0, 1.0));
        assert_approx_eq(relative_degrees(0.0, 0.0, 1.0, 1.0), 45.0);
        println!("{}", relative_degrees(1.0, 1.0, 0.0, 0.0));
        assert_approx_eq(relative_degrees(1.0, 1.0, 0.0, 0.0), 225.0);
        println!("{}", relative_degrees(0.0, 0.0, 2.0, 2.0));
        assert_approx_eq(relative_degrees(0.0, 0.0, 2.0, 2.0), 45.0);
        println!("{}", relative_degrees(2.0, 2.0, 0.0, 0.0));
        assert_approx_eq(relative_degrees(2.0, 2.0, 0.0, 0.0), 225.0);

        println!("{}", relative_degrees(0.0, 0.0, -1.0, 1.0));
        assert_approx_eq(relative_degrees(0.0, 0.0, -1.0, 1.0), 315.0);
        println!("{}", relative_degrees(-1.0, 1.0, 0.0, 0.0));
        assert_approx_eq(relative_degrees(-1.0, 1.0, 0.0, 0.0), 135.0);
        println!("{}", relative_degrees(0.0, 0.0, -2.0, 2.0));
        assert_approx_eq(relative_degrees(0.0, 0.0, -2.0, 2.0), 315.0);
        println!("{}", relative_degrees(-2.0, 2.0, 0.0, 0.0));
        assert_approx_eq(relative_degrees(-2.0, 2.0, 0.0, 0.0), 135.0);

        println!("{}", relative_degrees(0.0, 0.0, 0.0, 1.0));
        assert_approx_eq(relative_degrees(0.0, 0.0, 0.0, 1.0), 0.0);
        println!("{}", relative_degrees(0.0, 1.0, 0.0, 0.0));
        assert_approx_eq(relative_degrees(0.0, 1.0, 0.0, 0.0), 180.0);
        println!("{}", relative_degrees(0.0, 0.0, 0.0, 2.0));
        assert_approx_eq(relative_degrees(0.0, 0.0, 0.0, 2.0), 0.0);
        println!("{}", relative_degrees(0.0, 2.0, 0.0, 0.0));
        assert_approx_eq(relative_degrees(0.0, 2.0, 0.0, 0.0), 180.0);

        println!("{}", relative_degrees(0.0, 0.0, 1.0, 0.0));
        assert_approx_eq(relative_degrees(0.0, 0.0, 1.0, 0.0), 90.0);
        println!("{}", relative_degrees(1.0, 0.0, 0.0, 0.0));
        assert_approx_eq(relative_degrees(1.0, 0.0, 0.0, 0.0), 270.0);
        println!("{}", relative_degrees(0.0, 0.0, 2.0, 0.0));
        assert_approx_eq(relative_degrees(0.0, 0.0, 2.0, 0.0), 90.0);
        println!("{}", relative_degrees(2.0, 0.0, 0.0, 0.0));
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
