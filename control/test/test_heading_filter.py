"""Tests the heading Kalman Filter."""

import math
import numpy
import operator
import random
import unittest

from heading_filter import HeadingFilter

#pylint: disable=protected-access
#pylint: disable=too-many-public-methods


class TestHeadingFilter(unittest.TestCase):
    """Tests the heading Kalman filter."""

    def test_multiply(self):
        """Test the matrix multiply method."""
        with self.assertRaises(TypeError):
            HeadingFilter._multiply(0, 0)

        with self.assertRaises(ValueError):
            HeadingFilter._multiply(
                [[1, 1]],
                [[1, 1]]
            )

        with self.assertRaises(ValueError):
            HeadingFilter._multiply(
                [[1, 1]],
                [[1, 1], [1, 1], [1, 1]]
            )

        self.assertEqual(
            HeadingFilter._multiply(
                [[1, 2]],
                [[2, 3],
                 [5, 8]]
            ),
            [[2 + 10, 3 + 16]]
        )

        self.assertEqual(
            HeadingFilter._multiply(
                [[1, 2, 4],
                 [3, 7, 8]],
                [[2, 0, 1, 4, 6],
                 [1, 1, 1, 1, 1],
                 [5, 3, 8, 9, 7]]
            ),
            [[24, 14, 35, 42, 36],
             [53, 31, 74, 91, 81]]
        )

    def test_add(self):
        """test the matrix addition method."""
        with self.assertRaises(TypeError):
            HeadingFilter._add(0, 0)

        with self.assertRaises(ValueError):
            HeadingFilter._add(
                [[1, 1, 1]],
                [[1, 1]]
            )

        with self.assertRaises(ValueError):
            HeadingFilter._add(
                [[1, 1]],
                [[1, 1], [1, 1], [1, 1]]
            )

        self.assertEqual(
            HeadingFilter._add(
                [[1, 2]],
                [[3, 0]],
            ),
            [[4, 2]]
        )

        self.assertEqual(
            HeadingFilter._add(
                [[1, 2],
                 [3, 0]],
                [[3, 0],
                 [4, 1]]
            ),
            [[4, 2],
             [7, 1]]
        )

    def test_inverse(self):
        """Tests the matrix inverse method."""
        with self.assertRaises(ValueError):
            HeadingFilter._inverse(
                [[1, 2, 3],
                 [1, 2, 3],
                 [1, 2, 3]]
            )

        def assert_almost_equal(matrix1, matrix2):
            """Matrix version of unittest.assertAlmostEqual."""
            for row1, row2 in zip(matrix1, matrix2):
                for item1, item2 in zip(row1, row2):
                    self.assertAlmostEqual(item1, item2)

        test = [[2, 3],
                [1, 4]]
        identity = [[1, 0],
                    [0, 1]]
        assert_almost_equal(
            HeadingFilter._multiply(
                test,
                HeadingFilter._inverse(test)
            ),
            identity
        )
        assert_almost_equal(
            HeadingFilter._multiply(
                HeadingFilter._inverse(test),
                test
            ),
            identity
        )

    def test_estimate_gps(self):
        """Tests that the estimating of the headings via GPS is sane."""
        # I'm not sure how to independently validate these tests for accuracy.
        # The best I can think of is to do some sanity tests.
        initial_heading = 100.0
        heading_filter = HeadingFilter(initial_heading)

        self.assertEqual(heading_filter.estimated_heading(), initial_heading)

        heading = 200.0
        for _ in range(100):
            heading_filter.update_heading(heading)
        self.assertAlmostEqual(heading_filter.estimated_heading(), heading, 3)

    def test_estimate_turn(self):
        """Tests that the estimating of the headings via turning is sane."""
        # I'm not sure how to independently validate these tests for accuracy.
        # The best I can think of is to do some sanity tests.
        initial_heading = 100.0
        heading_filter = HeadingFilter(initial_heading)

        self.assertEqual(heading_filter.estimated_heading(), initial_heading)

        heading_d_s = 1.0
        measurements = [[0.0,], [heading_d_s,],]  # z
        heading_filter._observer_matrix = [[0, 0], [0, 1]]

        seconds = 50
        for _ in range(seconds):
            heading_filter._update(measurements, 1.0)
        self.assertAlmostEqual(
            heading_filter.estimated_heading(),
            initial_heading + heading_d_s * seconds,
            3
        )

    @unittest.skip('TODO')
    def test_estimate(self):
        """Tests that the estimating of the headings via both is sane."""
        # Scenario: turning with an estimated turn rate for 5 seconds, then
        # driving straight and getting GPS heading readings
        initial_heading = 100.0
        heading_filter = HeadingFilter(initial_heading)

        self.assertEqual(heading_filter.estimated_heading(), initial_heading)

        heading_d_s = 20.0
        measurements = [[0.0,], [heading_d_s,],]  # z
        heading_filter._observer_matrix = [[0, 0], [0, 1]]

        seconds = 50
        for _ in range(seconds):
            heading_filter._update(measurements, 1.0)
        self.assertAlmostEqual(
            heading_filter.estimated_heading(),
            initial_heading + heading_d_s * seconds,
            3
        )
