"""Status page for the vehicle."""

import cherrypy
import netifaces
import os
import subprocess
import sys

from monitor.web_socket_handler import WebSocketHandler


STATIC_DIR = 'static-web'


class StatusApp(object):
    """Status page for the vehicle."""

    def __init__(self, command, telemetry, logger, port):
        self._command = command
        self._telemetry = telemetry
        self._logger = logger
        self._port = port

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
                logger.warn(
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
                logger.info(
                    'Web server listening on {iface}'.format(
                        iface=iface
                    )
                )
                break
        if self._host_ip is None:
            logger.error('No valid host found, listening on loopback')
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
        index_file_name = STATIC_DIR + os.sep + 'index.html'
        if sys.version_info.major == 2:
            with open(index_file_name) as file_:
                index_page = file_.read().decode('utf-8')
        else:
            with open(index_file_name, encoding='utf-8') as file_:
                index_page = file_.read()
        return index_page.replace(
            '${webSocketAddress}',
            'ws://{host_ip}:{port}/ws'.format(
                host_ip=self._host_ip,
                port=self._port
            )
        )

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def telemetry(self):
        """Returns the telemetry data of the car."""
        return self._telemetry.get_data()

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def run(self):
        """Runs the car."""
        self._check_post()
        self._command.handle_message({'command': 'start'})
        self._logger.info('Received run command from web')
        return {'success': True}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def stop(self):
        """Stops the car."""
        self._check_post()
        self._command.handle_message({'command': 'stop'})
        self._logger.info('Received stop command from web')
        return {'success': True}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def reset(self):
        """Resets the waypoints."""
        self._check_post()
        self._command.handle_message({'command': 'reset'})
        self._logger.info('Received reset command from web')
        return {'success': True}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def calibrate_compass(self):  # pylint: disable=no-self-use
        """Calibrates the compass."""
        self._check_post()
        self._logger.info('Received calibrate compass command from web')
        self._command.handle_message({
            'command': 'calibrate-compass',
        })
        return {'success': True}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def line_up(self):  # pylint: disable=no-self-use
        """Plays the Mario Kart line up sound."""
        self._check_post()
        self._command.handle_message({'command': 'line-up'})
        if (
                os.path.isfile('/usr/bin/mpg123')
                and os.path.isfile('sound/race-start.mp3')
        ):
            subprocess.Popen(
                ('/usr/bin/mpg123', 'sound/race-start.mp3'),
                stdout=open('/dev/null', 'w')
            )
        return {'success': True}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def count_down(self):  # pylint: disable=no-self-use
        """Plays the Mario Kart count down sound."""
        self._check_post()
        self._command.handle_message({'command': 'count-down'})
        if os.path.isfile('/usr/bin/mpg123') and os.path.isfile('sound/count-down.mp3'):
            subprocess.Popen(
                ('mpg123', 'sound/count-down.mp3'),
                stdout=open('/dev/null', 'w')
            )
        return {'success': True}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def follow(self):  # pylint: disable=invalid-name
        """Tells the car to start following the phone."""
        self._check_post()
        self._logger.info('Received follow command from web')
        return {'success': False, 'message': 'Not implemented'}

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
