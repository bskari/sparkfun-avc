#!/usr/bin/env python
"""Dumps data from the GPS."""
import argparse
import serial

from control.sup800f import change_mode, get_message, parse_binary


def make_parser():
    """Builds and returns an argument parser."""
    parser = argparse.ArgumentParser(
        description='Dumps messages from the SUP800F module.'
    )

    parser.add_argument(
        '--gps',
        dest='gps',
        help='Print GPS messages.',
        action='store_true'
    )
    parser.add_argument(
        '--binary',
        dest='binary',
        help='Print binary messages.',
        action='store_true'
    )
    parser.add_argument(
        '--baud-rate',
        dest='baud_rate',
        help='Module baud rate.',
        type=int,
        default=115200
    )
    parser.add_argument(
        '--tty',
        dest='tty',
        help='TTY file.',
        type=str,
        default='/dev/ttyAMA0'
    )

    return parser


def main():
    """Main function."""
    parser = make_parser()
    args = parser.parse_args()

    ser = serial.Serial(args.tty, args.baud_rate)
    if args.gps or (args.gps is None and args.binary is None):
        change_mode(ser, 'nmea')
        while True:
            print(ser.readline())
    else:
        change_mode(ser, 'binary')

        format_string = '\n'.join((
            'acceleration X: {}',
            'acceleration Y: {}',
            'acceleration Z: {}',
            'magnetic X: {}',
            'magnetic Y: {}',
            'magnetic Z: {}',
            'pressure: {}',
            'temperature: {}',
        ))

        # The first message back should be an ack, ignore it
        get_message(ser)
        # The next message back is navigation data message, ignore it
        get_message(ser)

        while True:
            data = get_message(ser)
            if len(data) != 42:
                continue
            print(data)
            binary = parse_binary(data)._fields  # pylint: disable=protected-access
            print(format_string.format(*binary))  # pylint: disable=star-args


if __name__ == '__main__':
    main()
