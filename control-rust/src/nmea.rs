/**
 * Reads NMEA messages from the GPS.
 */
use std::error::Error;
use std::mem::transmute;
use std::num::ParseFloatError;

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
    pub hdop: f32,
}

/**
 * VTG: Course over ground and ground speed.
 */
#[derive(PartialEq)]
pub struct VtgMessage {
    pub course: Degrees,
    pub speed: MetersPerSecond,
}

/**
 * RMC: Recommended minimum specific GNSS data.
 */
#[derive(PartialEq)]
pub struct RmcMessage {
    pub latitude_degrees: f64,
    pub longitude_degrees: f64,
    pub speed: MetersPerSecond,
    pub course: Degrees,
    pub magnetic_variation: Degrees,
}

/**
 * GSA: GNSS DOP and active satellites.
 */
#[derive(PartialEq)]
pub enum FixMode {
    Manual,
    Automatic,
}
#[derive(PartialEq)]
pub enum FixType {
    NotAvailable,
    TwoD,
    ThreeD,
}
#[derive(PartialEq)]
pub struct GsaMessage {
    pub mode: FixMode,
    pub fix_type: FixType,
    pub satellites_used: i32,
    pub pdop: f32,
    pub hdop: f32,
    pub vdop: f32,
}

/**
 * GSV: GNSS satellites in view.
 */
#[derive(PartialEq, Debug)]
pub struct SatelliteInformation {
    id: i32,
    elevation: Degrees,
    azimuth: Degrees,
    snr_db: i32,
}
#[derive(PartialEq, Debug)]
pub struct GsvMessage {
    pub message_count: i32,
    pub message_sequence_number: i32,
    pub satellites_in_view: i32,
    pub satellites: Vec<SatelliteInformation>,
}

/**
 * GLL: Latitude/longitude.
 */
#[derive(PartialEq)]
pub struct GllMessage {
    pub latitude_degrees: f64,
    pub longitude_degrees: f64,
}

/**
 * STI: Pitch, roll, yaw, pressure, temperature.
 */
#[derive(PartialEq)]
pub struct StiMessage {
    pitch: Degrees,
    roll: Degrees,
    yaw: Degrees,
    pressure: Pascal,
    temperature: Celsius,
}

/**
 * Magnetometer, accelerometer, pressure and temperature.
 */
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

#[allow(dead_code)]
#[derive(PartialEq)]
pub enum NmeaMessage {
    Binary(BinaryMessage),
    Gga(GgaMessage),
    Gll(GllMessage),
    Gsa(GsaMessage),
    Gsv(GsvMessage),
    Vtg(VtgMessage),
    Rmc(RmcMessage),
    Sti(StiMessage),
}

macro_rules! bail_err {
    ($option:expr) => {
        match $option {
            Ok(s) => s,
            Err(e) => return Err(e.description().to_string()),
        };
    };
}
macro_rules! bail_none {
    ($option:expr) => {
        match $option {
            Some(s) => s,
            None => return Err("Message too short".to_string()),
        };
    };
}
macro_rules! convert {
    ($to:ty, $value:expr) => {
        unsafe { transmute::<u32, $to>(transmute::<_, u32>($value).to_le()) }
    };
}
macro_rules! array_to_type {
    ($to:ty, $array:expr) => {
        convert![$to, [$array[3], $array[2], $array[1], $array[0]]]
    };
}

