"""Threaded class for receiving messages. Because there are several different
kinds of messages that can be received (e.g. telemetry and command), this
single class receives them and then sends them to the appropriate class for
processing.
"""
import json
import socket
import threading
import time

# pylint: disable=superfluous-parens


class MessageRouter(threading.Thread):
    """Receives and routes UDP messages."""
    def __init__(self, sock, type_to_handler, logger):
        super(MessageRouter, self).__init__()
        self._socket = sock
        self._run = True
        self._type_to_handler = type_to_handler
        self._logger = logger

    def run(self):
        """Run in a thread, routes messages to the appropriate handlers."""
        while self._run:
            try:
                message, address = self._socket.recvfrom(4096)
            except socket.timeout:
                # This is normal and expected; the timeout is set so that this
                # thread can be stopped gracefully
                continue
            except IOError as socket_error:
                # If the socket is closed, just exit gracefully
                try:
                    self._socket.fileno()
                except IOError:
                    return

                self._logger.warning('Socket error: {error}'.format(error=str(socket_error)))
                continue

            try:
                message = json.loads(message)
            except ValueError:
                self._logger.warning(
                    'Unable to parse message: {message}'.format(
                        message=message
                    )
                )
                continue

            if 'requestResponse' in message:
                self._logger.info(
                    '{time}: {message}'.format(
                        time=time.time(),
                        message=message,
                    )
                )
                self._socket.sendto(
                    json.dumps({
                        'messageReceived': time.time(),
                    }),
                    (address[0], 5001)
                )

            if 'type' not in message:
                # Only asking for a response is a valid message
                if 'requestResponse' in message and len(message) == 1:
                    continue
                else:
                    self._logger.warning(
                        'Type missing from message: {message}'.format(
                            message=message
                        )
                    )
                    continue

            if 'timestamp' not in message:
                # This might not be accurate at all (the sender might have sent
                # the data 5s ago and we're just processing it now) but I guess
                # it's better than nothing
                message['timestamp'] = time.time()

            if message['type'] not in self._type_to_handler:
                self._logger.warning(
                    'Unknown or missing handler for message type "{t}"'.format(
                        t=message['type']
                    )
                )
            else:
                self._type_to_handler[message['type']].handle_message(message)

    def kill(self):
        """Kills the thread."""
        self._run = False
