use telemetry::{rotate_degrees_clockwise, wrap_degrees, Point};

#[allow(dead_code)]
struct LocationFilter {
    gps_observer_matrix: [[f32; 4]; 4],              // H
    compass_observer_matrix: [[f32; 4]; 4],          // H
    dead_reckoning_observer_matrix: [[f32; 4]; 4],   // H
    gps_measurement_noise: [[f32; 4]; 4],            // R
    compass_measurement_noise: [[f32; 4]; 4],        // R
    dead_reckoning_measurement_noise: [[f32; 4]; 4], // R

    // x m, y m, heading d, speed m/s
    estimates: [[f32; 1]; 4],     // x
    covariance: [[f32; 4]; 4],    // P
    process_noise: [[f32; 4]; 4], // Q
    last_observation_time_s: f32,

    // These paremeters are just scratch space for the
    // computations in update so that we can avoid reallocations
    out: [[f32; 4]; 4],
    out2: [[f32; 4]; 4],
    out3: [[f32; 4]; 4],
    out41: [[f32; 1]; 4],
    out41_2: [[f32; 1]; 4],
    kalman_gain: [[f32; 4]; 4],
}

impl LocationFilter {
    #[allow(dead_code)]
    pub fn new(x_m: f32, y_m: f32, heading_d: f32) -> LocationFilter {
        let lf = LocationFilter {
            gps_observer_matrix: identity(),
            compass_observer_matrix: [
                [0f32, 0f32, 0f32, 0f32],
                [0f32, 0f32, 0f32, 0f32],
                [0f32, 0f32, 1f32, 0f32],
                [0f32, 0f32, 0f32, 0f32],
            ],
            dead_reckoning_observer_matrix: [
                [0f32, 0f32, 0f32, 0f32],
                [0f32, 0f32, 0f32, 0f32],
                [0f32, 0f32, 0f32, 0f32],
                [0f32, 0f32, 0f32, 1f32],
            ],
            gps_measurement_noise: [
                [0f32, 0f32, 0f32, 0f32], // x_m will be filled in by the GPS accuracy
                [0f32, 0f32, 0f32, 0f32], // y_m will be filled in by the GPS accuracy
                [0f32, 0f32, 5f32, 0f32], // This degrees value is a guess
                [0f32, 0f32, 0f32, 1f32], // This speed value is a guess
            ],
            compass_measurement_noise: [
                [0f32, 0f32, 0f32, 0f32],
                [0f32, 0f32, 0f32, 0f32],
                // This degrees value is a guess. It's kept artificially high
                // because I've observed a lot of local interference as I drove
                // around before. TODO: Ignore magnetometer readings with bad
                // magnitudes that are obviously invalid and tune this down.
                [0f32, 0f32, 45f32, 0f32],
                [0f32, 0f32, 0f32, 0f32],
            ],
            dead_reckoning_measurement_noise: [
                [0f32, 0f32, 0f32, 0f32],
                [0f32, 0f32, 0f32, 0f32],
                [0f32, 0f32, 0f32, 0f32],
                // This speed value is a guess but should be higher than
                // the GPS speed value
                [0f32, 0f32, 0f32, 3f32],
            ],
            estimates: [[x_m], [y_m], [heading_d], [0.0f32]],
            // This will be populated as the filter runs
            // TODO: Ideally, this should be initialized to those values,
            // but for right now, identity matrix is fine
            covariance: identity(),
            // TODO: Tune this parameter for maximum performance
            process_noise: identity(),
            last_observation_time_s: 0.0,

            // These paremeters are just scratch space for the
            // computations in update so that we can avoid reallocations
            out: [[0.0f32; 4]; 4],
            out2: [[0.0f32; 4]; 4],
            out3: [[0.0f32; 4]; 4],
            out41: [[0.0f32; 1]; 4],
            out41_2: [[0.0f32; 1]; 4],
            kalman_gain: [[0.0f32; 4]; 4],
        };
        assert!(lf.dead_reckoning_measurement_noise[3][3] > lf.gps_measurement_noise[3][3]);
        return lf;
    }