// convert! needs unsafe in tests, but not in regular code
#[allow(unused_unsafe)]
impl NmeaMessage {
    pub fn parse(message: &str) -> Result<NmeaMessage, String> {
        // These if statements are sorted in the rough likelihood of appearance
        if message.starts_with("$GPGGA") {
            match NmeaMessage::parse_gga(message) {
                Ok(gga) => Ok(NmeaMessage::Gga(gga)),
                Err(e) => Err(e),
            }
        } else if message.starts_with("$GPVTG") {
            match NmeaMessage::parse_vtg(message) {
                Ok(vtg) => Ok(NmeaMessage::Vtg(vtg)),
                Err(e) => Err(e),
            }
        } else if message.starts_with("$PSTI") {
            match NmeaMessage::parse_sti(message) {
                Ok(sti) => Ok(NmeaMessage::Sti(sti)),
                Err(e) => Err(e),
            }
        } else if message.starts_with("$GPRMC") {
            match NmeaMessage::parse_rmc(message) {
                Ok(rmc) => Ok(NmeaMessage::Rmc(rmc)),
                Err(e) => Err(e),
            }
        } else if message.starts_with("$GPGSA") {
            match NmeaMessage::parse_gsa(message) {
                Ok(gsa) => Ok(NmeaMessage::Gsa(gsa)),
                Err(e) => Err(e),
            }
        } else if message.starts_with("$GPGSV") {
            match NmeaMessage::parse_gsv(message) {
                Ok(gsv) => Ok(NmeaMessage::Gsv(gsv)),
                Err(e) => Err(e),
            }
        } else if message.starts_with("$GPGLL") {
            match NmeaMessage::parse_gll(message) {
                Ok(gll) => Ok(NmeaMessage::Gll(gll)),
                Err(e) => Err(e),
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

        iterator.next(); // Skip the message type
        iterator.next(); // Skip the UTC time

        let latitude_degrees = {
            let string = bail_none!(iterator.next());
            let d = bail_err!(NmeaMessage::parse_degrees_minutes(string));

            let north_indicator = bail_none!(iterator.next());
            let north = north_indicator == "N";
            if north {
                d
            } else {
                debug_assert!(north_indicator == "S");
                -d
            }
        };

        let longitude_degrees = {
            let string = bail_none!(iterator.next());
            let d = bail_err!(NmeaMessage::parse_degrees_minutes(string));

            let east_indicator = bail_none!(iterator.next());
            let east = east_indicator == "E";
            if east {
                d
            } else {
                debug_assert!(east_indicator == "W");
                -d
            }
        };

        let gps_quality_indicator = bail_none!(iterator.next());
        if gps_quality_indicator == "0" {
            return Err("Position fix unavailable".to_string());
        }
        iterator.next(); // Skip the satellites used

        let hdop_str = bail_none!(iterator.next());
        let hdop: f32 = bail_err!(hdop_str.parse());
        // Ignore altitude, DGPS station id, and checksum

        Ok(GgaMessage {
            latitude_degrees: latitude_degrees,
            longitude_degrees: longitude_degrees,
            hdop: hdop,
        })
    }

    /**
     * The actual course and speed relative to the ground.
     */
    fn parse_vtg(message: &str) -> Result<VtgMessage, String> {
        // $GPVTG,x.x,T,x.x,M,x.x,N,x.x,K,a*hh<CR><LF>
        let mut iterator = message.split(',');

        iterator.next(); // Skip the message type

        let course_d_str = bail_none!(iterator.next());
        let course_d: f32 = bail_err!(course_d_str.parse());
        iterator.next(); // Skip the letter T indicating true course

        iterator.next(); // Skip the magnetic course
        iterator.next(); // Skip the letter M indicating magnetic course

        iterator.next(); // Skip speed in knots
        iterator.next(); // Skip the letter N indicating knots

        let speed_km_h_str = bail_none!(iterator.next());
        let speed_km_h: f32 = bail_err!(speed_km_h_str.parse());
        iterator.next(); // Skip the letter K indicating km/h

        let mode_and_checksum = bail_none!(iterator.next());
        if mode_and_checksum.starts_with("N") {
            return Err("Data not valid".to_string());
        }

        Ok(VtgMessage {
            course: course_d,
            speed: speed_km_h * 1000.0 / (60.0 * 60.0),
        })
    }

    /**
     * Time, date, position, course and speed data.
     */
    fn parse_rmc(message: &str) -> Result<RmcMessage, String> {
        // $GPRMC,111636.932,A,2447.0949,N,12100.5223,E,000.0,000.0,030407,003.9,W,A*12<CR><LF>
        let mut iterator = message.split(',');

        iterator.next(); // Skip the message type
        iterator.next(); // Skip the UTC time

        let status = bail_none!(iterator.next());
        if status == "V" {
            return Err("Navigation receiver warning".to_string());
        }

        let latitude_degrees = {
            let string = bail_none!(iterator.next());
            let d = bail_err!(NmeaMessage::parse_degrees_minutes(string));

            let north_indicator = bail_none!(iterator.next());
            let north = north_indicator == "N";
            if north {
                d
            } else {
                debug_assert!(north_indicator == "S");
                -d
            }
        };

        let longitude_degrees = {
            let string = bail_none!(iterator.next());
            let d = bail_err!(NmeaMessage::parse_degrees_minutes(string));

            let east_indicator = bail_none!(iterator.next());
            let east = east_indicator == "E";
            if east {
                d
            } else {
                debug_assert!(east_indicator == "W");
                -d
            }
        };

        let speed_knots_str = bail_none!(iterator.next());
        let speed_knots: f32 = bail_err!(speed_knots_str.parse());
        let speed: MetersPerSecond = speed_knots * 0.5144;

        let course_d_str = bail_none!(iterator.next());
        let course: Degrees = bail_err!(course_d_str.parse());

        iterator.next(); // Skip UTC date

        let magnetic_variation = {
            let magnetic_d_str = bail_none!(iterator.next());
            let magnetic: Degrees = bail_err!(magnetic_d_str.parse());
            let east_west = bail_none!(iterator.next());
            if east_west == "E" {
                -magnetic
            } else {
                debug_assert!(east_west == "W");
                magnetic
            }
        };

        let mode_and_checksum = bail_none!(iterator.next());
        if mode_and_checksum.starts_with("N") {
            return Err("Data not valid".to_string());
        }

        Ok(RmcMessage {
            latitude_degrees: latitude_degrees,
            longitude_degrees: longitude_degrees,
            speed: speed,
            course: course,
            magnetic_variation: magnetic_variation,
        })
    }

    /**
     * GSA: GPS receiver operating mode, satellites used in the navigation solution reported by the
     * GGA or GNS sentence and DOP values.
     */
    fn parse_gsa(message: &str) -> Result<GsaMessage, String> {
        // $GPGSA,A,x,xx,xx,xx,xx,xx,xx,xx,xx,xx,xx,xx,xx,x.x,x.x,x.x*hh<CR><LF>
        let mut iterator = message.split(',');

        iterator.next(); // Skip the message type

        let fix_mode_str = bail_none!(iterator.next());
        let fix_mode = if fix_mode_str == "A" {
            FixMode::Automatic
        } else {
            debug_assert!(fix_mode_str == "M");
            FixMode::Manual
        };

        let fix_type_str = bail_none!(iterator.next());
        let fix_type = if fix_type_str == "1" {
            FixType::NotAvailable
        } else if fix_type_str == "2" {
            FixType::TwoD
        } else {
            debug_assert!(fix_type_str == "3");
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

        Ok(GsaMessage {
            mode: fix_mode,
            fix_type: fix_type,
            satellites_used: satellites_used,
            pdop: pdop,
            hdop: hdop,
            vdop: vdop,
        })
    }

    /**
     * GSV: Number of satellites in view, IDs, elevation, azimuth and SNR.
     */
    fn parse_gsv(message: &str) -> Result<GsvMessage, String> {
        // $GPGSV,3,1,12,05,54,069,45,12,44,061,44,21,07,184,46,22,78,289,47*72<CR><LF>
        let mut iterator = message.split(',');

        iterator.next(); // Skip the message type

        let message_count_str = bail_none!(iterator.next());
        let message_count: i32 = bail_err!(message_count_str.parse());

        let message_sequence_number_str = bail_none!(iterator.next());
        let message_sequence_number: i32 = bail_err!(message_sequence_number_str.parse());

        let satellites_in_view_str = bail_none!(iterator.next());
        let satellites_in_view: i32 = bail_err!(satellites_in_view_str.parse());

        let mut satellites: Vec<SatelliteInformation> = Vec::with_capacity(6);
        let mut done = false;

        loop {
            let id_str = bail_none!(iterator.next());
            let id: i32 = bail_err!(id_str.parse());
            let elevation_str = bail_none!(iterator.next());
            let elevation: Degrees = bail_err!(elevation_str.parse());
            let azimuth_str = bail_none!(iterator.next());
            let azimuth: Degrees = bail_err!(azimuth_str.parse());
            let snr_str = bail_none!(iterator.next());
            let snr: i32 = match snr_str.parse() {
                Ok(value) => value,
                Err(_) => {
                    done = true;
                    // This might be the last in the series, in which case the string looks
                    // like "47*72" where the 72 is the message checksum
                    let mut snr_iterator = snr_str.split('*');
                    let snr = bail_none!(snr_iterator.next());
                    match snr.parse::<i32>() {
                        Ok(value) => value,
                        Err(e) => return Err(e.description().to_string()),
                    }
                }
            };
            satellites.push(SatelliteInformation {
                id: id,
                elevation: elevation,
                azimuth: azimuth,
                snr_db: snr,
            });
            if done {
                break;
            }
        }

        Ok(GsvMessage {
            message_count: message_count,
            message_sequence_number: message_sequence_number,
            satellites_in_view: satellites_in_view,
            satellites: satellites,
        })
    }

    /**
     * GLL: Latitude/longitude.
     */
    fn parse_gll(message: &str) -> Result<GllMessage, String> {
        // $GPGLL,ddmm.mmmm,a,dddmm.mmmm,a,hhmmss.sss,A,a*hh<CR><LF>
        let mut iterator = message.split(',');

        iterator.next(); // Skip the message type

        let latitude_degrees = {
            let string = bail_none!(iterator.next());
            let d = bail_err!(NmeaMessage::parse_degrees_minutes(string));

            let north_indicator = bail_none!(iterator.next());
            let north = north_indicator == "N";
            if north {
                d
            } else {
                debug_assert!(north_indicator == "S");
                -d
            }
        };

        let longitude_degrees = {
            let string = bail_none!(iterator.next());
            let d = bail_err!(NmeaMessage::parse_degrees_minutes(string));

            let east_indicator = bail_none!(iterator.next());
            let east = east_indicator == "E";
            if east {
                d
            } else {
                debug_assert!(east_indicator == "W");
                -d
            }
        };

        iterator.next(); // Skip UTC time

        let status = bail_none!(iterator.next());
        if status == "V" {
            return Err("Data not valid".to_string());
        }

        let mode_indicator = bail_none!(iterator.next());
        if mode_indicator == "V" {
            return Err("Data not valid".to_string());
        }

        Ok(GllMessage {
            latitude_degrees: latitude_degrees,
            longitude_degrees: longitude_degrees,
        })
    }

    /**
     * STI: Pitch, roll, yaw, pressure, temperature.
     */
    fn parse_sti(message: &str) -> Result<StiMessage, String> {
        // $PSTI,004,001,1,34.7,121.6,-48.2,99912,29.4*08<CR><LF>
        let mut iterator = message.split(',');

        iterator.next(); // Skip the message type
        iterator.next(); // Skip message id
        iterator.next(); // Skip message sub id

        let validity_flag = bail_none!(iterator.next());
        if validity_flag == "0" {
            return Err("Magnetic calibration not done".to_string());
        }
        debug_assert!(validity_flag == "1");

        let pitch_str = bail_none!(iterator.next());
        let pitch: Degrees = bail_err!(pitch_str.parse());

        let roll_str = bail_none!(iterator.next());
        let roll: Degrees = bail_err!(roll_str.parse());

        let yaw_str = bail_none!(iterator.next());
        let yaw: Degrees = bail_err!(yaw_str.parse());

        let pressure_str = bail_none!(iterator.next());
        let pressure: Pascal = bail_err!(pressure_str.parse());

        let temperature_and_checksum_str = bail_none!(iterator.next());
        let star_index = match temperature_and_checksum_str.chars().position(|x| x == '*') {
            Some(index) => index,
            None => return Err("Invalid temperature".to_string()),
        };
        let temperature: Celsius = bail_err!(temperature_and_checksum_str[0..star_index].parse());

        Ok(StiMessage {
            pitch: pitch,
            roll: roll,
            yaw: yaw,
            pressure: pressure,
            temperature: temperature,
        })
    }

    #[allow(dead_code)]
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
            Ok(NmeaMessage::Binary(BinaryMessage {
                x_gravity: acceleration_x,
                y_gravity: acceleration_y,
                z_gravity: acceleration_z,
                x_magnetic_field: magnetic_x,
                y_magnetic_field: magnetic_y,
                z_magnetic_field: magnetic_z,
                pressure: pressure,
                temperature: temperature,
            }))
        }
    }

    fn parse_degrees_minutes(degrees_minutes: &str) -> Result<f64, ParseFloatError> {
        let decimal_point_index = match degrees_minutes.chars().position(|x| x == '.') {
            Some(index) => index,
            None => return degrees_minutes.parse::<f64>(),
        };
        // There are always two digits for whole number minutes
        let degrees: f64 = match degrees_minutes[0..decimal_point_index - 2].parse() {
            Ok(i) => i,
            Err(e) => return Err(e),
        };
        let minutes: f64 = match degrees_minutes[decimal_point_index - 2..].parse() {
            Ok(f) => f,
            Err(e) => return Err(e),
        };
        Ok(degrees as f64 + minutes / 60.0f64)
    }
}

#[cfg(test)]
mod tests {
    use super::NmeaMessage::Binary;
    use super::{
        BinaryMessage, FixMode, FixType, GgaMessage, GllMessage, GsaMessage, GsvMessage,
        NmeaMessage, RmcMessage, SatelliteInformation, StiMessage, VtgMessage,
    };
    use std::fs::File;
    use std::io::{BufRead, BufReader};
    use std::mem::transmute;
    use std::path::Path;
    use std::thread::sleep;
    use std::time::Duration;

