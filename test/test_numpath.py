import unittest
from copy import copy
from math import tau

import numpy as np

from meerk40t.fill.fills import eulerian_fill, scanline_fill
from meerk40t.numpath import Numpath, TYPE_CLOSE
from meerk40t.svgelements import Matrix, Rect
from test import bootstrap


def draw(segments, w, h, filename="test.png"):
    from PIL import Image, ImageDraw
    im = Image.new('RGBA', (w, h), "white")
    draw = ImageDraw.Draw(im)
    for segment in segments:
        f = segment[0]
        t = segment[-1]
        draw.line(((f.real, f.imag), (t.real, t.imag)), fill="black")
    im.save(filename)


class TestNumpath(unittest.TestCase):
    """Tests the functionality of numpath class."""

    def test_numpath_translate_scale(self):
        w = 10000
        h = 10000
        numpath = Numpath()
        numpath.add_polyline((
                complex(0.05, 0.05),
                complex(0.95, 0.05),
                complex(0.95, 0.95),
                complex(0.05, 0.95),
                complex(0.05, 0.05),
        ))
        numpath.add_polyline((
                complex(0.25, 0.25),
                complex(0.75, 0.25),
                complex(0.75, 0.75),
                complex(0.25, 0.75),
                complex(0.25, 0.25),
            ))
        numpath.uscale(w)

        numpath2 = Numpath()
        numpath2.add_polyline((
                complex(w * 0.05, h * 0.05),
                complex(w * 0.95, h * 0.05),
                complex(w * 0.95, h * 0.95),
                complex(w * 0.05, h * 0.95),
                complex(w * 0.05, h * 0.05),
        ))
        numpath2.add_polyline((
                complex(w * 0.25, h * 0.25),
                complex(w * 0.75, h * 0.25),
                complex(w * 0.75, h * 0.75),
                complex(w * 0.25, h * 0.75),
                complex(w * 0.25, h * 0.25),
            ))
        self.assertTrue(np.all(numpath.segments == numpath2.segments))
        numpath.translate(3,3)
        self.assertFalse(np.all(numpath.segments == numpath2.segments))
        numpath.translate(-3,-3)
        self.assertTrue(np.all(numpath.segments == numpath2.segments))

    def test_numpath_bbox(self):
        w = 10000
        numpath = Numpath()
        numpath.add_polyline((
                complex(0.05, 0.05),
                complex(0.95, 0.05),
                complex(0.95, 0.95),
                complex(0.05, 0.95),
                complex(0.05, 0.05),
        ))
        numpath.add_polyline((
                complex(0.25, 0.25),
                complex(0.75, 0.25),
                complex(0.75, 0.75),
                complex(0.25, 0.75),
                complex(0.25, 0.25),
            ))
        numpath.uscale(w)
        self.assertEqual(numpath.bbox(), (500.0, 500.0, 9500.0, 9500.0))
        numpath.rotate(tau * .25)
        for x, y in zip(numpath.bbox(), (-9500.0, 500.00000000000057, -500.0, 9500.0)):
            self.assertAlmostEqual(x, y)

    def test_numpath_transform(self):
        numpath = Numpath()
        numpath.add_polyline((
            complex(0.05, 0.05),
            complex(0.95, 0.05),
            complex(0.95, 0.95),
            complex(0.05, 0.95),
            complex(0.05, 0.05),
        ))
        numpath.add_polyline((
            complex(0.25, 0.25),
            complex(0.75, 0.25),
            complex(0.75, 0.75),
            complex(0.25, 0.75),
            complex(0.25, 0.25),
        ))
        numpath.uscale(10000)
        c = copy(numpath)
        numpath.rotate(tau * .25)
        c.transform(Matrix("rotate(.25turn)"))
        t = numpath.segments == c.segments
        self.assertTrue(np.all(t))

    def test_numpath_close(self):
        numpath = Numpath()
        numpath.add_polyline((
            complex(0.05, 0.05),
            complex(0.95, 0.05),
            complex(0.95, 0.95),
            complex(0.05, 0.95),
            complex(0.05, 0.05),
        ))
        numpath.add_close()
        numpath.add_polyline((
            complex(0.25, 0.25),
            complex(0.75, 0.25),
            complex(0.75, 0.75),
            complex(0.25, 0.75),
            complex(0.25, 0.25),
        ))
        numpath.uscale(10000)
        numpath.rotate(tau * .25)
        subpaths = list(numpath.as_subpaths())
        self.assertEqual(len(subpaths), 2)
        self.assertEqual(len(subpaths[0]), 5)
        self.assertEqual(int(subpaths[0][-1][2]), TYPE_CLOSE)
        self.assertEqual(len(subpaths[1]), 4)

    def test_numpath_scanline(self):
        w = 10000
        h = 10000
        paths = (
            (
                (w * 0.05, h * 0.05),
                (w * 0.95, h * 0.05),
                (w * 0.95, h * 0.95),
                (w * 0.05, h * 0.95),
                (w * 0.05, h * 0.05),
            ),
            (
                (w * 0.25, h * 0.25),
                (w * 0.75, h * 0.25),
                (w * 0.75, h * 0.75),
                (w * 0.25, h * 0.75),
                (w * 0.25, h * 0.25),
            ),
        )

        fill = list(scanline_fill(settings={"hatch_distance": "0.02mm"}, outlines=paths, matrix=None))
        path = Numpath()
        last_x = None
        last_y = None
        for p in fill:
            if p is None:
                last_x = None
                last_y = None
                continue
            x, y = p
            if last_x is not None:
                path.add_line(complex(last_x, last_y), complex(x,y))
            last_x, last_y = x, y
        p = copy(path)
        self.assertNotEqual(path, p)
        #
        # print(path.segments)
        # print("Original segments...")
        # print(p.travel_distance())
        # p.two_opt_distance()
        # print(p.travel_distance())
        # print(p.segments)
        # draw(p.segments, w, h)