    /**
     * Runs the Kalman update using the provided measurements.
     */
    #[allow(dead_code)]
    pub fn update(
        &mut self,
        measurements_: &[f32; 4],
        observer_matrix: &[[f32; 4]; 4],
        measurement_noise: &[[f32; 4]; 4],
        time_diff_s: f32,
    ) {
        // For convenience, we let users supply measurements as [f32; 4], but
        // because we're doing matrix stuff, we need to convert them to 4x1
        let measurements = [
            [measurements_[0]],
            [measurements_[1]],
            [measurements_[2]],
            [measurements_[3]],
        ];
        // Prediction step
        // x = A * x + B
        let heading_d = self.estimated_heading_d();
        let delta = rotate_degrees_clockwise(
            &Point {
                x: 0.0,
                y: time_diff_s,
            },
            heading_d,
        );
        let transition = [
            // A
            [1.0f32, 0.0f32, 0.0f32, delta.x],
            [0.0f32, 1.0f32, 0.0f32, delta.y],
            [0.0f32, 0.0f32, 1.0f32, 0.0f32],
            [0.0f32, 0.0f32, 0.0f32, 1.0f32],
        ];
        // TODO: Add acceleration and turn values
        multiply44x41(&transition, &self.estimates, &mut self.out41);
        self.estimates = self.out41;
        //print44("1. A=", &transition);
        //print44("   P=", &self.covariance);
        //print41("   x=", &self.estimates);
        //print44("2. H=", observer_matrix);
        //print41("   z=", &measurements);
        //print41("3. x=", &self.estimates);

        // Update uncertainty
        // P = A * P * A' + Q
        multiply44x44(&transition, &self.covariance, &mut self.out);
        transpose(&transition, &mut self.out2);
        multiply44x44(&self.out, &self.out2, &mut self.out3);
        add(&self.out3, &self.process_noise, &mut self.out);
        self.covariance = self.out;
        //print44("4. P=", &self.covariance);

        // Compute the Kalman gain
        // K = P * H' * inv(H * P * H' + R)
        multiply44x44(observer_matrix, &self.covariance, &mut self.out);
        transpose(observer_matrix, &mut self.out2); // out2 = H'
        multiply44x44(&self.out, &self.out2, &mut self.out3);
        add(&self.out3, measurement_noise, &mut self.out);
        //print44("  H * P * H' + R =", &self.out);
        invert(&self.out, &mut self.out3); // out3 = inv(H * P * H' + R)
        multiply44x44(&self.covariance, &self.out2, &mut self.out); // out = P * H'
        multiply44x44(&self.out, &self.out3, &mut self.kalman_gain);
        //print44("5. K=", &self.kalman_gain);

        // Determine innovation or residual and update our estimate
        // x = x + K * (z - H * x)
        multiply44x41(observer_matrix, &self.estimates, &mut self.out41);
        subtract41(&measurements, &self.out41, &mut self.out41_2);
        let mut heading_d = self.out41_2[2][0];
        while heading_d > 180.0 {
            heading_d -= 360.0;
        }
        while heading_d <= -180.0 {
            heading_d += 360.0;
        }
        self.out41_2[2][0] = heading_d;

        multiply44x41(&self.kalman_gain, &self.out41_2, &mut self.out41);
        add41(&self.estimates, &self.out41, &mut self.out41_2);
        self.estimates = self.out41_2;
        self.estimates[2][0] = wrap_degrees(self.estimates[2][0]);

        //print41("6. x=", &self.estimates);

        // Update the covariance
        // P = (I - K * H) * P
        multiply44x44(&self.kalman_gain, observer_matrix, &mut self.out);
        let id = identity();
        subtract44(&id, &self.out, &mut self.out2);
        multiply44x44(&self.out2, &self.covariance, &mut self.out);
        self.covariance = self.out;
        //print44("7. P=", &self.covariance);
    }

