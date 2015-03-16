// Silence warnings about use of unstable features
#![feature(box_syntax)]
#![feature(core)]
#![feature(env)]
#![feature(fs)]
#![feature(io)]
#![feature(libc)]
#![feature(old_io)]
#![feature(old_path)]
#![feature(std_misc)]
#[macro_use]

extern crate log;
extern crate getopts; // This needs to be declared after log, otherwise you get compilation errors
extern crate time;
use getopts::Options;
use log::{set_logger, LogLevel, LogLevelFilter, LogRecord};
use std::env;
use std::old_io::IoErrorKind;
use std::old_io::net::pipe::UnixStream;
use std::old_io::timer::sleep;
use std::sync::mpsc::{channel, Sender, Receiver};
use std::str::from_utf8;
use std::thread::{JoinHandle, spawn};
use std::time::duration::Duration;
use time::{now, strftime};

use control::Control;
use driver::Percentage;
use filtered_telemetry::FilteredTelemetry;
use kml_waypoint_generator::KmlWaypointGenerator;
use socket_driver::SocketDriver;
use telemetry::TelemetryState;
use telemetry_message::{CommandMessage, TelemetryMessage};
use telemetry_provider::TelemetryProvider;

mod control;
mod driver;
mod filtered_telemetry;
mod kml_waypoint_generator;
mod location_filter;
mod nmea;
mod socket_driver;
mod telemetry;
mod telemetry_message;
mod telemetry_provider;
mod termios;
mod waypoint_generator;

struct StdoutLogger {
    level: LogLevel,
}
impl log::Log for StdoutLogger {
    fn enabled(&self, level: LogLevel, _module: &str) -> bool {
        level <= self.level
    }

    fn log(&self, record: &LogRecord) {
        if self.enabled(record.level(), record.location().module_path) {
            let now_tm = now();
            let time_str = match strftime("%Y/%m/%d %H:%M:%S.", &now_tm) {
                Ok(s) => s,
                Err(_) => "UNKNOWN".to_string()  // This should never happen
            } + &format!("{}", now_tm.tm_nsec)[0..3];
            let location = record.location();
            let file_name = match location.file.split('/').last() {
                Some(slashes) => {
                    match slashes.split('.').next() {
                        Some(name) => name,
                        None => "UNKNOWN",
                    }
                },
                None => "UNKNOWN",
            };
            println!(
                "{time} {file}:{line} {level:<5} {message}",
                time=time_str,
                file=file_name,
                line=location.line,
                level=record.level(),
                message=record.args());
        }
    }
}


fn main() {
    if !handle_opts() {
        return;
    }
    info!("Starting up");

    let mut quitters = Vec::new();

    let (request_telemetry_tx, request_telemetry_rx) = channel();
    let (telemetry_tx, telemetry_rx) = channel();
    let (command_tx, command_rx) = channel();
    let (quit_command_tx, quit_command_rx) = channel();
    quitters.push(quit_command_tx);

    // TODO: Send quit when Ctrl + C is pressed
    let mut join_handles = Vec::new();
    join_handles.push(
        spawn_control(
            request_telemetry_tx,
            telemetry_rx,
            command_rx,
            quit_command_rx));

    let (telemetry_message_tx, telemetry_message_rx) = channel();
    let (quit_termio_tx, quit_termio_rx) = channel();
    quitters.push(quit_termio_tx);
    join_handles.push(spawn_telemetry_provider(telemetry_message_tx, quit_termio_rx));

    let (quit_telemetry_tx, quit_telemetry_rx) = channel();

    join_handles.push(
        spawn_telemetry(
            request_telemetry_rx,
            telemetry_tx,
            telemetry_message_rx,
            quit_telemetry_rx));
    quitters.push(quit_telemetry_tx);

    let (quit_command_message_tx, quit_command_message_rx) = channel();
    quitters.push(quit_command_message_tx);
    join_handles.push(
        spawn_command_message_listener(
            command_tx,
            quit_command_message_rx));

    sleep(Duration::milliseconds(1000));

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
    spawn(move || {
        let waypoint_generator = Box::new(KmlWaypointGenerator::new(
            "../control/paths/solid-state-depot.kmz"));
        let driver = Box::new(SocketDriver::new());
        let mut control = Control::new(
            request_telemetry_tx,
            telemetry_rx,
            waypoint_generator,
            driver);

        control.run(command_rx, quit_rx);
    })
}


fn spawn_telemetry_provider(
    telemetry_message_tx: Sender<TelemetryMessage>,
    quit_rx: Receiver<()>,
) -> JoinHandle {
    spawn(move || {
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
    spawn(move || {
        let mut telemetry = FilteredTelemetry::new();
        telemetry.run(request_telemetry_rx, telemetry_tx, telemetry_message_rx, quit_rx);
    })
}


fn spawn_command_message_listener(
    command_tx: Sender<CommandMessage>,
    quit_rx: Receiver<()>,
) -> JoinHandle {
    spawn(move || {
        // Keep listening for start and stop messages on a Unix socket
        let server = Path::new("/tmp/command-socket");
        let mut socket = match UnixStream::connect(&server) {
            Ok(socket) => socket,
            Err(e) => {
                error!("Unable to open Unix socket: {}", e);
                return;
            }
        };

        socket.set_timeout(Some(1000u64));
        let mut message_bytes = Vec::<u8>::new();
        loop {
            let mut processing_required = false;
            loop {
                match socket.read_u8() {
                    Ok(byte) => {
                        if byte == '\n' as u8 {
                            processing_required = true;
                            break;
                        } else {
                            message_bytes.push(byte);
                        }
                    },
                    Err(e) => {
                        match e.kind {
                            IoErrorKind::TimedOut => break,
                            _ => {
                                error!("Error reading from domain socket: {}", e);
                                return;
                            }
                        }
                    }
                }
            }
            if processing_required {
                match from_utf8(message_bytes.as_slice()) {
                    Ok(message) => {
                        if message == "start" {
                            // TODO Send start command message
                            info!("Received message \"{}\" on Unix socket", message);
                        } else if message == "stop" {
                            // TODO Send stop command message
                            info!("Received message \"{}\" on Unix socket", message);
                        } else {
                            warn!("Unknown message \"{}\" on Unix socket", message);
                        }
                    },
                    Err(_) => error!("Unable to interpret bytes from Unix socket as UTF8"),
                }
                message_bytes.clear();
            }

            match quit_rx.try_recv() {
                Ok(_) => {
                    info!("Command message thread shutting down");
                    return;
                },
                Err(_) => (),
            }
        }
    })
}


fn handle_opts() -> bool {
    let mut opts = Options::new();
    opts.optflag("v", "verbose", "Prints extra logging.");
    opts.optflag("h", "help", "Print this help menu.");
    let mut args = std::env::args();
    args.next();  // Skip the program name
    let matches = match opts.parse(args) {
        Ok(m) => m,
        Err(e) => panic!("Unable to parse options: {}", e),
    };
    if matches.opt_present("h") {
        print_usage(opts);
        return false;
    }

    let level = if matches.opt_present("v") {
            LogLevel::Debug
        } else {
            LogLevel::Info
        };

    let status = set_logger(|max_log_level| {
        max_log_level.set(LogLevelFilter::Debug);
        Box::new(StdoutLogger { level: level })
    });
    match status {
        Ok(_) => (),
        Err(e) => panic!("Unable to initialize logger: {}", e)
    };
    true
}


fn print_usage(opts: Options) {
    let brief = "Usage: control-rust [options]";
    print!("{}", opts.usage(&brief));
}
