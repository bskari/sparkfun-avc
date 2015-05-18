pub type Percentage = f32;
/// Provides an interface to drive the car.
pub trait Driver {
    fn drive(&mut self, throttle: Percentage, steering: Percentage);
    fn get_throttle(&self) -> Percentage;
    fn get_steering(&self) -> Percentage;
}
