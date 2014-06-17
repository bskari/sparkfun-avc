"""Main command module that starts the different threads."""
from xml.etree import ElementTree
import argparse
import datetime
import json
import logging
import signal
import socket
import sys
import zipfile

from command import Command
from message_router import MessageRouter
from telemetry import Telemetry

# pylint: disable=superfluous-parens
# pylint: disable=global-statement
# pylint: disable=broad-except


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


def load_waypoints(kml_string):
    """Loads and returns the waypoints from a KML path file."""

    def get_child(element, tag_name):
        """Returns the child element with the given tag name."""
        for child in element:
            if tag_name in child.tag:
                return child
        raise ValueError('No {tag} element found'.format(tag=tag_name))

    root = ElementTree.fromstring(kml_string)
    if 'kml' not in root.tag:
        raise ValueError('Not a KML file')

    document = get_child(root, 'Document')
    placemark = get_child(document, 'Placemark')
    line_string = get_child(placemark, 'LineString')
    # Unlike all of the other tag names, "coordinates" is not capitalized
    coordinates = get_child(line_string, 'coordinates')

    waypoints = []
    text = coordinates.text.strip()
    for csv in text.split(' '):
        longitude, latitude, altitude = csv.split(',')
        waypoints.append((float(latitude), float(longitude)))
    return waypoints


def start_threads(
    listen_interface,
    listen_port,
    connect_host,
    connect_port,
    waypoints,
    logger
):
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
                assert not request_response, 'Already string in start threads'
                message_str = message

            if sys.version_info.major >= 3 and isinstance(message_str, str):
                message_str = bytes(message_str, 'utf-8')
            self._socket.sendto(message_str, (self._host, self._port))

    telemetry = Telemetry(logger)
    dgram_socket_wrapper = DgramSocketWrapper(connect_host, connect_port)
    command = Command(
        telemetry,
        dgram_socket_wrapper,
        logger,
        waypoints=waypoints
    )

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

    parser.add_argument(
        '-k',
        '--kml',
        dest='kml_file',
        help='The KML file from which to load waypoints.',
        default=None,
        type=str,
    )

    return parser


def main():
    """Sets up logging, signal handling, etc. and starts the threads."""
    signal.signal(signal.SIGINT, terminate)

    parser = make_parser()
    args = parser.parse_args()

    logger = logging.Logger('sparkfun')
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
    except Exception as exception:
        logging.warning('Could not create file log: ' + str(exception))

    stdout_handler = logging.StreamHandler(sys.stdout)
    if args.verbose:
        stdout_handler.setLevel(logging.DEBUG)
    else:
        stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    waypoints = None
    if args.kml_file is not None:
        try:
            with zipfile.ZipFile(args.kml_file) as archive:
                kml_string = archive.open('doc.kml').read()
                waypoints = load_waypoints(kml_string)
                logger.info(
                    'Loaded {length} waypoints'.format(
                        length=len(waypoints)
                    )
                )
        except Exception as exception:
            logger.error(
                'Unable to load kml file: {exception}'.format(
                    exception=str(exception)
                )
            )

    logger.debug('Calling start_threads')

    start_threads(
        '0.0.0.0',
        args.listen_port,
        args.server,
        args.command_port,
        waypoints,
        logger
    )


if __name__ == '__main__':
    main()
