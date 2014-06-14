"""Main command module that starts the different threads."""
import argparse
import datetime
import json
import logging
import signal
import socket
import sys

from command import Command
from message_router import MessageRouter
from telemetry import Telemetry

# pylint: disable=superfluous-parens
# pylint: disable=global-statement


THREADS = []
SOCKET = None


def terminate(signal_number, stack_frame):
    """Terminates the program. Used when a signal is received."""
    print(
        'Received signal {signal_number}, quitting'.format(
            signal_number=signal_number
        )
    )
    if SOCKET is not None:
        SOCKET.close()
    for thread in THREADS:
        thread.kill()
        thread.join()
    sys.exit(0)


def main(listen_interface, listen_port, connect_host, connect_port, logger):
    """Runs everything."""
    global SOCKET
    try:
        SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        SOCKET.bind((listen_interface, listen_port))
        SOCKET.settimeout(1)
    except IOError as ioe:
        logger.critical('Unable to listen on port: {ioe}'.format(ioe=ioe))
        sys.exit(1)

    class DgramSocketWrapper(object):
        """Simple wrapper around a socket so that modules don't need to worry
        about host, port, timeouts, or other details.
        """
        def __init__(self, host, port):
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._host = host
            self._port = port

        def send(self, message, request_response=None):
            """Sends a message through the socket."""
            if request_response is None:
                request_response = False
            if isinstance(message, list):
                if request_response and 'requestResponse' not in message:
                    message['requestResponse'] = True
                message_str = json.dumps(message)
            else:
                # If somebody's already converted to a string, then
                # request_response won't do anything
                assert not request_response, 'Already converted to string in main'
                message_str = message

            if sys.version_info.major >= 3 and isinstance(message_str, str):
                message_str = bytes(message_str, 'utf-8')
            self._socket.sendto(message_str, (self._host, self._port))

    telemetry = Telemetry(logger)
    dgram_socket_wrapper = DgramSocketWrapper(connect_host, connect_port)
    command = Command(telemetry, dgram_socket_wrapper, dgram_socket_wrapper, logger)

    message_type_to_service = {
        'command': command,
        'telemetry': telemetry,
    }

    message_router = MessageRouter(SOCKET, message_type_to_service, logger)

    message_router.start()
    command.start()
    logger.info('Started all threads')
    global THREADS
    THREADS = [message_router, command]

    # Use a fake timeout so that the main thread can still receive signals
    message_router.join(100000000000)
    # Once we get here, message_router has died and there's no point in
    # continuing because we're not receiving telemetry messages any more, so
    # close the socket and stop the command module
    SOCKET.close()
    command.stop()
    command.join(100000000000)


def make_parser():
    """Builds and returns an argument parser."""
    parser = argparse.ArgumentParser(
        description='Command and control software for the Sparkfun AVC.'
    )

    parser.add_argument(
        '-p',
        '--listen-port',
        dest='listen_port',
        help='The port to lisetn for messages on.',
        default=8384,
        type=int
    )

    parser.add_argument(
        '-c',
        '--command-port',
        dest='command_port',
        help='The port to send drive commands to.',
        default=12345,
        type=int
    )
    parser.add_argument(
        '-s',
        '--command-server',
        dest='server',
        help='The server to send drive commands to.',
        default='127.1',
        type=str
    )

    now = datetime.datetime.now()
    parser.add_argument(
        '-l',
        '--log',
        dest='log',
        help='The file to log to.',
        default=(
            '/media/USB/sparkfun-{date}.log'.format(
                date=datetime.datetime.strftime(
                    now,
                    '%Y-%m-%d-%H-%M'
                )
            )
        ),
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


if __name__ == '__main__':
    parser = make_parser()
    args = parser.parse_args()

    signal.signal(signal.SIGINT, terminate)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s:%(levelname)s %(message)s'
    )

    file_handler = None
    try:
        file_handler = logging.FileHandler(args.log)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
    except Exception as e:
        logging.warning('Could not create file log: ' + str(e))
        logger.setLevel(logging.INFO)
        pass

    stdout_handler = logging.StreamHandler(sys.stdout)
    if args.verbose:
        stdout_handler.setLevel(logging.DEBUG)
    else:
        stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    logger.debug('Calling main')

    main('0.0.0.0', args.listen_port, args.server, args.command_port, logger)
