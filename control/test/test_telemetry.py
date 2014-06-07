import math
import unittest

from telemetry import Telemetry


class TestTelemetry(unittest.TestCase):
    def test_rotate_radians_clockwise(self):
        base = (1.0, 0.0)

        not_rotated = Telemetry.rotate_radians_clockwise(base, 0.0)
        self.assertAlmostEqual(not_rotated[0], base[0])
        self.assertAlmostEqual(not_rotated[1], base[1])

        ninety = Telemetry.rotate_radians_clockwise(base, math.radians(90.0))
        self.assertAlmostEqual(ninety[0], 0.0)
        self.assertAlmostEqual(ninety[1], -1.0)

        one_eighty = Telemetry.rotate_radians_clockwise(base, math.radians(180.0))
        self.assertAlmostEqual(one_eighty[0], -base[0])
        self.assertAlmostEqual(one_eighty[1], base[1])

        two_seventy = Telemetry.rotate_radians_clockwise(base, math.radians(270.0))
        self.assertAlmostEqual(two_seventy[0], 0.0)
        self.assertAlmostEqual(two_seventy[1], 1.0)

        three_sixty = Telemetry.rotate_radians_clockwise(base, math.radians(360.0))
        self.assertAlmostEqual(three_sixty[0], base[0])
        self.assertAlmostEqual(three_sixty[1], base[1])

        negative_ninety = Telemetry.rotate_radians_clockwise(base, math.radians(-90.0))
        self.assertAlmostEqual(negative_ninety[0], two_seventy[0])
        self.assertAlmostEqual(negative_ninety[1], two_seventy[1])

    def test_latitude_to_m_per_d_longitude(self):
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
            Telemetry.latitude_to_m_per_d_longitude(40.08, cache=False), # Boulder
            85294.08886768305,
            places=2
        )
