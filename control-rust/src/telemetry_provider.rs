use std::fs::File;
use std::io::{BufRead, BufReader};
use std::old_io::timer;
use std::sync::mpsc::{Receiver, Sender};
use std::time::duration::Duration;

use telemetry::{Degrees, MetersPerSecond, Point, hdop_to_std_dev, latitude_longitude_to_point};
use telemetry_message::{GpsMessage, TelemetryMessage};
use termios::{Speed, Termio};
use nmea::NmeaMessage;


pub struct TelemetryProvider {
    speed: MetersPerSecond,
    heading: Degrees,
    point: Point,
    hdop: f32,
    telemetry_message_tx: Sender<TelemetryMessage>,
}


impl TelemetryProvider {
    pub fn new(telemetry_message_tx: Sender<TelemetryMessage>) -> TelemetryProvider {
        TelemetryProvider {
            speed: 0.0,
            heading: 315.0,  // Starting line of the Sparkfun AVC
            point: latitude_longitude_to_point(40.090583, -105.185664),
            hdop: 2.0,
            telemetry_message_tx: telemetry_message_tx,
        }
    }

    pub fn run(&mut self, quit_rx: Receiver<()>) {
        let tty = match File::open(&Path::new("/dev/ttyAMA0")) {
            Ok(f) => f,
            Err(m) => panic!("Unable to open /dev/ttyAMA0: {}", m.description())
        };
        match tty.set_speed(Speed::B1152000) {
            Ok(_) => (),
            Err(_) => {
                error!("Unable to set TTY speed");
                return;
            }
        }
        match tty.drop_input_output() {
            Ok(_) => (),
            Err(_) => {
                error!("Unable to drop TTY input and output");
                return;
            }
        }

        // Just do this test to make sure we're running on the Pi with GPS attached. If we just
        // blindly enter the loop without the GPS attached, we'll dead lock.
        let mut gps_message_received = false;
        for _ in range(0, 5) {
            if tty.input_buffer_count().unwrap() > 0 {
                gps_message_received = true;
                break;
            }
            timer::sleep(Duration::milliseconds(50));
        }
        if !gps_message_received {
            error!("No messages received from GPS, aborting telemetry provider thread");
            return;
        }

        let mut message = String::new();
        let mut reader = BufReader::new(tty);
        loop {
            match quit_rx.try_recv() {
                Ok(_) => {
                    info!("Telemetry provider shutting down");
                    return;
                },
                Err(_) => (),
            };

            // Blocking read
            match reader.read_line(&mut message) {
                Ok(_) => (),
                Err(e) => {
                    error!("Unable to read line from GPS: {}", e);
                    break;
                }
            }

            match NmeaMessage::parse(&message) {
                Ok(nmea) => match nmea {
                    NmeaMessage::Binary(_) => (),  // TODO Translate to compass
                    NmeaMessage::Gga(gga) => {
                        self.point = latitude_longitude_to_point(
                           gga.latitude_degrees,
                           gga.longitude_degrees);
                        self.hdop = gga.hdop;
                        if !self.send_gps() {
                            break;
                        }
                    },
                    NmeaMessage::Gll(gll) => {
                        self.point = latitude_longitude_to_point(
                           gll.latitude_degrees,
                           gll.longitude_degrees);
                        if !self.send_gps() {
                            break;
                        }
                    },
                    NmeaMessage::Gsa(gsa) => self.hdop = gsa.hdop,
                    NmeaMessage::Gsv(_) => (),  // TODO Gsv is satellites in view?
                    NmeaMessage::Vtg(vtg) => {
                        self.heading = vtg.course;
                        self.speed = vtg.speed;
                    },
                    NmeaMessage::Rmc(rmc) => {
                        self.point = latitude_longitude_to_point(
                           rmc.latitude_degrees,
                           rmc.longitude_degrees);
                        self.heading = rmc.course;
                        self.speed = rmc.speed;
                        if !self.send_gps() {
                            break;
                        }
                    },
                    NmeaMessage::Sti(sti) => (),  // I don't think there's anything useful here
                },
                Err(_) => (),
            }
        }
    }

    fn send_gps(&self) -> bool {
        let status = self.telemetry_message_tx.send(
            TelemetryMessage::Gps(
                GpsMessage {
                    point: self.point,
                    heading: self.heading,
                    speed: self.speed,
                    std_dev_x: hdop_to_std_dev(self.hdop),
                    std_dev_y: hdop_to_std_dev(self.hdop),}));
        match status {
            Ok(_) => true,
            Err(_) => false,
        }
    }
}
