use std::f64;

use telemetry_message::CompassMessage;
use telemetry_message::GpsMessage;
use telemetry_message::TelemetryMessage;


pub type Meter = f32;
pub type Degrees = f32;
pub type MetersPerSecond = f32;
#[derive(Clone)]
#[derive(Copy)]
pub struct Point {
    pub x: Meter,
    pub y: Meter,
}

#[derive(Clone)]
#[derive(Copy)]
pub struct TelemetryState {
    pub location: Point,
    pub heading: Degrees,
    pub speed: MetersPerSecond,
    pub stopped: bool,
}


/**
 * Provides Telemetry data, possibly filtered to be more accurate.
 */
pub trait Telemetry {
    /**
     * Returns the raw sensor readings.
     */
    fn get_raw_gps(&self) -> &GpsMessage;

    /**
     * Returns the raw sensor readings.
     */
    fn get_raw_compass(&self) -> &CompassMessage;

    /**
     * Returns the (possibly filtered) telemetry data.
     */
    fn get_data(&self) -> &TelemetryState;

    /**
     * End point for processing commands executed by the Command module.
     */
    fn process_drive_command(&mut self, throttle:f32, steering:f32);

    /**
     * Processes a telemetry message.
     */
    fn handle_message(&mut self, message:&TelemetryMessage);

    /**
     * Returns true if the car is stopped.
     */
    fn is_stopped(&self) -> bool;
}


/**
 * Rotates a point a number of degrees clockwise around the origin.
 */
#[allow(dead_code)]
pub fn rotate_degrees_clockwise(point: &Point, degrees: Degrees) -> Point {
    let sine = degrees.sine_d();
    let cosine = degrees.cosine_d();
    Point {
        x: cosine * point.x + sine * point.y,
        y: -sine * point.x + cosine * point.y
    }
}


/**
 * Returns the equatorial radius of the Earth in meters. I don't know how to
 * define constants in Rust.
 */
fn equatorial_radius_m() -> f64 {
    6378.1370 * 1000.0
}


/**
 * Returns the number of meters per degree of latitude. I don't know how to
 * define constants in Rust.
 */
pub fn m_per_latitude_d() -> f64 {
    equatorial_radius_m() * f64::consts::PI_2 / 360.0
}


/**
 * Returns the number of meters per degree longitude at a given latitude.
 */
pub fn latitude_d_to_m_per_longitude_d(latitude: f64) -> f64 {
    let radius_m: f64 = latitude.cosine_d() * equatorial_radius_m();
    let circumference_m: f64 = f64::consts::PI_2 * radius_m;
    circumference_m / 360.0
}


/**
 * Determines if the vehicle facing a heading in degrees needs to turn left to
 * left to reach a goal heading in degrees.
 */
