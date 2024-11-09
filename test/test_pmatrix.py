import unittest

from meerk40t.core.units import Angle
from meerk40t.tools.pmatrix import PMatrix


class TestPmatrix(unittest.TestCase):
    """These tests ensure the basic functions of the Geomstr elements."""

    def test_pmatrix_map(self):
        p = PMatrix(0, 0, 0, 0, 0, 0, 0, 0, 0)

    def test_matrix_map_identity(self):
        """
        Maps one perspective the same perspective.
        """
        m1 = PMatrix.map(
            (1, 1),
            (1, -1),
            (-1, -1),
            (-1, 1),
            (1, 1),
            (1, -1),
            (-1, -1),
            (-1, 1),
        )
        self.assertTrue(m1.is_identity())

        m1 = PMatrix.map(
            (101, 101),
            (101, 99),
            (99, 99),
            (99, 101),
            (101, 101),
            (101, 99),
            (99, 99),
            (99, 101),
        )
        self.assertTrue(m1.is_identity())

    def test_matrix_map_scale_half(self):
        m1 = PMatrix.map(
            (2, 2),
            (2, -2),
            (-2, -2),
            (-2, 2),
            (1, 1),
            (1, -1),
            (-1, -1),
            (-1, 1),
        )
        self.assertEqual(m1, PMatrix.scale(0.5))

    def test_matrix_map_translate(self):
        m1 = PMatrix.map(
            (0, 0),
            (0, 1),
            (1, 1),
            (1, 0),
            (100, 100),
            (100, 101),
            (101, 101),
            (101, 100),
        )
        self.assertEqual(m1, PMatrix.translate(100, 100))

    def test_matrix_map_rotate(self):
        m1 = PMatrix.map(
            (0, 0),
            (0, 1),
            (1, 1),
            (1, 0),
            (0, 1),
            (1, 1),
            (1, 0),
            (0, 0),
        )
        m2 = PMatrix.rotate(Angle("-90deg"), 0.5, 0.5)
        self.assertEqual(m1, m2)

    def test_matrix_rotate_non_origin(self):
        rx = 203.2
        ry = 102.2
        m1 = (
            PMatrix.translate(rx, ry)
            @ PMatrix.rotate(Angle("-90deg"))
            @ PMatrix.translate(-rx, -ry)
        )
        m2 = PMatrix.rotate(Angle("-90deg"), rx, ry)
        self.assertEqual(m1, m2)
        pt = m1.point_in_matrix(rx, ry)
        self.assertAlmostEqual(pt, complex(rx, ry))

    def test_matrix_map_translate_scale_y(self):
        m1 = PMatrix.map(
            (0, 0),
            (0, 1),
            (1, 1),
            (1, 0),
            (100, 100),
            (100, 102),
            (101, 102),
            (101, 100),
        )
        self.assertEqual(m1, PMatrix.translate(100, 100) @ PMatrix.scale_y(2))

    def test_matrix_perspective_ccw_unit_square(self):
        """
        This is the unit square ccw. So we mirror it across the x-axis and rotate it back into position.
        """
        m1 = PMatrix.perspective((0, 0), (1, 0), (1, 1), (0, 1))
        m2 = PMatrix.rotate(Angle("-90deg")) @ PMatrix.scale(-1, 1)
        self.assertEqual(m1, m2)

    def test_matrix_perspective_unit_square(self):
        """
        This is the cw unit square, which is our default perspective, meaning we have the identity matrix
        """
        m1 = PMatrix.perspective((0, 0), (0, 1), (1, 1), (1, 0))
        m2 = PMatrix()
        self.assertEqual(m1, m2)
