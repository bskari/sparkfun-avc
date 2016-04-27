"""Status page for the vehicle."""

import cherrypy
import netifaces
import os
import sys

STATIC_DIR = 'static-web'
WEB_TELEMETRY_DIR = 'control' + os.sep + 'web_telemetry' + os.sep


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
                    'Web telemetry server listening on {iface}'.format(
                        iface=iface
                    )
                )
                break
        if self._host_ip is None:
            logger.error('No valid host found, listening on loopback')
            self._host_ip = get_ip('lo')

    @staticmethod
    def get_config(web_telemetry_root_dir):
        """Returns the required CherryPy configuration for this application."""
        return {
            '/': {
                'tools.sessions.on': True,
                'tools.staticdir.root':
                    web_telemetry_root_dir + '/control/web_telemetry/',
            },
            '/static': {
                'tools.staticdir.on': True,
                'tools.staticdir.dir': '..' + os.sep + '..'  + os.sep + STATIC_DIR
            },
        }

    @cherrypy.expose
    def index(self):  # pylint: disable=no-self-use
        """Index page."""
        index_page = None
        index_file_name = WEB_TELEMETRY_DIR + 'index.html'
        if sys.version_info.major == 2:
            with open(index_file_name) as file_:
                index_page = file_.read().decode('utf-8')
        else:
            with open(index_file_name, encoding='utf-8') as file_:
                index_page = file_.read()
        return index_page
