import unittest
from copy import copy

from meerk40t.fill.fills import eulerian_fill, scanline_fill
from meerk40t.numpath import Numpath
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

