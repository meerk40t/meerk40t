import unittest
from test import bootstrap

from meerk40t.fill.fills import eulerian_fill, scanline_fill
from meerk40t.svgelements import Matrix


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
            complex(w * 0.05, h * 0.05),
            complex(w * 0.95, h * 0.05),
            complex(w * 0.95, h * 0.95),
            complex(w * 0.05, h * 0.95),
            complex(w * 0.05, h * 0.05),
            None,
            complex(w * 0.25, h * 0.25),
            complex(w * 0.75, h * 0.25),
            complex(w * 0.75, h * 0.75),
            complex(w * 0.25, h * 0.75),
            complex(w * 0.25, h * 0.25),
        )

        fill = list(eulerian_fill(settings={}, outlines=paths, matrix=None))
        self.assertEqual(len(fill), 13)
        for x, y in fill:
            self.assertIn(x, (500, 2500, 7500, 9500))

    def test_fill_euler_scale(self):
        w = 1000
        h = 1000
        paths = (
            complex(w * 0.05, h * 0.05),
            complex(w * 0.95, h * 0.05),
            complex(w * 0.95, h * 0.95),
            complex(w * 0.05, h * 0.95),
            complex(w * 0.05, h * 0.05),
            None,
            complex(w * 0.25, h * 0.25),
            complex(w * 0.75, h * 0.25),
            complex(w * 0.75, h * 0.75),
            complex(w * 0.25, h * 0.75),
            complex(w * 0.25, h * 0.25),
        )
        matrix = Matrix.scale(0.005)
        fill = list(eulerian_fill(settings={}, outlines=paths, matrix=matrix))
        self.assertEqual(len(fill), 327)
        for x, y in fill:
            self.assertIn(x, (50, 250, 750, 950))

        # draw(fill, w, h)

    def test_fill_hatch(self):
        """
        Tests hatch generation by manually executing the regular planning steps.
        """
        kernel = bootstrap.bootstrap()
        try:
            kernel.console("rect 0 0 1in 1in\n")
            kernel.console("operation* delete\n")
            kernel.console("hatch\n")
            hatch_op = list(kernel.elements.ops())[0]
            rect = list(kernel.elements.elems())[0]

            # Add rect refences into hatch.
            hatch_op.children[0].add_reference(rect)

            hatch_copy = hatch_op.copy_with_reified_tree()

            hatch_effect = hatch_copy.children[0]
            shape = hatch_effect.as_geometry()
            self.assertEqual(len(shape), 50)
            print(shape)
        finally:
            kernel()

    def test_fill_hatch_2rect(self):
        """
        Test the hatch with manual steps, counting lines in two rectangles.
        """

        kernel = bootstrap.bootstrap()
        try:
            kernel.console("rect 0 0 1in 1in\n")
            kernel.console("rect 3in 0 1in 1in\n")
            kernel.console("operation* delete\n")
            kernel.console("hatch\n")

            ops = list(kernel.elements.ops())
            hatch = ops[0]
            hatch_effect = hatch.children[0]
            rect0 = list(kernel.elements.elems())[0]
            hatch_effect.add_reference(rect0)
            rect1 = list(kernel.elements.elems())[1]
            hatch_effect.add_reference(rect1)

            hatch_copy = hatch.copy_with_reified_tree()

            hatch_effect = hatch_copy.children[0]
            shape0 = hatch_effect.as_geometry()
            self.assertEqual(len(shape0), 100)
        finally:
            kernel()

    def test_fill_scanline(self):
        w = 10000
        h = 10000
        paths = (
            complex(w * 0.05, h * 0.05),
            complex(w * 0.95, h * 0.05),
            complex(w * 0.95, h * 0.95),
            complex(w * 0.05, h * 0.95),
            complex(w * 0.05, h * 0.05),
            None,
            complex(w * 0.25, h * 0.25),
            complex(w * 0.75, h * 0.25),
            complex(w * 0.75, h * 0.75),
            complex(w * 0.25, h * 0.75),
            complex(w * 0.25, h * 0.25),
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
            kernel()
