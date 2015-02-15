/**
 * Reads NMEA messages from the GPS.
 */

use std::error::Error;


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
    pub course_d: f32,
    pub speed_m_s: f32,
}


#[derive(PartialEq)]
pub enum NmeaMessage {
    Gga(GgaMessage),
    Vtg(VtgMessage),
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
}


#[cfg(test)]
mod tests {
    use super::{NmeaMessage, GgaMessage, VtgMessage};
    use super::NmeaMessage::{Gga, Vtg};

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
}
