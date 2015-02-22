/**
 * Reads NMEA messages from the GPS.
 */

use std::error::Error;
use std::mem::transmute;
use std::num::{Int, Float};

use telemetry::Degrees;
use telemetry::MetersPerSecond;

pub type Gravity = f32;
pub type MicroTesla = f32;
pub type Pascal = u32;
pub type Celsius = f32;


/**
 * GGA: Global positioning system fix data.
 */
#[derive(PartialEq)]
pub struct GgaMessage {
    pub latitude_degrees: f64,
    pub longitude_degrees: f64,
    pub horizontal_dilution_of_precision: f32,
}


/**
 * VTG: Course over ground and ground speed.
 */
#[derive(PartialEq)]
pub struct VtgMessage {
    pub course_d: Degrees,
    pub speed_m_s: MetersPerSecond,
}


#[derive(PartialEq)]
pub struct BinaryMessage {
    x_gravity: Gravity,
    y_gravity: Gravity,
    z_gravity: Gravity,
    x_magnetic_field: MicroTesla,
    y_magnetic_field: MicroTesla,
    z_magnetic_field: MicroTesla,
    pressure: Pascal,
    temperature: Celsius,
}


#[derive(PartialEq)]
pub enum NmeaMessage {
    Gga(GgaMessage),
    Vtg(VtgMessage),
    Binary(BinaryMessage),
}


macro_rules! bail_err {
    ($option:expr) => (
        match $option {
            Ok(s) => s,
            Err(e) => return Err(e.description().to_string()),
        };
    );
}
macro_rules! bail_none {
    ($option:expr) => (
        match $option {
            Some(s) => s,
            None => return Err("Message too short".to_string()),
        };
    );
}
macro_rules! convert {
    ($to:ty, $value:expr) => (
        unsafe {
            transmute::<u32, $to>(
                transmute::<_, u32>($value).to_le()
            )
        }
    )
}
macro_rules! array_to_type {
    ($to:ty, $array:expr) => (
        convert![$to, [$array[3], $array[2], $array[1], $array[0]]]
    )
}

impl NmeaMessage {
    fn parse(message: &str) -> Result<NmeaMessage, String> {
        if message.starts_with("$GPGGA") {
            // $GPGGA,hhmmss.sss,ddmm.mmmm,a,dddmm.mmmm,a,x,xx,x.x,x.x,M,,,,xxxx*hh<CR><LF>
            let mut iterator = message.split(',');

            iterator.next();  // Skip the message type
            iterator.next();  // Skip the timestamp since midnight UTC

            let latitude_degrees = {
                let string = bail_none!(iterator.next());
                let degrees: i32 = bail_err!(string[0..2].parse());
                let minutes: f64 = bail_err!(string[2..].parse());

                let north_indicator = bail_none!(iterator.next());
                let north = north_indicator == "N";
                let d = degrees as f64 + minutes / 60.0f64;
                if north { d } else { -d }
            };

            let longitude_degrees = {
                let string = bail_none!(iterator.next());
                let degrees: i32 = bail_err!(string[0..2].parse());
                let minutes: f64 = bail_err!(string[2..].parse());

                let east_indicator = bail_none!(iterator.next());
                let east = east_indicator == "E";
                let d = degrees as f64 + minutes / 60.0f64;
                if east { d } else { -d }
            };

            iterator.next();  // Skip the GPS quality indicator
            iterator.next();  // Skip the satellites used

            let hdop_str = bail_none!(iterator.next());
            let hdop: f32 = bail_err!(hdop_str.parse());

            Ok(
                NmeaMessage::Gga (
                    GgaMessage {
                        latitude_degrees: latitude_degrees,
                        longitude_degrees: longitude_degrees,
                        horizontal_dilution_of_precision: hdop,
                    }
                )
            )

        } else if message.starts_with("$GPVTG") {
            // GPVTG,x.x,T,x.x,M,x.x,N,x.x,K,a*hh<CR><LF>
            let mut iterator = message.split(',');

            iterator.next();  // Skip the message type

            let course_d_str = bail_none!(iterator.next());
            let course_d: f32 = bail_err!(course_d_str.parse());
            iterator.next();  // Skip the letter T indicating true course

            iterator.next();  // Skip the magnetic course
            iterator.next();  // Skip the letter M indicating magnetic course

            iterator.next();  // Skip speed in knots
            iterator.next();  // Skip the letter N indicating knots

            let speed_km_h_str = bail_none!(iterator.next());
            let speed_km_h: f32 = bail_err!(speed_km_h_str.parse());

            Ok(
                NmeaMessage::Vtg (
                    VtgMessage {
                        course_d: course_d,
                        speed_m_s: speed_km_h * 1000.0 / (60.0 * 60.0),
                    }
                )
            )
        } else {
            Err("Unknown NMEA message type".to_string())
        }
    }