    #[allow(dead_code)]
    pub fn estimated_location_m(&self) -> (f32, f32) {
        (self.estimates[0][0], self.estimates[1][0])
    }

    pub fn estimated_heading_d(&self) -> f32 {
        self.estimates[2][0]
    }

    #[allow(dead_code)]
    pub fn estimated_speed_m_s(&self) -> f32 {
        self.estimates[3][0]
    }
}

fn identity() -> [[f32; 4]; 4] {
    [
        [1f32, 0f32, 0f32, 0f32],
        [0f32, 1f32, 0f32, 0f32],
        [0f32, 0f32, 1f32, 0f32],
        [0f32, 0f32, 0f32, 1f32],
    ]
}

fn multiply44x44(a: &[[f32; 4]; 4], b: &[[f32; 4]; 4], out: &mut [[f32; 4]; 4]) {
    for row in 0..a.len() {
        for column in 0..a[0].len() {
            let mut sum: f32 = 0.0;
            for iter in 0..4 {
                sum += a[row][iter] * b[iter][column];
            }
            out[row][column] = sum;
        }
    }
}

fn multiply44x41(a: &[[f32; 4]; 4], b: &[[f32; 1]; 4], out: &mut [[f32; 1]; 4]) {
    for row in 0..a.len() {
        for column in 0..b[0].len() {
            let mut sum: f32 = 0.0;
            for iter in 0..4 {
                sum += a[row][iter] * b[iter][column];
            }
            out[row][column] = sum;
        }
    }
}

fn add(a: &[[f32; 4]; 4], b: &[[f32; 4]; 4], out: &mut [[f32; 4]; 4]) {
    for row in 0..a.len() {
        for column in 0..a[0].len() {
            out[row][column] = a[row][column] + b[row][column];
        }
    }
}

fn subtract44(a: &[[f32; 4]; 4], b: &[[f32; 4]; 4], out: &mut [[f32; 4]; 4]) {
    for row in 0..a.len() {
        for column in 0..a[0].len() {
            out[row][column] = a[row][column] - b[row][column];
        }
    }
}

fn subtract41(a: &[[f32; 1]; 4], b: &[[f32; 1]; 4], out: &mut [[f32; 1]; 4]) {
    for row in 0..a.len() {
        for column in 0..a[0].len() {
            out[row][column] = a[row][column] - b[row][column];
        }
    }
}

fn add41(a: &[[f32; 1]; 4], b: &[[f32; 1]; 4], out: &mut [[f32; 1]; 4]) {
    for row in 0..a.len() {
        for column in 0..a[0].len() {
            out[row][column] = a[row][column] + b[row][column];
        }
    }
}

fn invert(a: &[[f32; 4]; 4], out: &mut [[f32; 4]; 4]) {
    if _invert(a, out) == false {
        // Just fudge it
        let mut new_a: [[f32; 4]; 4] = [[0f32; 4]; 4];
        for row in 0..a.len() {
            for column in 0..a[0].len() {
                if row == column && a[row][column] == 0.0f32 {
                    new_a[row][column] = 0.000001f32;
                } else {
                    new_a[row][column] = a[row][column];
                }
            }
        }
        let success = _invert(&new_a, out);
        assert!(success);
    }
}

