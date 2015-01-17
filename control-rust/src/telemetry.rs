use telemetry_message::TelemetryMessage;

/**
 * Provides Telemetry data, possibly filtered to be more accurate.
 */
pub trait Telemetry {
    fn get_raw_data(&self) -> &TelemetryMessage;
    fn get_data(&self) -> &TelemetryMessage;
    fn process_drive_command(&mut self, throttle:f32, steering:f32) -> ();
    fn handle_message(&self, message:&TelemetryMessage) -> ();
    fn is_stopped(&self) -> bool;
}
