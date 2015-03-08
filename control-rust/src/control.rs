extern crate log;
extern crate time;
use std::mem::transmute;
use std::num::Float;
use std::old_io::timer;
use std::sync::mpsc::{Sender, Receiver};
use std::time::duration::Duration;

use driver::{Driver, Percentage};
use telemetry::{Degrees, TelemetryState, difference_d, distance, is_turn_left, relative_degrees};
use telemetry_message::CommandMessage;
use waypoint_generator::WaypointGenerator;

type MilliSeconds = u64;

#[derive(PartialEq)]
enum ControlState {
    WaitingForStart,
    Running,
    CollisionRecovery,
}


pub struct Control {
    state: ControlState,
    run: bool,
    collision_time_ms: MilliSeconds,
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
            telemetry_rx: telemetry_rx,
            request_telemetry_tx: request_telemetry_tx,
            waypoint_generator: waypoint_generator,
            driver: driver,}
    }

    /**
     * Drives the car around. Should be run in a thread.
     */
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
                    CommandMessage::Start => self.run = true,
                    CommandMessage::Stop => self.run = false,
                }
            }

            if !self.run_incremental() {
                return;
            }
            timer::sleep(Duration::milliseconds(50));
        }
    }

    /**
     * Decides what to do and commands the vehicle for this time slice.
     */
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
            }
        }

        // Everything's perfectly all right now. We're fine. We're all fine here now, thank you.
        // How are you?
        return true;
    }

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
        let waypoint = self.waypoint_generator.get_current_raw_waypoint(&state.location);
        let distance_m = distance(&state.location, &waypoint);
        let throttle: f32 = if distance_m > 5.0 {
                1.0
            } else if distance_m > 2.0 {
                0.75
            } else {
                0.5
            };

        let goal_heading: Degrees = relative_degrees(&state.location, &waypoint);

        // We want to stay in the heading range of the waypoint +- 1/2 of the waypoint reached
        // distance diameter
        let mut range: Degrees = 2.0 * (
            self.waypoint_generator.reach_distance() /
            distance_m
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
            } else if difference < 45.0 || throttle > 0.5 {
                0.75
            } else {
                1.0
            };

        let steering: f32 = if is_turn_left(state.heading, goal_heading) {
                -steering_magnitude
            } else {
                steering_magnitude
            };

        self.drive(throttle, steering);
    }

    fn collision_recovery(&mut self, now_ms: MilliSeconds) {
        // Stop the motor for .5 seconds, then back up for 1 second, then pause
        // for .5 seconds
        let stop_ms = 500 as MilliSeconds;
        let back_up_ms = 1000 as MilliSeconds;
        let pause_ms = 500 as MilliSeconds;
        if now_ms < self.collision_time_ms + stop_ms {
            self.drive(0.0f32, 0.0f32);
        } else if now_ms < self.collision_time_ms + stop_ms + back_up_ms {
            // TODO Choose a random direction
            self.drive(-0.5f32, -0.5f32);
        } else if now_ms < self.collision_time_ms + stop_ms + back_up_ms + pause_ms {
            self.drive(0.0f32, 0.0f32);
        } else {
            self.state = ControlState::Running;
        }
    }

    #[allow(unused_variables)]
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
    use std::sync::mpsc::{channel, Sender, Receiver};
    use std::thread::Thread;

    use driver::{Driver, Percentage};
    use super::{Control, ControlState, MilliSeconds};
    use super::ToMilliseconds;
    use telemetry::{Meter, Point, TelemetryState};
    use waypoint_generator::WaypointGenerator;

    struct DummyWaypointGenerator {
        done: bool,
    }
    impl WaypointGenerator for DummyWaypointGenerator {
        fn get_current_waypoint(&self, point: &Point) -> Point { Point {x: 100.0, y: 100.0 } }
        fn get_current_raw_waypoint(&self, point: &Point) -> Point { Point { x: 100.0, y: 100.0 } }
        fn next(&mut self) { self.done = true; }
        fn reached(&self, point: &Point) -> bool { false }
        fn done(&self) -> bool { self.done }
        fn reach_distance(&self) -> Meter { 1.0 }
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
        Thread::spawn(move || {
            telemetry_rx.recv();
            telemetry_2_tx.send(
                TelemetryState {
                    location: Point { x: 0.0, y: 0.0 },
                    heading: 0.0f32,
                    speed: 0.0f32,
                    stopped: true});
        });

        let waypoint_generator = Box::new(DummyWaypointGenerator {
            done: false,});
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

        control.collision_recovery(now + 400);
        assert!(control.state == ControlState::CollisionRecovery);
        assert!(control.driver.get_throttle() == 0.0 as Percentage);
        assert!(control.driver.get_steering() == 0.0 as Percentage);

        control.collision_recovery(now + 600);
        assert!(control.state == ControlState::CollisionRecovery);
        assert!(control.driver.get_throttle() < 0.0 as Percentage);
        assert!(control.driver.get_steering() != 0.0 as Percentage);

        control.collision_recovery(now + 1400);
        assert!(control.state == ControlState::CollisionRecovery);
        assert!(control.driver.get_throttle() < 0.0 as Percentage);
        assert!(control.driver.get_steering() != 0.0 as Percentage);

        control.collision_recovery(now + 1600);
        assert!(control.state == ControlState::CollisionRecovery);
        assert!(control.driver.get_throttle() == 0.0 as Percentage);
        assert!(control.driver.get_steering() == 0.0 as Percentage);

        control.collision_recovery(now + 1900);
        assert!(control.state == ControlState::CollisionRecovery);
        assert!(control.driver.get_throttle() == 0.0 as Percentage);
        assert!(control.driver.get_steering() == 0.0 as Percentage);

        control.collision_recovery(now + 2100);
        assert!(control.state != ControlState::CollisionRecovery);
    }
}
