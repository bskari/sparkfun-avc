/**
 * Reads NMEA messages from the GPS.
 */

use std::error::Error;
use std::mem::transmute;
use std::num::{Int, Float, ParseFloatError};

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


/**
 * RMC: Recommended minimum specific GNSS data.
 */
#[derive(PartialEq)]
pub struct RmcMessage {
    pub latitude_degrees: f64,
    pub longitude_degrees: f64,
    pub speed_m_s: MetersPerSecond,
    pub course_d: Degrees,
    pub magnetic_variation: Degrees,
}

/**
 * GSA: GNSS DOP and active satellites.
 */
#[derive(PartialEq)]
pub enum FixMode {
    Manual,
    Automatic
}
#[derive(PartialEq)]
pub enum FixType {
    NotAvailable,
    TwoD,
    ThreeD,
}
#[derive(PartialEq)]
pub struct GsaMessage {
    mode: FixMode,
    fix_type: FixType,
    satellites_used: i32,
    position_dilution_of_precision: f32,
    horizontal_dilution_of_precision: f32,
    vertical_dilution_of_precision: f32,
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
    Binary(BinaryMessage),
    Gga(GgaMessage),
    Gsa(GsaMessage),
    Vtg(VtgMessage),
    Rmc(RmcMessage),
}


