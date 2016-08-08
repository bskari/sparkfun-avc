"""Starts the Python parts for the Rust control."""
import argparse
import os
import pwd
import signal
import socket
import subprocess
import sys
import threading
import time

from control.button import Button
from control.driver import Driver
from control.test.dummy_logger import DummyLogger
from control.test.dummy_telemetry import DummyTelemetry
from monitor.http_server import HttpServer

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


class DriverListener(threading.Thread):
    """Receives commands on a socket from the controlling program to drive."""

    def __init__(self, socket_file_name):
        super(DriverListener, self).__init__()
        self.name = self.__class__.__name__

        self._socket_file_name = socket_file_name
        self._run = True
        self._connected = False
        self._connection = None

        dummy_logger = DummyLogger()
        dummy_telemetry = DummyTelemetry(dummy_logger, (100, 100))
        self._driver = Driver(dummy_telemetry, dummy_logger)

    def run(self):
        """Runs in a thread. Waits for clients to connects then receives and
        handles drive messages.
        """
        try:
            print('DriverListener waiting for commands')
            while self._run:
                try:
                    self.run_socket()
                except Exception as exc:
                    print('Error in DriverListener: {}'.format(exc))
                    return
        except Exception as exc:
            print('DriverListener failed with exception {}'.format(exc))

    def run_socket(self):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                os.unlink(self._socket_file_name)
            except Exception:
                pass
            sock.bind(self._socket_file_name)
            pi = pwd.getpwnam('pi')
            os.chown(self._socket_file_name, pi.pw_uid, pi.pw_gid)
            sock.listen(1)
            sock.settimeout(1)
            try:
                self.wait_for_connections(sock)
            except socket.timeout:
                return
            except socket.error as exc:
                print('DriverListener error with socket: {}'.format(exc))
                if exc.errno == 32:  # Broken pipe
                    print('DriverListener closing socket')
                    sock.shutdown(socket.SHUT_RDWR)
                    sock.close()
                    return
                elif exc.errno == 98:  # Address already in use
                    print('DriverListener quitting waiting for connections')
                    return
                else:
                    print('Unknown error')
                    return

    def wait_for_connections(self, sock):
        while self._run:
            self._connection, _ = sock.accept()
            self._connected = True
            print('DriverListener client connected')
            # Now we're connected, so just wait until someone
            # calls handle_message
            while self._run:
                try:
                    command = self._connection.recv(4096)
                    throttle, steering = [float(i) for i in command.split(' ')]
                    print('DriverListener driving {} {}'.format(throttle, steering))
                    self._driver.drive(throttle, steering)
                except socket.timeout:
                    continue

    def kill(self):
        """Stops the thread."""
        self._run = False


class CommandForwarder(threading.Thread):
    """Forwards commands to clients connected to a socket."""
    VALID_COMMANDS = {'calibrate-compass', 'line-up', 'start', 'stop'}

    def __init__(self, socket_file_name):
        super(CommandForwarder, self).__init__()

        self._socket_file_name = socket_file_name
        self._run = True
        self._connected = False
        self._connection = None

    def run(self):
        """Runs in a thread. Waits for clients to connects then forwards
        command messages to them.
        """
        try:
            while self._run:
                try:
                    self.run_socket()
                except Exception as exc:
                    print('Error in CommandForwarder: {}'.format(exc))
                    return
        except Exception as exc:
            print('CommandForwarder failed with exception {}'.format(exc))

    def run_socket(self):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                os.unlink(self._socket_file_name)
            except Exception:
                pass
            sock.bind(self._socket_file_name)
            pi = pwd.getpwnam('pi')
            os.chown(self._socket_file_name, pi.pw_uid, pi.pw_gid)
            sock.listen(1)
            sock.settimeout(1)
            try:
                self.wait_for_connections(sock)
            except socket.error as exc:
                print('CommandForwarder error with socket: {}'.format(exc))
                self._connected = False
                if exc.errno == 32:  # Broken pipe
                    print('CommandForwarder closing socket')
                    sock.shutdown(socket.SHUT_RDWR)
                    sock.close()
                    return
                elif exc.errno == 98:  # Address already in use
                    print('CommandForwarder quitting waiting for connections')
                    return
                else:
                    return

    def wait_for_connections(self, sock):
        while self._run:
            try:
                self._connection, _ = sock.accept()
                self._connected = True
                print('CommandForwarder command client connected')
                # Now we're connected, so just wait until someone
                # calls handle_message
                while self._run:
                    time.sleep(1)
                    # Test to see if we're still connected
                    # TODO: If nobody's connected, this causes the program to
                    # quit. Goes directly to quit, does not throw an exception,
                    # does not collect $200.
                    self._connection.send(b'')
                return
            except socket.timeout:
                continue

    def kill(self):
        """Stops the thread."""
        self._run = False

    def handle_message(self, message):
        """Forwards command messages, e.g. 'start' or 'stop'."""
        if not self._connected:
            print('CommandForwarder received message "{}" but nobody is connected', message)
            return
        if 'command' not in message:
            print('CommandForwarder no command in command message')
            return

        if message['command'] not in self.VALID_COMMANDS:
            print(
                'CommandForwarder unknown command: "{command}"'.format(
                    command=message['command']
                )
            )
            return

        try:
            if message['command'] == 'line-up':
                # TODO: Right now, line-up just means start recording the camera
                pass
            else:
                self._connection.sendall(message['command'].encode('utf-8'))

            if message['command'] == 'stop':
                # TODO: We also want to stop the camera when someone clicks stop
                pass

        except Exception as exc:
            print(
                'Unable to forward command "{}": {}'.format(
                    message['command'],
                    exc
                )
            )


