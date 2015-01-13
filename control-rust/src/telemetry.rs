use stdout_logger::StdoutLogger;
use telemetry_message::TelemetryMessage;

struct Telemetry<'a> {
    data: &'a mut TelemetryMessage,
    logger: &'a StdoutLogger,

    throttle: f32,
    steering: f32,
}


impl<'a> Telemetry<'a> {
    fn get_raw_data(&self) -> &TelemetryMessage {
        self.data
    }

    fn get_data(&self) -> &TelemetryMessage {
        self.data
    }

    fn process_drive_command(&mut self, throttle:f32, steering:f32) -> () {
        if throttle < -1.0 || throttle > 1.0 {
            self.logger.info("Invalid throttle");
            return;
        }
        if steering < -1.0 || steering > 1.0 {
            self.logger.warning("Invalid steering");
            return;
        }

        self.throttle = throttle;
        self.steering = steering;

        // TODO: Update the filter?
    }

    fn handle_message(&self, message:&TelemetryMessage) -> () {
        // TODO: Save the message
    }
}

fn rotate_degrees_clockwise(point:(f32, f32), degrees:f32) -> (f32, f32) {
    let (pt_x, pt_y) = point;
    let (sine, cosine) = (-degrees).to_radians().sin_cos();

    (pt_x * cosine - pt_y * sine, pt_x * sine + pt_y * cosine)
}


#[cfg(test)]
fn assert_approx_eq(value_1:f32, value_2:f32) -> () {
    // Yeah, I know this is bad, see
    // http://randomascii.wordpress.com/2012/02/25/comparing-floating-point-numbers-2012-edition/

    // This is the best we can do with f32
    let tolerance: f32 = 0.000001;
    let diff = (value_1 - value_2).abs();
    assert!(diff < tolerance, "{} < {} failed", diff, tolerance);
}


#[cfg(test)]
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
