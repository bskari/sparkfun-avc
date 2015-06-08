/// Reads messages from the SUP800F module and forwards the data.
use sup800f::{get_message, switch_to_binary_mode, switch_to_nmea_mode};

use std::error::Error;
use std::fs::File;
use std::path::Path;
use std::sync::mpsc::{Receiver, Sender};
use std::thread;

use telemetry::{
    Degrees,
    MetersPerSecond,
    Point,
    hdop_to_std_dev,
    latitude_longitude_to_point,
    wrap_degrees};
use telemetry_message::{CompassMessage, GpsMessage, TelemetryMessage};
use termios::{Speed, Termio};
use nmea::{MicroTesla, NmeaMessage};


pub struct TelemetryProvider {
    speed: MetersPerSecond,
    heading: Degrees,
    magnetometer_std_dev: f32,
    point: Point,
    hdop: f32,
    telemetry_message_tx: Sender<TelemetryMessage>,
    magnetometer_offsets: [f32; 2],
}


impl TelemetryProvider {
    pub fn new(telemetry_message_tx: Sender<TelemetryMessage>) -> TelemetryProvider {
        TelemetryProvider {
            speed: 0.0,
            heading: 315.0,  // Starting line of the Sparkfun AVC
            magnetometer_std_dev: 0.0,
            point: latitude_longitude_to_point(40.090583, -105.185664),
            hdop: 2.0,
            telemetry_message_tx: telemetry_message_tx,
            magnetometer_offsets: [-4.43, -0.43],  // From observation
        }
    }