fn _invert(a: &[[f32; 4]; 4], out: &mut [[f32; 4]; 4]) -> bool {
    let s0: f32 = a[0][0] * a[1][1] - a[1][0] * a[0][1];
    let s1: f32 = a[0][0] * a[1][2] - a[1][0] * a[0][2];
    let s2: f32 = a[0][0] * a[1][3] - a[1][0] * a[0][3];
    let s3: f32 = a[0][1] * a[1][2] - a[1][1] * a[0][2];
    let s4: f32 = a[0][1] * a[1][3] - a[1][1] * a[0][3];
    let s5: f32 = a[0][2] * a[1][3] - a[1][2] * a[0][3];

    let c5: f32 = a[2][2] * a[3][3] - a[3][2] * a[2][3];
    let c4: f32 = a[2][1] * a[3][3] - a[3][1] * a[2][3];
    let c3: f32 = a[2][1] * a[3][2] - a[3][1] * a[2][2];
    let c2: f32 = a[2][0] * a[3][3] - a[3][0] * a[2][3];
    let c1: f32 = a[2][0] * a[3][2] - a[3][0] * a[2][2];
    let c0: f32 = a[2][0] * a[3][1] - a[3][0] * a[2][1];

    let det = s0 * c5 - s1 * c4 + s2 * c3 + s3 * c2 - s4 * c1 + s5 * c0;
    if det == 0.0 {
        return false;
    }
    let invdet: f32 = 1.0f32 / det;

    out[0][0] = (a[1][1] * c5 - a[1][2] * c4 + a[1][3] * c3) * invdet;
    out[0][1] = (-a[0][1] * c5 + a[0][2] * c4 - a[0][3] * c3) * invdet;
    out[0][2] = (a[3][1] * s5 - a[3][2] * s4 + a[3][3] * s3) * invdet;
    out[0][3] = (-a[2][1] * s5 + a[2][2] * s4 - a[2][3] * s3) * invdet;

    out[1][0] = (-a[1][0] * c5 + a[1][2] * c2 - a[1][3] * c1) * invdet;
    out[1][1] = (a[0][0] * c5 - a[0][2] * c2 + a[0][3] * c1) * invdet;
    out[1][2] = (-a[3][0] * s5 + a[3][2] * s2 - a[3][3] * s1) * invdet;
    out[1][3] = (a[2][0] * s5 - a[2][2] * s2 + a[2][3] * s1) * invdet;

    out[2][0] = (a[1][0] * c4 - a[1][1] * c2 + a[1][3] * c0) * invdet;
    out[2][1] = (-a[0][0] * c4 + a[0][1] * c2 - a[0][3] * c0) * invdet;
    out[2][2] = (a[3][0] * s4 - a[3][1] * s2 + a[3][3] * s0) * invdet;
    out[2][3] = (-a[2][0] * s4 + a[2][1] * s2 - a[2][3] * s0) * invdet;

    out[3][0] = (-a[1][0] * c3 + a[1][1] * c1 - a[1][2] * c0) * invdet;
    out[3][1] = (a[0][0] * c3 - a[0][1] * c1 + a[0][2] * c0) * invdet;
    out[3][2] = (-a[3][0] * s3 + a[3][1] * s1 - a[3][2] * s0) * invdet;
    out[3][3] = (a[2][0] * s3 - a[2][1] * s1 + a[2][2] * s0) * invdet;

    return true;
}

fn transpose(a: &[[f32; 4]; 4], out: &mut [[f32; 4]; 4]) {
    for row in 0..a.len() {
        for column in 0..a[0].len() {
            out[row][column] = a[column][row];
        }
    }
}

//fn print44(message: &str, a: &[[f32; 4]; 4]) {
//    println!("{}", message);
//    for row in 0..a.len() {
//        for column in 0..a[0].len() {
//            print!("{}\t", a[row][column]);
//        }
//        println!("");
//    }
//}
//
//
//fn print41(message: &str, a: &[[f32; 1]; 4]) {
//    print!("{}", message);
//    for row in 0..a.len() {
//        print!("{}\t", a[row][0]);
//    }
//    println!("");
//}

#[cfg(test)]
mod tests {
    use super::{add, identity, invert, multiply44x44, LocationFilter};
    use telemetry::{rotate_degrees_clockwise, Point};

    fn assert_equal(a: &[[f32; 4]; 4], b: &[[f32; 4]; 4]) {
        for row in 0..a.len() {
            for column in 0..a[0].len() {
                let diff = (a[row][column] - b[row][column]).abs();
                assert!(diff < 0.00001f32);
            }
        }
    }

