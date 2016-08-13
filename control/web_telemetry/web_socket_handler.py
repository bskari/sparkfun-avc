"""Websocket handler for sending messages to clients."""

from ws4py.websocket import WebSocket
import json

from messaging.async_logger import AsyncLogger
from messaging.async_producers import TelemetryProducer


class WebSocketHandler(WebSocket):  # pylint: disable=no-init
    """Websocket handler for sending messages to clients."""

    @staticmethod
    def received_message(message):
        """Handler for receiving a message on the websocket."""
        if message.is_binary:
            # TODO(2016-08-13) Log an error
            return
        message = json.loads(str(message))
        if 'latitude_d' in message:
            TelemetryProducer().gps_reading(
                message['latitude_d'],
                message['longitude_d'],
                message['accuracy'],
                message['heading_d'],
                message['speed_m_s'],
                message['timestamp']
            )
        elif 'compass_d' in message:
            TelemetryProducer().compass_reading(
                message['compass_d'],
                message['confidence']
            )
        else:
            AsyncLogger().error(
                'Received unexpected web telemetry message: {}'.format(
                    message
                )
            )

    def closed(self, code, reason=None):
        """Handler for when a websocket is closed."""
        # There's nothing to do here for now
