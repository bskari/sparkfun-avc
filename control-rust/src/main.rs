#[macro_use]
extern crate log; // This needs to be declared first, otherwise you get compilation errors
extern crate chrono;
#[macro_use]
extern crate enum_primitive;
extern crate getopts;
extern crate num;
extern crate simplelog;

use getopts::{Matches, Options};
use simplelog::{CombinedLogger, Config, LevelFilter, TermLogger, WriteLogger};
use std::error::Error;
use std::fs::File;
use std::io::Read;
use std::os::unix::net::UnixStream;
use std::path::Path;
use std::str::from_utf8;
use std::sync::mpsc::{channel, Receiver, Sender};
use std::thread::{sleep, spawn, JoinHandle};
use std::time::Duration;

use control::Control;
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

macro_rules! warn_err {
    ($option:expr) => {
        match $option {
            Ok(s) => s,
            Err(e) => warn!("{}", e.description().to_string()),
        };
    };
}

fn main() {
    let options = match handle_opts() {
        Some(options) => options,
        None => panic!("Unable to parse options"),
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
    let path_file_name = match options.opt_str("p") {
        Some(value) => value,
        None => "../paths/solid-state-depot.kmz".to_string(),
    };
    let max_throttle: f32 = match options.opt_str("max-throttle") {
        Some(value) => match value.parse() {
            Ok(throttle_value) => throttle_value,
            Err(_) => panic!("Invalid throttle, should be between 0.25 and 1.0"),
        },
        None => 1.0,
    };

    join_handles.push(spawn_control(
        &path_file_name,
        max_throttle,
        request_telemetry_tx,
        telemetry_rx,
        command_rx,
        quit_command_rx,
    ));

    let (telemetry_message_tx, telemetry_message_rx) = channel();
    let (quit_termio_tx, quit_termio_rx) = channel();
    quitters.push(quit_termio_tx);
    join_handles.push(spawn_telemetry_provider(
        telemetry_message_tx,
        quit_termio_rx,
    ));

    let (quit_telemetry_tx, quit_telemetry_rx) = channel();

    join_handles.push(spawn_telemetry(
        request_telemetry_rx,
        telemetry_tx,
        telemetry_message_rx,
        quit_telemetry_rx,
    ));
    quitters.push(quit_telemetry_tx);

    let (quit_command_message_tx, quit_command_message_rx) = channel();
    quitters.push(quit_command_message_tx);
    join_handles.push(spawn_command_message_listener(
        command_tx,
        quit_command_message_rx,
    ));

    sleep(Duration::from_millis(1000));

    for quitter in quitters {
        warn_err!(quitter.send(()));
    }

    for handle in join_handles {
        match handle.join() {
            Ok(_) => (),
            Err(_) => error!("Unable to join thread, child thread panicked"),
        }
    }

    info!("Main thread shutting down");
}

fn spawn_control(
    path_file_name: &str,
    max_throttle: f32,
    request_telemetry_tx: Sender<()>,
    telemetry_rx: Receiver<TelemetryState>,
    command_rx: Receiver<CommandMessage>,
    quit_rx: Receiver<()>,
) -> JoinHandle<()> {
    let waypoint_generator = Box::new(KmlWaypointGenerator::new(&path_file_name));
    spawn(move || {
        let driver = Box::new(SocketDriver::new(max_throttle));
        let mut control = Control::new(
            request_telemetry_tx,
            telemetry_rx,
            waypoint_generator,
            driver,
        );

        control.run(command_rx, quit_rx);
    })
}

fn spawn_telemetry_provider(
    telemetry_message_tx: Sender<TelemetryMessage>,
    quit_rx: Receiver<()>,
) -> JoinHandle<()> {
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
) -> JoinHandle<()> {
    spawn(move || {
        let mut telemetry = FilteredTelemetry::new();
        telemetry.run(
            request_telemetry_rx,
            telemetry_tx,
            telemetry_message_rx,
            quit_rx,
        );
    })
}

fn spawn_command_message_listener(
    command_tx: Sender<CommandMessage>,
    quit_rx: Receiver<()>,
) -> JoinHandle<()> {
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

        match socket.set_read_timeout(Some(Duration::from_millis(1000u64))) {
            Ok(()) => (),
            Err(err) => error!("Unable to set read timeout: {}", err),
        }
        let mut message_bytes = Vec::<u8>::new();
        loop {
            let mut buffer: [u8; 20] = [0; 20];
            loop {
                match socket.read(&mut buffer) {
                    Ok(size) => if size > 0 {
                        for index in 0..size {
                            message_bytes.push(buffer[index])
                        }
                        if message_bytes[message_bytes.len() - 1] == '\n' as u8 {
                            break;
                        }
                    },
                    Err(e) => {
                        error!("Error reading from domain socket: {}", e);
                    }
                }
            }
            match from_utf8(&message_bytes) {
                Ok(message) => {
                    info!("Received message \"{}\" on Unix socket", message);
                    if message == "start" {
                        warn_err!(command_tx.send(CommandMessage::Start));
                    } else if message == "stop" {
                        warn_err!(command_tx.send(CommandMessage::Stop));
                    } else if message == "calibrate-compass" {
                        warn_err!(command_tx.send(CommandMessage::CalibrateCompass));
                    } else {
                        warn!("Unknown message \"{}\" on Unix socket", message);
                    }
                }
                Err(_) => error!("Unable to interpret bytes from Unix socket as UTF8"),
            }
            message_bytes.clear();

            match quit_rx.try_recv() {
                Ok(_) => {
                    info!("Command message thread shutting down");
                    return;
                }
                Err(_) => (),
            }
        }
    })
}

fn handle_opts() -> Option<Matches> {
    let mut opts = Options::new();
    opts.optflag("v", "verbose", "Prints extra logging.");
    opts.optflag("h", "help", "Print this help menu.");
    opts.optopt("p", "path", "Filename for KML path to drive.", "FILE");
    opts.optopt(
        "",
        "max-throttle",
        "Maximum throttle to drive at (defaults to 1.0)",
        "THROTTLE",
    );
    let mut args = std::env::args();
    args.next(); // Skip the program name
    let matches = match opts.parse(args) {
        Ok(m) => m,
        Err(e) => panic!("Unable to parse options: {}", e),
    };
    if matches.opt_present("h") {
        print_usage(opts);
        return None;
    }

    let level = if matches.opt_present("v") {
        LevelFilter::Debug
    } else {
        LevelFilter::Info
    };
    let log_file_name = chrono::Utc::now()
        .format("log/%Y-%m-%d-%H-%M-sparkfun.log")
        .to_string();
    match File::create(&log_file_name) {
        Ok(file) => {
            CombinedLogger::init(vec![
                TermLogger::new(LevelFilter::Warn, Config::default()).unwrap(),
                WriteLogger::new(level, Config::default(), file),
            ]).unwrap();
        }
        Err(_) => {
            CombinedLogger::init(vec![
                TermLogger::new(LevelFilter::Warn, Config::default()).unwrap(),
            ]).unwrap();
            error!("Unable to open log file");
        }
    }

    match matches.opt_str("max-throttle") {
        Some(throttle_str) => {
            let throttle: f32 = match throttle_str.parse() {
                Ok(value) => value,
                Err(_) => panic!("Invalid throttle, should be between 0.25 and 1.0"),
            };
            if throttle < 0.25 || throttle > 1.0 {
                panic!("Invalid throttle, should be between 0.25 and 1.0");
            }
        }
        None => (),
    };
    Some(matches)
}

fn print_usage(opts: Options) {
    let brief = "Usage: control-rust [options]";
    print!("{}", opts.usage(&brief));
}
