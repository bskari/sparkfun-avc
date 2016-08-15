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
        try:
            if message.is_binary:
                # TODO(2016-08-13) Log an error
                return
            message = json.loads(str(message))
            if 'latitude_d' in message:
                TelemetryProducer().gps_reading(
                    message['latitude_d'],
                    message['longitude_d'],
                    message['accuracy_m'],
                    message['heading_d'],
                    message['speed_m_s'],
                    message['timestamp_s']
                )
            elif 'compass_d' in message:
                TelemetryProducer().compass_reading(
                    message['compass_d'],
                    message['confidence']
                )
            else:
                AsyncLogger().error(
                    'Received unexpected web telemetry message: "{}"'.format(
                        message
                    )
                )
        # We need to catch all exceptions because any that are raised will close
        # the websocket
        except Exception as exc:  # pylint: disable=broad-except
            AsyncLogger().error(
                'Error processing web telemetry message "{}": {} {}'.format(
                    message,
                    type(exc),
                    exc
                )
            )

    def closed(self, code, reason=None):
        """Handler for when a websocket is closed."""
        # There's nothing to do here for now
