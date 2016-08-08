"""Message broker that receives from Unix domain sockets."""

import os
import socket


def consume_messages(message_type, callback):
    """Starts consuming messages."""
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    socket_folder = os.sep.join(('.', 'messaging', 'sockets'))
    socket_address = socket_folder + os.sep + message_type
    if os.path.exists(socket_address):
        os.remove(socket_address)

    try:
        os.mkdir(socket_folder)
    except OSError:
        pass

    try:
        sock.bind(socket_address)
    except socket.error as err:
        print(err)
        return

    while True:
        datagram = sock.recv(4096)
        if not datagram:
            break
        if datagram == b'QUIT':
            break
        message = datagram.decode('utf-8')
        callback(message)

    sock.close()
    os.remove(socket_address)