    /// Processes and forwards messages from the SUP800F module
    pub fn run(&mut self, quit_rx: Receiver<()>) {
        let mut tty = match File::open(&Path::new("/dev/ttyAMA0")) {
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
        for _ in (0..5) {
            if tty.input_buffer_count().unwrap() > 0 {
                gps_message_received = true;
                break;
            }
            thread::sleep_ms(50);
        }
        if !gps_message_received {
            error!("No messages received from GPS, aborting telemetry provider thread");
            return;
        }

        let mut message = String::new();
        let mut binary_message_count = 0;
        loop {
            match quit_rx.try_recv() {
                Ok(_) => {
                    info!("Telemetry provider shutting down");
                    return;
                },
                Err(_) => (),
            };

            // Blocking read
            let message = match get_message(&mut tty) {
                Ok(message) => message,
                Err(e) => {
                    error!("Unable to read line from GPS: {}", e);
                    break;
                }
            };

            match NmeaMessage::parse(&message) {
                Ok(nmea) => match nmea {
                    NmeaMessage::Binary(binary) => {
                        let adjusted_x = binary.x_magnetic_field - self.magnetometer_offsets[0];
                        let adjusted_y = binary.y_magnetic_field - self.magnetometer_offsets[1];
                        self.heading = adjusted_x.atan2(adjusted_y);
                        // TODO: Compute this
                        self.magnetometer_std_dev = 1.0;
                        if !self.send_compass() {
                            break;
                        }
                        binary_message_count += 1;
                    },
                    NmeaMessage::Gga(gga) => {
                        self.point = latitude_longitude_to_point(
                           gga.latitude_degrees,
                           gga.longitude_degrees);
                        self.hdop = gga.hdop;
                        if !self.send_gps() {
                            break;
                        }
                        binary_message_count = -1;
                    },
                    NmeaMessage::Gll(gll) => {
                        self.point = latitude_longitude_to_point(
                           gll.latitude_degrees,
                           gll.longitude_degrees);
                        if !self.send_gps() {
                            break;
                        }
                        binary_message_count = -1;
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
                        binary_message_count = -1;
                    },
                    NmeaMessage::Sti(_) => (),  // I don't think there's anything useful here
                    NmeaMessage::Ack(_) => (),  // TODO
                },
                Err(_) => (),
            }

            // I don't expect binary_message_count to unexpectedly get above 3, but just in case
            if binary_message_count >= 3 {
                switch_to_nmea_mode(&mut tty);
            } else if binary_message_count == -1 {
                switch_to_binary_mode(&mut tty);
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

    fn send_compass(&self) -> bool {
        let status = self.telemetry_message_tx.send(
            TelemetryMessage::Compass(
                CompassMessage {
                    heading: self.heading,
                    std_dev: self.magnetometer_std_dev,}));
        match status {
            Ok(_) => true,
            Err(_) => false,
        }
    }
}


fn tilt_compensated_compass(
    magnetic_x: MicroTesla,
    magnetic_y: MicroTesla,
    magnetic_z: MicroTesla
) -> Degrees {
    // TODO: Get readings for these
    let acceleration_x: MetersPerSecond = 0.0;
    let acceleration_y: MetersPerSecond = 0.0;
    let acceleration_z: MetersPerSecond = 1.0;
    arbitrary_tilt_compensated_compass(
        acceleration_x,
        acceleration_y,
        acceleration_z,
        magnetic_x,
        magnetic_y,
        magnetic_z)
}


fn arbitrary_tilt_compensated_compass(
    acceleration_x: MetersPerSecond,
    acceleration_y: MetersPerSecond,
    acceleration_z: MetersPerSecond,
    magnetic_x: MicroTesla,
    magnetic_y: MicroTesla,
    magnetic_z: MicroTesla
) -> Degrees {
    // TODO: Get readings for these
    let magnetic_x_bias: MicroTesla = 0.0;
    let magnetic_y_bias: MicroTesla = 0.0;
    let magnetic_z_bias: MicroTesla = 0.0;

    let norm = 1.0;
    assert!(norm == (
        acceleration_x * acceleration_x
        + acceleration_y * acceleration_y
        + acceleration_z * acceleration_z
    ).sqrt());

    let mag_x = (magnetic_x - magnetic_x_bias) / norm;
    let mag_y = (magnetic_y - magnetic_y_bias) / norm;
    let mag_z = (magnetic_z - magnetic_z_bias) / norm;
    let roll = acceleration_y.atan2(
        (acceleration_x * acceleration_x + acceleration_z * acceleration_z).sqrt()
    );
    let pitch = acceleration_x.atan2(
        (acceleration_y * acceleration_y + acceleration_z * acceleration_z).sqrt()
    );
    let yaw = wrap_degrees(
        (-mag_y * roll.cos() + mag_z * roll.sin()).atan2(
            mag_x * pitch.cos()
            + mag_z * pitch.sin() * roll.sin()
            + mag_z * pitch.sin() * roll.cos()
        ).to_degrees()
    );
    yaw
}


#[cfg(test)]
mod tests {
    use super::arbitrary_tilt_compensated_compass;

    #[test]
    fn test_arbitrary_tilt_compensated_compass() {
        let accel_values = vec![
            // Level
            (0.0f32, 0.0, 1.0),
            (0.0, 0.0, 1.0),
            (0.0, 0.0, 1.0),
            (0.0, 0.0, 1.0),
            (0.0, 0.0, 1.0),
            // Sideways
            (0.0f32, 1.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 1.0, 0.0),
        ];
        let mag_values = vec![
            (1.0f32, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (-1.0, 0.0, 0.0),
            (0.0, -1.0, 0.0),
            (1.0, 1.0, 0.0),

            (1.0f32, 0.0, 0.0),
            (0.0, 0.0, 1.0),
            (-1.0, 0.0, 0.0),
            (0.0, 0.0, -1.0),
        ];
        let expected_headings = vec![
            0.0f32, 270.0, 180.0, 90.0, 315.0,
            0.0, 90.0, 180.0, 270.0,
        ];
        for ((accels, mags), expected) in accel_values.iter().zip(mag_values).zip(expected_headings) {
            let (accel_x, accel_y, accel_z) = *accels;
            let (mag_x, mag_y, mag_z) = mags;
            let compass = arbitrary_tilt_compensated_compass(accel_x, accel_y, accel_z, mag_x, mag_y, mag_z);
            if compass != expected {
                println!(
                    "For accel {:?} mag {:?}, computed {}, expected {}",
                    accels,
                    mags,
                    compass,
                    expected);
            }
            assert!(compass == expected);
        }
    }
}
