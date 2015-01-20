use std::f32;

use logger::Logger;
use telemetry::Telemetry;
use telemetry_message::TelemetryMessage;


struct FilteredTelemetry<'a> {
    data: &'a mut TelemetryMessage,
    logger: Box<Logger + 'a>,

    throttle: f32,
    steering: f32,
}


impl<'a> Telemetry for FilteredTelemetry<'a> {
    fn get_raw_data(&self) -> &TelemetryMessage {
        self.data
    }

    fn get_data(&self) -> &TelemetryMessage {
        self.data
    }

    fn process_drive_command(&mut self, throttle:f32, steering:f32) -> () {
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

    fn handle_message(&self, message:&TelemetryMessage) -> () {
        // TODO: Save the message
    }

    fn is_stopped(&self) -> bool {
        // TODO: Implement this
        false
    }
}
