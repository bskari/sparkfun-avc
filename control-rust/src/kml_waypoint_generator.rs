use std::io::BufferedReader;
use std::io::File;
use std::io::fs::PathExtensions;
use std::io::process::Command;

use waypoint_generator::WaypointGenerator;


/**
 * Loads and returns waypoints from a KML file.
 */
struct KmlWaypointGenerator {
    waypoints: Vec<(f32, f32)>,
    current_waypoint: u32,
}


impl KmlWaypointGenerator {
    pub fn new(file_name: &str) -> KmlWaypointGenerator {
        KmlWaypointGenerator {
            waypoints: KmlWaypointGenerator::load_waypoints(file_name),
            current_waypoint: 0
        }
    }

    /**
     * Parse a float from a string. The Pi has an older version of rustc, and
     * the official method for parsing a float differ between that version and
     * nightly, so we have to do ths manually.
     */
    fn parse_float(float_str: &str) -> Option<f32> {
        let mut value: f32 = 0.0;
        let mut negative = false;
        let mut negative_allowed = true;
        let mut decimal = false;
        let mut decimal_value: f32 = 0.0;
        let mut multiplier: f32 = 1.0;
        for letter in float_str.chars() {
            if letter == '-' {
                if negative_allowed {
                    negative = !negative;
                    continue;
                } else {
                    return None;
                }
            }
            negative_allowed = false;

            if letter == '.' {
                if decimal {
                    return None;
                }
                decimal = true;
                multiplier = 1.0;
                continue;
            }

            let digit_value = (letter as i32 - '0' as i32);
            if digit_value > 10 || digit_value < 0 {
                return None;
            }
            if decimal {
                decimal_value = decimal_value * 10.0 + digit_value as f32;
                multiplier *= 0.1;
            } else {
                value = value * 10.0 + digit_value as f32;
            }
        }

        Some(value + decimal_value * multiplier)
    }

    fn load_waypoints(file_name: &str) -> Vec<(f32, f32)> {
        let path = Path::new(file_name);
        if !path.exists() || !path.is_file() {
            fail!("File does not exist: {}", file_name);
        }

        // A KML file is a zip archive containing a single file named "doc.kml"
        // that is an XML file
        let temp_directory = "/tmp/waypoints";
        let zip_io_result = Command::new("unzip")
            .arg(file_name)
            .arg("-d")  // Output directory
            .arg(temp_directory)
            .spawn();
        match zip_io_result {
            Ok(p) => (),
            Err(e) => fail!("Failed to unzip file: {}", e),
        };

        let mut waypoints = Vec::<(f32, f32)>::new();
        let file_path = Path::new("/tmp/doc.kml");
        let mut xml_file = BufferedReader::new(File::open(&file_path));
        let mut coordinates_open_tag = false;
        // We should use a real XML parser here, but Google Earth saves the
        // <coordinates> tag on one line, then the coordinates on the next,
        // then the closing </coordinates> tag on the next, so we'll just rely
        // on that fact
        for line_option in xml_file.lines() {
            match line_option {
                Ok(line) => {
                    if line.as_slice().contains("<coordinates>") {
                        coordinates_open_tag = true;
                    } else if coordinates_open_tag {
                        let mut latitude = 0.0f32;
                        let mut longitude = 0.0f32;
                        for long_lat_alt in line.as_slice().words() {
                            let mut iterator = long_lat_alt.split(',');
                            let mut success = true;
                            match iterator.next() {
                                Some(longitude_str) => {
                                    let parsed_longitude: Option<f32> = KmlWaypointGenerator::parse_float(longitude_str);
                                    match parsed_longitude {
                                        Some(longitude_) => longitude = longitude_,
                                        None => {
                                            println!("Unable to parse longitude: '{}'", longitude_str);
                                            success = false;
                                        },
                                    }
                                },
                                None => println!("No longitude"),
                            }

                            match iterator.next() {
                                Some(latitude_str) => {
                                    // Rust 0.13 feature :(
                                    let parsed_latitude: Option<f32> = KmlWaypointGenerator::parse_float(latitude_str);
                                    match parsed_latitude {
                                        Some(latitude_) => latitude = latitude_,
                                        None => {
                                            println!("Unable to parse latitude: '{}'", latitude_str);
                                            success = false;
                                        },
                                    }
                                }
                                None => println!("No latitude"),
                            }

                            if (success) {
                                waypoints.push((latitude, longitude));
                            }
                        }
                        break;
                    }
                }
                Err(e) => println!("error {}", e),
            }
        }
        waypoints
    }
}


impl WaypointGenerator for KmlWaypointGenerator {
    fn get_current_waypoint(&self, x_m: f32, y_m: f32) -> (f32, f32) {
        // TODO
        (0.0, 0.0)
    }

    fn get_current_raw_waypoint(&self, x_m: f32, y_m: f32) -> (f32, f32) {
        // TODO
        (0.0, 0.0)
    }

    fn next(&self) {
        // TODO
    }

    fn reached(&self, x_m: f32, y_m: f32) -> bool {
        // TODO
        return false;
    }

    fn done(&self) -> bool {
        // TODO
        return false;
    }
}
