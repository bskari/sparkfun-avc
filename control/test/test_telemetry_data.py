"""Tests the Sup800fTelemetry class."""
import unittest

from control.sup800f_telemetry import Sup800fTelemetry
from control.test.dummy_logger import DummyLogger


class TestSup800fTelemetry(unittest.TestCase):
    """Tests the Sup800fTelemetry class."""

    def test_handle_gprmc(self):
        """Tests the GPRMC message parsing."""
        class DummyTelemetry(object):
            def __init__(self):
                self.message = None

            def handle_message(self, message_):
                self.message = message_

        dummy_telemetry = DummyTelemetry()
        sup800f = Sup800fTelemetry(dummy_telemetry, None, DummyLogger())
        # Sparkfun HQ (40.090841, -105.185090), 5 m/s, 180.0
        sup800f._handle_gprmc(
            '$GPRMC,123456.789,A,4005.429,N,10511.105,W,9.719,180.0,030415,003.9,W,A*hh\r\n'
        )

        # We just want to check to see that we're close to Sparkfun, because I
        # just eyeballed a point on Google Maps to get the above coordinates
        self.assertLess(dummy_telemetry.message['x_m'], 100)
        self.assertLess(dummy_telemetry.message['y_m'], 100)
        self.assertAlmostEqual(dummy_telemetry.message['gps_d'], 180.0)
        self.assertAlmostEqual(dummy_telemetry.message['speed_m_s'], 5.0, 3)


if __name__ == '__main__':
    unittest.main()
