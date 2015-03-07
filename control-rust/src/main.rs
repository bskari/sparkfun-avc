// Silence warnings about use of unstable features
#![feature(box_syntax)]
#![feature(core)]
#![feature(fs)]
#![feature(io)]
#![feature(libc)]
#![feature(old_io)]
#![feature(old_path)]
#![feature(std_misc)]
#[macro_use]

extern crate log;
extern crate time;
use log::{set_logger, LogLevel, LogLevelFilter, LogRecord};
use std::sync::mpsc::{channel, Sender, Receiver};
use std::thread;
use std::thread::JoinHandle;
use time::{now, strftime};

use control::Control;
use filtered_telemetry::FilteredTelemetry;
use kml_waypoint_generator::KmlWaypointGenerator;
use telemetry::TelemetryState;
use telemetry_message::{CommandMessage, TelemetryMessage};
use telemetry_provider::TelemetryProvider;

mod control;
mod driver;
mod filtered_telemetry;
mod kml_waypoint_generator;
mod location_filter;
mod nmea;
mod telemetry;
mod telemetry_message;
mod telemetry_provider;
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
            let time_str = match strftime("%Y/%m/%d %H:%M:%S.", &now_tm) {
                Ok(s) => s,
                Err(_) => "UNKNOWN".to_string()  // This should never happen
            } + &format!("{}", now_tm.tm_nsec)[0..3];
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
        Ok(_) => (),
        Err(e) => println!("Unable to initialize logger: {}", e)
    };
    info!("Starting up");

    let mut quitters = Vec::new();

    let (request_telemetry_tx, request_telemetry_rx) = channel();
    let (telemetry_tx, telemetry_rx) = channel();
    let (command_tx, command_rx) = channel();
    let (quit_command_tx, quit_command_rx) = channel();
    quitters.push(quit_command_tx);

    // TODO: Send quit when Ctrl + C is pressed
    let mut join_handles = Vec::new();
    join_handles.push(spawn_control(request_telemetry_tx, telemetry_rx, command_rx,
                                    quit_command_rx));

    let (telemetry_message_tx, telemetry_message_rx) = channel();
    let (quit_termio_tx, quit_termio_rx) = channel();
    quitters.push(quit_termio_tx);
    join_handles.push(spawn_telemetry_provider(telemetry_message_tx, quit_termio_rx));

    let (quit_telemetry_tx, quit_telemetry_rx) = channel();

    join_handles.push(spawn_telemetry(request_telemetry_rx, telemetry_tx, telemetry_message_rx,
                                      quit_telemetry_rx));
    quitters.push(quit_telemetry_tx);

    for quitter in quitters {
        match quitter.send(()) {
            Ok(_) => (),
            Err(e) => error!("Unable to send quit message: {}", e)
        }
    }

    for handle in join_handles {
        match handle.join() {
            Ok(_) => (),
            Err(_) => error!("Unable to join thread, child thread panicked")
        }
    }

    info!("Main thread shutting down");
}


fn spawn_control(
    request_telemetry_tx: Sender<()>,
    telemetry_rx: Receiver<TelemetryState>,
    command_rx: Receiver<CommandMessage>,
    quit_rx: Receiver<()>,
) -> JoinHandle {
    thread::spawn(move || {
        let waypoint_generator = KmlWaypointGenerator::new(
            "../control/paths/solid-state-depot.kmz");
        let mut control = Control::new(
            request_telemetry_tx,
            telemetry_rx,
            &waypoint_generator);

        control.run(command_rx, quit_rx);
    })
}


fn spawn_telemetry_provider(
    telemetry_message_tx: Sender<TelemetryMessage>,
    quit_rx: Receiver<()>,
) -> JoinHandle {
    thread::spawn(move || {
        let mut provider = TelemetryProvider::new(telemetry_message_tx);
        provider.run(quit_rx);
    })
}


fn spawn_telemetry(
    request_telemetry_rx: Receiver<()>,
    telemetry_tx: Sender<TelemetryState>,
    telemetry_message_rx: Receiver<TelemetryMessage>,
    quit_rx: Receiver<()>,
) -> JoinHandle {
    thread::spawn(move || {
        let mut telemetry = FilteredTelemetry::new();
        telemetry.run(request_telemetry_rx, telemetry_tx, telemetry_message_rx, quit_rx);
    })
}
