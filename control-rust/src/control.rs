extern crate time;
use std::old_io::timer;
use std::sync::mpsc::{Sender, Receiver};
use std::thread::Thread;
use std::time::duration::Duration;

use telemetry::TelemetryState;

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
    telemetry_tx: Sender<()>,
    telemetry_rx: Receiver<TelemetryState>,
    command_rx: Receiver<String>,
    collision_time_ms: MilliSeconds,
}


impl Control {
    pub fn new(
        telemetry_tx: Sender<()>,
        telemetry_rx: Receiver<TelemetryState>,
        command_rx: Receiver<String>,
    ) -> Control {
        Control {
            state: ControlState::WaitingForStart,
            run: false,
            telemetry_rx: telemetry_rx,
            telemetry_tx: telemetry_tx,
            command_rx: command_rx,
            collision_time_ms: 0,
        }
    }

    /**
     * Drives the car around. Should be run in a thread.
     */
    pub fn run(&mut self) {
        loop {
            // Check for new messages
            while let Ok(message) = self.command_rx.try_recv() {
                if message == "start" {
                    self.run = true;
                } else if message == "stop" {
                    self.run = false;
                } else if message == "quit" {
                    return;
                } else {
                    // TODO: Log an error
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

        match self.state {
            ControlState::WaitingForStart => self.waiting_for_start(),
            ControlState::Running => self.running(),
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
            // TODO drive(0.0f32, 0.0f32);
        } else if now_ms < self.collision_time_ms + stop_ms + back_up_ms {
            // TODO Choose a random direction
            // TODO drive(-0.5f32, -0.5f32);
        } else if now_ms < self.collision_time_ms + stop_ms + back_up_ms + pause_ms {
            // TODO drive(0.0f32, 0.0f32);
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
    extern crate time;
    use std::sync::mpsc::{channel, Sender, Receiver};
    use std::thread::Thread;

    use super::{Control, ControlState, MilliSeconds};
    use super::ToMilliseconds;
    use telemetry::TelemetryState;

    #[test]
    fn test_collision_recovery() {
        let (command_tx, command_rx) = channel();
        let (telemetry_tx, telemetry_rx) = channel();
        let (telemetry_2_tx, telemetry_2_rx) = channel();

        // Fake telemetry end point returns test data
        Thread::spawn(move || {
            telemetry_rx.recv();
            println!("Fake Telemetry received a message!");
            telemetry_2_tx.send(
                TelemetryState {
                    x_m: 0.0f32,
                    y_m: 0.0f32,
                    heading_d: 0.0f32,
                    speed_m_s: 0.0f32,
                    stopped: true,
                }
            );
        });

        let mut control = Control::new(telemetry_tx, telemetry_2_rx, command_rx);
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
