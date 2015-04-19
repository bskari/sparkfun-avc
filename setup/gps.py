"""Configures the GPS module."""
import argparse
import functools
import serial
import struct


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


def make_parser():
    """Builds and returns an argument parser."""
    parser = argparse.ArgumentParser(
        description='Configures the SUP800F GPS module.'
    )

    parser.add_argument(
        '--baud-rate',
        dest='baud_rate',
        help='Set the baud rate to transmit data.',
        default=None,
    )

    # Message intervals
    parser.add_argument(
        '--gga',
        dest='gga',
        help='The interval rate for GGA messages',
        default=None,
        type=int,
    )
    parser.add_argument(
        '--gsa',
        dest='gsa',
        help='The interval rate for GSA messages',
        default=None,
        type=int,
    )
    parser.add_argument(
        '--gsv',
        dest='gsv',
        help='The interval rate for GSV messages',
        default=None,
        type=int,
    )
    parser.add_argument(
        '--gll',
        dest='gll',
        help='The interval rate for GLL messages',
        default=None,
        type=int,
    )
    parser.add_argument(
        '--rmc',
        dest='rmc',
        help='The interval rate for RMC messages',
        default=None,
        type=int,
    )
    parser.add_argument(
        '--vtg',
        dest='vtg',
        help='The interval rate for VTG messages',
        default=None,
        type=int,
    )
    parser.add_argument(
        '--zda',
        dest='zda',
        help='The interval rate for ZDA messages',
        default=None,
        type=int,
    )

    parser.add_argument(
        '--binary',
        dest='binary',
        help='The interval rate for binary messages',
        default=None,
        type=int,
    )

    parser.add_argument(
        '--update-rate',
        dest='update_rate',
        help='The Hertz rate for all messages',
        default=None,
        type=int,
    )

    parser.add_argument(
        '--reset',
        dest='reset',
        help='Reset to factory defaults.',
        action='store_true'
    )

    parser.add_argument(
        '--test',
        dest='test',
        help='Save configuration to RAM, but not Flash.',
        action='store_true'
    )

    parser.add_argument(
        '--tty',
        dest='tty',
        help='TTY file.',
        type=str,
        default='/dev/ttyAMA0'
    )
    parser.add_argument(
        '--current-baud-rate',
        dest='current_baud_rate',
        help='The current baud rate to talk with the module.',
        default=115200,
    )

    return parser


def set_baud_rate(ser, baud_rate, test):
    """Set the baud rate."""
    baud_rate_to_value = {
        4800: 0,
        9600: 1,
        19200: 2,
        38400: 3,
        57600: 4,
        115200: 5,
        230400: 6,
        460800: 7,
        921600: 8,
    }
    value = baud_rate_to_value[baud_rate]
    raise NotImplementedError()


def set_nmea_intervals(ser, args, test):
    """Set message intervals."""
    interval_format = ''.join((
        '!',  # network format (big-endian)
        'B',  # message id, 8 = set NMEA intervals
        'B',  # GGA interval
        'B',  # GSA interval
        'B',  # GSV interval
        'B',  # GLL interval
        'B',  # RMC interval
        'B',  # VTG interval
        'B',  # ZDA interval
        'B',  # save to Flash, 0 = no, 1 = yes
    ))
    ser.write(
        format_message(
            struct.pack(
                interval_format,
                8,
                args.gga,
                args.gsa,
                args.gsv,
                args.gll,
                args.rmc,
                args.vtg,
                args.zda,
                0 if test else 1
            )
        )
    )


def set_binary_interval(ser, interval, test):
    """Set binary message interval."""
    interval_format = ''.join((
        '!',  # network format (big-endian)
        'B',  # message id, 11 = set binary intervals
        'B',  # binary interval
        'B',  # save to Flash, 0 = no, 1 = yes
    ))
    ser.write(
        format_message(
            struct.pack(
                interval_format,
                11,
                interval,
                0 if test else 1
            )
        )
    )
    ser.flush()


def set_update_rate(ser, rate, test):
    """Sets the message rate."""
    if rate not in (1, 2, 4, 5, 8, 10, 20, 25, 40, 50):
        raise ValueError('Invalid update rate')

    update_format = ''.join((
        '!',  # network format (big-endian)
        'B',  # message id, 0x0E = set update rate
        'B',  # rate
        'B',  # save to Flash, 0 = no, 1 = yes
    ))
    ser.write(
        format_message(
            struct.pack(
                update_format,
                0x0E,
                rate,
                0 if test else 1
            )
        )
    )
    ser.flush()



def reset(ser):
    """Reset to factory defaults."""
    reset_format = ''.join((
        '!',  # network format (big-endian)
        'B',  # message id, 4 = reset
        'B',  # type, 0 = reserved, 1 = reboot after resetting to default
    ))
    ser.write(format_message(struct.pack(reset_format, 4, 1)))


def check_response(ser):
    """Checks for an ack/nack response."""
    response_format = ''.join((
        '!',  # network format (big-endian)
        'xx', # The message will have 2 header bytes
        'H',  # payload length
        'B',  # message id
        'B',  # ack id
        'xxx', # and 3 checksum bytes
    ))
    print('Waiting for ack or nack')
    while True:
        data = get_message(ser)
        try:
            length, message_id, ack_id = struct.unpack(response_format, data)
        except Exception as exc:  # pylint: ignore=broad-except
            print(exc)
            continue
        if message_id not in (83, 84):
            continue
        if message_id == 83:
            print('Ack')
        else:
            print('Nack')


def main():
    """Configures the GPS module."""
    parser = make_parser()
    args = parser.parse_args()

    ser = serial.Serial(args.tty, args.current_baud_rate)

    if args.baud_rate is not None:
        if args.baud_rate not in BAUD_RATE_TO_VALUE:
            print('Invalid baud rate: {}'.format(args.baud_rate))
        else:
            set_baud_rate(args.baud_rate)
            check_response(ser)

    required_intervals = ('gga', 'gsa', 'gsv', 'gll', 'rmc', 'vtg', 'zda')
    kwargs = dict(args._get_kwargs())
    interval_changed = any((
        kwargs[key] is not None for key in required_intervals
    ))
    if interval_changed:
        any_not_set = any((
            kwargs[key] is None for key in required_intervals
        ))
        if any_not_set:
            print('You must set values for all {}'.format(required_intervals))
            example = ' '.join(('--{} 1'.format(k)) for k in required_intervals)
            print('Example: {}'.format(example))
        else:
            set_nmea_intervals(ser, args, args.test)
            check_response(ser)

    if args.update_rate:
        set_update_rate(ser, args.update_rate, args.test)
        check_response(ser)

    if args.reset:
        reset(ser)
        check_response(ser)

    if args.binary:
        set_binary_interval(ser, args.binary, args.test)
        check_response(ser)


if __name__ == '__main__':
    main()
