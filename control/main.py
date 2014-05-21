import signal
import socket
import sys

from command import Command
from message_router import MessageRouter
from telemetry import Telemetry


THREADS = []


def terminate(signal_number, stack_frame):
    print(
        'Received signal {signal_number}, quitting'.format(
            signal_number=signal_number
        )
    )
    for thread in THREADS:
        thread.stop()
        thread.join()
    sys.exit(0)


def main(listen_interface, listen_port, connect_host, connect_port):
    #signal.signal(signal.SIGINT, terminate)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((listen_interface, listen_port))
        sock.settimeout(1)
    except IOError as ioe:
        print('Unable to listen on port: {ioe}'.format(ioe=ioe))
        sys.exit(1)

    class DgramSocketWrapper(object):
        def __init__(self, host, port):
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._host = host
            self._port = port
        
        def send(message):
            self._socket.sendto((host, port), message)

    telemetry = Telemetry()
    dgram_socket_wrapper = DgramSocketWrapper(connect_host, connect_port)
    command = Command(telemetry, dgram_socket_wrapper, dgram_socket_wrapper)

    message_type_to_service = {
        'command': command,
        'telemetry': telemetry,
    }

    message_router = MessageRouter(sock, message_type_to_service)

    message_router.start()
    command.start()
    global THREADS
    THREADS = [message_router, command]

    # Use a fake timeout so that the main thread can still receive signals
    message_router.join(100000000000)
    # Once we get here, message_router has died and there's no point in
    # continuing because we're not receiving telemetry messages any more, so
    # close the socket and stop the command module
    sock.close()
    command.stop()
    command.join(100000000000)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, terminate)
    main('0.0.0.0', 8384, '127.1', 12345)
