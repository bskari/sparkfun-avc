"""Tests the compass estimator class."""
import mock
import time
import unittest

from estimated_compass import EstimatedCompass

#pylint: disable=invalid-name
#pylint: disable=protected-access
#pylint: disable=too-many-public-methods


class TestEstimatedCompass(unittest.TestCase):
    """Tests the EstimatedCompass class."""
    @classmethod
    def setUpClass(cls):
        class FakeLogger(object):
            def warning(self, o):
                pass
            def info(self, o):
                pass
            def debug(self, o):
                pass

        cls.logger = FakeLogger()

    @mock.patch.object(time, 'time')
    def test_turn_then_straight(self, mock_time):
        """Test that the compass points back to the direction of the turn."""
        step_time_s = 0.05
        lower_time_s = 0.0
        upper_time_s = 1.0 + step_time_s / 2.0
        step_count = int((upper_time_s - lower_time_s) / step_time_s)

        mock_time.side_effect = [i * step_time_s for i in range(step_count * 2)]

        estimated_compass = EstimatedCompass(self.logger)
        initial_heading_d = 180.0
        estimated_compass.process_drive_command(1.0, 1.0, 180.0)
        self.assertEqual(mock_time.call_count, 1)
        self.assertTrue(estimated_compass._compass_turning)

        for call in range(1, step_count):
            self.assertNotEqual(
                initial_heading_d,
                estimated_compass.get_estimated_heading(initial_heading_d)
            )
            self.assertEqual(mock_time.call_count, call + 1)

        self.assertTrue(estimated_compass._compass_turning)

        # We should eventually get the compass back
        final_heading_d = 270.0
        estimated_compass.process_drive_command(1.0, 0.0, 270.0)
        for _ in range(10):
            estimated_compass.get_estimated_heading(final_heading_d)

        self.assertEqual(
            estimated_compass.get_estimated_heading(final_heading_d),
            final_heading_d
        )
        self.assertFalse(estimated_compass._compass_turning)

    def test_sanity(self):
        """Test that calculations are sane."""
        estimated_compass = EstimatedCompass(self.logger)

        estimated_compass.process_drive_command(1.0, 1.0, 0)
        right = estimated_compass._car_turn_rate_d_s()
        self.assertGreater(right, 0)

        estimated_compass.process_drive_command(1.0, -1.0, 0)
        left = estimated_compass._car_turn_rate_d_s()
        self.assertLess(left, 0)

    def test_blending(self):
        """Test that calculations are blended with observations."""
        estimated_compass = EstimatedCompass(self.logger)

        estimated_compass.process_drive_command(1.0, 1.0, 0)
        right = estimated_compass._car_turn_rate_d_s()

        estimated_compass.process_drive_command(1.0, 0.9, 0)
        lesser_right = estimated_compass._car_turn_rate_d_s()
        self.assertGreater(right, lesser_right)
