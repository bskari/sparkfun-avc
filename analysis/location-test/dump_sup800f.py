"""Dumps the SUP800F module to localhost for analysis too."""
from control.sup800f import switch_to_nmea_mode
from control.sup800f_telemetry import Sup800fTelemetry
from control.telemetry import Telemetry
from control.telemetry import CENTRAL_LONGITUDE
from control.telemetry import CENTRAL_LATITUDE
import math
import serial
import urllib.request
import urllib.parse


class LoggerDummy(object):
    def __init__(self):
        self.debug = print
        self.info = print
        self.warn = print
        self.error = print
        self.critical = print


class TelemetryDummy(object):
    def __init__(self):
        self.boulder_latitude_m_per_d_longitude = \
            Telemetry.latitude_to_m_per_d_longitude(40.015)

    def handle_message(self, message):
        if 'y_m' not in message:
            # Compass data, ignore
            return
        values = {
            'latitude': message['latitude'],
            'longitude': message['longitude'],
        }
        data = urllib.parse.urlencode(values)
        data = data.encode('ascii')
        request = urllib.request.Request('https://127.0.0.1:4443/post', data)
        with urllib.request.urlopen(request) as response:
            pass


def main():
    logger = LoggerDummy()

    serial_ = serial.Serial('/dev/ttyAMA0', 115200)
    serial_.setTimeout(1.0)
    for _ in range(10):
        serial_.readline()
    try:
        switch_to_nmea_mode(serial_)
    except:
        logger.error('Unable to set mode')
    for _ in range(10):
        serial_.readline()
    logger.info('Done')
    serial_ = serial.Serial('/dev/ttyAMA0', 115200)

    telemetry = TelemetryDummy()

    sup800f_telemetry = Sup800fTelemetry(telemetry, serial_, logger)
    sup800f_telemetry.start()
    sup800f_telemetry.join(1000000)


if __name__ == '__main__':
    main()
