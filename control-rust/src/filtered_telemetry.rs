extern crate log;
use std::old_io::timer;
use std::sync::mpsc::{Receiver, Sender};
use std::time::duration::Duration;

use telemetry::{Telemetry, Point, TelemetryState};
use telemetry_message::{CompassMessage, GpsMessage, TelemetryMessage};


#[allow(dead_code)]
pub struct FilteredTelemetry {
    throttle: f32,
    steering: f32,
    gps_message: Box<GpsMessage>,
    compass_message: Box<CompassMessage>,
    state: TelemetryState,
}


impl FilteredTelemetry {
    pub fn new() -> FilteredTelemetry {
        FilteredTelemetry {
            throttle: 0.0,
            steering: 0.0,
            gps_message: box GpsMessage {
                point: Point {x: 0.0, y: 0.0 },
                heading: 0.0,
                speed: 0.0,
                std_dev_x: 2.0,
                std_dev_y: 2.0,
            },
            compass_message: box CompassMessage { heading: 0.0, std_dev: 0.0 },
            state: TelemetryState {
                location: Point { x: 0.0, y: 0.0 },
                heading: 0.0,
                speed: 0.0,
                stopped: true},
        }
    }

    pub fn run(
        &mut self,
        request_telemetry_rx: Receiver<()>,
        telemetry_tx: Sender<TelemetryState>,
        telemetry_message_rx: Receiver<TelemetryMessage>,
        quit_rx: Receiver<()>
    ) {
        loop {
            match quit_rx.try_recv() {
                Ok(_) => {
                    info!("Telemetry shutting down");
                    return;
                },
                Err(_) => (),
            }

            let mut processed = false;

            while let Ok(_) = request_telemetry_rx.try_recv() {
                match telemetry_tx.send(self.state) {
                    Ok(_) => (),
                    Err(e) => {
                        error!("Unable to send telemetry: {}", e);
                        return;
                    }
                }
                processed = true;
            }

            while let Ok(message) = telemetry_message_rx.try_recv() {
                // TODO: Process the message
                processed = true;
            };

            // I don't know if this is a great solution or not
            if !processed {
                timer::sleep(Duration::milliseconds(10));
            }
        }
    }
}


impl Telemetry for FilteredTelemetry {
    fn get_raw_gps(&self) -> &GpsMessage {
        & *self.gps_message
    }

    fn get_raw_compass(&self) -> &CompassMessage {
        & *self.compass_message
    }

    fn get_data(&self) -> &TelemetryState {
        // TODO
        &self.state
    }

    fn process_drive_command(&mut self, throttle: f32, steering: f32) -> () {
        if throttle < -1.0 || throttle > 1.0 {
            info!("Invalid throttle");
            return;
        }
        if steering < -1.0 || steering > 1.0 {
            warn!("Invalid steering");
            return;
        }

        self.throttle = throttle;
        self.steering = steering;

        // TODO: Update the filter?
    }

    #[allow(unused_variables)]
    fn handle_message(&mut self, telemetry_message: &TelemetryMessage) -> () {
        match telemetry_message {
            &TelemetryMessage::Gps(ref gps_message) => {
            },
            &TelemetryMessage::Compass(ref compass_message) => {
            },
        }
    }

    fn is_stopped(&self) -> bool {
        // TODO: Implement this
        false
    }
}
