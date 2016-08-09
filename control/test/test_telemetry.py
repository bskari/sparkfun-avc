"""Tests the Telemetry class."""
import math
import mock
import unittest

from control.telemetry import CENTRAL_LATITUDE, CENTRAL_LONGITUDE, Telemetry
from messaging.message_consumer import consume_messages

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

    def assert_almost_equal_point(self, point_1, point_2):
        """Tests that two points are almost equal."""
        x_1, y_1 = point_1
        x_2, y_2 = point_2
        self.assertAlmostEqual(x_1, x_2, 4)
        self.assertAlmostEqual(y_1, y_2, 4)

    def test_offset_from_waypoint(self):
        """Tests offset from waypoint."""
        offset = Telemetry.offset_from_waypoint
        almost_equal = self.assert_almost_equal_point

        almost_equal(offset(0.0, 0.0, 1.0), (0.0, -1.0))

        almost_equal(offset(0.0, 45.0, 1.0), (-0.707107, -0.707107))
        almost_equal(offset(10.0, 35.0, 1.0), (-0.707107, -0.707107))
        almost_equal(offset(20.0, 25.0, 1.0), (-0.707107, -0.707107))
        almost_equal(offset(350.0, 55.0, 1.0), (-0.707107, -0.707107))
        almost_equal(offset(340.0, 65.0, 1.0), (-0.707107, -0.707107))

        almost_equal(offset(0.0, -45.0, 1.0), (0.707107, -0.707107))
        almost_equal(offset(10.0, -55.0, 1.0), (0.707107, -0.707107))
        almost_equal(offset(20.0, -65.0, 1.0), (0.707107, -0.707107))
        almost_equal(offset(350.0, -35.0, 1.0), (0.707107, -0.707107))
        almost_equal(offset(340.0, -25.0, 1.0), (0.707107, -0.707107))

        almost_equal(offset(90.0, 45.0, 1.0), (-0.707107, 0.707107))
        almost_equal(offset(90.0, -45.0, 1.0), (-0.707107, -0.707107))
        almost_equal(offset(180.0, 45.0, 1.0), (0.707107, 0.707107))
        almost_equal(offset(180.0, -45.0, 1.0), (-0.707107, 0.707107))
        almost_equal(offset(270.0, 45.0, 1.0), (0.707107, -0.707107))
        almost_equal(offset(270.0, -45.0, 1.0), (0.707107, 0.707107))

        _345 = 36.86989764584402
        almost_equal(offset(0.0, _345, 5.0), (-3.0, -4.0))
        almost_equal(offset(180.0, _345, 5.0), (3.0, 4.0))

    def test_distance_to_waypoint(self):
        """Tests the distance calculation."""
        distance = Telemetry.distance_to_waypoint

        for p in (1, -1):
            self.assertAlmostEqual(distance(p * 45, p * 90, 1.0), math.sqrt(2))
            assert(
                distance(p * 30.0, p * 35.0, 1.0)
                < distance(p * 30.0, p * 35.0, 2.0)
                < distance(p * 30.0, p * 35.0, 3.0))
            _345 = 36.86989764584402
            self.assertAlmostEqual(distance(p * _345, p * 90.0, 4.0), 5.0)
            self.assertAlmostEqual(distance(p * (90 - _345), p * 90, 3.0), 5.0)

    def test_intersection(self):
        """Tests the line intersection algorithm."""
        intersect_cases = (
            ((-1, 0), (1, 0), (0, 1), (0, -1)),
            ((1, 1), (-1, -1), (-1, 1), (1, -1)),
        )
        for case in intersect_cases:
            self.assertTrue(Telemetry.intersects(*case))  # pylint: disable=star-args

        separate_cases = (
            ((1, 1), (0, 0), (-1, -1), (-2, -2)),
            ((1, 1), (0, 0), (-1, -1), (5, 20)),
        )
        for case in separate_cases:
            self.assertFalse(Telemetry.intersects(*case))  # pylint: disable=star-args

        smoke_cases = (
            ((-1, 1), (0, 0), (-1, 1), (0, 0)),  # Same
            ((-1, 1), (0, 0), (-5, 5), (0, 0)),  # Overlap with 1 end points
            ((-1, 1), (0, 0), (-5, 5), (5, -5)),  # Overlap
            ((1, 0), (-1, 0), (2, -1), (-2, -1)),  # Parallel
            ((1, 1), (1, 1), (2, 2), (2, 2)),  # Points
            ((1, 1), (1, 1), (1, 1), (1, 1)),  # Same points
            ((0.0, 0.0), (1.0, 0.0), (1.0, 0.0), (1.0, 1.0)),  # End to end
        )
        for case in smoke_cases:
            # Just make sure nothing catches on fire
            Telemetry.intersects(*case)  # pylint: disable=star-args

    def test_point_in_polygon(self):
        """Tests point in polygon."""
        diamond = ((1, 0), (0, -1), (-1, 0), (0, 1))
        for point in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
            self.assertFalse(Telemetry.point_in_polygon(point, diamond))
        self.assertTrue(Telemetry.point_in_polygon((0, 0), diamond))

        # -------------
        # |  *  *  *  |
        # |*/-\ * /-\*|
        # |/ * \-/ * \|
        polygon = (
            (0, 0), (0, 4), (8, 4), (8, 0), (6, 2), (4, 0), (2, 2)
        )
        inside = ((1, 1), (2, 3), (4, 3), (6, 3), (7, 1))
        outside = (
            (2, 1), (6, 1), (8.1, 0.1), (8.1, 3.9), (-1, -1), (100, 0),
            (0, 100), (100, 100), (-100, -100), (-100, 100), (100, -100)
        )
        for point in inside:
            self.assertTrue(Telemetry.point_in_polygon(point, polygon))
        for point in outside:
            self.assertFalse(Telemetry.point_in_polygon(point, polygon))

        # Test the last segment. The function uses an arbitrary offset, so test
        # all directions so that we can change the offset and not break.
        tiny = 0.0001
        polygon = ((-tiny, -tiny), (tiny, -tiny), (tiny, tiny), (-tiny, tiny))
        self.assertTrue(Telemetry.point_in_polygon((0, 0), polygon))
        for point in polygon:
            point_2 = [i * 2 for i in point]
            self.assertFalse(Telemetry.point_in_polygon(point_2, polygon))
        for point in (-tiny, tiny):
            point_2 = (point * 2, 0)
            self.assertFalse(Telemetry.point_in_polygon(point_2, polygon))
        for point in (-tiny, tiny):
            point_2 = (0, point * 2)
            self.assertFalse(Telemetry.point_in_polygon(point_2, polygon))
        for point in polygon:
            point_2 = (point[0] * 2, point[1])
            self.assertFalse(Telemetry.point_in_polygon(point_2, polygon))
        for point in polygon:
            point_2 = (point[0], point[1] * 2)
            self.assertFalse(Telemetry.point_in_polygon(point_2, polygon))

    @mock.patch('control.telemetry.consume_messages')
    def test_central_offset(self, mock_consume):
        """The offset should default to Sparkfun, or be loaded from the KML
        course.
        """
        telemetry = Telemetry()
        self.assertLess(
            telemetry.distance_m(
                # From Google Earth
                40.090764,
                -105.184879,
                CENTRAL_LATITUDE,
                CENTRAL_LONGITUDE
            ),
            100
        )

        # Smoke test
        course = {
            'course': ((1, 2), (3, 4)),
            'inner': ()
        }
        with mock.patch.object(Telemetry, '_load_kml', return_value=course):
            with mock.patch('builtins.open'):
                Telemetry('file.kml')


if __name__ == '__main__':
    unittest.main()
