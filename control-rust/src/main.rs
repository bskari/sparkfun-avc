// Silence warnings about use of unstable features
#![feature(box_syntax)]
#![feature(core)]
#![feature(io)]
#![feature(path)]
#![feature(std_misc)]
#[macro_use]

extern crate log;
extern crate time;
use log::{set_logger, LogLevel, LogLevelFilter, LogRecord};
use std::old_io::timer;
use std::sync::mpsc::{channel, Sender, Receiver};
use std::thread;
use std::thread::JoinHandle;
use std::time::duration::Duration;
use time::{now, strftime};

use control::Control;
use kml_waypoint_generator::KmlWaypointGenerator;
use telemetry::TelemetryState;
use telemetry_message::{CommandMessage, CompassMessage, GpsMessage};
use waypoint_generator::WaypointGenerator;

mod control;
mod driver;
mod filtered_telemetry;
mod kml_waypoint_generator;
mod location_filter;
mod nmea;
mod telemetry;
mod telemetry_message;
mod termios;
mod waypoint_generator;

struct StdoutLogger;
impl log::Log for StdoutLogger {
    fn enabled(&self, level: LogLevel, _module: &str) -> bool {
        level <= LogLevel::Info
    }

    fn log(&self, record: &LogRecord) {
        if self.enabled(record.level(), record.location().module_path) {
            let now_tm = now();
            let time_str = match strftime("%Y/%m/%d %H:%M:%S", &now_tm) {
                Ok(s) => s,
                Err(e) => "UNKNOWN".to_string(),
            };
            println!("{} - {} - {}", time_str, record.level(), record.args());
        }
    }
}


fn main() {
    let status = set_logger(|max_log_level| {
        max_log_level.set(LogLevelFilter::Info);
        Box::new(StdoutLogger)
    });
    match status {
        Ok(logger) => (),
        Err(e) => println!("Unable to initialize logger"),
    };

    let (request_telemetry_tx, request_telemetry_rx) = channel();
    let (telemetry_tx, telemetry_rx) = channel();
    let (command_tx, command_rx) = channel();

    // TODO: Send quit when Ctrl + C is pressed
    let mut join_handles = Vec::new();
    join_handles.push(spawn_control(request_telemetry_tx, telemetry_rx, command_rx));

    // TODO: Remove testing
    command_tx.send(CommandMessage::Quit);

    for handle in join_handles {
        handle.join();
    }
}


fn spawn_control(
    request_telemetry_tx: Sender<()>,
    telemetry_rx: Receiver<TelemetryState>,
    command_rx: Receiver<CommandMessage>,
) -> JoinHandle {
    thread::spawn(move || {
        let waypoint_generator = KmlWaypointGenerator::new(
            "../control/paths/solid-state-depot.kmz");
        let control = Control::new(
            request_telemetry_tx,
            telemetry_rx,
            command_rx,
            &waypoint_generator);
        loop {
            // TODO
            break;
        }
    })
}
