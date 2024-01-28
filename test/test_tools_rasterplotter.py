import time
import unittest

import numpy as np
from PIL import Image, ImageDraw

from meerk40t.tools.rasterplotter import RasterPlotter


class TestRasterPlotter(unittest.TestCase):
    def test_rasterplotter_largecircle(self):
        """
        Tests the speed of rasterplotter for large circle.

        :return:
        """
        image = Image.new("RGBA", (2560, 2560), "white")
        draw = ImageDraw.Draw(image)
        draw.ellipse((0, 0, 2560, 2560), "black")
        image = image.convert("L")
        img = np.array(image)
        # img = image.load()
        plotter = RasterPlotter(img, 2560, 2560)
        t = time.time()
        i = 0
        for x, y, on in plotter.plot():
            i += 0
        print(i)
        print(f"\nTime taken to finish process {time.time() - t}\n")
