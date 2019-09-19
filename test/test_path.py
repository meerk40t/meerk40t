from __future__ import print_function

import unittest

import svg_parser
from path import *


class TestPath(unittest.TestCase):

    def test_subpaths(self):
        object_path = Path()
        svg_parser.parse_svg_path(object_path, "M0,0 50,50 100,100z M0,100 50,50, 100,0")
        for i, p in enumerate(object_path.as_subpaths()):
            if i == 0:
                self.assertEqual(p.d(), "M 0,0 L 50,50 L 100,100 Z")
            elif i == 1:
                self.assertEqual(p.d(), "M 0,100 L 50,50 L 100,0")
            self.assertLessEqual(i, 1)
