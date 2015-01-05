"""Thread to run the HTTP server stuff."""

from ws4py.server.cherrypyserver import WebSocketPlugin
from ws4py.server.cherrypyserver import WebSocketTool
import cherrypy
import logging
import os
import threading

from monitor.status_app import StatusApp


class HttpServer(threading.Thread):
    """Runs CherryPy in a thread."""
    def __init__(self, command, telemetry, logger):
        super(HttpServer, self).__init__()

        config = StatusApp.get_config(os.path.abspath(os.getcwd()))

        application = cherrypy.tree.mount(
            StatusApp(command, telemetry, logger),
            '/',
            config
        )

        cherrypy.config.update({
            'server.socket_host': '0.0.0.0',
            'server.socket_port': 8080,
        })

        WebSocketPlugin(cherrypy.engine).subscribe()
        cherrypy.tools.websocket = WebSocketTool()

        # OMG, shut up CherryPy, nobody cares about your problems
        application.log.access_log.setLevel(logging.ERROR)
        application.log.error_log.setLevel(logging.ERROR)
        cherrypy.log.access_log.setLevel(logging.ERROR)
        cherrypy.log.error_log.setLevel(logging.ERROR)

    def run(self):
        """Runs the thread and server in a thread."""
        cherrypy.engine.start()

    @staticmethod
    def kill():
        """Stops the thread and server."""
        cherrypy.engine.exit()
