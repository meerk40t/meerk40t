from __future__ import division

import unittest

from path import *
from svg_parser import parse_svg_path


def parse_path(pathd):
    parser = Path()
    parse_svg_path(parser, pathd)
    return parser


paths = [
    'M 100,100 L 300,100 L 200,300 Z',
    'M 0,0 L 50,20 M 100,100 L 300,100 L 200,300 Z',
    'M 100,100 L 200,200',
    'M 100,200 L 200,100 L -100,-200',
    'M 100,200 C 100,100 250,100 250,200 S 400,300 400,200',
    'M 100,200 C 100,100 400,100 400,200',
    'M 100,500 C 25,400 475,400 400,500',
    'M 100,800 C 175,700 325,700 400,800',
    'M 600,200 C 675,100 975,100 900,200',
    'M 600,500 C 600,350 900,650 900,500',
    'M 600,800 C 625,700 725,700 750,800 S 875,900 900,800',
    'M 200,300 Q 400,50 600,300 T 1000,300',
    'M -3.4E+38,3.4E+38 L -3.4E-38,3.4E-38',
    'M 0,0 L 50,20 M 50,20 L 200,100 Z',
    'M 600,350 L 650,325 A 25,25 -30 0,1 700,300 L 750,275',
]


class TestGeneration(unittest.TestCase):
    """Examples from the SVG spec"""

    def test_svg_examples(self):
        for path in paths[15:]:
            self.assertEqual(parse_path(path).d(), path)

    def test_svg_example0(self):
        path = paths[0]
        self.assertEqual(parse_path(path).d(), path)

    def test_svg_example1(self):
        path = paths[1]
        self.assertEqual(parse_path(path).d(), path)

    def test_svg_example2(self):
        path = paths[2]
        self.assertEqual(parse_path(path).d(), path)

    def test_svg_example3(self):
        path = paths[3]
        self.assertEqual(parse_path(path).d(), path)

    def test_svg_example4(self):
        path = paths[4]
        self.assertEqual(parse_path(path).d(), path)

    def test_svg_example5(self):
        path = paths[5]
        self.assertEqual(parse_path(path).d(), path)

    def test_svg_example6(self):
        path = paths[6]
        self.assertEqual(parse_path(path).d(), path)

    def test_svg_example7(self):
        path = paths[7]
        self.assertEqual(parse_path(path).d(), path)

    def test_svg_example8(self):
        path = paths[8]
        self.assertEqual(parse_path(path).d(), path)

    def test_svg_example9(self):
        path = paths[9]
        self.assertEqual(parse_path(path).d(), path)

    def test_svg_example10(self):
        path = paths[10]
        self.assertEqual(parse_path(path).d(), path)

    def test_svg_example11(self):
        path = paths[11]
        self.assertEqual(parse_path(path).d(), path)

    def test_svg_example12(self):
        path = paths[12]
        self.assertEqual(parse_path(path).d(), path)

    def test_svg_example13(self):
        path = paths[13]
        self.assertEqual(parse_path(path).d(), path)

    def test_svg_example14(self):
        path = paths[14]
        self.assertEqual(parse_path(path).d(), path)