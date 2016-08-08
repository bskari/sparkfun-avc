"""Message broker that sends to Unix domain sockets."""

import os
import socket


class MessageProducer(object):
    """Message broker that sends to Unix domain sockets."""

    def __init__(self, message_type):
        self._message_type = message_type
        socket_address = os.sep.join(
            ('.', 'messaging', 'sockets', message_type)
        )

        if not os.path.exists(socket_address):
            raise ValueError('Socket does not exist: {}'.format(socket_address))

        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self._socket.connect(socket_address)

    def publish(self, message):
        """Publishes a message."""
        self._socket.send(message.encode('utf-8'))

    def kill(self):
        """Kills all listening consumers."""
        try:
            self._socket.send(b'QUIT')
        except ConnectionRefusedError:  # pylint: disable=undefined-variable
            pass
