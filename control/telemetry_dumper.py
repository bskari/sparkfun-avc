"""Dumps telemetry data to the websocket handler for broadcast to all
clients.
"""

import threading
import time


class TelemetryDumper(threading.Thread):
    """Dumps telemetry data to the websocket handler for broadcast to all
    clients.
    """

    def __init__(self, telemetry, web_socket_handler, sleep_seconds=None):
        super(TelemetryDumper, self).__init__()
        self._telemetry = telemetry
        self._web_socket_handler = web_socket_handler
        if sleep_seconds is None:
            self._sleep_seconds = 1.0
        else:
            self._sleep_seconds = sleep_seconds
        self._run = True

    def run(self):
        """Runs in a thread."""
        while self._run:
            try:
                time.sleep(self._sleep_seconds)
                # TODO(2015-01-04) Include waypoint and raw sensor data too
                data = self._telemetry.get_data()
                data['throttle'] = self._telemetry._throttle
                data['steering'] = self._telemetry._steering

                # Round the floating point values
                old_data = data.copy()
                for key, value in old_data.items():
                    try:
                        if int(value) != value:
                            data[key] = round(value, 3)
                    except:  # pylint: disable=bare-except
                        pass

                self._web_socket_handler.broadcast_telemetry(data)
            except:  # pylint: disable=bare-except
                pass

    def kill(self):
        """Stops the thread."""
        self._run = False
