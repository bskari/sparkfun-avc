"""Main command module that starts the different threads."""
from ws4py.server.cherrypyserver import WebSocketPlugin
from ws4py.server.cherrypyserver import WebSocketTool
import argparse
import cherrypy
import datetime
import logging
import os
import serial
import signal
import subprocess
import sys
import threading
import time

from control.command import Command
from control.driver import Driver, STEERING_GPIO_PIN, STEERING_NEUTRAL_US, THROTTLE_GPIO_PIN, THROTTLE_NEUTRAL_US
from control.kml_waypoint_generator import KmlWaypointGenerator
from control.sup800f import switch_to_nmea_mode
from control.sup800f_telemetry import Sup800fTelemetry
from control.telemetry import Telemetry
from control.telemetry_dumper import TelemetryDumper
from control.web_telemetry.status_app import StatusApp as WebTelemetryStatusApp
from messaging import config
from messaging.async_logger import AsyncLogger, AsyncLoggerReceiver
from messaging.message_consumer import consume_messages
from messaging.message_producer import MessageProducer
from monitor.status_app import StatusApp as MonitorApp
from monitor.web_socket_logging_handler import WebSocketLoggingHandler

# pylint: disable=global-statement
# pylint: disable=broad-except

def override_imports_for_non_rpi():
    """Overrides modules that only work on the Raspberry Pi. Importing RPIO
    (used in button) on a non Raspberry Pi raises a SystemError, so for testing
    on other systems, just ignore it.
    """
    class Dummy(object):  # pylint: disable=missing-docstring,too-few-public-methods
        def __getattr__(self, attr):
            return lambda *arg, **kwarg: time.sleep(0.01)
    # pylint: disable=invalid-name
    global Button
    Button = lambda *arg: Dummy()
    serial.Serial = lambda *arg: Dummy()
    global Driver
    Driver = lambda *arg: Dummy()
    global Sup800fTelemetry
    Sup800fTelemetry = lambda *arg: Dummy()
    global switch_to_nmea_mode
    switch_to_nmea_mode = lambda *arg: Dummy()
    # Ignore messages
    drop = lambda message: None
    drop2 = lambda: consume_messages(config.COMMAND_FORWARDED_EXCHANGE, drop)
    thread = threading.Thread(target=drop2)
    thread.name = config.COMMAND_FORWARDED_EXCHANGE
    thread.start()

try:
    from control.button import Button
except SystemError:
    print('Disabling button because not running on Raspberry Pi')
    override_imports_for_non_rpi()

THREADS = []
POPEN = None
DRIVER = None
EMIT_INITIALIZED = False


