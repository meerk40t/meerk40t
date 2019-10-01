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
