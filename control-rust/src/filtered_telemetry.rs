use logger::Logger;
use telemetry::Telemetry;
use telemetry_message::CompassMessage;
use telemetry_message::GpsMessage;
use telemetry_message::TelemetryMessage::Command;
use telemetry_message::TelemetryMessage::Compass;
use telemetry_message::TelemetryMessage::Gps;
use telemetry_message::TelemetryMessage;


#[allow(dead_code)]
struct FilteredTelemetry<'a> {
    logger: &'a (Logger + 'a),
    throttle: f32,
    steering: f32,
    gps_message: Box<GpsMessage>,
    compass_message: Box<CompassMessage>,
}


impl <'a> FilteredTelemetry<'a> {
    fn new(logger: &Logger) -> FilteredTelemetry {
        FilteredTelemetry {
            logger: logger,
            throttle: 0.0f32,
            steering: 0.0f32,
            gps_message: box GpsMessage {
                x_m: 0f32,
                y_m: 0f32,
                heading_d: 0f32,
                speed_m_s: 0f32,
                ms_since_midnight: 0i32,
            },
            compass_message: box CompassMessage {
                heading_d: 0f32,
                magnetometer: (0f32, 0f32, 0f32),
                ms_since_midnight: 0i32,
            }
        }
    }
}


impl <'a> Telemetry for FilteredTelemetry <'a> {
    fn get_raw_gps(&self) -> &GpsMessage {
        & *self.gps_message
    }

    fn get_raw_compass(&self) -> &CompassMessage {
        & *self.compass_message
    }

    fn get_data(&self) -> &GpsMessage {
        & *self.gps_message
    }

    fn process_drive_command(&mut self, throttle: f32, steering: f32) -> () {
        if throttle < -1.0 || throttle > 1.0 {
            self.logger.info("Invalid throttle");
            return;
        }
        if steering < -1.0 || steering > 1.0 {
            self.logger.warning("Invalid steering");
            return;
        }

        self.throttle = throttle;
        self.steering = steering;

        // TODO: Update the filter?
    }

    #[allow(unused_variables)]
    fn handle_message(&mut self, telemetry_message: &TelemetryMessage) -> () {
        match telemetry_message {
            &Gps(ref gps_message) => {
            },
            &Compass(ref compass_message) => {
            },
            &Command(ref command_message) => {
            },
        }
    }

    fn is_stopped(&self) -> bool {
        // TODO: Implement this
        false
    }
}