class CherryPyServer(threading.Thread):
    """Runs the various web apps in a thread."""

    def __init__(self, port, address, telemetry):
        super(CherryPyServer, self).__init__()
        self.name = self.__class__.__name__

        # Web monitor
        config = MonitorApp.get_config(os.path.abspath(os.getcwd()))
        status_app = cherrypy.tree.mount(
            MonitorApp(telemetry, port),
            '/',
            config
        )
        cherrypy.config.update({
            'server.socket_host': address,
            'server.socket_port': port,
            'server.ssl_module': 'builtin',
            'server.ssl_certificate': 'control/web_telemetry/cert.pem',
            'server.ssl_private_key': 'control/web_telemetry/key.pem',
            'engine.autoreload.on': False,
        })

        WebSocketPlugin(cherrypy.engine).subscribe()
        cherrypy.tools.websocket = WebSocketTool()

        # Web telemetry
        config = WebTelemetryStatusApp.get_config(os.path.abspath(os.getcwd()))
        web_telemetry_app = cherrypy.tree.mount(
            WebTelemetryStatusApp(telemetry, port),
            '/telemetry',
            config
        )

        # OMG, shut up CherryPy, nobody cares about your problems
        for app in (status_app, web_telemetry_app, cherrypy):
            app.log.access_log.setLevel(logging.ERROR)
            app.log.error_log.setLevel(logging.ERROR)

    def run(self):
        """Runs the thread and server in a thread."""
        cherrypy.engine.start()

    @staticmethod
    def kill():
        """Stops the thread and server."""
        cherrypy.engine.exit()


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

    DRIVER.drive(0.0, 0.0)
    time.sleep(0.2)
    try:
        with open('/dev/pi-blaster', 'w') as blaster:
            time.sleep(0.1)
            blaster.write(
                '{pin}={throttle}\n'.format(
                    pin=THROTTLE_GPIO_PIN,
                    throttle=THROTTLE_NEUTRAL_US
                )
            )
            time.sleep(0.1)
            blaster.write(
                '{pin}={steering}\n'.format(
                    pin=STEERING_GPIO_PIN,
                    steering=STEERING_NEUTRAL_US
                )
            )
            time.sleep(0.1)
    except IOError:
        pass

    for socket in os.listdir(os.sep.join(('.', 'messaging', 'sockets'))):
        MessageProducer(socket).kill()
    time.sleep(0.1)

    for thread in THREADS:
        thread.kill()
        thread.join()
    # Some threads should still be active
    expected = set(('MainThread', '_TimeoutMonitor'))
    actives = set((thread.name for thread in threading.enumerate()))
    if not (actives <= expected):
        print('Trying to exit while {} threads are still active!'.format(
            threading.active_count()
        ))
        for thread in threading.enumerate():
            print(thread.name)
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
        max_throttle,
        kml_file_name,
):
    """Runs everything."""
    logger.info('Creating Telemetry')
    telemetry = Telemetry(kml_file_name)
    logger.info('Done creating Telemetry')
    global DRIVER
    DRIVER = Driver(telemetry)
    DRIVER.set_max_throttle(max_throttle)


    logger.info('Setting SUP800F to NMEA mode')
    serial_ = serial.Serial('/dev/ttyAMA0', 115200)
    serial_.setTimeout(1.0)
    for _ in range(10):
        serial_.readline()
    try:
        switch_to_nmea_mode(serial_)
    except:  # pylint: disable=W0702
        logger.error('Unable to set mode')
    for _ in range(10):
        serial_.readline()
    logger.info('Done')

    button = Button()

    port = int(get_configuration('PORT', 8080))
    address = get_configuration('ADDRESS', '0.0.0.0')

    # The following objects must be created in order, because of message
    # exchange dependencies
    # TODO(2016-08-21) Have something better than sleeps to work around race
    # conditions
    logger.info('Creating threads')
    sup800f_telemetry = Sup800fTelemetry(serial_)
    time.sleep(0.5)
    command = Command(telemetry, DRIVER, waypoint_generator)
    time.sleep(0.5)
    telemetry_dumper = TelemetryDumper(
        telemetry,
        waypoint_generator,
        web_socket_handler
    )
    time.sleep(0.5)
    cherry_py_server = CherryPyServer(port, address, telemetry)

    global THREADS
    THREADS += (
        button,
        cherry_py_server,
        command,
        sup800f_telemetry,
        telemetry_dumper,
    )
    for thread in THREADS:
        thread.start()
    logger.info('Started all threads')

    # Use a fake timeout so that the main thread can still receive signals
    sup800f_telemetry.join(100000000000)
    # Once we get here, sup800f_telemetry has died and there's no point in
    # continuing because we're not receiving telemetry messages any more, so
    # stop the command module
    command.stop()
    command.join(100000000000)
    cherry_py_server.kill()
    cherry_py_server.join(100000000000)
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
            '/data/sparkfun-{date}.log'.format(
                date=datetime.datetime.strftime(
                    now,
                    '%Y-%m-%d_%H-%M-%S'
                )
            )
        ),
        type=str
    )

    parser.add_argument(
        '--video',
        dest='video',
        help='The video file name.',
        default=(
            '/data/video-{date}.h264'.format(
                date=datetime.datetime.strftime(
                    now,
                    '%Y-%m-%d_%H-%M-%S'
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
        POPEN = subprocess.Popen((
            'raspivid', '-o', args.video, '-w', '1024', '-h', '576', '-b', '6000000', '-t', '300000'
        ))
    except Exception:
        logging.warning('Unable to save video')

    concrete_logger = logging.Logger('sparkfun')
    concrete_logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s:%(levelname)s %(message)s'
    )

    file_handler = None
    try:
        file_handler = logging.FileHandler(args.log)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        concrete_logger.addHandler(file_handler)
    except Exception as exception:
        logging.warning('Could not create file log: ' + str(exception))

    stdout_handler = logging.StreamHandler(sys.stdout)
    if args.verbose:
        stdout_handler.setLevel(logging.DEBUG)
    else:
        stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(formatter)
    concrete_logger.addHandler(stdout_handler)

    async_logger = AsyncLoggerReceiver(concrete_logger)
    # We need to start async_logger now so that other people can log to it
    async_logger.start()
    time.sleep(0.1)
    THREADS.append(async_logger)

    web_socket_handler = WebSocketLoggingHandler()
    web_socket_handler.setLevel(logging.INFO)
    web_socket_handler.setFormatter(formatter)
    concrete_logger.addHandler(web_socket_handler)

    logger = AsyncLogger()

    if sys.version_info.major < 3:
        logger.warn(
            'Python 2 is not officially supported, use at your own risk'
        )

    kml_file = args.kml_file
    if kml_file is None:
        logger.info(
            'Setting waypoints to Solid State Depot for testing'
        )
        kml_file = 'paths/solid-state-depot.kml'
    waypoint_generator = KmlWaypointGenerator(kml_file)

    logger.debug('Calling start_threads')

    start_threads(
        waypoint_generator,
        logger,
        web_socket_handler,
        args.max_throttle,
        kml_file,
    )


if __name__ == '__main__':
    main()
