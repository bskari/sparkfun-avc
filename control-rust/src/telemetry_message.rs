pub struct GpsMessage {
    pub x_m: f32,
    pub y_m: f32,
    pub heading_d: f32,
    pub speed_m_s: f32,
    pub ms_since_midnight: i32,
}
pub struct CompassMessage {
    pub heading_d: f32,
    pub magnetometer: (f32, f32, f32),
    pub ms_since_midnight: i32,
}
pub struct CommandMessage {
    pub command: String,
}

#[allow(dead_code)]
pub enum TelemetryMessage {
    Gps(GpsMessage),
    Compass(CompassMessage),
    Command(CommandMessage),
}
