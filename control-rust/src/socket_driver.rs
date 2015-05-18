use std::io::Write;
use std::path::Path;
use unix_socket::UnixStream;

use driver::{Driver, Percentage};

/// Sends drive commands to a Unix domain socket.
pub struct SocketDriver {
    throttle: Percentage,
    steering: Percentage,
    max_throttle: Percentage,
    socket: UnixStream,
}

impl SocketDriver {
    pub fn new(max_throttle: Percentage) -> SocketDriver {
        let server = Path::new("/tmp/driver-socket");
        let socket = match UnixStream::connect(server) {
            Ok(socket) => socket,
            Err(e) => panic!("Unable to open Unix socket for driver: {}", e),
        };

        SocketDriver {
            throttle: 0.0,
            steering: 0.0,
            max_throttle: max_throttle,
            socket: socket,}
    }
}

impl Driver for SocketDriver {
    fn drive(&mut self, throttle: Percentage, steering: Percentage) {
        self.throttle = self.max_throttle.max(throttle);
        self.steering = steering;
        match self.socket.write(format!("{} {}\n", self.throttle, self.steering).as_bytes()) {
            Ok(_) => (),
            Err(err) => error!("Unable to send drive command: {}", err),
        }
    }

    fn get_throttle(&self) -> Percentage {
        self.throttle
    }

    fn get_steering(&self) -> Percentage {
        self.steering
    }
}