    use termios::{Speed, Termio};

    #[test]
    fn test_parse_gga() {
        let message = "$GPGGA,033403.456,0102.3456,N,0102.3456,W,1,11,0.8,108.2,M,,,,0000*01\r\n";
        let expected = GgaMessage {
            latitude_degrees: 1.0390933333333334f64,
            longitude_degrees: -1.0390933333333334f64,
            hdop: 0.8f32,
        };
        match NmeaMessage::parse_gga(message) {
            Ok(gga) => assert!(expected == gga),
            _ => assert!(false),
        };
    }

    #[test]
    fn test_parse_vtg() {
        // 36 km/h = 10 m/s
        let message = "$GPVTG,123.4,T,356.1,M,000.0,N,0036.0,K,A*32\r\n";
        let expected = VtgMessage {
            course: 123.4,
            speed: 10.0,
        };
        match NmeaMessage::parse_vtg(message) {
            Ok(vtg) => assert!(expected == vtg),
            _ => assert!(false),
        }
    }

    #[test]
    fn test_parse_rmc() {
        let message =
            "$GPRMC,111636.932,A,2447.0949,N,12100.5223,E,000.0,000.0,030407,003.9,W,A*12\r\n";
        let expected = RmcMessage {
            latitude_degrees: 24.784915,
            longitude_degrees: 121.008705,
            speed: 0.0,
            course: 0.0,
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
            pdop: 1.2,
            hdop: 0.8,
            vdop: 0.6,
        };
        match NmeaMessage::parse_gsa(message) {
            Ok(gsa) => assert!(expected == gsa),
            _ => assert!(false),
        }
    }

