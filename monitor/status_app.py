"""Status page for the vehicle."""

import cherrypy
import netifaces
import os
import signal
import subprocess
import sys

from monitor.web_socket_handler import WebSocketHandler
from messaging.async_logger import AsyncLogger
from messaging.async_producers import CommandProducer
from messaging.async_producers import WaypointProducer


STATIC_DIR = 'static-web'
MONITOR_DIR = 'monitor' + os.sep


class StatusApp(object):
    """Status page for the vehicle."""

    def __init__(self, telemetry, waypoint_generator, port):
        self._command = CommandProducer()
        self._telemetry = telemetry
        self._logger = AsyncLogger()
        self._port = port
        self._waypoint_generator = waypoint_generator

        def get_ip(interface):
            """Returns the IPv4 address of a given interface."""
            try:
                addresses = netifaces.ifaddresses(interface)
                if len(addresses) == 0:
                    return None
                if netifaces.AF_INET not in addresses:
                    return None
                return addresses[netifaces.AF_INET][0]['addr']
            except Exception as exc:  # pylint: disable=broad-except
                self._logger.warn(
                    'Exception trying to get interface address: {exc}'.format(
                        exc=str(exc)
                    )
                )
                return None

        self._host_ip = None

        def interface_preference(interface):
            """Ordering function that orders wireless adapters first, then
            physical, then loopback.
            """
            if interface.startswith('wlan') or interface == 'en1':
                return 0
            if interface.startswith('eth') or interface == 'en0':
                return 1
            if interface.startswith('lo'):
                return 2
            return 3

        interfaces = sorted(netifaces.interfaces(), key=interface_preference)
        for iface in interfaces:
            self._host_ip = get_ip(iface)
            if self._host_ip is not None:
                self._logger.info(
                    'Monitor web server listening on {iface}'.format(
                        iface=iface
                    )
                )
                break
        if self._host_ip is None:
            self._logger.error('No valid host found, listening on loopback')
            self._host_ip = get_ip('lo')

    @staticmethod
    def get_config(monitor_root_dir):
        """Returns the required CherryPy configuration for this application."""
        return {
            '/': {
                'tools.sessions.on': True,
                'tools.staticdir.root': monitor_root_dir + '/monitor/',
            },
            '/static': {
                'tools.staticdir.on': True,
                'tools.staticdir.dir': '..' + os.sep + STATIC_DIR
            },
            '/ws': {
                'tools.websocket.on': True,
                'tools.websocket.handler_cls': WebSocketHandler
            },
        }

    @cherrypy.expose
    def index(self):  # pylint: disable=no-self-use
        """Index page."""
        # This is the worst templating ever, but I don't feel like it's worth
        # installing a full engine just for this one substitution
        index_page = None
        index_file_name = MONITOR_DIR + 'index.html'
        if sys.version_info.major == 2:
            with open(index_file_name) as file_:
                index_page = file_.read().decode('utf-8')
        else:
            with open(index_file_name, encoding='utf-8') as file_:
                index_page = file_.read()
        return index_page.replace(
            '${webSocketAddress}',
            '{host_ip}:{port}/ws'.format(
                host_ip=self._host_ip,
                port=self._port
            )
        ).replace(
            '${waypointFileOptions}',
            '\n'.join((
                '<option value="{file}">{file}</option>'.format(file=i)
                for i in os.listdir('paths')
                if i.endswith('kml') or i.endswith('kmz')
            ))
        )

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def telemetry_json(self):
        """Returns the telemetry data of the car."""
        telemetry = self._telemetry.get_data(update=False)
        waypoint_x_m, waypoint_y_m = self._waypoint_generator.get_raw_waypoint()
        telemetry.update({
            'waypoint_x_m': waypoint_x_m,
            'waypoint_y_m': waypoint_y_m,
        })
        return telemetry

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def run(self):
        """Runs the car."""
        self._check_post()
        self._command.start()
        self._logger.info('Received run command from web')
        return {'success': True}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def stop(self):
        """Stops the car."""
        self._check_post()
        self._command.stop()
        self._logger.info('Received stop command from web')
        return {'success': True}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def reset(self):
        """Resets the waypoints."""
        self._check_post()
        self._command.reset()
        self._logger.info('Received reset command from web')
        return {'success': True}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def calibrate_compass(self):  # pylint: disable=no-self-use
        """Calibrates the compass."""
        self._check_post()
        self._logger.info('Received calibrate compass command from web')
        self._command.calibrate_compass()
        return {'success': True}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def set_max_throttle(self, throttle):  # pylint: disable=no-self-use
        """Hands off the maximum throttle to the command exchange."""
        self._logger.info('Received throttle command from web')
        self._command.set_max_throttle(throttle)
        return {'success': True}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def set_waypoints(self, kml_file_name):  # pylint: disable=no-self-use
        """Hands off the file to load waypoints to the waypoint exchange."""
        self._logger.info(
            'Received set waypoints: {} command from web'.format(
                kml_file_name
            )
        )
        WaypointProducer().load_kml_file(kml_file_name)
        self._telemetry.load_kml_from_file_name(kml_file_name)
        return {'success': True}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def shut_down(self):
        """Shuts down the Pi."""
        self._command.stop()
        subprocess.Popen(('bash', '-c', 'sleep 10 && sudo shutdown -h now'))
        os.kill(os.getpid(), signal.SIGINT)
        return {'success': True}

    @cherrypy.expose
    def ws(self):  # pylint: disable=invalid-name
        """Dummy method to tell CherryPy to expose the web socket end point."""
        pass

    @staticmethod
    def _check_post():
        """Checks that the request method is POST."""
        if cherrypy.request.method != 'POST':
            cherrypy.response.headers['Allow'] = 'POST'
            raise cherrypy.HTTPError(405)
