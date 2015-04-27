"""Main command module that starts the different threads."""
import argparse
import datetime
import logging
import os
import serial
import signal
import subprocess
import sys

from control.button import Button
from control.command import Command
from control.kml_waypoint_generator import KmlWaypointGenerator
from control.telemetry import Telemetry
from control.telemetry_dumper import TelemetryDumper
from control.driver import Driver
from control.telemetry_data import TelemetryData
from monitor.http_server import HttpServer
from monitor.web_socket_logging_handler import WebSocketLoggingHandler

# pylint: disable=global-statement
# pylint: disable=broad-except


THREADS = []
POPEN = None


def terminate(signal_number, stack_frame):  # pylint: disable=unused-argument
    """Terminates the program. Used when a signal is received."""
    print(
        'Received signal {signal_number}, quitting'.format(
            signal_number=signal_number
        )
    )
    if POPEN is not None and POPEN.poll() is None:
        print('Killing image capture')
        try:
            POPEN.kill()
        except OSError:
            pass

    for thread in THREADS:
        thread.kill()
        thread.join()
    sys.exit(0)


def get_configuration(value, default):
    """Returns a system configuration value."""
    if value in os.environ:
        return os.environ[value]
    return default


def start_threads(
        waypoint_generator,
        logger,
        web_socket_handler,
        max_throttle
):
    """Runs everything."""
    # TODO: Get latitude longitude central coordinate from the GPS
    telemetry = Telemetry(logger)  # Sparkfun HQ
    driver = Driver(telemetry, logger)
    driver.set_max_throttle(max_throttle)

    command = Command(telemetry, driver, waypoint_generator, logger)
    serial_ = serial.Serial('/dev/ttyAMA0', 115200)
    telemetry_data = TelemetryData(telemetry, serial_, logger)
    first_waypoint = waypoint_generator.get_current_waypoint(0.0, 0.0)
    telemetry_data._x_m = first_waypoint[0] - 100.0
    telemetry_data._y_m = first_waypoint[1] - 100.0
    monitor_port = int(get_configuration('MONITOR_PORT', 8080))
    monitor_address = get_configuration('MONITOR_ADDRESS', '0.0.0.0')
    http_server = HttpServer(
        command,
        telemetry,
        telemetry_data,
        logger,
        port=monitor_port,
        address=monitor_address
    )
    button = Button(command, logger)
    telemetry_dumper = TelemetryDumper(
        telemetry,
        waypoint_generator,
        web_socket_handler
    )

    global THREADS
    THREADS = [command, telemetry_data, http_server, button, telemetry_dumper]
    for thread in THREADS:
        thread.start()
    logger.info('Started all threads')

    # Use a fake timeout so that the main thread can still receive signals
    telemetry_data.join(100000000000)
    # Once we get here, telemetry_data has died and there's no point in
    # continuing because we're not receiving telemetry messages any more, so
    # stop the command module
    command.stop()
    command.join(100000000000)
    http_server.kill()
    http_server.join(100000000000)
    button.kill()
    button.join(100000000000)


def make_parser():
    """Builds and returns an argument parser."""
    parser = argparse.ArgumentParser(
        description='Command and control software for the Sparkfun AVC.'
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

    parser.add_argument(
        '--max-throttle',
        dest='max_throttle',
        help='The max throttle to drive at.',
        default=1.0,
        type=float,
    )

    return parser


def main():
    """Sets up logging, signal handling, etc. and starts the threads."""
    signal.signal(signal.SIGINT, terminate)

    parser = make_parser()
    args = parser.parse_args()

    try:
        global POPEN
        POPEN = subprocess.Popen(
            'raspivid -o /media/USB/video/run.h264 -w 1024 -h 576 -b 6000000'
        )
    except Exception:
        logging.warning('Unable to save video')

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

    web_socket_handler = WebSocketLoggingHandler()
    web_socket_handler.setLevel(logging.INFO)
    web_socket_handler.setFormatter(formatter)
    logger.addHandler(web_socket_handler)

    if sys.version_info.major < 3:
        logger.warn(
            'Python 2 is not officially supported, use at your own risk'
        )

    waypoint_generator = None
    if args.kml_file is not None:
        waypoint_generator = KmlWaypointGenerator(logger, args.kml_file)
    else:
        logger.info('Setting waypoints to Solid State Depot for testing')
        waypoint_generator = KmlWaypointGenerator(
            logger,
            'paths/solid-state-depot.kmz'
        )

    logger.debug('Calling start_threads')

    start_threads(
        waypoint_generator,
        logger,
        web_socket_handler,
        args.max_throttle,
    )


if __name__ == '__main__':
    main()
