extern crate log;
extern crate time;
use std::num::Float;
use std::old_io::timer;
use std::sync::mpsc::{Sender, Receiver};
use std::thread::Thread;
use std::time::duration::Duration;

use telemetry::{
    Degrees,
    Point,
    TelemetryState,
    difference_d,
    distance,
    is_turn_left,
    relative_degrees,
};
use telemetry_message::CommandMessage;
use waypoint_generator::WaypointGenerator;

type MilliSeconds = u64;

#[derive(PartialEq)]
enum ControlState {
    WaitingForStart,
    Running,
    CollisionRecovery,
}


pub struct Control<'a> {
    state: ControlState,
    run: bool,
    telemetry_tx: Sender<()>,
    telemetry_rx: Receiver<TelemetryState>,
    command_rx: Receiver<CommandMessage>,
    collision_time_ms: MilliSeconds,
    waypoint_generator: &'a (WaypointGenerator + 'a),
}


impl<'a> Control<'a> {
    pub fn new(
        telemetry_tx: Sender<()>,
        telemetry_rx: Receiver<TelemetryState>,
        command_rx: Receiver<CommandMessage>,
        waypoint_generator: &'a (WaypointGenerator + 'a),
    ) -> Control {
        Control {
            state: ControlState::WaitingForStart,
            run: false,
            telemetry_rx: telemetry_rx,
            telemetry_tx: telemetry_tx,
            command_rx: command_rx,
            collision_time_ms: 0,
            waypoint_generator: waypoint_generator,
        }
    }

    /**
     * Drives the car around. Should be run in a thread.
     */
    pub fn run(&mut self) {
        loop {
            // Check for new messages
            while let Ok(message) = self.command_rx.try_recv() {
                match message {
                    CommandMessage::Start => self.run = true,
                    CommandMessage::Stop => self.run = false,
                    CommandMessage::Quit => return,
                }
            }

            if !self.run_incremental() {
                return;
            }
            timer::sleep(Duration::milliseconds(100));
        }
    }

    /**
     * Decides what to do and commands the vehicle for this time slice.
     */
    fn run_incremental(&mut self) -> bool {
        // Request the lastest telemetry information
        let state;
        self.telemetry_tx.send(());
        match self.telemetry_rx.recv() {
            Ok(received_state) => state = received_state,
            Err(e) => return false,
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

    fn running(&self, state: &TelemetryState) {
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

        self.drive(throttle, steering_magnitude);
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
    fn drive(&self, throttle_percentage: f32, steering_percentage: f32) {
        // TODO
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

    use super::{Control, ControlState, MilliSeconds};
    use super::ToMilliseconds;
    use telemetry::{Meter, Point, TelemetryState};
    use waypoint_generator::WaypointGenerator;

    struct DummyWaypointGenerator {
        // I got
        // error: structure literal must either have at least one field or use functional structure update syntax
        // if I left this out and I'm not sure how to work around it
        _dummy: f32,
    }
    impl DummyWaypointGenerator {
        fn new() -> DummyWaypointGenerator { DummyWaypointGenerator { _dummy: 0.0 } }
    }
    impl WaypointGenerator for DummyWaypointGenerator {
        fn get_current_waypoint(&self, point: &Point) -> Point { Point {x: 100.0, y: 100.0 } }
        fn get_current_raw_waypoint(&self, point: &Point) -> Point { Point { x: 100.0, y: 100.0 } }
        fn next(&self) {}
        fn reached(&self, point: &Point) -> bool { false }
        fn done(&self) -> bool { false }
        fn reach_distance(&self) -> Meter { 1.0 }
    }

    #[test]
    fn test_collision_recovery() {
        let (command_tx, command_rx) = channel();
        let (telemetry_tx, telemetry_rx) = channel();
        let (telemetry_2_tx, telemetry_2_rx) = channel();

        // Fake telemetry end point returns test data
        Thread::spawn(move || {
            telemetry_rx.recv();
            telemetry_2_tx.send(
                TelemetryState {
                    location: Point { x: 0.0, y: 0.0 },
                    heading: 0.0f32,
                    speed_m_s: 0.0f32,
                    stopped: true
                });
        });

        let waypoint_generator = DummyWaypointGenerator::new();

        let mut control = Control::new(
            telemetry_tx,
            telemetry_2_rx,
            command_rx,
            &waypoint_generator);
        control.state = ControlState::Running;
        control.run = true;
        control.run_incremental();

        let now = time::now().to_milliseconds();
        control.collision_recovery(now + 0);
        assert!(control.state == ControlState::CollisionRecovery);
        //assert!(driver.get_throttle() == 0.0 as Percentage);
        //assert!(driver.get_steering() == 0.0 as Percentage);

        control.collision_recovery(now + 400);
        assert!(control.state == ControlState::CollisionRecovery);
        //assert!(driver.get_throttle() == 0.0 as Percentage);
        //assert!(driver.get_steering() == 0.0 as Percentage);

        control.collision_recovery(now + 600);
        assert!(control.state == ControlState::CollisionRecovery);
        //assert!(driver.get_throttle() < 0.0 as Percentage);
        //assert!(driver.get_steering() != 0.0 as Percentage);

        control.collision_recovery(now + 1400);
        assert!(control.state == ControlState::CollisionRecovery);
        //assert!(driver.get_throttle() < 0.0 as Percentage);
        //assert!(driver.get_steering() != 0.0 as Percentage);

        control.collision_recovery(now + 1600);
        assert!(control.state == ControlState::CollisionRecovery);
        //assert!(driver.get_throttle() == 0.0 as Percentage);
        //assert!(driver.get_steering() == 0.0 as Percentage);

        control.collision_recovery(now + 1900);
        assert!(control.state == ControlState::CollisionRecovery);
        //assert!(driver.get_throttle() == 0.0 as Percentage);
        //assert!(driver.get_steering() == 0.0 as Percentage);

        control.collision_recovery(now + 2100);
        assert!(control.state != ControlState::CollisionRecovery);
    }
}
