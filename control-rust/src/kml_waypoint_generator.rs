use libc::consts::os::posix88::ENOENT;
use std::fs::{File, PathExt, remove_dir_all};
use std::io::{BufRead, BufReader};
use std::path::Path;
use std::process::Command;

use telemetry::{Meter, Point, distance, latitude_longitude_to_point};
use waypoint_generator::WaypointGenerator;


/**
 * Loads and returns waypoints from a KML file.
 */
#[allow(dead_code)]
pub struct KmlWaypointGenerator {
    waypoints: Vec<Point>,
    current_waypoint: usize,
}


impl KmlWaypointGenerator {
    /**
     * Loads waypoints from a KML path file.
     */
    pub fn new(kml_file_name: &str) -> KmlWaypointGenerator {
        let xml_file = KmlWaypointGenerator::extract_doc_kml(kml_file_name);
        let waypoints_line = KmlWaypointGenerator::extract_waypoints_line(xml_file);
        let points = KmlWaypointGenerator::parse_waypoints_line(&waypoints_line[..]);
        KmlWaypointGenerator::new_from_waypoints(points)
    }

    /**
     * For testing.
     */
    fn new_from_waypoints(waypoints: Vec<Point>) -> KmlWaypointGenerator {
        KmlWaypointGenerator {
            waypoints: waypoints,
            current_waypoint: 0,
        }
    }

    /**
     * Returns a file handle to the doc.kml file from a kml file (in zip format).
     */
    fn extract_doc_kml(kml_file_name: &str) -> BufReader<File> {
        let path = Path::new(kml_file_name);
        if !path.exists() || !path.is_file() {
            panic!("File does not exist: {}", kml_file_name);
        }

        // A KML file is a zip archive containing a single file named "doc.kml"
        // that is an XML file
        let temp_directory = "/tmp/waypoints";
        match remove_dir_all(temp_directory) {
            Ok(_) => (),
            Err(e) => match e.raw_os_error() {
                Some(errno) => if errno == ENOENT {
                        ()  // Directory does not exist; that's fine
                    } else {
                        warn!("Failed to remove temp directory: {}", e)
                    },
                None => warn!("Failed to remove temp directory: {}", e),
            }
        };
        let zip_io_result = Command::new("unzip")
            .arg(kml_file_name)
            .arg("-d")  // Output directory
            .arg(temp_directory)
            .spawn();
        let mut zip_child = match zip_io_result {
            Ok(child) => (child),
            Err(e) => panic!("Failed to unzip file: {}", e),
        };

        match zip_child.wait() {
            Ok(_) => (),
            Err(e) => panic!("Failed to unzip file: {}", e),
        };

        let mut waypoints = Vec::<Point>::new();
        let file_path = Path::new("/tmp/waypoints/doc.kml");
        let file = match File::open(&file_path) {
            Ok(f) => f,
            Err(_) => panic!("Couldn't open doc.kml"),
        };
        BufReader::new(file)
    }

    /**
     * Returns the waypoints line (e.g. "40.9,-105.3,0 41.1,-105.2,0") from the doc.kml file
     * extracted from a kml file.
     */
    fn extract_waypoints_line<T: BufRead>(xml_file: T) -> String {
        let mut coordinates_open_tag = false;
        // We should use a real XML parser here, but Google Earth saves the
        // <coordinates> tag on one line, then the coordinates on the next,
        // then the closing </coordinates> tag on the next, so we'll just rely
        // on that fact
        for line_option in xml_file.lines() {
            match line_option {
                Ok(line) => {
                    if line.contains("<coordinates>") {
                        coordinates_open_tag = true;
                    } else if coordinates_open_tag {
                        return line;
                    }
                }
                Err(e) => println!("error {}", e),
            }
        }
        panic!("No waypoints line found");
    }

    /**
     * Returns the waypoints from a waypoint formatted line, e.g. "40.9,-105.3,0 41.1,-105.2,0".
     */
    fn parse_waypoints_line(line: &str) -> Vec<Point> {
        let mut waypoints: Vec<Point> = vec![];
        let mut latitude = 0.0f64;
        let mut longitude = 0.0f64;
        for long_lat_alt in line.split_whitespace() {
            let mut iterator = long_lat_alt.split(',');
            let mut success = true;
            match iterator.next() {
                Some(longitude_str) => {
                    let parsed_longitude = longitude_str.parse::<f64>();
                    match parsed_longitude {
                        Ok(longitude_) => longitude = longitude_,
                        Err(e) => {
                            println!("Unable to parse longitude: '{}', {}", longitude_str, e);
                            success = false;
                        },
                    }
                },
                None => println!("No longitude"),
            }

            match iterator.next() {
                Some(latitude_str) => {
                    let parsed_latitude = latitude_str.parse::<f64>();
                    match parsed_latitude {
                        Ok(latitude_) => latitude = latitude_,
                        Err(e) => {
                            println!(
                                "Unable to parse latitude: '{}', {}",
                                 latitude_str,
                                 e);
                            success = false;
                        },
                    }
                }
                None => println!("No latitude"),
            }

            if success {
                waypoints.push(latitude_longitude_to_point(latitude, longitude));
            }
        }
        waypoints
    }
}