    #[test]
    fn test_parse_gsv() {
        let message = "$GPGSV,3,1,12,05,54,069,45,12,44,061,44,21,07,184,46,22,78,289,47*72\r\n";
        let expected = GsvMessage {
            message_count: 3,
            message_sequence_number: 1,
            satellites_in_view: 12,
            satellites: vec![
                SatelliteInformation {
                    id: 05,
                    elevation: 54.0,
                    azimuth: 069.0,
                    snr_db: 45,
                },
                SatelliteInformation {
                    id: 12,
                    elevation: 44.0,
                    azimuth: 061.0,
                    snr_db: 44,
                },
                SatelliteInformation {
                    id: 21,
                    elevation: 07.0,
                    azimuth: 184.0,
                    snr_db: 46,
                },
                SatelliteInformation {
                    id: 22,
                    elevation: 78.0,
                    azimuth: 289.0,
                    snr_db: 47,
                },
            ],
        };
        match NmeaMessage::parse_gsv(message) {
            Ok(gsv) => assert!(expected == gsv),
            _ => assert!(false),
        }

        let message_2 = "$GPGSV,3,2,12,30,65,118,45,09,12,047,37,18,62,157,47,06,08,144,45*7C\r\n";
        let expected_2 = GsvMessage {
            message_count: 3,
            message_sequence_number: 2,
            satellites_in_view: 12,
            satellites: vec![
                SatelliteInformation {
                    id: 30,
                    elevation: 65.0,
                    azimuth: 118.0,
                    snr_db: 45,
                },
                SatelliteInformation {
                    id: 09,
                    elevation: 12.0,
                    azimuth: 047.0,
                    snr_db: 37,
                },
                SatelliteInformation {
                    id: 18,
                    elevation: 62.0,
                    azimuth: 157.0,
                    snr_db: 47,
                },
                SatelliteInformation {
                    id: 06,
                    elevation: 08.0,
                    azimuth: 144.0,
                    snr_db: 45,
                },
            ],
        };
        match NmeaMessage::parse_gsv(message_2) {
            Ok(gsv) => {
                println!("\n{:?}\n{:?}", expected_2, gsv);
                assert!(expected_2 == gsv)
            }
            _ => assert!(false),
        }
    }

