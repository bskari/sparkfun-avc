extern crate log;
extern crate time;
use std::sync::mpsc::{Sender, Receiver};
use std::thread::sleep_ms;

use driver::{Driver, Percentage};
use telemetry::{Degrees, TelemetryState, difference_d, distance, is_turn_left, relative_degrees};
use telemetry_message::CommandMessage;
use waypoint_generator::WaypointGenerator;

type MilliSeconds = u64;

#[derive(PartialEq)]
enum ControlState {
    CalibrateCompass,
    WaitingForStart,
    Running,
    CollisionRecovery,
}


pub struct Control {
    state: ControlState,
    run: bool,
    collision_time_ms: MilliSeconds,
    calibrate_time_ms: MilliSeconds,
    request_telemetry_tx: Sender<()>,
    telemetry_rx: Receiver<TelemetryState>,
    waypoint_generator: Box<WaypointGenerator>,
    driver: Box<Driver>,
}


impl Control {
    pub fn new(
        request_telemetry_tx: Sender<()>,
        telemetry_rx: Receiver<TelemetryState>,
        waypoint_generator: Box<WaypointGenerator>,
        driver: Box<Driver>,
    ) -> Control {
        Control {
            state: ControlState::WaitingForStart,
            run: false,
            collision_time_ms: 0,
            calibrate_time_ms: 0,
            telemetry_rx: telemetry_rx,
            request_telemetry_tx: request_telemetry_tx,
            waypoint_generator: waypoint_generator,
            driver: driver,}
    }

    /// Drives the car around. Should be run in a thread.
    pub fn run(&mut self, command_rx: Receiver<CommandMessage>, quit_rx: Receiver<()>) {
        loop {
            match quit_rx.try_recv() {
                Ok(_) => {
                    info!("Control shutting down");
                    return;
                },
                Err(_) => (),
            };

            // Check for new messages
            while let Ok(message) = command_rx.try_recv() {
                match message {
                    CommandMessage::CalibrateCompass => {
                        if self.state != ControlState::WaitingForStart {
                            warn!("Tried to calibrate compass while running, ignoring");
                        } else {
                            self.calibrate_time_ms = time::now().to_milliseconds();
                            self.state = ControlState::CalibrateCompass;
                            self.run = true;
                        }
                    },
                    CommandMessage::Start => self.run = true,
                    CommandMessage::Stop => self.run = false,
                }
            }

            if !self.run_incremental() {
                return;
            }
            sleep_ms(50);
        }
    }

    /// Decides what to do and commands the vehicle for this time slice.
    fn run_incremental(&mut self) -> bool {
        // Request the lastest telemetry information
        let state;
        match self.request_telemetry_tx.send(()) {
            Ok(_) => (),
            Err(e) => {
                error!("Unable to request telemetry information: {}", e);
                return false;
            }
        }
        match self.telemetry_rx.recv() {
            Ok(received_state) => state = received_state,
            Err(e) => {
                error!("Unable to receive telemetry information: {}", e);
                return false;
            }
        }

        // Halting the car supercedes all other states
        if !self.run {
            self.state = ControlState::WaitingForStart;
        } else if state.stopped {
            // We want to drive for at least one second between collisions
            self.collision_time_ms = time::now().to_milliseconds();
            self.state = ControlState::CollisionRecovery;
        }

        if self.waypoint_generator.done() {
            self.run = false;
        }

        match self.state {
            ControlState::WaitingForStart => self.waiting_for_start(),
            ControlState::Running => self.running(&state),
            ControlState::CollisionRecovery => {
                let now_ms = time::now().to_milliseconds();
                self.collision_recovery(now_ms);
            },
            ControlState::CalibrateCompass => {
                let now_ms = time::now().to_milliseconds();
                self.calibrate_compass(now_ms);
            }
        }

        // Everything's perfectly all right now. We're fine. We're all fine here now, thank you.
        // How are you?
        return true;
    }

    /// Returns true if the car is waiting to start the race.
    fn waiting_for_start(&mut self) {
        if !self.run {
            return;
        }
        self.state = ControlState::Running;
    }