impl WaypointGenerator for KmlWaypointGenerator {
    #[allow(unused_variables)]
    fn get_current_waypoint(&self, point: &Point) -> Option<Point> {
        if !self.done() {
            Some(self.waypoints[self.current_waypoint])
        } else {
            None
        }
    }

    fn get_current_raw_waypoint(&self, point: &Point) -> Option<Point> {
        self.get_current_waypoint(point)
    }

    fn next(&mut self) {
        self.current_waypoint += 1;
    }

    #[allow(unused_variables)]
    fn reached(&self, point: &Point) -> bool {
        // TODO: Change this so that it returns true if we're within a certain distance (e.g. 1m)
        // or if we are within a certain distance (e.g. 3m) and we start getting farther away
        let current_option = self.get_current_waypoint(point);
        let current = match current_option {
            Some(point) => point,
            None => return false,
        };
        if distance(&current, point) < 1.0 {
            return true;
        }
        return false;
    }

    fn done(&self) -> bool {
        if self.current_waypoint >= self.waypoints.len() {
            return true;
        }
        return false;
    }

    #[allow(unused_variables)]
    fn reach_distance(&self) -> Meter {
        1.0
    }
}


#[cfg(test)]
mod tests {
    use num::traits::{Float, FromPrimitive};
    use std::io::BufRead;

    use super::KmlWaypointGenerator;
    use telemetry::Point;
    use waypoint_generator::WaypointGenerator;

    fn assert_approx_eq<T: Float + FromPrimitive>(value_1: T, value_2: T) {
        assert!(approx_eq(value_1, value_2));
    }
    fn approx_eq<T: Float + FromPrimitive>(value_1: T, value_2: T) -> bool {
        // Yeah, I know this is bad, see
        // http://randomascii.wordpress.com/2012/02/25/comparing-floating-point-numbers-2012-edition/

        let diff = (value_1 - value_2).abs();
        // This is the best we can do with f32
        diff < FromPrimitive::from_f32(0.00001f32).unwrap()
    }

    #[test]
    fn test_get_current_waypoint() {
        let first = Point { x: 1.0, y: 1.0 };
        let other = Point { x: 200.0, y: 200.0 };
        let waypoint_generator = KmlWaypointGenerator::new_from_waypoints(
            vec![first, other]
        );
        let current_option = waypoint_generator.get_current_waypoint(&other);
        let current = match current_option {
            Some(point) => point,
            None => {
                assert!(false);
                Point { x: 0.0, y: 0.0 }  // This should never be reached
            }
        };
        assert!(current.x == first.x);
        assert!(current.y == first.y);
    }

    #[test]
    fn test_get_current_raw_waypoint() {
        // For KML, this is identical to get_current_waypoint
        let first = Point { x: 1.0, y: 1.0 };
        let other = Point { x: 200.0, y: 200.0 };
        let waypoint_generator = KmlWaypointGenerator::new_from_waypoints(
            vec![first, other]
        );
        let current_option = waypoint_generator.get_current_waypoint(&other);
        let current = match current_option {
            Some(point) => point,
            None => {
                assert!(false);
                Point { x: 0.0, y: 0.0 }  // This should never be reached
            }
        };
        assert!(current.x == first.x);
        assert!(current.y == first.y);
    }

    #[test]
    fn test_next() {
        let first = Point { x: 1.0, y: 1.0 };
        let second = Point { x: 2.0, y: 2.0 };
        let other = Point { x: 200.0, y: 200.0 };
        let mut waypoint_generator = KmlWaypointGenerator::new_from_waypoints(
            vec![first, second]
        );

        let current_option = waypoint_generator.get_current_waypoint(&other);
        let current = match current_option {
            Some(point) => point,
            None => {
                assert!(false);
                Point { x: 0.0, y: 0.0 }  // This should never be reached
            }
        };
        assert!(current.x == first.x);
        assert!(current.y == first.y);

        waypoint_generator.next();
        let current_option_2 = waypoint_generator.get_current_waypoint(&other);
        let current_2 = match current_option_2 {
            Some(point) => point,
            None => {
                assert!(false);
                panic!("This should never be reached");
            }
        };
        assert!(current_2.x == second.x);
        assert!(current_2.y == second.y);

        for _ in 0..3 {
            waypoint_generator.next();
            match waypoint_generator.get_current_waypoint(&other) {
                Some(_) => {
                    assert!(false);
                    panic!("This should never be reached");
                },
                None => ()
            }
        }
    }

