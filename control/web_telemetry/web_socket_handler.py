"""Websocket handler for sending messages to clients."""

from ws4py.websocket import WebSocket


class WebSocketHandler(WebSocket):  # pylint: disable=no-init
    """Websocket handler for sending messages to clients."""

    def received_message(self, message):  # pylint: disable=no-self-use
        """Handler for receiving a message on the websocket."""
        # TODO(2016-04-27) Use a logger instead of a raw print
        print(
            'Warning: Received unexpected message'
            ' from websocket client: {}'.format(
                message.data.decode('utf-8')
            )
        )

    def closed(self, code, reason=None):
        """Handler for when a websocket is closed."""
        # There's nothing to do here for now