    #[test]
    fn test_parse_gll() {
        let message = "$GPGLL,2447.0944,N,12100.5213,E,112609.932,A,A*57\r\n";
        let expected = GllMessage {
            latitude_degrees: 24.784906666666668,
            longitude_degrees: 121.00868833333334,
        };
        match NmeaMessage::parse_gll(message) {
            Ok(gll) => assert!(expected == gll),
            _ => assert!(false),
        };
    }

    #[test]
    fn test_parse_sti() {
        let message = "$PSTI,004,001,1,34.7,121.6,-48.2,99912,29.4*08\r\n";
        let expected = StiMessage {
            pitch: 34.7,
            roll: 121.6,
            yaw: -48.2,
            pressure: 99912,
            temperature: 29.4,
        };
        match NmeaMessage::parse_sti(message) {
            Ok(sti) => assert!(expected == sti),
            Err(e) => {
                println!("{}", e);
                assert!(false)
            }
        };
    }

    #[test]
    fn test_parse() {
        let gga = "$GPGGA,033403.456,0102.3456,N,0102.3456,W,1,11,0.8,108.2,M,,,,0000*01\r\n";
        let vtg = "$GPVTG,123.4,T,356.1,M,000.0,N,0036.0,K,A*32\r\n";
        let rmc =
            "$GPRMC,111636.932,A,2447.0949,N,12100.5223,E,000.0,000.0,030407,003.9,W,A*12\r\n";
        let gsa = "$GPGSA,A,3,05,12,21,22,30,09,18,06,14,01,31,,1.2,0.8,0.6*36\r\n";
        let gsv = "$GPGSV,3,1,12,05,54,069,45,12,44,061,44,21,07,184,46,22,78,289,47*72\r\n";
        let gll = "$GPGLL,2447.0944,N,12100.5213,E,112609.932,A,A*57\r\n";
        let sti = "$PSTI,004,001,1,34.7,121.6,-48.2,99912,29.4*08\r\n";

        match NmeaMessage::parse(gga).unwrap() {
            NmeaMessage::Gga(_gga) => (),
            _ => assert!(false),
        };
        match NmeaMessage::parse(vtg).unwrap() {
            NmeaMessage::Vtg(_vtg) => (),
            _ => assert!(false),
        };
        match NmeaMessage::parse(rmc).unwrap() {
            NmeaMessage::Rmc(_rmc) => (),
            _ => assert!(false),
        };
        match NmeaMessage::parse(gsa).unwrap() {
            NmeaMessage::Gsa(_gsa) => (),
            _ => assert!(false),
        };
        match NmeaMessage::parse(gsv).unwrap() {
            NmeaMessage::Gsv(_gsv) => (),
            _ => assert!(false),
        };
        match NmeaMessage::parse(gll).unwrap() {
            NmeaMessage::Gll(_gll) => (),
            _ => assert!(false),
        };
        match NmeaMessage::parse(sti).unwrap() {
            NmeaMessage::Sti(_sti) => (),
            _ => assert!(false),
        };
    }

