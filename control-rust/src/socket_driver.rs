use std::old_io::net::pipe::UnixStream;
use std::sync::mpsc::{Select, Receiver};
use std::time::Duration;

use driver::{Driver, Percentage};

/**
 * Sends drive commands to a Unix domain socket.
 */
pub struct SocketDriver {
    throttle: Percentage,
    steering: Percentage,
}

impl SocketDriver {
    pub fn new(
    ) -> SocketDriver {
        SocketDriver {
            throttle: 0.0,
            steering: 0.0,}
    }

    /**
     * Sends drive commands to a Unix domain socket endpoint.
     */
    pub fn run(&mut self, command_rx: Receiver<(Percentage, Percentage)>, quit_rx: Receiver<()>) {
        let server = Path::new("/tmp/driver-socket");
        let mut socket = match UnixStream::connect(&server) {
            Ok(socket) => socket,
            Err(e) => {
                error!("Unable to open Unix socket for driver: {}", e);
                return;
            }
        };
        loop {
            let select = Select::new();
            let mut quit_handle = select.handle(&quit_rx);
            let mut rx_handle = select.handle(&command_rx);
            unsafe {
                quit_handle.add();
                rx_handle.add();
            }

            let triggered_handle_id = select.wait();
            if triggered_handle_id == quit_handle.id() {
                info!("SocketDriver shutting down");
                return;
            } else {
                assert!(triggered_handle_id == rx_handle.id());
                let throttle: Percentage;
                let steering: Percentage;
                match rx_handle.recv() {
                    Ok(pair) => {
                        let (t, s) = pair;
                        throttle = t;
                        steering = s;
                    },
                    Err(e) => {
                        warn!("Unable to receive drive command: {}", e);
                        continue;
                    }
                }
                self.drive(throttle, steering);
            }
        }
    }
}

impl Driver for SocketDriver {
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
