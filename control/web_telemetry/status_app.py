"""Status page for the vehicle."""

import cherrypy
import netifaces
import os
import sys
from ws4py.websocket import WebSocket
import json

from control.web_telemetry.web_socket_handler import WebSocketHandler
from messaging.async_logger import AsyncLogger
from messaging.async_producers import TelemetryProducer

STATIC_DIR = 'static-web'
WEB_TELEMETRY_DIR = 'control' + os.sep + 'web_telemetry' + os.sep


class StatusApp(object):
    """Status page for the vehicle."""

    def __init__(self, telemetry, port):
        self._telemetry = telemetry
        logger = AsyncLogger()
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
        index_file_name = WEB_TELEMETRY_DIR + 'index.html'
        if sys.version_info.major == 2:
            with open(index_file_name) as file_:
                index_page = file_.read().decode('utf-8')
        else:
            with open(index_file_name, encoding='utf-8') as file_:
                index_page = file_.read()
        return index_page.replace(
            '${webSocketAddress}',
            '{host_ip}:{port}/telemetry/ws'.format(
                host_ip=self._host_ip,
                port=self._port
            )
        ).replace(
            '${postAddress}',
            '//{host_ip}:{port}/telemetry/post_telemetry'.format(
                host_ip=self._host_ip,
                port=self._port
            )
        )

    @cherrypy.expose
    def ws(self):  # pylint: disable=invalid-name
        """Dummy method to tell CherryPy to expose the web socket end point."""
        pass

    @cherrypy.expose
    @cherrypy.tools.allow(methods=['POST'])
    @cherrypy.tools.json_out()
    def post_telemetry(self, message):  # pylint: disable=no-self-use
        """End point for receiving telemetry readings. Some phones don't support
        websockets, so just use plain old POST.
        """
        try:
            message = json.loads(str(message))

            if 'latitude_d' in message:
                TelemetryProducer().gps_reading(
                    message['latitude_d'],
                    message['longitude_d'],
                    message['accuracy_m'],
                    message['heading_d'],
                    message['speed_m_s'],
                    message['timestamp_s']
                )
            elif 'compass_d' in message:
                TelemetryProducer().compass_reading(
                    message['compass_d'],
                    message['confidence']
                )
            else:
                AsyncLogger().error(
                    'Received unexpected web telemetry message: {}'.format(
                        message
                    )
                )

        except Exception as exc:  # pylint: disable=broad-except
            AsyncLogger().error(
                'Invalid POST telemetry message "{}": {} {}'.format(
                    message,
                    type(exc),
                    exc
                )
            )
            return {'success': False, 'message': str(exc)}

        return {'success': True}
