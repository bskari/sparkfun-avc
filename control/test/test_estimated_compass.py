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

    @mock.patch.object(time, 'time')
    def test_turn_then_straight(self, mock_time):
        """Test that the compass points back to the direction of the turn."""
        step_time_s = 0.05
        lower_time_s = 0.0
        upper_time_s = 1.0 + step_time_s / 2.0
        step_count = int((upper_time_s - lower_time_s) / step_time_s)

        mock_time.side_effect = [i * step_time_s for i in range(step_count * 2)]

        estimated_compass = EstimatedCompass()
        initial_heading_d = 180.0
        estimated_compass.process_command(1.0, 1.0, 180.0)
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
        estimated_compass.process_command(1.0, 0.0, 270.0)
        for _ in range(10):
            estimated_compass.get_estimated_heading(final_heading_d)

        self.assertEqual(
            estimated_compass.get_estimated_heading(final_heading_d),
            final_heading_d
        )
        self.assertFalse(estimated_compass._compass_turning)
