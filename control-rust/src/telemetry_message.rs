use telemetry::{Degrees, Meters, MetersPerSecond, Point};

pub struct GpsMessage {
    pub point: Point,
    pub heading: Degrees,
    pub speed: MetersPerSecond,
    pub std_dev_x: Meters,
    pub std_dev_y: Meters,
}
pub struct CompassMessage {
    pub heading: Degrees,
    pub std_dev: Degrees,
}
pub enum CommandMessage {
    CalibrateCompass,
    Start,
    Stop,
}

#[allow(dead_code)]
pub enum TelemetryMessage {
    Gps(GpsMessage),
    Compass(CompassMessage),
}
