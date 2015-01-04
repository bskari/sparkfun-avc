"""Status page for the vehicle."""

import cherrypy
import subprocess


class StatusApp(object):
    """Status page for the vehicle."""

    def __init__(self, command, telemetry, logger):
        self._command = command
        self._telemetry = telemetry
        self._logger = logger

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
        }

    @cherrypy.expose
    def index(self):  # pylint: disable=no-self-use
        """Index page."""
        return open('monitor/static/index.html')

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

    @staticmethod
    def _check_post():
        """Checks that the request method is POST."""
        if cherrypy.request.method != 'POST':
            cherrypy.response.headers['Allow'] = 'POST'
            raise cherrypy.HTTPError(405)
