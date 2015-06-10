extern crate log;
use std::sync::mpsc::{Receiver, Sender};
use std::thread;

use location_filter::LocationFilter;
use telemetry::{Telemetry, Point, TelemetryState};
use telemetry_message::{AccelerometerMessage, CompassMessage, GpsMessage, TelemetryMessage};


#[allow(dead_code)]
pub struct FilteredTelemetry {
    throttle: f32,
    steering: f32,
    accelerometer_message: Box<AccelerometerMessage>,
    gps_message: Box<GpsMessage>,
    compass_message: Box<CompassMessage>,
    state: TelemetryState,
    filter: LocationFilter,
}


impl FilteredTelemetry {
    pub fn new() -> FilteredTelemetry {
        FilteredTelemetry {
            throttle: 0.0,
            steering: 0.0,
            gps_message: Box::new(GpsMessage {
                point: Point {x: 0.0, y: 0.0 },
                heading: 0.0,
                speed: 0.0,
                std_dev_x: 2.0,
                std_dev_y: 2.0,
            }),
            compass_message: Box::new(CompassMessage { heading: 0.0, std_dev: 0.0 }),
            accelerometer_message: Box::new(AccelerometerMessage { x: 0.0, y: 0.0, z: 0.0 }),
            state: TelemetryState {
                location: Point { x: 0.0, y: 0.0 },
                heading: 0.0,
                speed: 0.0,
                stopped: false},
            // TODO: Fill in the starting values of the Sparkfun AVC. These placeholders aren't a
            // huge deal because the filter should zero in quickly after a few readings.
            filter: LocationFilter::new(50.0, 50.0, 315.0),
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
                thread::sleep_ms(10);
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

    fn get_data(&mut self) -> &TelemetryState {
        let time_diff = self.filter.update_observation_time();
        self.filter.prediction_step(time_diff);

        self.state.location = self.filter.estimated_location();
        self.state.heading = self.filter.estimated_heading();
        self.state.speed = self.filter.estimated_speed();
        self.state.stopped = false;
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

        let max_turn_rate_d_s = 90.0f32;  // Estimated from observation
        self.filter.estimated_turn_rate_d_s = max_turn_rate_d_s * steering;
    }

    fn handle_message(&mut self, telemetry_message: &TelemetryMessage) -> () {
        match telemetry_message {
            // TODO
            &TelemetryMessage::Gps(ref gps_message) => {
                self.filter.update_gps(
                    gps_message.point.x,
                    gps_message.std_dev_x,
                    gps_message.point.y,
                    gps_message.std_dev_y,
                    gps_message.heading,
                    gps_message.speed);
            },
            &TelemetryMessage::Compass(ref compass_message) => {
            },
            &TelemetryMessage::Accelerometer(ref accelerometer_message) => {
            },
        }
    }

    fn is_stopped(&self) -> bool {
        self.state.stopped
    }
}
