//#![feature(slicing_syntax)]
// Silence warnings about use of unstable features
#![feature(core)]
#![feature(io)]
#![feature(path)]
#![feature(std_misc)]

pub mod filtered_telemetry;
pub mod kml_waypoint_generator;
pub mod location_filter;
pub mod logger;
pub mod stdout_logger;
pub mod telemetry;
pub mod telemetry_message;
pub mod waypoint_generator;
