"""Main command module that starts the different threads."""
import argparse
import datetime
import logging
import signal
import subprocess
import sys

from command import Command
from kml_waypoint_generator import KmlWaypointGenerator
from monitor.http_server import HttpServer
from telemetry import Telemetry
from test.dummy_driver import DummyDriver
from test.dummy_telemetry_data import DummyTelemetryData

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


def start_threads(
        waypoint_generator,
        logger
):
    """Runs everything."""
    telemetry = Telemetry(logger)
    driver = DummyDriver(telemetry, logger)

    command = Command(telemetry, driver, waypoint_generator, logger)
    telemetry_data = DummyTelemetryData(telemetry, logger)
    http_server = HttpServer(command, telemetry, logger)

    global THREADS
    THREADS = [command, telemetry_data, http_server]
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
        logger
    )


if __name__ == '__main__':
    main()
