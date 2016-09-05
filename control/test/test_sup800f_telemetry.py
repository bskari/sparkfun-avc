"""Tests the Sup800fTelemetry class."""

# pylint: disable=protected-access

import unittest

# Patch out the logger
from messaging import async_logger
from control.test.dummy_logger import DummyLogger
async_logger.AsyncLogger = DummyLogger

# Patch out the telemetry
from messaging import async_producers
class DummyTelemetry(object):
    def __init__(self):
        self.message = {}
    def gps_reading(self, lat, long, accuracy, bearing, speed, timestamp, device_id):
        self.message['lat'] = lat
        self.message['long'] = long
        self.message['accuracy'] = accuracy
        self.message['bearing'] = bearing
        self.message['speed'] = speed
        self.message['timestamp'] = timestamp
async_producers.TelemetryProducer = DummyTelemetry

from control.sup800f_telemetry import Sup800fTelemetry


class TestSup800fTelemetry(unittest.TestCase):
    """Tests the Sup800fTelemetry class."""

    def test_handle_gprmc(self):
        """Tests the GPRMC message parsing."""
        sup800f = Sup800fTelemetry(None)
        # Sparkfun HQ (40.090483, -105.185083), 5 m/s, 180.0
        sup800f._handle_gprmc(
            '$GPRMC,123456.789,A,4005.429,N,10511.105,W,9.719,180.0,030415,003.9,W,A*hh\r\n'
        )

        # We just want to check to see that we're close to Sparkfun, because I
        # just eyeballed a point on Google Maps to get the above coordinates
        dummy_telemetry = sup800f._telemetry
        self.assertAlmostEqual(dummy_telemetry.message['lat'], 40.090483, 6)
        self.assertAlmostEqual(dummy_telemetry.message['long'], -105.185083, 6)
        self.assertAlmostEqual(dummy_telemetry.message['bearing'], 180.0)
        self.assertAlmostEqual(dummy_telemetry.message['speed'], 5.0, 3)
        self.assertAlmostEqual(
            dummy_telemetry.message['timestamp'],
            1428064496.789,
            3
        )

    def test_handle_gpgsa(self):
        """Tests the GPGSA message parsing."""
        sup800f = Sup800fTelemetry(None)
        sup800f._handle_gpgsa(
            '$GPGSA,A,3,23,03,26,09,27,16,22,31,,,,,1.9,1.1,1.5*31\r\n'
        )
        self.assertEqual(sup800f._hdop, 1.1)


if __name__ == '__main__':
    unittest.main()