    #[test]
    fn test_reached() {
        let first = Point { x: 1.0, y: 1.0 };
        let other = Point { x: 200.0, y: 200.0 };
        let waypoint_generator = KmlWaypointGenerator::new_from_waypoints(
            vec![first, other]
        );
        let current_option = waypoint_generator.get_current_waypoint(&other);
        let current = match current_option {
            Some(point) => point,
            None => {
                assert!(false);
                panic!("This should never be reached");
            }
        };

        let mut current = first;

        // Exactly on the point
        assert!(waypoint_generator.reached(&current));

        // Within reach_distance of the point
        current.x += waypoint_generator.reach_distance() * 0.999;
        assert!(waypoint_generator.reached(&current));
        current.x = first.x;
        current.y += waypoint_generator.reach_distance() * 0.999;
        assert!(waypoint_generator.reached(&current));

        // Outside
        current.x += waypoint_generator.reach_distance() * 0.999;
        assert!(!waypoint_generator.reached(&current));
        current.x += 1000.0;
        current.y += 1000.0;
        assert!(!waypoint_generator.reached(&current));
        current.x -= 5000.0;
        current.y -= 5000.0;
        assert!(!waypoint_generator.reached(&current));
    }

    #[test]
    fn test_done() {
        let first = Point { x: 1.0, y: 1.0 };
        let mut waypoint_generator = KmlWaypointGenerator::new_from_waypoints(vec![first]);
        assert!(!waypoint_generator.done());
        for _ in 0..3 {
            waypoint_generator.next();
            assert!(waypoint_generator.done());
        }
    }

    #[test]
    fn test_extract_waypoints_line() {
        let xml_template = (r#"<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:kml="http://www.opengis.net/kml/2.2" xmlns:atom="http://www.w3.org/2005/Atom">
<Document>
	<name>rally-1-loop.kmz</name>
	<Style id="s_ylw-pushpin_hl">
		<IconStyle>
			<scale>1.3</scale>
			<Icon>
				<href>http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png</href>
			</Icon>
			<hotSpot x="20" y="2" xunits="pixels" yunits="pixels"/>
		</IconStyle>
	</Style>
	<StyleMap id="m_ylw-pushpin">
		<Pair>
			<key>normal</key>
			<styleUrl>#s_ylw-pushpin</styleUrl>
		</Pair>
		<Pair>
			<key>highlight</key>
			<styleUrl>#s_ylw-pushpin_hl</styleUrl>
		</Pair>
	</StyleMap>
	<Style id="s_ylw-pushpin">
		<IconStyle>
			<scale>1.1</scale>
			<Icon>
				<href>http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png</href>
			</Icon>
			<hotSpot x="20" y="2" xunits="pixels" yunits="pixels"/>
		</IconStyle>
	</Style>
	<Placemark>
		<name>Rally 1 loop</name>
		<styleUrl>#m_ylw-pushpin</styleUrl>
		<LineString>
			<tessellate>1</tessellate>
			<coordinates>
                {}
			</coordinates>
		</LineString>
	</Placemark>
</Document>
</kml>
"#);
        let first = Point { x: 1.0, y: -5.0 };
        let second = Point { x: -3.0, y: 10.0 };
        let coordinates_line = format!("{},{},0 {},{},0", first.x, first.y, second.x, second.y);
        let xml_string = xml_template.replace("{}", &coordinates_line[..]);
        // Hey, Rust already defines a impl<'a> BufRead for &'a [u8]! Cool!
        let xml_buffer = xml_string.as_bytes();
        assert!(
            KmlWaypointGenerator::extract_waypoints_line(xml_buffer).trim() == coordinates_line
        );
    }

    fn test_parse_waypoints_line() {
        let first = Point { x: 1.0, y: -5.0 };
        let second = Point { x: -3.0, y: 10.0 };
        let coordinates_line = format!("{},{},0 {},{},0", first.x, first.y, second.x, second.y);
        let points = KmlWaypointGenerator::parse_waypoints_line(&coordinates_line[..]);
        assert!(points.len() == 2);
        assert!(points[0] == first);
        assert!(points[1] == second);
    }
}
