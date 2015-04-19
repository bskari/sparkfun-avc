#!/usr/bin/env python
"""Dumps data from the GPS."""
import argparse
import functools
import serial
import struct
import sys


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


def format_message(payload):
    """Formats a message for the SUP800F."""
    header_format = ''.join((
        '!',  # network format (big-endian)
        'BB',  # start of sequence, A0 A1
        'H',  # payload length
    ))
    tail_format = ''.join((
        '!',  # network format (big-endian)
        'B',  # checksum
        'BB',  # end of sequence, 0D 0A
    ))
    checksum = functools.reduce(lambda a, b: a ^ b, payload, 0)
    return (
        struct.pack(header_format, 0xA0, 0xA1, len(payload))
        + payload
        + struct.pack(tail_format, checksum, 0x0D, 0x0A)
    )


def get_message(ser):
    """Returns a single message."""
    # Keep consuming bytes until we see the header message
    while True:
        part = ser.read(1)
        if part != b'\xA0':
            continue
        part = ser.read(1)
        if part != b'\xA1':
            continue
        part = ser.read(2)
        payload_length = struct.unpack('!H', part)[0]
        rest = ser.read(payload_length + 3)
        if rest[-2:] != b'\r\n':
            print(r"Message didn't end in \r\n")
        return b'\xA0\xA1' + struct.pack('!H', payload_length) + rest


def main():
    """Main function."""
    parser = make_parser()
    args = parser.parse_args()

    type_format = ''.join((
        '!',  # network format (big-endian)
        'B',  # message id, 9 = configure message type
        'B',  # none = 0, NMEA = 1, binary = 2
        'B',  # 0 = SRAM, 1 = SRAM and Flash
    ))

    ser = serial.Serial(args.tty, args.baud_rate)
    if args.gps or (args.gps is None and args.binary is None):
        gps_message = struct.pack(type_format, 9, 1, 0)
        ser.write(format_message(gps_message))
        while True:
            print(ser.readline())
    else:
        binary_message = struct.pack(type_format, 9, 2, 0)
        ser.write(format_message(binary_message))
        ser.flush()

        # I'm not sure why, but the module is returning an extra byte for some
        # reason. It's even reporting the payload as one byte too long, so just
        # cut an extra byte off.
        binary_format = ''.join((
            '!',  # network format (big-endian)
            'xxxx', # The message will have 4 header bytes
            'B',  # message id
            'B',  # message sub id
            'x',  # see above comment
            'f',  # acceleration X
            'f',  # acceleration Y
            'f',  # acceleration Z
            'f',  # magnetic X
            'f',  # magnetic Y
            'f',  # magnetic Z
            'I',  # pressure
            'f',  # temperature
            'xxx', # and 3 checksum bytes
        ))

        format_string = '\n'.join((
            'message id: {}',
            'message sub id: {}',
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
            print(format_string.format(*struct.unpack(binary_format, data)))


if __name__ == '__main__':
    main()
