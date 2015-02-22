// Silence warnings about use of unstable features
#![feature(box_syntax)]
#![feature(core)]
#![feature(io)]
#![feature(path)]
#![feature(std_misc)]

mod control;
mod driver;
mod filtered_telemetry;
mod kml_waypoint_generator;
mod location_filter;
mod logger;
mod nmea;
mod stdout_logger;
mod telemetry;
mod telemetry_message;
mod termios;
mod waypoint_generator;

fn main() {
}
