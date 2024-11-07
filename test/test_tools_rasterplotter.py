import time
import math
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
        image.save("ellipse.png")
        img = np.array(image)
        # img = image.load()
        for algo in ("raster", "floodfill"):
            plotter = RasterPlotter(img, 2560, 2560, algorithm=algo)
            t = time.time()
            steps = 0
            steps_on = 0
            steps_off = 0
            travel_off = 0
            travel_on = 0
            lastx = None
            lasty = None
            for x, y, on in plotter.plot():
                if lastx:
                    delta = math.sqrt((lastx - x)*(lastx - x) + (lasty - y)*(lasty - y))
                else:
                    delta = 0
                if on:
                    steps_on += 1
                    travel_on += delta
                else:
                    steps_off += 1
                    travel_off += delta
                lastx = x
                lasty = y
                steps += 1
            print(f"\nTime taken to finish {algo} process {time.time() - t:.2f}sec")
            print(f"Steps: total: {steps} active: {steps_on}, travel: {steps_off}")
            print(f"Distance: total: {travel_off + travel_on:.0f} active: {travel_on:.0f}, travel: {travel_off:.0f}")
