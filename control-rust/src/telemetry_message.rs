pub struct TelemetryMessage {
    latitude: Option<f32>,
    longitude: Option<f32>,
    heading: Option<f32>,
    bearing: Option<f32>,
    time_stamp: Option<f32>,
    speed: Option<f32>,
    magnetometer: Option<(f32, f32, f32)>,
}
