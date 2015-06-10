use telemetry::{Degrees, Meters, MetersPerSecond, Point, StandardGravities};


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
pub struct AccelerometerMessage {
    pub x: StandardGravities,
    pub y: StandardGravities,
    pub z: StandardGravities,
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
    Accelerometer(AccelerometerMessage),
}
