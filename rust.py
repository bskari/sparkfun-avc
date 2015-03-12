"""Starts the Python parts for the Rust control."""
import argparse
import os
import pwd
import signal
import socket
import sys
import threading
import time

from control.button import Button
from control.test.dummy_logger import DummyLogger

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


class CommandForwarder(threading.Thread):
    """Forwards commands to clients connected to a socket."""
    VALID_COMMANDS = {'start', 'stop'}

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
        while self._run:
            try:
                self.run_socket()
            except Exception as exc:
                print('Error in CommandForwarder: {}'.format(exc))
                return

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
                print('Error with socket: {}'.format(exc))
                if exc.errno == 32:  # Broken pipe
                    print('Closing socket')
                    sock.shutdown(socket.SHUT_RDWR)
                    sock.close()
                    return
                elif exc.errno == 98:  # Address already in use
                    print('Quitting waiting for connections')
                    return
                else:
                    return

    def wait_for_connections(self, sock):
        while self._run:
            try:
                self._connection, _ = sock.accept()
                print('Client connected')
                # Now we're connected, so just wait until someone
                # calls handle_message
                while self._run:
                    time.sleep(1)
                    # Test to see if we're still connected
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
            print('Received message "{}" but nobody is connected', message)
            return
        if 'command' not in message:
            print('No command in command message')
            return

        if message['command'] not in self.VALID_COMMANDS:
            print(
                'Unknown command: "{command}"'.format(
                    command=message['command']
                )
            )
            return

        try:
            self._connection.sendall(message['command'].encode('utf-8'))
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
        print('Waiting for commands')
        while self._run:
            command = sys.stdin.readline()
            if command == '':
                continue
            else:
                self._command.handle_message({'command': command})

    def kill(self):
        """Stops the thread."""
        self._run = False


def start_threads(stdin):
    """Runs everything."""
    dummy_logger = DummyLogger()
    forwarder = CommandForwarder('/tmp/command-socket')
    button = Button(forwarder, dummy_logger)

    global THREADS
    THREADS = [forwarder, button]
    if stdin:
        reader = StdinReader(forwarder)
        THREADS.append(reader)

    for thread in THREADS:
        thread.start()
    print('Started all threads')

    # Once forwarder quits, we can kill everything else
    forwarder.join()
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
        '-i',
        '--stdin',
        dest='stdin',
        help='Read control commands from stdin as well as from other sources.',
        action='store_true'
    )

    return parser


def main():
    """Sets up logging, signal handling, etc. and starts the threads."""
    signal.signal(signal.SIGINT, terminate)

    parser = make_parser()
    args = parser.parse_args()

    # TODO: Use the Raspberry Pi camera module Python module to save video

    print('Calling start_threads')

    start_threads(stdin=args.stdin)


if __name__ == '__main__':
    main()
