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
    def __init__(
            self,
            command,
            telemetry,
            telemetry_data,
            logger,
            address=None,
            port=None
    ):
        super(HttpServer, self).__init__()
        if address is None:
            address = '0.0.0.0'
        if port is None:
            port = 8080

        config = StatusApp.get_config(os.path.abspath(os.getcwd()))

        application = cherrypy.tree.mount(
            StatusApp(command, telemetry, telemetry_data, logger, port),
            '/',
            config
        )

        cherrypy.config.update({
            'server.socket_host': address,
            'server.socket_port': port
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