macro_rules! bail_err {
    ($option:expr) => (
        match $option {
            Ok(s) => s,
            Err(e) => return Err(e.description().to_string())
        };
    );
}
macro_rules! bail_none {
    ($option:expr) => (
        match $option {
            Some(s) => s,
            None => return Err("Message too short".to_string())
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
        // These if statements are sorted in the rough likelihood of appearance
        if message.starts_with("$GPGGA") {
            match NmeaMessage::parse_gga(message) {
                Ok(gga) => Ok(NmeaMessage::Gga(gga)),
                Err(e) => Err(e)
            }
        } else if message.starts_with("$GPVTG") {
            match NmeaMessage::parse_vtg(message) {
                Ok(vtg) => Ok(NmeaMessage::Vtg(vtg)),
                Err(e) => Err(e)
            }
        } else if message.starts_with("$GPRMC") {
            match NmeaMessage::parse_rmc(message) {
                Ok(rmc) => Ok(NmeaMessage::Rmc(rmc)),
                Err(e) => Err(e)
            }
        } else if message.starts_with("$GPGSA") {
            match NmeaMessage::parse_gsa(message) {
                Ok(gsa) => Ok(NmeaMessage::Gsa(gsa)),
                Err(e) => Err(e)
            }
        } else {
            Err("Unknown NMEA message type".to_string())
        }
    }

    /**
     * Time, position and fix related data for a GPS receiver.
     */
    fn parse_gga(message: &str) -> Result<GgaMessage, String> {
        // $GPGGA,hhmmss.sss,ddmm.mmmm,a,dddmm.mmmm,a,x,xx,x.x,x.x,M,,,,xxxx*hh<CR><LF>
        let mut iterator = message.split(',');

        iterator.next();  // Skip the message type
        iterator.next();  // Skip the UTC time

        let latitude_degrees = {
            let string = bail_none!(iterator.next());
            let d = bail_err!(NmeaMessage::parse_degrees_minutes(string));

            let north_indicator = bail_none!(iterator.next());
            let north = north_indicator == "N";
            if north { d } else { assert!(north_indicator == "S"); -d }
        };

        let longitude_degrees = {
            let string = bail_none!(iterator.next());
            let d = bail_err!(NmeaMessage::parse_degrees_minutes(string));

            let east_indicator = bail_none!(iterator.next());
            let east = east_indicator == "E";
            if east { d } else { assert!(east_indicator == "W"); -d }
        };

        let gps_quality_indicator = bail_none!(iterator.next());
        if gps_quality_indicator == "0" {
            return Err("Position fix unavailable".to_string());
        }
        iterator.next();  // Skip the satellites used

        let hdop_str = bail_none!(iterator.next());
        let hdop: f32 = bail_err!(hdop_str.parse());
        // Ignore altitude, DGPS station id, and checksum

        Ok(
            GgaMessage {
                latitude_degrees: latitude_degrees,
                longitude_degrees: longitude_degrees,
                horizontal_dilution_of_precision: hdop,
            }
        )
    }

    /**
     * The actual course and speed relative to the ground.
     */
    fn parse_vtg(message: &str) -> Result<VtgMessage, String> {
        // $GPVTG,x.x,T,x.x,M,x.x,N,x.x,K,a*hh<CR><LF>
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
        iterator.next();  // Skip the letter K indicating km/h

        let mode_and_checksum = bail_none!(iterator.next());
        if mode_and_checksum.starts_with("N") {
            return Err("Data not valid".to_string());
        }

        Ok(
            VtgMessage {
                course_d: course_d,
                speed_m_s: speed_km_h * 1000.0 / (60.0 * 60.0),
            }
        )
    }

    /**
     * Time, date, position, course and speed data.
     */
    fn parse_rmc(message: &str) -> Result<RmcMessage, String> {
        // $GPRMC,111636.932,A,2447.0949,N,12100.5223,E,000.0,000.0,030407,003.9,W,A*12<CR><LF>
        let mut iterator = message.split(',');

        iterator.next();  // Skip the message type
        iterator.next();  // Skip the UTC time

        let status = bail_none!(iterator.next());
        if status == "V" {
            return Err("Navigation receiver warning".to_string());
        }

        let latitude_degrees = {
            let string = bail_none!(iterator.next());
            let d = bail_err!(NmeaMessage::parse_degrees_minutes(string));

            let north_indicator = bail_none!(iterator.next());
            let north = north_indicator == "N";
            if north { d } else { assert!(north_indicator == "S"); -d }
        };

        let longitude_degrees = {
            let string = bail_none!(iterator.next());
            let d = bail_err!(NmeaMessage::parse_degrees_minutes(string));

            let east_indicator = bail_none!(iterator.next());
            let east = east_indicator == "E";
            if east { d } else { assert!(east_indicator == "W"); -d }
        };

        let speed_knots_str = bail_none!(iterator.next());
        let speed_knots: f32 = bail_err!(speed_knots_str.parse());
        let speed_m_s: MetersPerSecond = speed_knots * 0.5144;

        let course_d_str = bail_none!(iterator.next());
        let course: Degrees = bail_err!(course_d_str.parse());

        iterator.next();  // Skip UTC date

        let magnetic_variation = {
            let magnetic_d_str = bail_none!(iterator.next());
            let magnetic: Degrees = bail_err!(magnetic_d_str.parse());
            let east_west = bail_none!(iterator.next());
            if east_west == "E" { -magnetic } else { assert!(east_west == "W"); magnetic }
        };

        let mode_and_checksum = bail_none!(iterator.next());
        if mode_and_checksum.starts_with("N") {
            return Err("Data not valid".to_string());
        }

        Ok(
            RmcMessage {
                latitude_degrees: latitude_degrees,
                longitude_degrees: longitude_degrees,
                speed_m_s: speed_m_s,
                course_d: course,
                magnetic_variation: magnetic_variation,
            }
        )
    }

    /**
     * GSA: GPS receiver operating mode, satellites used in the navigation solution reported by the
     * GGA or GNS sentence and DOP values.
     */
    fn parse_gsa(message: &str) -> Result<GsaMessage, String> {
        // $GPGSA,A,x,xx,xx,xx,xx,xx,xx,xx,xx,xx,xx,xx,xx,x.x,x.x,x.x*hh<CR><LF>
        let mut iterator = message.split(',');

        iterator.next();  // Skip the message type

        let fix_mode_str = bail_none!(iterator.next());
        let fix_mode = if fix_mode_str == "A" {
                FixMode::Automatic
            } else {
                assert!(fix_mode_str == "M");
                FixMode::Manual
            };

        let fix_type_str = bail_none!(iterator.next());
        let fix_type = if fix_type_str == "1" {
                FixType::NotAvailable
            } else if fix_type_str == "2" {
                FixType::TwoD
            } else {
                assert!(fix_type_str == "3");
                FixType::ThreeD
            };

        let mut satellites_used = 0;
        loop {
            let satellite_id = bail_none!(iterator.next());
            if satellite_id.len() == 0 {
                break;
            }
            satellites_used += 1;
        }

        let pdop_str = bail_none!(iterator.next());
        let pdop: f32 = bail_err!(pdop_str.parse());

        let hdop_str = bail_none!(iterator.next());
        let hdop: f32 = bail_err!(hdop_str.parse());

        let vdop_and_checksum_str = bail_none!(iterator.next());
        let star_index = match vdop_and_checksum_str.chars().position(|x| x == '*') {
            Some(index) => index,
            None => return Err("Invalid VDOP".to_string()),
        };
        let vdop: f32 = bail_err!(vdop_and_checksum_str[0..star_index].parse());

        Ok(
            GsaMessage {
                mode: fix_mode,
                fix_type: fix_type,
                satellites_used: satellites_used,
                position_dilution_of_precision: pdop,
                horizontal_dilution_of_precision: hdop,
                vertical_dilution_of_precision: vdop,
            }
        )
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

    fn parse_degrees_minutes(degrees_minutes: &str) -> Result<f64, ParseFloatError> {
        let decimal_point_index = match degrees_minutes.chars().position(|x| x == '.') {
            Some(index) => index,
            None => return degrees_minutes.parse::<f64>()
        };
        // There are always two digits for whole number minutes
        let degrees: f64 = match degrees_minutes[0..decimal_point_index - 2].parse() {
            Ok(i) => i,
            Err(e) => return Err(e)
        };
        let minutes: f64 = match degrees_minutes[decimal_point_index - 2..].parse() {
            Ok(f) => f,
            Err(e) => return Err(e)
        };
        Ok(degrees as f64 + minutes / 60.0f64)
    }
}


#[cfg(test)]
mod tests {
    use std::fs::File;
    use std::io::{BufRead, BufReader, Read};
    use std::mem::transmute;
    use std::num::{Int, Float};
    use std::path::Path;
    use super::{
        BinaryMessage,
        FixMode,
        FixType,
        GgaMessage,
        GsaMessage,
        NmeaMessage,
        RmcMessage,
        VtgMessage
    };
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
        match NmeaMessage::parse_gga(message) {
            Ok(gga) => assert!(expected == gga),
            _ => assert!(false)
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
        match NmeaMessage::parse_vtg(message) {
            Ok(vtg) => assert!(expected == vtg),
            _ => assert!(false)
        }
    }

    #[test]
    fn test_parse_rmc() {
        let message = "$GPRMC,111636.932,A,2447.0949,N,12100.5223,E,000.0,000.0,030407,003.9,W,A*12\r\n";
        let expected = RmcMessage {
            latitude_degrees: 24.784915,
            longitude_degrees: 121.008705,
            speed_m_s: 0.0,
            course_d: 0.0,
            magnetic_variation: 3.9,
        };
        match NmeaMessage::parse_rmc(message) {
            Ok(rmc) => assert!(expected == rmc),
            _ => assert!(false),
        }
    }

    #[test]
    fn test_parse_gsa() {
        let message = "$GPGSA,A,3,05,12,21,22,30,09,18,06,14,01,31,,1.2,0.8,0.6*36\r\n";
        let expected = GsaMessage {
            mode: FixMode::Automatic,
            fix_type: FixType::ThreeD,
            satellites_used: 11,
            position_dilution_of_precision: 1.2,
            horizontal_dilution_of_precision: 0.8,
            vertical_dilution_of_precision: 0.6,
        };
        match NmeaMessage::parse_gsa(message) {
            Ok(gsa) => assert!(expected == gsa),
            _ => assert!(false),
        }
    }

    #[test]
    fn test_parse() {
        let gga = "$GPGGA,033403.456,0102.3456,N,0102.3456,W,1,11,0.8,108.2,M,,,,0000*01\r\n";
        let vtg = "$GPVTG,123.4,T,356.1,M,000.0,N,0036.0,K,A*32\r\n";
        let rmc = "$GPRMC,111636.932,A,2447.0949,N,12100.5223,E,000.0,000.0,030407,003.9,W,A*12\r\n";
        let gsa = "$GPGSA,A,3,05,12,21,22,30,09,18,06,14,01,31,,1.2,0.8,0.6*36\r\n";

        match NmeaMessage::parse(gga).unwrap() {
            NmeaMessage::Gga(gga) => (),
            _ => assert!(false)
        };
        match NmeaMessage::parse(vtg).unwrap() {
            NmeaMessage::Vtg(vtg) => (),
            _ => assert!(false)
        };
        match NmeaMessage::parse(rmc).unwrap() {
            NmeaMessage::Rmc(rmc) => (),
            _ => assert!(false)
        };
        match NmeaMessage::parse(gsa).unwrap() {
            NmeaMessage::Gsa(gsa) => (),
            _ => assert!(false)
        };
    }

    #[test]
    fn test_tty() {
        return;
        // This will fail on everything but the Pi, so let's just ignore it if we're not running on
        // the Pi.
        if !cfg!(target_arch = "arm") {
            return;
        }
        let mut tty = match File::open(Path::new("/dev/ttyAMA0")) {
            Ok(f) => f,
            Err(m) => panic!("Unable to open /dev/ttyAMA0.")
        };
        tty.set_speed(Speed::B1152000);
        tty.drop_input_output();
        let mut reader = BufReader::new(tty);
        let mut message = String::new();
        reader.read_line(&mut message);
        match NmeaMessage::parse(&message) {
            Ok(m) => (),
            Err(e) => panic!("Unable to parse NmeaMessage")
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
            Binary(binary) => assert!(binary == expected),
            _ => assert!(false)
        }
    }

    #[test]
    fn test_convert() {
        assert!((convert![f32, 0xBD4FE154u32] - -0.050752).abs() < 0.001);
    }
}
