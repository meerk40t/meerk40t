import time
import unittest

import numpy as np
from PIL import Image, ImageDraw

from meerk40t.tools.rasterplotter import RasterPlotter


class TestRasterPlotter(unittest.TestCase):
    def _test_rasterplotter(self, image, testcase: str):
        image = image.convert("L")
        width = image.width
        height = image.height
        img = image.load()
        plotter = RasterPlotter(img, width, height)
        t = time.time()
        i = 0
        ipos = plotter.initial_position_in_scene()
        lpos = plotter.final_position_in_scene()
        lastx, lasty = ipos
        pixels = 0
        for x, y, on in plotter.plot():
            i += 1
            if on:
                pixels += (abs(x - lastx) + 1) * (abs(y - lasty) + 1)
            lastx, lasty = x, y
        print(
            f"\n{testcase} found: {i} lines, {pixels} pixels, ranging from ({ipos[0]}, {ipos[1]}) to ({lpos[0]}, {lpos[1]})"
        )
        print(f"Time taken to finish process {time.time() - t:.3f}s\n")

    def test_onepixel_black_image(self):
        """
        Tests the speed of rasterplotter for a one pixel image.

        :return:
        """
        image = Image.new("RGBA", (1, 1), "black")  # This is an empty image
        self._test_rasterplotter(image, "One pixel empty image")

    def test_onepixel_white_image(self):
        """
        Tests the speed of rasterplotter for a one pixel image.

        :return:
        """
        image = Image.new("RGBA", (1, 1), "white")  # This is a one-pixel image
        self._test_rasterplotter(image, "One pixel full image")

    def test_line_image(self):
        """
        Tests the speed of rasterplotter for a one pixel image.

        :return:
        """
        image = Image.new("RGBA", (10, 1), "black")
        draw = ImageDraw.Draw(image)
        draw.line((1, 0, 8, 0), "white")

        self._test_rasterplotter(image, "8 pixel line")

    def test_rasterplotter_largecircle(self):
        """
        Tests the speed of rasterplotter for large circle.

        :return:
        """
        image = Image.new("RGBA", (2560, 2560), "white")
        draw = ImageDraw.Draw(image)
        draw.ellipse((0, 0, 2560, 2560), "black")
        self._test_rasterplotter(image, "Large ellipse")