class StdinReader(threading.Thread):
    """Sends commands read from stdin."""
    def __init__(self, command):
        super(StdinReader, self).__init__()
        self._command = command
        self._run = True

    def run(self):
        try:
            print('StdinReader waiting for commands')
            while self._run:
                command = sys.stdin.readline()
                if command == '':
                    continue
                else:
                    self._command.handle_message({'command': command})
        except Exception as exc:
            print('StdinReader failed with exception {}'.format(exc))

    def kill(self):
        """Stops the thread."""
        self._run = False


def start_threads(stdin, control_socket, driver_socket):
    """Runs everything."""
    dummy_logger = DummyLogger()
    forwarder = CommandForwarder(control_socket)
    button = Button(forwarder, dummy_logger)
    dummy_telemetry = DummyTelemetry(dummy_logger, (50.0, 50.0))
    http_server = HttpServer(
        forwarder,
        dummy_telemetry,
        dummy_logger,
        port=8080,
        address='0.0.0.0'
    )

    driver = DriverListener(driver_socket)

    global THREADS
    THREADS = [forwarder, button, driver, http_server]
    if stdin:
        reader = StdinReader(forwarder)
        THREADS.append(reader)

    for thread in THREADS:
        thread.start()
    print('Started all threads')

    # Once forwarder quits, we can kill everything else
    forwarder.join()
    print('Forwarder thread exited, killing all threads')
    for thread in THREADS:
        thread.kill()
        thread.join()


def make_parser():
    """Builds and returns an argument parser."""
    parser = argparse.ArgumentParser(
        description='Command and control software for the Sparkfun AVC.'
    )

    parser.add_argument(
        '--control-socket',
        dest='control_socket',
        help='The Unix domain socket to send control commands on.',
        default='/tmp/command-socket',
        type=str,
    )

    parser.add_argument(
        '--driver-socket',
        dest='driver_socket',
        help='The Unix domain socket to listen for drive commands on.',
        default='/tmp/driver-socket',
        type=str,
    )

    parser.add_argument(
        '-i',
        '--stdin',
        dest='stdin',
        help='Read control commands from stdin as well as from other sources.',
        action='store_true'
    )

    parser.add_argument(
        '-w',
        '--watchdog',
        dest='watchdog',
        help='Run in a watchdog form with restart.',
        action='store_true'
    )

    return parser


def main():
    """Sets up logging, signal handling, etc. and starts the threads."""
    signal.signal(signal.SIGINT, terminate)

    parser = make_parser()
    args = parser.parse_args()

    # I was getting an error where calling connection.send on a closed socket
    # was immediately exiting the program. So, use a watchdog and fork a
    # subprocess to restart instead.
    if args.watchdog:
        raw_args = ['python'] + [
            arg for arg in sys.argv
            if arg != '-w' and arg != '--watchdog'
        ]

        for _ in range(10):
            print('Forking subprocess for watchdog')
            process = subprocess.Popen(raw_args)
            exit_code = process.wait()
            print('Child process exited with code {}'.format(exit_code))
        return

    # TODO: Use the Raspberry Pi camera module Python module to save video

    print('Calling start_threads')
    start_threads(args.stdin, args.control_socket, args.driver_socket)
    print('Done calling start_threads')


if __name__ == '__main__':
    main()
