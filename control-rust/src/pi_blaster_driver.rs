use std::fs::File;
use std::io::Write;

use driver::{Driver, Percentage};

/// Sends Errnocommands to the kernel PWM interface.
pub struct PiBlasterDriver {
    throttle: Percentage,
    steering: Percentage,
    max_throttle: Percentage,
    blaster: Box<Write>,
}

impl PiBlasterDriver {
    pub fn new() -> PiBlasterDriver {
        PiBlasterDriver::new_limit_throttle(1.0)
    }

    pub fn new_limit_throttle(max_throttle: Percentage) -> PiBlasterDriver {
        assert!(max_throttle > 0.0);
        let blaster = match File::create("/dev/pi-blaster") {
            Ok(file) => file,
            Err(err) => panic!("Unable to open Pi Blaster dev device /dev/pi-blaster"),
        };

        PiBlasterDriver {
            throttle: 0.0,
            steering: 0.0,
            max_throttle: max_throttle.min(1.0),
            blaster: Box::new(blaster),}
    }
}

impl Driver for PiBlasterDriver {
    fn drive(&mut self, throttle: Percentage, steering: Percentage) {
        let throttle_gpio_pin = 18;
        let steering_gpio_pin = 4;

        self.throttle = self.max_throttle.min(throttle);
        if throttle < 0.0 && throttle < -self.max_throttle {
            self.throttle = -self.max_throttle;
        }
        self.steering = steering;
        // Throttle
        let throttle_message = format!(
            "{}={}\n",
            throttle_gpio_pin,
            self.format_throttle(throttle),
        );
        match self.blaster.write(throttle_message.as_bytes()) {
            Ok(_) => (),
            Err(err) => error!("Unable to send drive command throttle: {}", err),
        }
        // Steering
        let steering_message = format!(
            "{}={}\n",
            steering_gpio_pin,
            self.format_steering(steering),
        );
        match self.blaster.write(steering_message.as_bytes()) {
            Ok(_) => (),
            Err(err) => error!("Unable to send drive command steering: {}", err),
        }
    }

    fn get_throttle(&self) -> Percentage {
        self.throttle
    }

    fn get_steering(&self) -> Percentage {
        self.steering
    }

}


impl PiBlasterDriver {
    fn format_throttle(&self, mut throttle: Percentage) -> f32 {
        let throttle_neutral_us = 1500f32;
        let throttle_diff = 500f32;
        if throttle > self.max_throttle {
            throttle = self.max_throttle;
        } else if throttle < -self.max_throttle {
            throttle = -self.max_throttle;
        }
        (throttle * throttle_diff + throttle_neutral_us) * 0.0001
    }

    fn format_steering(&self, mut steering: Percentage) -> f32 {
        let steering_neutral_us = 1650f32;
        let steering_diff = 300f32;
        // Turning sharply at high speeds causes the car to roll over, so limit it
        if self.throttle >= 0.5 {
            if steering > 0.5 {
                steering = 0.5;
            } else if steering < -0.5 {
                steering = -0.5;
            }
        }
        (steering * steering_diff + steering_neutral_us) * 0.0001
    }
}


#[cfg(test)]
mod tests {
    use num::traits::{Float, FromPrimitive};

    use driver::Driver;
    use super::PiBlasterDriver;

    macro_rules! assert_approx_eq {
        ( $value_1:expr, $value_2:expr) => {
            assert!(approx_eq($value_1, $value_2));
        }
    }
    fn approx_eq<T: Float + FromPrimitive>(value_1: T, value_2: T) -> bool {
        // Yeah, I know this is bad, see
        // http://randomascii.wordpress.com/2012/02/25/comparing-floating-point-numbers-2012-edition/

        let diff = (value_1 - value_2).abs();
        // This is the best we can do with f32
        diff < FromPrimitive::from_f32(0.00001f32).unwrap()
    }

    #[test]
    fn test_format_throttle() {
        // This will fail on everything but the Pi, so let's just ignore it if we're not running on
        // the Pi.
        if !cfg!(target_arch = "arm") {
            return;
        }
        // Low
        {
            let driver = PiBlasterDriver::new_limit_throttle(0.5);
            assert_approx_eq!(driver.format_throttle(2.0), 0.1750);
            assert_approx_eq!(driver.format_throttle(-2.0), 0.1250);
        }
        // High
        {
            let driver = PiBlasterDriver::new_limit_throttle(100.0);
            assert_approx_eq!(driver.format_throttle(2.0), 0.2000);
            assert_approx_eq!(driver.format_throttle(-2.0), 0.1000);
        }
        // Unspecified
        {
            let driver = PiBlasterDriver::new();
            assert_approx_eq!(driver.format_throttle(2.0), 0.2000);
            assert_approx_eq!(driver.format_throttle(-2.0), 0.1000);
        }
    }

    #[test]
    fn test_format_steering() {
        // This will fail on everything but the Pi, so let's just ignore it if we're not running on
        // the Pi.
        if !cfg!(target_arch = "arm") {
            return;
        }
        {
            let mut driver = PiBlasterDriver::new();
            driver.drive(0.0, 0.0);
            assert_approx_eq!(driver.format_steering(1.0), 0.1950);
            assert_approx_eq!(driver.format_steering(-1.0), 0.1350);
        }
        // High speed turns are limited
        {
            let mut driver = PiBlasterDriver::new();
            driver.drive(1.0, 0.0);
            assert_approx_eq!(driver.format_steering(1.0), 0.1800);
            assert_approx_eq!(driver.format_steering(-1.0), 0.1500);
        }
    }
}