    #[test]
    fn test_tty() {
        // This will fail on everything but the Pi, so let's just ignore it if we're not running on
        // the Pi.
        if !cfg!(target_arch = "arm") {
            return;
        }
        let tty = match File::open(Path::new("/dev/ttyAMA0")) {
            Ok(f) => f,
            Err(_m) => panic!("Unable to open /dev/ttyAMA0."),
        };
        tty.set_speed(Speed::B1152000).unwrap();
        tty.drop_input_output().unwrap();
        let mut message = String::new();
        let mut buffer_ready = false;
        for _ in 0..20 {
            if tty.input_buffer_count().unwrap() > 0 {
                buffer_ready = true;
                break;
            } else {
                sleep(Duration::from_millis(50));
            }
        }
        assert!({
            "No messages received from the GPS over the virtual TTY";
            buffer_ready
        });
        let mut reader = BufReader::new(tty);
        reader.read_line(&mut message).unwrap();
        let message = String::new();
        match NmeaMessage::parse(&message) {
            Ok(_m) => (),
            Err(e) => panic!(format!(
                "Unable to parse NmeaMessage\n{}\nbecause {}",
                message, e
            )),
        }
    }

    #[test]
    fn test_parse_binary() {
        let message: [u8; 34] = [
            0xCFu8, 0x01, 0xBD, 0x4F, 0xE1, 0x54, 0xBE, 0x15, 0xE9, 0xE2, 0x3F, 0x6F, 0x3C, 0xB4,
            0xC0, 0xC5, 0x9D, 0x2A, 0x40, 0x79, 0x84, 0x08, 0x40, 0xCE, 0xFA, 0xB0, 0x00, 0x01,
            0x85, 0xB1, 0x41, 0xF1, 0x99, 0x9A,
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
            _ => assert!(false),
        }
    }

    #[test]
    fn test_convert() {
        assert!((convert![f32, 0xBD4FE154u32] - -0.050752).abs() < 0.001);
    }
}
