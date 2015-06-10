use telemetry::{Degrees, Gravities, Meter, MetersPerSecond, Point};


pub struct GpsMessage {
    pub point: Point,
    pub heading: Degrees,
    pub speed: MetersPerSecond,
    pub std_dev_x: Meter,
    pub std_dev_y: Meter,
}
pub struct CompassMessage {
    pub heading: Degrees,
    pub std_dev: Degrees,
}
pub struct AccelerometerMessage {
    pub x: Gravities,
    pub y: Gravities,
    pub z: Gravities,
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
