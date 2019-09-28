from __future__ import print_function

import unittest

import svg_parser
from path import *


class TestPath(unittest.TestCase):

    def test_subpaths(self):
        path = Path()
        svg_parser.parse_svg_path(path, "M0,0 50,50 100,100z M0,100 50,50, 100,0")
        for i, p in enumerate(path.as_subpaths()):
            if i == 0:
                self.assertEqual(p.d(), "M 0,0 L 50,50 L 100,100 Z")
            elif i == 1:
                self.assertEqual(p.d(), "M 0,100 L 50,50 L 100,0")
            self.assertLessEqual(i, 1)

    def test_move_quad_smooth(self):
        path = Path()
        path.move((4, 4), (20, 20), (25, 25), 6 + 3j)
        path.quad((20, 33), (100, 100))
        path.smooth_quad((13, 45), (16, 16), (34, 56), "z")
        self.assertEqual(path.d(), "M 4,4 L 20,20 L 25,25 L 6,3 Q 20,33 100,100 T 13,45 T 16,16 T 34,56 T 4,4 Z")

    def test_move_cubic_smooth(self):
        path = Path()
        path.move((4, 4), (20, 20), (25, 25), 6 + 3j)
        path.cubic((20, 33), (25, 25), (100, 100))
        path.smooth_cubic((13, 45), (16, 16), (34, 56), "z")
        self.assertEqual(path.d(), "M 4,4 L 20,20 L 25,25 L 6,3 C 20,33 25,25 100,100 S 13,45 16,16 S 34,56 4,4 Z")

    def test_angle(self):
        self.assertEqual(Angle.degrees(90).as_turns, 0.25)
        self.assertEqual(Angle.degrees(180).as_turns, 0.50)
        self.assertEqual(Angle.degrees(360).as_turns, 1.0)
        self.assertEqual(Angle.degrees(720).as_turns, 2.0)
        self.assertEqual(Angle.radians(tau).as_turns, 1.0)
        self.assertEqual(Angle.radians(tau / 50.0).as_turns, 1.0 / 50.0)
        self.assertEqual(Angle.gradians(100).as_turns, 0.25)
        self.assertEqual(Angle.turns(100).as_turns, 100)
        self.assertEqual(Angle.gradians(100).as_gradians, 100)
        self.assertEqual(Angle.degrees(100).as_degrees, 100)
        self.assertEqual(Angle.radians(100).as_radians, 100)
        self.assertEqual(Angle.parse("90deg").as_radians, tau / 4.0)
        self.assertEqual(Angle.parse("90turn").as_radians, tau * 90)

    def test_transform_translate(self):
        matrix = Matrix()
        path = Path()
        path.move((0, 0), (0, 100), (100, 100), 100 + 0j, "z")
        svg_parser.parse_svg_transform("translate(5,4)", matrix)
        path *= matrix
        self.assertEqual("M 5,4 L 5,104 L 105,104 L 105,4 L 5,4 Z", path.d())

    def test_transform_scale(self):
        matrix = Matrix()
        path = Path()
        path.move((0, 0), (0, 100), (100, 100), 100 + 0j, "z")
        svg_parser.parse_svg_transform("scale(2)", matrix)
        path *= matrix
        self.assertEqual("M 0,0 L 0,200 L 200,200 L 200,0 L 0,0 Z", path.d())

    def test_transform_rotate(self):
        matrix = Matrix()
        path = Path()
        path.move((0, 0), (0, 100), (100, 100), 100 + 0j, "z")
        svg_parser.parse_svg_transform("rotate(360)", matrix)
        path *= matrix
        self.assertAlmostEqual(path[0][1].x, 0)
        self.assertAlmostEqual(path[0][1].y, 0)

        self.assertAlmostEqual(path[1][1].x, 0)
        self.assertAlmostEqual(path[1][1].y, 100)

        self.assertAlmostEqual(path[2][1].x, 100)
        self.assertAlmostEqual(path[2][1].y, 100)
        self.assertAlmostEqual(path[3][1].x, 100)
        self.assertAlmostEqual(path[3][1].y, 0)
        self.assertAlmostEqual(path[4][1].x, 0)
        self.assertAlmostEqual(path[4][1].y, 0)

    def test_transform_value(self):
        matrix = Matrix()
        path = Path()
        path.move((0, 0), (0, 100), (100, 100), 100 + 0j, "z")
        svg_parser.parse_svg_transform("rotate(360,50,50)", matrix)
        path *= matrix
        self.assertAlmostEqual(path[0][1].x, 0)
        self.assertAlmostEqual(path[0][1].y, 0)

        self.assertAlmostEqual(path[1][1].x, 0)
        self.assertAlmostEqual(path[1][1].y, 100)

        self.assertAlmostEqual(path[2][1].x, 100)
        self.assertAlmostEqual(path[2][1].y, 100)
        self.assertAlmostEqual(path[3][1].x, 100)
        self.assertAlmostEqual(path[3][1].y, 0)
        self.assertAlmostEqual(path[4][1].x, 0)
        self.assertAlmostEqual(path[4][1].y, 0)

    def test_transform_skewx(self):
        matrix = Matrix()
        path = Path()
        path.move((0, 0), (0, 100), (100, 100), 100 + 0j, "z")
        svg_parser.parse_svg_transform("skewX(10,50,50)", matrix)
        path *= matrix
        self.assertEqual("M -8.81635,0 L 8.81635,100 L 108.816,100 L 91.1837,0 L -8.81635,0 Z", path.d())

    def test_transform_skewy(self):
        matrix = Matrix()
        path = Path()
        path.move((0, 0), (0, 100), (100, 100), 100 + 0j, "z")
        svg_parser.parse_svg_transform("skewY(10, 50,50)", matrix)
        path *= matrix
        print(path.d())
        self.assertEqual("M 0,-8.81635 L 0,91.1837 L 100,108.816 L 100,8.81635 L 0,-8.81635 Z", path.d())

    def test_matrix_repr_rotate(self):
        """
        [a c e]
        [b d f]
        """
        v = "Matrix(%3f, %3f, %3f, %3f, %3f, %3f)" % (0, 1, -1, 0, 0, 0)
        self.assertEqual(v, repr(Matrix.rotate(radians(90))))

    def test_matrix_repr_scale(self):
        """
        [a c e]
        [b d f]
        """
        v = "Matrix(%3f, %3f, %3f, %3f, %3f, %3f)" % (2, 0, 0, 2, 0, 0)
        self.assertEqual(v, repr(Matrix.scale(2)))

    def test_matrix_repr_hflip(self):
        """
        [a c e]
        [b d f]
        """
        v = "Matrix(%3f, %3f, %3f, %3f, %3f, %3f)" % (-1, 0, 0, 1, 0, 0)
        self.assertEqual(v, repr(Matrix.scale(-1, 1)))

    def test_matrix_repr_vflip(self):
        """
        [a c e]
        [b d f]
        """
        v = "Matrix(%3f, %3f, %3f, %3f, %3f, %3f)" % (1, 0, 0, -1, 0, 0)
        self.assertEqual(v, repr(Matrix.scale(1, -1)))

    def test_matrix_repr_post_cat(self):
        """
        [a c e]
        [b d f]
        """
        v = "Matrix(%3f, %3f, %3f, %3f, %3f, %3f)" % (2, 0, 0, 2, -20, -20)
        m = Matrix.scale(2)
        m.post_cat(Matrix.translate(-20, -20))
        self.assertEqual(v, repr(m))

    def test_matrix_repr_pre_cat(self):
        """
        [a c e]
        [b d f]
        """
        v = "Matrix(%3f, %3f, %3f, %3f, %3f, %3f)" % (2, 0, 0, 2, -20, -20)
        m = Matrix.translate(-20, -20)
        m.pre_cat(Matrix.scale(2))
        self.assertEqual(v, repr(m))

    def test_matrix(self):
        matrix = Matrix()
        matrix.post_rotate(radians(90), 100, 100)
        p = matrix.point_in_matrix_space((50, 50))
        self.assertAlmostEqual(p[0], 150)
        self.assertAlmostEqual(p[1], 50)

    def test_matrix_2(self):
        matrix = Matrix()
        matrix.post_scale(2, 2, 50, 50)

        p = matrix.point_in_matrix_space((50, 50))
        self.assertAlmostEqual(p[0], 50)
        self.assertAlmostEqual(p[1], 50)

        p = matrix.point_in_matrix_space((25, 25))
        self.assertAlmostEqual(p[0], 0)
        self.assertAlmostEqual(p[1], 0)

        matrix.post_rotate(radians(45), 50, 50)
        p = matrix.point_in_matrix_space((25, 25))
        self.assertAlmostEqual(p[0], 50)

    def test_matrix_cat_identity(self):
        identity = Matrix()
        from random import random
        for i in range(50):
            q = Matrix(random(), random(), random(), random(), random(), random())
            p = copy(q)
            q.post_cat(identity)
            self.assertEqual(q, p)

    def test_matrix_3(self):
        matrix = Matrix()
        matrix.post_scale(0.5, 0.5)
        p = matrix.point_in_matrix_space((100, 100))
        self.assertAlmostEqual(p[0], 50)
        self.assertAlmostEqual(p[1], 50)

    def test_matrix_3_2(self):
        matrix = Matrix()
        matrix.post_scale(2, 2, 100, 100)
        p = matrix.point_in_matrix_space((50, 50))
        self.assertAlmostEqual(p[0], 0)
        self.assertAlmostEqual(p[1], 0)

    def test_convex_hull(self):
        pts = (3, 4), (4, 6), (18, -2), (9, 0)
        hull = [e for e in Point.convex_hull(pts)]
        self.assertEqual([(3, 4), (9, 0), (18, -2), (4, 6)], hull)

        # bounding box and a bunch of random numbers that must be inside.
        pts = [(100, 100), (100, -100), (-100, -100), (-100, 100)]
        from random import randint
        for i in range(50):
            pts.append((randint(-99, 99), randint(-99, 99)))
        hull = [e for e in Point.convex_hull(pts)]
        for p in hull:
            self.assertEqual(abs(p[0]), 100)
            self.assertEqual(abs(p[1]), 100)