    fn running(&mut self, state: &TelemetryState) {
        while self.waypoint_generator.reached(&state.location) {
            self.waypoint_generator.next();
            if self.waypoint_generator.done() {
                return;
            }
        }
        let waypoint_option = self.waypoint_generator.get_current_waypoint(&state.location);
        let waypoint = match waypoint_option {
            Some(point) => point,
            None => return,
        };
        let distance = distance(&state.location, &waypoint);
        let mut throttle: f32 = if distance > 5.0 {
                1.0
            } else if distance > 2.0 {
                0.75
            } else {
                0.5
            };

        let goal_heading: Degrees = relative_degrees(&state.location, &waypoint);

        // We want to stay in the heading range of the waypoint +- 1/2 of the waypoint reached
        // distance diameter
        let mut range: Degrees = 2.0 * (
            self.waypoint_generator.reach_distance() / distance
        ).atan().to_degrees();
        // Range should never be > 90.0; otherwise, we would have already reached the waypoint.
        if range < 5.0 {
            range = 5.0;
        }

        let difference = difference_d(state.heading, goal_heading);
        // TODO: We should keep turning until we exactly hit the heading, rather than continually
        // adjusting as we get inside or outside of the range
        let steering_magnitude: f32 = if difference < range {
                0.0
            } else if difference < 15.0 {
                0.25
            } else if difference < 30.0 {
                0.5
            } else if difference < 45.0 {
                0.75
            } else {
                1.0
            };

        let steering: f32 = if is_turn_left(state.heading, goal_heading) {
                -steering_magnitude
            } else {
                steering_magnitude
            };

        throttle = throttle.min(
            if steering > 0.50 {
                0.25
            } else if steering > 0.25 {
                0.5
            } else {
                1.0
            }
        );

        self.drive(throttle, steering);
    }

    /// Recovers from a collision by backing up in a random direction.
    fn collision_recovery(&mut self, now_ms: MilliSeconds) {
        // TODO Turn in a direction toward the waypoint
        let turn = -0.25f32;

        // Stop the motor for 1.0 seconds, then back up for 1 second, then pause for .5 seconds
        let stop_ms = 1000 as MilliSeconds;
        // The ESC requires you to send on-off before it will reverse with a final on
        let reverse_esc_ms = 250 as MilliSeconds;
        let back_up_ms = 1000 as MilliSeconds;
        let pause_ms = 500 as MilliSeconds;
        if now_ms < self.collision_time_ms + stop_ms {
            self.drive(0.0f32, 0.0f32);
        } else if now_ms < self.collision_time_ms + stop_ms + reverse_esc_ms {
            self.drive(-0.5f32, turn);
        } else if now_ms < self.collision_time_ms + stop_ms + reverse_esc_ms * 2 {
            self.drive(0.0f32, turn);
        } else if now_ms < self.collision_time_ms + stop_ms + reverse_esc_ms * 2 + back_up_ms {
            // We use 0.5 throttle even though 0.5 forward is pretty fast, because reverse throttle
            // is slower
            self.drive(-0.5f32, turn);
        } else if now_ms < self.collision_time_ms + stop_ms + reverse_esc_ms * 2 + back_up_ms + pause_ms {
            self.drive(0.0f32, 0.0f32);
        } else {
            self.state = ControlState::Running;
        }
    }

    fn calibrate_compass(&mut self, now_ms: MilliSeconds) {
        // TODO: While we do have the car drive in circles part down, the telemetry_provider is not
        // updated with the readings!
        // Drive around in circles for 20 seconds
        if now_ms < self.calibrate_time_ms + 20000 {
            self.drive(0.5f32, 1.0f32);
        } else {
            self.state = ControlState::WaitingForStart;
            self.run = false;
        }
    }

