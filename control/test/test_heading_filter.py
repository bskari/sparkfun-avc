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
        foo = [[2, 3],
               [1, 4]]
        identity = [[1, 0],
                    [0, 1]]
        print(HeadingFilter._inverse(foo))
        self.assertEqual(
            HeadingFilter._multiply(
                foo,
                HeadingFilter._inverse(foo)
            ),
            identity
        )
        self.assertEqual(
            HeadingFilter._multiply(
                HeadingFilter._inverse(foo),
                foo
            ),
            identity
        )
