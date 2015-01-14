"""Manual remote control for the Grasshopper Tamiya."""
import json
import signal
import socket
import sys

from control.driver import Driver
from control.test.dummy_logger import DummyLogger
from control.test.dummy_telemetry import DummyTelemetry

driver = None


def signal_handler(signal_number, frame):
    # Don't exit on resizing the terminal
    if signal_number == signal.SIGWINCH:
        return
    # Anything else, quit
    global driver
    driver.drive(0.0, 0.0)
    sys.exit(0)


def main():
    """Main function."""
    signal.signal(signal.SIGWINCH, signal_handler)

    # First, shut the damn car up
    throttle_percentage = 0.0
    # And reset the steering
    steering_percentage = 0.0

    logger = DummyLogger()
    telemetry = DummyTelemetry(logger, (40.0182663, -105.2761267))
    global driver
    driver = Driver(telemetry, logger)

    socket_ = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_.bind(('', 12345))
    socket_.settimeout(2)

    try:
        data = None
        while True:
            print(
                'Throttle: {}, steering: {}'.format(
                    throttle_percentage,
                    steering_percentage
                )
            )


            try:
                data, address = socket_.recvfrom(1024)  # pylint: disable=unused-variable
                command = json.loads(data.decode())
            except ValueError as value_error:
                print('Unable to parse JSON {}: {}'.format(data, value_error))
                continue
            except:
                print('Timed out')
                throttle_percentage = 0.0
                steering_percentage = 0.0
                command = {}

            if 'quit' in command:
                break
            if 'throttle' in command:
                throttle_percentage = float(command['throttle'])
            if 'steering' in command:
                steering_percentage = float(command['steering'])
            driver.drive(throttle_percentage, steering_percentage)
    except Exception as exc:  # pylint: disable=broad-except
        print('Exception: {}'.format(exc))
    finally:
        driver.drive(0.0, 0.0)


if __name__ == '__main__':
    for i in range(10):
        main()
