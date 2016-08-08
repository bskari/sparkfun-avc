"""Dumps telemetry data to the websocket handler for broadcast to all
clients.
"""

import threading
import time


class TelemetryDumper(threading.Thread):
    """Dumps telemetry data to the websocket handler for broadcast to all
    clients.
    """

    def __init__(
        self,
        telemetry,
        waypoint_generator,
        web_socket_handler,
        sleep_seconds=None
    ):
        super(TelemetryDumper, self).__init__()
        self.name = self.__class__.__name__
        self._telemetry = telemetry
        self._waypoint_generator = waypoint_generator
        self._web_socket_handler = web_socket_handler
        if sleep_seconds is None:
            self._sleep_seconds = 0.5
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
                data['throttle'] = self._telemetry._target_throttle  # pylint: disable=protected-access
                data['steering'] = self._telemetry._target_steering  # pylint: disable=protected-access
                data['compass_calibrated'] = 'unknown'

                x_m, y_m = self._waypoint_generator.get_raw_waypoint()
                data['waypoint_x_m'] = x_m
                data['waypoint_y_m'] = y_m

                self._web_socket_handler.broadcast_telemetry(data)
            except:  # pylint: disable=bare-except
                pass

    def kill(self):
        """Stops the thread."""
        self._run = False
