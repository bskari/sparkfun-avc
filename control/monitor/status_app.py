"""Status page for the vehicle."""

import cherrypy
import netifaces
import subprocess
import sys

from monitor.web_socket_handler import WebSocketHandler


class StatusApp(object):
    """Status page for the vehicle."""

    def __init__(self, command, telemetry, logger):
        self._command = command
        self._telemetry = telemetry
        self._logger = logger

        def get_ip(interface):
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
        interfaces = sorted(
            [
                iface for iface in netifaces.interfaces()
                if iface.startswith('wlan')
                or iface.startswith('eth')
            ],
            reverse=True
        )
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
            logger.error('No valid host found, listening on lo')
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
                'tools.staticdir.dir': './static',
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
        if sys.version_info.major == 2:
            with open('monitor/static/index.html') as file_:
                index_page = file_.read().decode('utf-8')
        else:
            with open('monitor/static/index.html', encoding='utf-8') as file_:
                index_page = file_.read()
        return index_page.replace(
            '${webSocketAddress}',
            'ws://{host_ip}:8080/ws'.format(host_ip=self._host_ip)
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
        self._command.run_course()
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
    def calibrate_compass(self):  # pylint: disable=no-self-use
        """Calibrates the compass."""
        self._check_post()
        self._logger.info('Received calibrate compass command from web')
        return {'success': False, 'message': 'Not implemented'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def line_up(self):  # pylint: disable=no-self-use
        """Plays the Mario Kart line up sound."""
        self._check_post()
        subprocess.Popen(
            ('mpg123', 'sound/race-start.mp3'),
            stdout=open('/dev/null', 'w')
        )
        return {'success': True}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def count_down(self):  # pylint: disable=no-self-use
        """Plays the Mario Kart count down sound."""
        self._check_post()
        subprocess.Popen(
            ('mpg123', 'sound/count-down.mp3'),
            stdout=open('/dev/null', 'w')
        )
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
