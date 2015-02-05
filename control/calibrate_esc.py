"""Programs the ESC."""
from control import driver as driver_module
from control.driver import Driver
from control.test.dummy_logger import DummyLogger
from control.test.dummy_telemetry import DummyTelemetry


def main():
    """Main function."""
    # First, shut the damn car up
    throttle_percentage = 0.0
    # And reset the steering
    steering_percentage = 0.0

    logger = DummyLogger()
    telemetry = DummyTelemetry(logger, (40.0182663, -105.2761267))
    driver = Driver(telemetry, logger)

    # driver limits the reverse throttle to 25% to prevent motor damage
    driver._get_throttle = lambda percentage: \
        int(
            driver_module.THROTTLE_NEUTRAL_US
            + driver_module.THROTTLE_DIFF
            * percentage
        ) // 10 * 10

    driver.drive(0.0, 0.0)
    input('''
Disconnect the motor cables. While holding down the setup button on the ESC,
switch on the power. The LED should start changing colors from red -> green ->
orange. Red is for calibrating the throttle high and low points for forward and
reverse. Press setup when the LED is red; the LED will start to single flash
red.

Press enter to continue.
''')

    driver.drive(1.0, 0.25)
    input('''
Press the set button. The LED should start to double flash red

Press enter to continue.
''')

    driver.drive(-1.0, -0.25)
    input('''
Press the set button. The LED should turn off. That's it!

Press enter to exit.
''')

    driver.drive(0.0, 0.0)

if __name__ == '__main__':
    main()
