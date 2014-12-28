"""Analyzes the speed and acceleration profile of the car."""
import argparse
import json
import socket
import serial


def make_parser():
    """Builds and returns an argument parser."""
    parser = argparse.ArgumentParser(
        description='Analyzes the speed and acceleration profile of the car.'
    )

    parser.add_argument(
        '-t',
        '--throttle',
        dest='throttle',
        help='The throttle to use.',
        default=1.0,
        type=float
    )

    parser.add_argument(
        '-p',
        '--port',
        dest='port',
        help='The port to send drive commands to.',
        default=12345,
        type=int
    )

    parser.add_argument(
        '-s',
        '--server',
        dest='server',
        help='The server to send drive commands to.',
        default='10.2',
        type=str
    )

    parser.add_argument(
        '-v',
        '--verbose',
        dest='verbose',
        help='Increase output.',
        action='store_true'
    )

    return parser


def measure(throttle_percentage, host, port, verbose=False):
    """Drives the car and measures the time until it trips a sensor."""
    serial_console = serial.Serial('/dev/tty.usbserial', 9600)
    socket_ = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    if verbose:
        print('Starting the car at throttle {}'.format(throttle_percentage))
    socket_.sendto(
        json.dumps({
            'throttle': throttle_percentage,
            'turn': 0.0
        }),
        (host, port)
    )

    serial_console.write(b'start\n')
    start_time = serial_console.readline()

    # Wait for the response
    if verbose:
        print('Waiting for the response from the Arduino')
    end_time = serial_console.readline()

    # Stop the car
    socket_.sendto(
        json.dumps({
            'throttle': 0.0,
            'turn': 0.0
        }),
        (host, port)
    )

    start_s = float(start_time)
    end_s = float(end_time)
    print('Total seconds: {}'.format(end_s - start_s))


def main():
    """Runs the speed and acceleration profiler."""
    parser = make_parser()
    args = parser.parse_args()

    measure(args.throttle, args.server, args.port, args.verbose)


if __name__ == '__main__':
    main()
