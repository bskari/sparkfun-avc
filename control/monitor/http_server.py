"""Thread to run the HTTP server stuff."""
import cherrypy
import logging
import os
import threading

from monitor.status_app import StatusApp


class HttpServer(threading.Thread):
    """Runs CherryPy in a thread."""
    def __init__(self, command, telemetry, logger):
        super(HttpServer, self).__init__()
        application = cherrypy.tree.mount(
            StatusApp(command, telemetry, logger),
            '/',
            StatusApp.get_config(os.path.abspath(os.getcwd()))
        )
        # OMG, shut up CherryPy, nobody cares about your problems
        application.log.access_log.setLevel(logging.CRITICAL)
        application.log.error_log.setLevel(logging.CRITICAL)
        cherrypy.log.access_log.setLevel(logging.CRITICAL)
        cherrypy.log.error_log.setLevel(logging.CRITICAL)

        cherrypy.engine.start()
        cherrypy.engine.block()

    @staticmethod
    def kill():
        """Stops the thread and server."""
        cherrypy.engine.stop()