    fn drive(&mut self, throttle_percentage: Percentage, steering_percentage: Percentage) {
        self.driver.drive(throttle_percentage, steering_percentage);
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
    extern crate time;
    use num::traits::{Float, FromPrimitive};
    use std::sync::mpsc::{channel, Sender, Receiver};
    use std::thread::spawn;

    use driver::{Driver, Percentage};
    use super::{Control, ControlState, MilliSeconds};
    use super::ToMilliseconds;
    use telemetry::{Meters, Point, TelemetryState};
    use waypoint_generator::WaypointGenerator;

    macro_rules! assert_approx_eq {
        ( $value_1:expr, $value_2:expr ) => {
            assert!(approx_eq($value_1, $value_2));
        }
    }
    fn approx_eq<T: Float + FromPrimitive>(value_1: T, value_2: T) -> bool {
        // Yeah, I know this is bad, see
        // http://randomascii.wordpress.com/2012/02/25/comparing-floating-point-numbers-2012-edition/

        let diff = (value_1 - value_2).abs();
        // This is the best we can do with f32
        diff < FromPrimitive::from_f32(0.00001f32).unwrap()
    }

    struct DummyWaypointGenerator {
        pub done: bool,
        pub waypoint: Point,
    }
    impl WaypointGenerator for DummyWaypointGenerator {
        fn get_current_waypoint(&self, point: &Point) -> Option<Point> { Some(self.waypoint) }
        fn get_current_raw_waypoint(&self, point: &Point) -> Option<Point> { Some(self.waypoint) }
        fn next(&mut self) { self.done = true; }
        fn reached(&self, point: &Point) -> bool { false }
        fn done(&self) -> bool { self.done }
        fn reach_distance(&self) -> Meters { 1.0 }
    }

    struct DummyDriver {
        throttle: Percentage,
        steering: Percentage,
    }
    impl Driver for DummyDriver {
        fn drive(&mut self, throttle: Percentage, steering: Percentage) {
            self.throttle = throttle;
            self.steering = steering;
        }
        fn get_throttle(&self) -> Percentage {
            self.throttle
        }
        fn get_steering(&self) -> Percentage {
            self.steering
        }
    }

    #[test]
    fn test_collision_recovery() {
        let (telemetry_tx, telemetry_rx) = channel();
        let (telemetry_2_tx, telemetry_2_rx) = channel();

        // Fake telemetry end point returns test data
        spawn(move || {
            telemetry_rx.recv();
            telemetry_2_tx.send(
                TelemetryState {
                    location: Point { x: 0.0, y: 0.0 },
                    heading: 0.0f32,
                    speed: 0.0f32,
                    stopped: true});
        });

        let waypoint_generator = Box::new(DummyWaypointGenerator {
            done: false,
            waypoint: Point { x: 100.0, y: 100.0 }});
        let driver = Box::new(DummyDriver {
            throttle: 0.0,
            steering: 0.0,});

        let mut control = Control::new(
            telemetry_tx,
            telemetry_2_rx,
            waypoint_generator,
            driver);
        control.state = ControlState::Running;
        control.run = true;
        control.run_incremental();

        let now = time::now().to_milliseconds();
        control.collision_recovery(now + 0);
        assert!(control.state == ControlState::CollisionRecovery);
        assert!(control.driver.get_throttle() == 0.0 as Percentage);
        assert!(control.driver.get_steering() == 0.0 as Percentage);

        control.collision_recovery(now + 900);
        assert!(control.state == ControlState::CollisionRecovery);
        assert!(control.driver.get_throttle() == 0.0 as Percentage);
        assert!(control.driver.get_steering() == 0.0 as Percentage);

        control.collision_recovery(now + 1100);
        assert!(control.state == ControlState::CollisionRecovery);
        assert!(control.driver.get_throttle() < 0.0 as Percentage);
        assert!(control.driver.get_steering() != 0.0 as Percentage);

        control.collision_recovery(now + 1300);
        assert!(control.state == ControlState::CollisionRecovery);
        assert!(control.driver.get_throttle() == 0.0 as Percentage);
        assert!(control.driver.get_steering() != 0.0 as Percentage);

        control.collision_recovery(now + 1600);
        assert!(control.state == ControlState::CollisionRecovery);
        assert!(control.driver.get_throttle() < 0.0 as Percentage);
        assert!(control.driver.get_steering() != 0.0 as Percentage);

        control.collision_recovery(now + 2400);
        assert!(control.state == ControlState::CollisionRecovery);
        assert!(control.driver.get_throttle() < 0.0 as Percentage);
        assert!(control.driver.get_steering() != 0.0 as Percentage);

        control.collision_recovery(now + 2600);
        assert!(control.state == ControlState::CollisionRecovery);
        assert!(control.driver.get_throttle() == 0.0 as Percentage);
        assert!(control.driver.get_steering() == 0.0 as Percentage);

        control.collision_recovery(now + 3100);
        assert!(control.state != ControlState::CollisionRecovery);
    }

    #[test]
    fn test_running() {
        for values in [
            // (position_x, position_y, goal_x, goal_y, heading, throttle, steering)
            // If the waypoint is behind us, throttle should be low and turn should be high
            (0.0f32, 0.0, 1.0, -100.0, 0.0, 0.25, 1.0),
            (0.0, 0.0, 100.0, 101.0, 270.0, 0.25, 1.0),
            // If the waypoint is straight ahead, throttle should be high and turn should be off
            (0.0, 0.0, 1.0, 100.0, 0.0, 1.0, 0.0),
            (0.0, 0.0, -1.0, -100.0, 180.0, 1.0, 0.0),
            (0.0, 0.0, -50.0, 50.0, 315.0, 1.0, 0.0),
            // If we are close to the waypoint, slow down
            (0.0, 0.0, 0.0, 1.0, 0.0, 0.5, 0.0),
        ].iter() {
            let (position_x, position_y, goal_x, goal_y, heading, throttle, steering) = *values;

            let (telemetry_tx, telemetry_rx) = channel();
            let (telemetry_2_tx, telemetry_2_rx) = channel();

            let mut waypoint_generator = Box::new(DummyWaypointGenerator {
                done: false,
                waypoint: Point { x: goal_x, y: goal_y}});
            let driver = Box::new(DummyDriver {
                throttle: 0.0,
                steering: 0.0,});

            let state = TelemetryState {
                location: Point { x: position_x, y: position_y },
                heading: heading,
                speed: 0.0f32,
                stopped: true};

            let mut control = Control::new(
                telemetry_tx,
                telemetry_2_rx,
                waypoint_generator,
                driver);
            control.state = ControlState::Running;
            control.run = true;

            control.running(&state);
            assert!(control.state == ControlState::Running);
            println!("throttle {}", control.driver.get_throttle());
            assert_approx_eq!(control.driver.get_throttle(), throttle);
            println!("steering {}", control.driver.get_steering());
            assert_approx_eq!(control.driver.get_steering(), steering);
            println!("done");
        }
    }
}
