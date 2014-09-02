"""Tests the Telemetry class."""
import math
import mock
import unittest

from telemetry import Telemetry

#pylint: disable=invalid-name
#pylint: disable=too-many-public-methods


class TestTelemetry(unittest.TestCase):
    """Tests the Telemetry class."""
    def test_rotate_radians_clockwise(self):
        """Tests rotating a vector radians clockwise."""
        base = (1.0, 0.0)

        not_rotated = Telemetry.rotate_radians_clockwise(base, 0.0)
        self.assertAlmostEqual(not_rotated[0], base[0])
        self.assertAlmostEqual(not_rotated[1], base[1])

        ninety = Telemetry.rotate_radians_clockwise(base, math.radians(90.0))
        self.assertAlmostEqual(ninety[0], 0.0)
        self.assertAlmostEqual(ninety[1], -1.0)

        one_eighty = Telemetry.rotate_radians_clockwise(
            base,
            math.radians(180.0)
        )
        self.assertAlmostEqual(one_eighty[0], -base[0])
        self.assertAlmostEqual(one_eighty[1], base[1])

        two_seventy = Telemetry.rotate_radians_clockwise(
            base,
            math.radians(270.0)
        )
        self.assertAlmostEqual(two_seventy[0], 0.0)
        self.assertAlmostEqual(two_seventy[1], 1.0)

        three_sixty = Telemetry.rotate_radians_clockwise(
            base,
            math.radians(360.0)
        )
        self.assertAlmostEqual(three_sixty[0], base[0])
        self.assertAlmostEqual(three_sixty[1], base[1])

        negative_ninety = Telemetry.rotate_radians_clockwise(
            base,
            math.radians(-90.0)
        )
        self.assertAlmostEqual(negative_ninety[0], two_seventy[0])
        self.assertAlmostEqual(negative_ninety[1], two_seventy[1])

    @unittest.skip(
'''This example checks against a NASA ellipsoid Earth algorithm, which is
different from the current algorithm.'''
    )
    def test_latitude_to_m_per_d_longitude(self):
        """Tests the conversion from latitude to meters per degree longitude."""
        # Assume Earth is a sphere
        self.assertAlmostEqual(
            Telemetry.EQUATORIAL_RADIUS_M * 2.0 * math.pi / 360.0,
            Telemetry.latitude_to_m_per_d_longitude(0.0)
        )

        # Should be symmetrical
        for degree in range(0, 85, 1):
            self.assertAlmostEqual(
                Telemetry.latitude_to_m_per_d_longitude(degree),
                Telemetry.latitude_to_m_per_d_longitude(-degree)
            )

        # At the poles, should be 0
        self.assertAlmostEqual(
            Telemetry.latitude_to_m_per_d_longitude(90.0),
            0.0
        )

        # Known values, from http://www.csgnetwork.com/degreelenllavcalc.html
        self.assertAlmostEqual(
            Telemetry.M_PER_D_LATITUDE,
            111319.458,
            places=1
        )
        self.assertAlmostEqual(
            # Boulder
            Telemetry.latitude_to_m_per_d_longitude(40.08, cache=False),
            85294.08886768305,
            places=2
        )

    @mock.patch.object(Telemetry, 'm_per_d_latitude')
    @mock.patch.object(Telemetry, 'latitude_to_m_per_d_longitude')
    def test_distance_m(
        self,
        mock_latitude_to_m_per_d_longitude,
        mock_m_per_latitude
    ):
        mock_latitude_to_m_per_d_longitude.return_value = 1.0
        mock_m_per_latitude.return_value = 1.0

        self.assertAlmostEqual(Telemetry.distance_m(2, 0, 0, 0), 2)
        self.assertAlmostEqual(Telemetry.distance_m(0, 2, 0, 0), 2)
        self.assertAlmostEqual(Telemetry.distance_m(0, 0, 2, 0), 2)
        self.assertAlmostEqual(Telemetry.distance_m(0, 0, 0, 2), 2)

        self.assertAlmostEqual(Telemetry.distance_m(0, 0, 1, 1), math.sqrt(2))

        for mult_1 in (-1, 1):
            for mult_2 in (-1, 1):
                self.assertAlmostEqual(
                    Telemetry.distance_m(mult_1 * 3, mult_2 * 4, 0, 0),
                    5
                )
                self.assertAlmostEqual(
                    Telemetry.distance_m(mult_1 * 4, mult_2 * 3, 0, 0),
                    5
                )
                self.assertAlmostEqual(
                    Telemetry.distance_m(0, 0, mult_1 * 3, mult_2 * 4),
                    5
                )
                self.assertAlmostEqual(
                    Telemetry.distance_m(0, 0, mult_1 * 4, mult_2 * 3),
                    5
                )

    def test_is_turn_left(self):
        self.assertTrue(Telemetry.is_turn_left(1, 0))
        self.assertFalse(Telemetry.is_turn_left(0, 1))

        self.assertTrue(Telemetry.is_turn_left(1, 359))
        self.assertFalse(Telemetry.is_turn_left(359, 1))

        self.assertTrue(Telemetry.is_turn_left(1, 270))
        self.assertTrue(Telemetry.is_turn_left(0, 270))
        self.assertTrue(Telemetry.is_turn_left(359, 270))

        self.assertFalse(Telemetry.is_turn_left(1, 90))
        self.assertFalse(Telemetry.is_turn_left(0, 90))
        self.assertFalse(Telemetry.is_turn_left(359, 90))

        # These shouldn't throw
        Telemetry.is_turn_left(0, 0)
        Telemetry.is_turn_left(1, 1)
        Telemetry.is_turn_left(180, 180)
        Telemetry.is_turn_left(180, 0)
        Telemetry.is_turn_left(270, 90)
        Telemetry.is_turn_left(360, 0)
        Telemetry.is_turn_left(0, 360)

    @mock.patch.object(Telemetry, 'm_per_d_latitude')
    @mock.patch.object(Telemetry, 'latitude_to_m_per_d_longitude')
    def test_relative_degrees(
        self,
        mock_latitude_to_m_per_d_longitude,
        mock_m_per_latitude
    ):
        mock_latitude_to_m_per_d_longitude.return_value = 1.0
        mock_m_per_latitude.return_value = 1.0

        self.assertAlmostEqual(Telemetry.distance_m(2, 0, 0, 0), 2)
        self.assertAlmostEqual(Telemetry.distance_m(0, 2, 0, 0), 2)
        self.assertAlmostEqual(Telemetry.distance_m(0, 0, 2, 0), 2)
        self.assertAlmostEqual(Telemetry.distance_m(0, 0, 0, 2), 2)

        self.assertAlmostEqual(Telemetry.distance_m(0, 0, 1, 1), math.sqrt(2))

        for mult_1 in (-1, 1):
            for mult_2 in (-1, 1):
                self.assertAlmostEqual(
                    Telemetry.distance_m(mult_1 * 3, mult_2 * 4, 0, 0),
                    5
                )
                self.assertAlmostEqual(
                    Telemetry.distance_m(mult_1 * 4, mult_2 * 3, 0, 0),
                    5
                )
                self.assertAlmostEqual(
                    Telemetry.distance_m(0, 0, mult_1 * 3, mult_2 * 4),
                    5
                )
                self.assertAlmostEqual(
                    Telemetry.distance_m(0, 0, mult_1 * 4, mult_2 * 3),
                    5
                )

    def test_acceleration_mss_velocity_ms_to_ds(self):
        """Tests the conversion from acceleration m/s^s and velocity m/s
        to rotational speed d/s."""
        # Examples taken from
        # www.mattawanschools.org/14662062013835470/lib/14662062013935470/
        # Ch_8_Problem_set.pdf
        velocity_ms = 2 * math.pi * 4.0 / 2.0
        acceleration_mss = velocity_ms ** 2 / 4.0
        self.assertAlmostEqual(
            4.0 * 0.5 * 360.0,  # 2 seconds per revolution
            Telemetry.acceleration_mss_velocity_ms_to_ds(
                acceleration_mss,
                velocity_ms
            )
        )

        velocity_ms = 2 * math.pi * 5e4 / 1.8e3
        acceleration_mss = velocity_ms ** 2 / 5e4
        self.assertAlmostEqual(
            30 * 60 * 360.0,  # 1 revolution per 30 minutes
            Telemetry.acceleration_mss_velocity_ms_to_ds(
                acceleration_mss,
                velocity_ms
            )
        )

    def test_wrap_degrees(self):
        """Tests wrap degrees."""
        for d in range(0, 360):
            self.assertAlmostEqual(d, Telemetry.wrap_degrees(d))

        self.assertAlmostEqual(0.0, Telemetry.wrap_degrees(0.0))
        self.assertAlmostEqual(0.0, Telemetry.wrap_degrees(360.0))
        self.assertAlmostEqual(359.0, Telemetry.wrap_degrees(-1.0))
        self.assertAlmostEqual(359.0, Telemetry.wrap_degrees(-361.0))
        self.assertAlmostEqual(1.0, Telemetry.wrap_degrees(361.0))
        self.assertAlmostEqual(1.0, Telemetry.wrap_degrees(721.0))

    def test_difference_d(self):
        """Tests the difference calculation between two headings."""
        self.assertAlmostEqual(Telemetry.difference_d(359.0, 0.0), 1.0)
        self.assertAlmostEqual(Telemetry.difference_d(0.0, 1.0), 1.0)
        self.assertAlmostEqual(Telemetry.difference_d(359.0, 1.0), 2.0)
        self.assertAlmostEqual(Telemetry.difference_d(360.0, 365.0), 5.0)
        self.assertAlmostEqual(Telemetry.difference_d(-355.0, 365.0), 0.0)


if __name__ == '__main__':
    unittest.main()
