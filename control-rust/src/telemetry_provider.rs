use std::fs::File;
use std::io::{BufRead, BufReader, Read};
use std::sync::mpsc::{Receiver, Sender};

use telemetry::{Degrees, MetersPerSecond, Point, hdop_to_std_dev, latitude_longitude_to_point};
use telemetry_message::{CompassMessage, GpsMessage, TelemetryMessage};
use termios::{Speed, Termio};
use nmea::NmeaMessage;


pub struct TelemetryProvider {
    tty: BufReader<File>,
    speed: MetersPerSecond,
    heading: Degrees,
    point: Point,
    hdop: f32,
    telemetry_message_tx: Sender<TelemetryMessage>,
}


impl TelemetryProvider {
    pub fn new(telemetry_message_tx: Sender<TelemetryMessage>) -> TelemetryProvider {
        TelemetryProvider {
            tty: {
                let tty = match File::open(&Path::new("/dev/ttyAMA0")) {
                    Ok(f) => f,
                    Err(m) => panic!("Unable to open /dev/ttyAMA0")
                };
                tty.set_speed(Speed::B1152000);
                tty.drop_input_output();
                BufReader::new(tty)},
            speed: 0.0,
            heading: 315.0,  // Starting line of the Sparkfun AVC
            point: latitude_longitude_to_point(40.090583, -105.185664),
            hdop: 2.0,
            telemetry_message_tx: telemetry_message_tx,
        }
    }

    pub fn run(&mut self, quit_rx: Receiver<()>) {
        let mut message = String::new();
        loop {
            match quit_rx.try_recv() {
                Ok(_) => {
                    info!("Telemetry provider shutting down");
                    return;
                },
                Err(_) => (),
            };

            // Blocking read
            self.tty.read_line(&mut message);

            match NmeaMessage::parse(&message) {
                Ok(nmea) => match nmea {
                    NmeaMessage::Binary(binary) => (),  // TODO Translate to compass
                    NmeaMessage::Gga(gga) => {
                        self.point = latitude_longitude_to_point(
                           gga.latitude_degrees,
                           gga.longitude_degrees);
                        self.hdop = gga.hdop;
                        self.send_gps();
                    },
                    NmeaMessage::Gll(gll) => {
                        self.point = latitude_longitude_to_point(
                           gll.latitude_degrees,
                           gll.longitude_degrees);
                        self.send_gps();
                    },
                    NmeaMessage::Gsa(gsa) => self.hdop = gsa.hdop,
                    NmeaMessage::Gsv(gsv) => (),  // TODO Gsv is satellites in view?
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
                        self.send_gps();
                    },
                    NmeaMessage::Sti(sti) => (),  // I don't think there's anything useful here
                },
                Err(_) => (),
            }
        }
    }

    fn send_gps(&self) {
        self.telemetry_message_tx.send(
            TelemetryMessage::Gps(
                GpsMessage {
                    point: self.point,
                    heading: self.heading,
                    speed: self.speed,
                    std_dev_x: hdop_to_std_dev(self.hdop),
                    std_dev_y: hdop_to_std_dev(self.hdop),}));
    }
}
