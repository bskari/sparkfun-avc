extern crate time;

use driver::Driver;
use telemetry::Telemetry;
use telemetry_message::TelemetryMessage;


type MilliSeconds = u64;


#[derive(PartialEq)]
enum ControlState {
    WaitingForStart,
    Running,
    CollisionRecovery,
}


pub struct Control<'a, 'b> {
    state: ControlState,
    run: bool,
    telemetry: &'a (Telemetry + 'a),
    driver: &'b mut (Driver + 'b),
    collision_time_ms: MilliSeconds,
}


impl <'a, 'b> Control <'a, 'b> {
    pub fn new(telemetry: &'a Telemetry, driver: &'b mut Driver) -> Control <'a, 'b> {
        Control {
            state: ControlState::WaitingForStart,
            run: false,
            telemetry: telemetry,
            driver: driver,
            collision_time_ms: 0,
        }
    }

    /**
     * Decides what to do and commands the vehicle for this time slice.
     */
    fn run_incremental(&mut self) {
        // Halting the car supercedes all other states
        if !self.run {
            self.state = ControlState::WaitingForStart;
        } else if (self.telemetry.is_stopped()) {
            // We want to drive for at least one second between collisions
            self.collision_time_ms = time::now().to_milliseconds();
            self.state = ControlState::CollisionRecovery;
        }

        match self.state {
            ControlState::WaitingForStart => self.waiting_for_start(),
            ControlState::Running => self.running(),
            ControlState::CollisionRecovery => {
                let now_ms = time::now().to_milliseconds();
                self.collision_recovery(now_ms);
            }
        }
    }

    pub fn handle_message(&self, message: &str) {
        // TODO
    }

    fn waiting_for_start(&mut self) {
        if !self.run {
            return;
        }
        self.state = ControlState::Running;
    }

    fn running(&self) {
        // TODO: Drive around
    }

    fn collision_recovery(&mut self, now_ms: MilliSeconds) {
        // Stop the motor for .5 seconds, then back up for 1 second, then pause
        // for .5 seconds
        let stop_ms = 500 as MilliSeconds;
        let back_up_ms = 1000 as MilliSeconds;
        let pause_ms = 500 as MilliSeconds;
        if now_ms < self.collision_time_ms + stop_ms {
            self.driver.drive(0.0f32, 0.0f32);
        } else if now_ms < self.collision_time_ms + stop_ms + back_up_ms {
            // TODO Choose a random direction
            self.driver.drive(-0.5f32, -0.5f32);
        } else if now_ms < self.collision_time_ms + stop_ms + back_up_ms + pause_ms {
            self.driver.drive(0.0f32, 0.0f32);
        } else {
            self.state = ControlState::Running;
        }
    }
}


trait ToMilliseconds {
    fn to_milliseconds(&self) -> MilliSeconds;
}


impl ToMilliseconds for time::Tm {
    fn to_milliseconds(&self) -> MilliSeconds {
        let timespec = self.to_timespec();
        (timespec.sec * 1000 + timespec.nsec as i64 / 1000000) as MilliSeconds
    }
}


#[cfg(test)]
mod tests {
    use driver::Driver;
    use driver::Percentage;
    use telemetry::Telemetry;
    use telemetry_message::CompassMessage;
    use telemetry_message::GpsMessage;
    use telemetry_message::TelemetryMessage;
    use super::Control;
    use super::ControlState;
    use super::MilliSeconds;

    struct TestDriver {
        pub throttle: Percentage,
        pub steering: Percentage,
    }

    impl TestDriver {
        fn new() -> TestDriver {
            TestDriver {
                throttle: 0.0f32,
                steering: 0.0f32,
            }
        }
    }

    impl Driver for TestDriver {
        fn drive(&mut self, throttle: Percentage, steering: Percentage) {
            self.throttle = throttle;
            self.steering = steering;
        }

        fn get_throttle(&self) -> f32 {
            self.throttle
        }

        fn get_steering(&self) -> f32 {
            self.steering
        }
    }

    struct TestTelemetry {
        pub gps: GpsMessage,
        pub compass: CompassMessage,
        pub stopped: bool,
    }

    impl TestTelemetry {
        fn new() -> TestTelemetry {
            TestTelemetry {
                gps: GpsMessage {
                    x_m: 0f32,
                    y_m: 0f32,
                    heading_d: 0f32,
                    speed_m_s: 0f32,
                    ms_since_midnight: 0i32,
                },
                compass: CompassMessage {
                    heading_d: 0f32,
                    magnetometer: (0f32, 0f32, 0f32),
                    ms_since_midnight: 0i32,
                },
                stopped: false,
            }
        }
    }

    impl Telemetry for TestTelemetry {
        fn get_raw_gps(&self) -> &GpsMessage { &self.gps }
        fn get_raw_compass(&self) -> &CompassMessage { &self.compass }
        fn get_data(&self) -> &GpsMessage { &self.gps }
        fn process_drive_command(&mut self, throttle:f32, steering:f32) { }
        fn handle_message(&mut self, message: &TelemetryMessage) { }
        fn is_stopped(&self) -> bool { self.stopped }
    }

    #[test]
    fn test_collision_recovery() {
        let telemetry = TestTelemetry::new();
        let mut driver = TestDriver::new();
        let control = Control::new(&telemetry, &mut driver);

        // TODO: Figure out how to do these assertions after the driver has
        // been lent to control
        assert!(false);
        /*
        control.collision_recovery(0 as MilliSeconds);
        assert!(control.state == ControlState::CollisionRecovery);
        assert!(driver.get_throttle() == 0.0 as Percentage);
        assert!(driver.get_steering() == 0.0 as Percentage);

        control.collision_recovery(400 as MilliSeconds);
        assert!(control.state == ControlState::CollisionRecovery);
        assert!(driver.get_throttle() == 0.0 as Percentage);
        assert!(driver.get_steering() == 0.0 as Percentage);

        control.collision_recovery(600 as MilliSeconds);
        assert!(control.state == ControlState::CollisionRecovery);
        assert!(driver.get_throttle() < 0.0 as Percentage);
        assert!(driver.get_steering() != 0.0 as Percentage);

        control.collision_recovery(1400 as MilliSeconds);
        assert!(control.state == ControlState::CollisionRecovery);
        assert!(driver.get_throttle() < 0.0 as Percentage);
        assert!(driver.get_steering() != 0.0 as Percentage);

        control.collision_recovery(1600 as MilliSeconds);
        assert!(control.state == ControlState::CollisionRecovery);
        assert!(driver.get_throttle() == 0.0 as Percentage);
        assert!(driver.get_steering() == 0.0 as Percentage);

        control.collision_recovery(1900 as MilliSeconds);
        assert!(control.state == ControlState::CollisionRecovery);
        assert!(driver.get_throttle() == 0.0 as Percentage);
        assert!(driver.get_steering() == 0.0 as Percentage);

        control.collision_recovery(2100 as MilliSeconds);
        assert!(control.state != ControlState::CollisionRecovery);
        */
    }
}