    fn parse_binary(message: &[u8; 34]) -> Result<NmeaMessage, String> {
        // The payload length from the GPS is always 34 bytes
        unsafe {
            let acceleration_x: Gravity = array_to_type![f32, message[2..6]];
            let acceleration_y: Gravity = array_to_type![f32, message[6..10]];
            let acceleration_z: Gravity = array_to_type![f32, message[10..14]];
            let magnetic_x: MicroTesla = array_to_type![f32, message[14..18]];
            let magnetic_y: MicroTesla = array_to_type![f32, message[18..22]];
            let magnetic_z: MicroTesla = array_to_type![f32, message[22..26]];
            let pressure: Pascal = array_to_type![u32, message[26..30]];
            let temperature: Celsius = array_to_type![f32, message[30..34]];
            Ok(
                NmeaMessage::Binary (
                    BinaryMessage {
                        x_gravity: acceleration_x,
                        y_gravity: acceleration_y,
                        z_gravity: acceleration_z,
                        x_magnetic_field: magnetic_x,
                        y_magnetic_field: magnetic_y,
                        z_magnetic_field: magnetic_z,
                        pressure: pressure,
                        temperature: temperature,
                    }
                )
            )
        }
    }
}


#[cfg(test)]
mod tests {
    use std::fs::File;
    use std::io::{BufRead, BufReader, Read};
    use std::mem::transmute;
    use std::num::{Int, Float};
    use std::path::Path;
    use super::{BinaryMessage, NmeaMessage, GgaMessage, VtgMessage};
    use super::NmeaMessage::{Binary, Gga, Vtg};
    use termios::{Speed, Termio};

    #[test]
    fn test_parse_gga() {
        let message = "$GPGGA,033403.456,0102.3456,N,0102.3456,W,1,11,0.8,108.2,M,,,,0000*01\r\n";
        let expected = GgaMessage {
            latitude_degrees: 1.0390933333333334f64,
            longitude_degrees: -1.0390933333333334f64,
            horizontal_dilution_of_precision: 0.8f32,
        };
        match NmeaMessage::parse(message).unwrap() {
            Gga(gga) => {
                assert!(expected == gga);
            }
            _ => assert!(false),
        }
    }

    #[test]
    fn test_parse_vtg() {
        // 36 km/h = 10 m/s
        let message = "$GPVTG,123.4,T,356.1,M,000.0,N,0036.0,K,A*32\r\n";
        let expected = VtgMessage {
            course_d: 123.4,
            speed_m_s: 10.0,
        };
        match NmeaMessage::parse(message).unwrap() {
            Vtg(vtg) => {
                assert!(expected == vtg);
            },
            _ => assert!(false),
        }
    }

    #[test]
    fn test_tty() {
        // This will fail on everything but the Pi, so let's just ignore it if we're not running on
        // the Pi.
        if !cfg!(target_arch = "arm") {
            return;
        }
        let mut tty = match File::open(Path::new("/dev/ttyAMA0")) {
            Ok(f) => f,
            Err(m) => panic!("Unable to open /dev/ttyAMA0."),
        };
        tty.set_speed(Speed::B1152000);
        tty.drop_input_output();
        let mut reader = BufReader::new(tty);
        let mut message = String::new();
        reader.read_line(&mut message);
        match NmeaMessage::parse(&message) {
            Ok(m) => (),
            Err(e) => panic!("Unable to parse NmeaMessage"),
        }
    }

    #[test]
    fn test_parse_binary() {
        let message: [u8; 34] = [
            0xCFu8, 0x01, 0xBD, 0x4F, 0xE1, 0x54, 0xBE, 0x15, 0xE9, 0xE2, 0x3F, 0x6F, 0x3C, 0xB4,
            0xC0, 0xC5, 0x9D, 0x2A, 0x40, 0x79, 0x84, 0x08, 0x40, 0xCE, 0xFA, 0xB0, 0x00, 0x01,
            0x85, 0xB1, 0x41, 0xF1, 0x99, 0x9A
        ];
        let x_gravity = convert![f32, 0xBD4FE154u32];
        let y_gravity = convert![f32, 0xBE15E9E2u32];
        let z_gravity = convert![f32, 0x3F6F3CB4u32];
        let x_magnetic_field = convert![f32, 0xC0C59D2Au32];
        let y_magnetic_field = convert![f32, 0x40798408u32];
        let z_magnetic_field = convert![f32, 0x40CEFAB0u32];
        let pressure = convert![u32, 0x000185B1u32];
        let temperature = convert![f32, 0x41F1999Au32];
        let expected = BinaryMessage {
            x_gravity: x_gravity,
            y_gravity: y_gravity,
            z_gravity: z_gravity,
            x_magnetic_field: x_magnetic_field,
            y_magnetic_field: y_magnetic_field,
            z_magnetic_field: z_magnetic_field,
            pressure: pressure,
            temperature: temperature,
        };
        match NmeaMessage::parse_binary(&message).unwrap() {
            Binary(binary) => {
                println!("x_gravity: expected {}, computed {}", expected.x_gravity, binary.x_gravity);
                assert!(binary == expected);
            },
            _ => assert!(false),
        }
    }

    #[test]
    fn test_convert() {
        println!("{}, {}", convert![f32, 0xBD4FE154u32], 0.93452);
        assert!((convert![f32, 0xBD4FE154u32] - -0.050752).abs() < 0.001);
    }
}