    fn assert_approx_eq(value_1: f32, value_2: f32) -> () {
        // Yeah, I know this is bad, see
        // http://randomascii.wordpress.com/2012/02/25/comparing-floating-point-numbers-2012-edition/

        // This is the best we can do with f32
        let tolerance: f32 = 0.0001;
        let diff = (value_1 - value_2).abs();
        assert!(diff < tolerance, "{} < {} failed", diff, tolerance);
    }

    #[test]
    fn test_multiply44x44() {
        let mut out = [[0.0f32; 4]; 4];
        let identity_ = identity();

        multiply44x44(&identity_, &identity_, &mut out);
        assert_equal(&out, &identity_);

        let array = [[1.0f32; 4], [2.0f32; 4], [3.0f32; 4], [4.0f32; 4]];
        multiply44x44(&identity_, &array, &mut out);
        assert_equal(&out, &array);
        multiply44x44(&array, &identity_, &mut out);
        assert_equal(&out, &array);

        multiply44x44(&array, &array, &mut out);
        assert!(out[0][0] == 10.0);
        assert!(out[1][0] == 20.0);
    }

    #[test]
    fn test_add() {
        let mut out = [[0.0f32; 4]; 4];
        let identity_ = identity();

        add(&identity_, &identity_, &mut out);
        for row in 0..out.len() {
            for column in 0..out[0].len() {
                assert!(out[row][column] == 2.0f32 * identity_[row][column]);
            }
        }

        for row in 0..out.len() {
            for column in 0..out[0].len() {
                assert!(out[row][column] == 2.0f32 * identity_[row][column]);
            }
        }
    }

    #[test]
    fn test_invert() {
        let mut out = [[0.0f32; 4]; 4];
        let identity_ = identity();

        invert(&identity_, &mut out);
        assert_equal(&out, &identity_);

        let mut array = identity();
        for row in 0..out.len() {
            for column in 0..out[0].len() {
                array[row][column] += row as f32 * column as f32 + row as f32;
            }
        }

        invert(&array, &mut out);
        let copy = out;
        multiply44x44(&array, &copy, &mut out);
        assert_equal(&out, &identity_);
    }

    /**
     * Tests that the estimating of the locations via dead reckoning at a
     * constant speed is sane.
     */
    #[test]
    fn test_update_constant_speed() {
        // I'm not sure how to independently validate these tests for accuracy.
        // The best I can think of is to do some sanity tests.
        let start_coordinates_m = (100.0f32, 200.0f32);
        let (start_x, start_y) = start_coordinates_m;
        let heading_d = 32.0f32;
        let mut location_filter = LocationFilter::new(start_x, start_y, heading_d);

        assert!(location_filter.estimated_location_m() == start_coordinates_m);

        let speed_m_s: f32 = 1.8;
        // This would normally naturally get set by running the Kalman filter;
        // we'll just manually set it now
        location_filter.estimates[3][0] = speed_m_s;

        let measurements: [f32; 4] = [0.0, 0.0, heading_d, 0.0];

        let seconds = 5u32;
        let compass_observer_matrix = location_filter.compass_observer_matrix;
        let compass_measurement_noise = location_filter.compass_measurement_noise;
        for _ in 0..seconds {
            location_filter.update(
                &measurements,
                &compass_observer_matrix,
                &compass_measurement_noise,
                1.0f32,
            );
        }

        let offset = rotate_degrees_clockwise(
            &Point {
                x: 0.0,
                y: speed_m_s * seconds as f32,
            },
            heading_d,
        );
        let (new_x, new_y) = (start_x + offset.x, start_y + offset.y);

        let (predicted_x, predicted_y) = location_filter.estimated_location_m();
        println!(
            "px {} nx {}, py {} ny {}",
            predicted_x, new_x, predicted_y, new_y
        );
        assert_approx_eq(predicted_x, new_x);
        assert_approx_eq(predicted_y, new_y);
    }
}