#[allow(dead_code)]
pub fn is_turn_left(heading_d: Degrees, goal_heading_d: Degrees) -> bool {
    let point_1 = rotate_degrees_clockwise(&Point { x: 0.0, y: 1.0 }, heading_d);
    let (pt_1_0, pt_1_1) = (point_1.x, point_1.y);
    let point_2 = rotate_degrees_clockwise(&Point { x: 0.0, y: 1.0 }, goal_heading_d);
    let (pt_2_0, pt_2_1) = (point_2.x, point_2.y);
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
#[allow(dead_code)]
pub fn relative_degrees(point_1: &Point, point_2: &Point) -> Degrees {
    let relative_x_m = point_2.x - point_1.x;
    let relative_y_m = point_2.y - point_1.y;
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
#[allow(dead_code)]
pub fn wrap_degrees(degrees: Degrees) -> Degrees {
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
#[allow(dead_code)]
pub fn difference_d(heading_1: Degrees, heading_2: Degrees) -> Degrees {
    let wrap_1_d = wrap_degrees(heading_1);
    let wrap_2_d = wrap_degrees(heading_2);
    let mut diff_d = (wrap_1_d - wrap_2_d).abs();
    if diff_d > 180.0 {
        diff_d = 360.0 - diff_d;
    }
    diff_d
}


/**
 * Distance between 2 points.
 */
pub fn distance(point_1: &Point, point_2: &Point) -> Meter {
    let diff_x = (point_1.x - point_2.x).abs();
    let diff_y = (point_1.y - point_2.y).abs();
    (diff_x * diff_x + diff_y * diff_y).sqrt()
}


/**
 * Latitude and longitude to meters from an arbitrary central location. The Pi only single
 * precision hardware float capability which affords 6~9 digits of precision. If we only used
 * latitude and longitude, we would need double prevision everywhere, which would run slowly on the
 * Pi. As long as we're within a kilometer of the central point, we should have at least centimeter
 * precision, which should work fine.
 */
pub fn latitude_longitude_to_point(latitude: f64, longitude: f64) -> Point {
    let central_latitude = 40.0941804f64;
    let central_longitude = -105.1872092f64;
    let latitude_diff = latitude - central_latitude;
    let longitude_diff = longitude - central_longitude;
    Point {
        // Hopefully LLVM will optimize this call out
        x: (latitude_d_to_m_per_longitude_d(central_latitude) * longitude_diff) as f32,
        y: (m_per_latitude_d() * latitude_diff) as f32,
    }
}


/**
 * Estimation of converting HDOP to standard deviation. This is a complete guess.
 */
pub fn hdop_to_std_dev(hdop: f32) -> Meter {
    hdop * 2.0
}


/**
 * Sine, cosine, and powi appear to be broken for this build of Rust 0.12 on
 * Raspberry Pi, so I wrote my own! Taylor series expansion.
 */
trait MyTrig {
    fn sine_d(&self) -> Self;
    fn cosine_d(&self) -> Self;
}
impl MyTrig for f32 {
    fn sine_d(&self) -> f32 {
        self.to_radians().sin()
    }

    fn cosine_d(&self) -> f32 {
        self.to_radians().cos()
    }
}
impl MyTrig for f64 {
    fn sine_d(&self) -> f64{
        self.to_radians().sin()
    }

    fn cosine_d(&self) -> f64{
        self.to_radians().cos()
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


#[cfg(test)]
mod tests {
    use std::f64;
    use std::num::{Float, FromPrimitive};
    use super::{
        Point,
        Degrees,
        difference_d,
        distance,
        equatorial_radius_m,
        is_turn_left,
        latitude_d_to_m_per_longitude_d,
        relative_degrees,
        rotate_degrees_clockwise,
        wrap_degrees,
    };

    fn assert_approx_eq<T: Float + FromPrimitive>(value_1: T, value_2: T) {
        assert!(approx_eq(value_1, value_2));
    }
    fn approx_eq<T: Float + FromPrimitive>(value_1: T, value_2: T) -> bool {
        // Yeah, I know this is bad, see
        // http://randomascii.wordpress.com/2012/02/25/comparing-floating-point-numbers-2012-edition/

        let diff = (value_1 - value_2).abs();
        // This is the best we can do with f32
        diff < FromPrimitive::from_f32(0.00001f32).unwrap()
    }


    fn test_rotate(point: &Point, degrees: Degrees, expected_point: &Point) {
        let new_point = rotate_degrees_clockwise(point, degrees);
        assert_approx_eq(new_point.x, expected_point.x);
        assert_approx_eq(new_point.y, expected_point.y);
    }

    #[test]
    fn test_rotate_degrees_clockwise() {
        let base_x = 0.0f32;
        let base_y = 1.0f32;
        let base = Point { x: base_x, y: base_y };

        test_rotate(&base, 0.0, &base);
        test_rotate(&base, 45.0, &Point { x: 0.707106781f32, y: 0.707106781f32 });
        test_rotate(&base, 90.0, &Point { x: base_y, y: -base_x });
        test_rotate(&base, 180.0, &Point { x: -base_x, y: -base_y });
        test_rotate(&base, 270.0, &Point { x: -base_y, y: base_x });
        test_rotate(&base, 360.0, &base);

        let point_359 = rotate_degrees_clockwise(&base, 359.0);
        let (x_359, y_359) = (point_359.x, point_359.y);
        assert!(-0.1 < x_359 && x_359 < base_x);
        assert!(0.9 < y_359 && y_359 < base_y);

        test_rotate(&base, -90.0, &Point { x: -base_y, y: base_x });
        test_rotate(&base, -180.0, &Point { x: base_x, y: -base_y });
        test_rotate(&base, -270.0, &Point { x: base_y, y: base_x });
        test_rotate(&base, -360.0, &base);

        test_rotate(&base, 720.0, &base);
        test_rotate(&base, -720.0, &base);

        let skewed_x = 1.0;
        let skewed_y = 2.0;
        let skewed = Point { x: skewed_x, y: skewed_y };

        test_rotate(&skewed, 0.0, &skewed);
        test_rotate(&skewed, 90.0, &Point { x: skewed_y, y: -skewed_x });
        test_rotate(&skewed, 180.0, &Point { x: -skewed_x, y: -skewed_y });
        test_rotate(&skewed, 270.0, &Point { x: -skewed_y, y: skewed_x });
        test_rotate(&skewed, 360.0, &skewed);

        test_rotate(&skewed, -90.0, &Point { x: -skewed_y, y: skewed_x });
        test_rotate(&skewed, -180.0, &Point { x: -skewed_x, y: -skewed_y });
        test_rotate(&skewed, -270.0, &Point { x: skewed_y, y: -skewed_x });
        test_rotate(&skewed, -360.0, &skewed);

        test_rotate(&skewed, 720.0, &skewed);
        test_rotate(&skewed, -720.0, &skewed);
    }

    #[test]
    fn test_latitude_d_to_m_per_longitude_d_spherical() {
        // Assume Earth is a sphere
        assert_approx_eq(
            equatorial_radius_m() * f64::consts::PI_2 / 360.0,
            latitude_d_to_m_per_longitude_d(0.0));

        // Should be symmetrical
        for degrees in (0i32..85) {
            assert_approx_eq(
                latitude_d_to_m_per_longitude_d(degrees as f64),
                latitude_d_to_m_per_longitude_d(-degrees as f64));
        }

        // At the poles, should be 0
        let diff = (latitude_d_to_m_per_longitude_d(90.0)).abs();
        assert!(diff < 0.01);
    }

    #[test]
    #[should_panic]  // We're using a less accurate spherical method right now
    fn test_latitude_d_to_m_per_longitude_d_oblong() {
        // Known values, from http://www.csgnetwork.com/degreelenllavcalc.html
        // M_PER_D_LATITUDE = 111319.458,
        assert_approx_eq(
            // Boulder
            latitude_d_to_m_per_longitude_d(40.08),
            85294.08886768305);
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
        assert_approx_eq(relative_degrees(&Point {x: 0.0, y: 0.0}, &Point {x: 1.0, y: 1.0}), 45.0);
        assert_approx_eq(relative_degrees(&Point {x: 1.0, y: 1.0}, &Point {x: 0.0, y: 0.0}), 225.0);
        assert_approx_eq(relative_degrees(&Point {x: 0.0, y: 0.0}, &Point {x: 2.0, y: 2.0}), 45.0);
        assert_approx_eq(relative_degrees(&Point {x: 2.0, y: 2.0}, &Point {x: 0.0, y: 0.0}), 225.0);

        assert_approx_eq(relative_degrees(&Point {x: 0.0, y: 0.0}, &Point {x: -1.0, y: 1.0}), 315.0);
        assert_approx_eq(relative_degrees(&Point {x: -1.0, y: 1.0}, &Point {x: 0.0, y: 0.0}), 135.0);
        assert_approx_eq(relative_degrees(&Point {x: 0.0, y: 0.0}, &Point {x: -2.0, y: 2.0}), 315.0);
        assert_approx_eq(relative_degrees(&Point {x: -2.0, y: 2.0}, &Point {x: 0.0, y: 0.0}), 135.0);

        assert_approx_eq(relative_degrees(&Point {x: 0.0, y: 0.0}, &Point {x: 0.0, y: 1.0}), 0.0);
        assert_approx_eq(relative_degrees(&Point {x: 0.0, y: 1.0}, &Point {x: 0.0, y: 0.0}), 180.0);
        assert_approx_eq(relative_degrees(&Point {x: 0.0, y: 0.0}, &Point {x: 0.0, y: 2.0}), 0.0);
        assert_approx_eq(relative_degrees(&Point {x: 0.0, y: 2.0}, &Point {x: 0.0, y: 0.0}), 180.0);

        assert_approx_eq(relative_degrees(&Point {x: 0.0, y: 0.0}, &Point {x: 1.0, y: 0.0}), 90.0);
        assert_approx_eq(relative_degrees(&Point {x: 1.0, y: 0.0}, &Point {x: 0.0, y: 0.0}), 270.0);
        assert_approx_eq(relative_degrees(&Point {x: 0.0, y: 0.0}, &Point {x: 2.0, y: 0.0}), 90.0);
        assert_approx_eq(relative_degrees(&Point {x: 2.0, y: 0.0}, &Point {x: 0.0, y: 0.0}), 270.0);
    }

    #[test]
    fn test_wrap_degrees() {
        for d in (0i32..360) {
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

    #[test]
    fn test_distance() {
        println!("1");
        assert_approx_eq(
            distance(
                &Point { x: 0.0, y: 0.0 },
                &Point { x: 0.0, y: 0.0 }),
            0.0);
        println!("2");
        assert_approx_eq(
            distance(
                &Point { x: 0.0, y: 0.0 },
                &Point { x: 3.0, y: 4.0 }),
            5.0);
        println!("3");
        assert_approx_eq(
            distance(
                &Point { x: 0.0, y: 0.0 },
                &Point { x: 4.0, y: 3.0 }),
            5.0);
        println!("4");
        assert_approx_eq(
            distance(
                &Point { x: -1.0, y: -3.0 },
                &Point { x: 2.0, y: 1.0 }),
            5.0);
        println!("5");
        assert_approx_eq(
            distance(
                &Point { x: 2.0, y: 1.0 },
                &Point { x: -1.0, y: -3.0 }),
            5.0);
    }
}
