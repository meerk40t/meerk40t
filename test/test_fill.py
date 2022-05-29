import unittest

from meerk40t.fill.fills import eulerian_fill
from meerk40t.svgelements import Matrix


class TestFill(unittest.TestCase):
    """Tests the functionality of fills."""

    def test_fill_euler(self):
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

        fills = list(eulerian_fill(settings={}, outlines=paths, matrix=None, penbox_pass=None))
        self.assertEqual(len(fills), 1)
        settings, fill = fills[0]
        self.assertEqual(len(fill), 13)
        for x, y in fill:
            self.assertIn(x, (500, 2500, 7500, 9500))

    def test_fill_euler_scale(self):
        w = 1000
        h = 1000
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
        matrix = Matrix.scale(0.005)
        fills = list(eulerian_fill(settings={}, outlines=paths, matrix=matrix, penbox_pass=None))
        self.assertEqual(len(fills), 1)
        settings, fill = fills[0]
        self.assertEqual(len(fill), 327)
        for x, y in fill:
            self.assertIn(x, (50, 250, 750, 950))

        # from PIL import Image, ImageDraw
        # im = Image.new('RGBA', (w, h), "white")
        # draw = ImageDraw.Draw(im)
        # last_x = None
        # last_y = None
        # for x, y in fill:
        #     if last_x is not None:
        #         draw.line((last_x, last_y, x, y), fill="black")
        #     last_x, last_y = x, y
        # im.save("test.png")
