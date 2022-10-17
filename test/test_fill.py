import unittest
from copy import copy

from meerk40t.core.cutplan import CutPlan
from test import bootstrap

from meerk40t.fill.fills import eulerian_fill, scanline_fill
from meerk40t.svgelements import Matrix, Rect


def draw(fill, w, h, filename="test.png"):
    from PIL import Image, ImageDraw

    im = Image.new("RGBA", (w, h), "white")
    draw = ImageDraw.Draw(im)
    last_x = None
    last_y = None
    for x, y in fill:
        if last_x is not None:
            draw.line((last_x, last_y, x, y), fill="black")
        last_x, last_y = x, y
    im.save(filename)


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

        fill = list(eulerian_fill(settings={}, outlines=paths, matrix=None))
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
        fill = list(eulerian_fill(settings={}, outlines=paths, matrix=matrix))
        self.assertEqual(len(fill), 327)
        for x, y in fill:
            self.assertIn(x, (50, 250, 750, 950))

        # draw(fill, w, h)

    def test_fill_hatch(self):
        kernel = bootstrap.bootstrap()
        try:
            kernel.console("operation* delete\n")
            kernel.console("rect 0 0 1in 1in\n")
            kernel.console("hatch\n")
            hatch = list(kernel.elements.ops())[0]
            rect = list(kernel.elements.elems())[0]
            hatch.hatch_type = "eulerian"
            hatch.add_node(copy(rect))
            c = CutPlan("q", kernel.planner)
            # kernel.console("tree list\n")
            hatch.preprocess(kernel.root, Matrix(), c)
            c.execute()
            # kernel.console("tree list\n")
            polyline_node = hatch.children[0]
            shape = polyline_node.shape
            self.assertEqual(len(shape), 77)
            print(shape)
        finally:
            kernel.shutdown()

    def test_fill_hatch2(self):
        kernel = bootstrap.bootstrap()
        try:
            kernel.console("operation* delete\n")
            kernel.console("rect 0 0 1in 1in\n")
            kernel.console("rect 3in 0 1in 1in\n")
            kernel.console("hatch\n")
            hatch = list(kernel.elements.ops())[0]
            hatch.hatch_type = "eulerian"
            rect0 = list(kernel.elements.elems())[0]
            hatch.add_node(copy(rect0))
            rect1 = list(kernel.elements.elems())[1]
            hatch.add_node(copy(rect1))
            commands = list()
            # kernel.console("tree list\n")
            c = CutPlan("q", kernel.planner)
            hatch.preprocess(kernel.root, Matrix(), c)
            c.execute()
            # kernel.console("tree list\n")
            polyline_node0 = hatch.children[0]
            shape0 = polyline_node0.shape
            self.assertEqual(len(shape0), 77)
            # print(shape0)

            polyline_node1 = hatch.children[1]
            shape1 = polyline_node1.shape
            self.assertEqual(len(shape1), 50)
            # print(shape1)
        finally:
            kernel.shutdown()

    def test_fill_scanline(self):
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

        fill = list(scanline_fill(settings={}, outlines=paths, matrix=None))
        for p in fill:
            if p is None:
                continue
            x, y = p
            self.assertIn(x, (500, 2500, 7500, 9500))

    def test_fill_kernel_registered(self):
        kernel = bootstrap.bootstrap()
        try:
            eulerian_fill_k = kernel.lookup("hatch/eulerian")
            self.assertIs(eulerian_fill_k, eulerian_fill)
        finally:
            kernel.shutdown()
