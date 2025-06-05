import time
import unittest

from copy import copy
from PIL import Image, ImageDraw

from meerk40t.constants import (
    RASTER_B2T,
    RASTER_CROSSOVER,
    RASTER_GREEDY_H,
    RASTER_GREEDY_V,
    RASTER_HATCH,
    RASTER_L2R,
    RASTER_R2L,
    RASTER_SPIRAL,
    RASTER_T2B,
)
from meerk40t.tools.rasterplotter import RasterPlotter


class TestRasterPlotter(unittest.TestCase):
    def _test_rasterplotter(
        self, 
        image, 
        testcase: str="", 
        method:int=0, 
        horizontal:bool=True,
        bidirectional:bool=False,
        sx:bool=True,
        sy:bool=True,
    ):
        image = image.convert("L")
        width = image.width
        height = image.height
        img = image.load()
        parameters = {
            # Provide an override for the minimumx / minimumy / horizontal / bidirectional
            RASTER_T2B: (None, True, True, None),  # top to bottom
            RASTER_B2T: (None, False, True, None),  # bottom to top
            RASTER_R2L: (False, None, False, None),  # right to left
            RASTER_L2R: (True, None, False, None),  # left to right
            RASTER_HATCH: (None, None, None, None),  # crossraster (one of the two)
            RASTER_GREEDY_H: (None, None, None, True),  # greedy neighbour horizontal
            RASTER_GREEDY_V: (None, None, None, True),  # greedy neighbour
            RASTER_CROSSOVER: (None, None, None, True),  # true crossover
        }
        def_x, def_y, def_hor, def_bidir = parameters.get(
            method, (None, None, None, None)
        )
        start_minimum_x = def_x if sx is None else sx
        start_minimum_y = def_y if sy is None else sy
        horizontal = horizontal if def_hor is None else def_hor
        bidirectional = bidirectional if def_bidir is None else def_bidir
        plotter = RasterPlotter(
            img, width, height, 
            direction=method, 
            bidirectional=bidirectional,
            start_minimum_x=start_minimum_x,
            start_minimum_y=start_minimum_y,
        )
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
            f"\n{testcase} (horiz={horizontal}, bidir={bidirectional}) found: {i} lines, {pixels} pixels, ranging from ({ipos[0]}, {ipos[1]}) to ({lpos[0]}, {lpos[1]})"
        )
        print(f"Time taken to finish process {time.time() - t:.3f}s\n")

    def test_onepixel_black_image(self):
        """
        Tests the speed of rasterplotter for a one pixel image.

        :return:
        """
        image = Image.new("RGBA", (1, 1), "black")  # This is an empty image
        cases = [
            ("One pixel empty image - Top to Bottom", RASTER_T2B, False, False),
            ("One pixel empty image - Bottom to Top", RASTER_B2T, False, False),
            ("One pixel empty image - Left to Right", RASTER_L2R, True,  False),
            ("One pixel empty image - Right to Left", RASTER_R2L, True, False ),
            ("One pixel empty image - Top to Bottom", RASTER_T2B, False, True),
            ("One pixel empty image - Bottom to Top", RASTER_B2T, False, True),
            ("One pixel empty image - Left to Right", RASTER_L2R, True,  True),
            ("One pixel empty image - Right to Left", RASTER_R2L, True, True ),
        ]
        for msg, method, horizontal, bidir in cases:
            img = copy(image)
            self._test_rasterplotter(img, msg, method=method, horizontal=horizontal, bidirectional=bidir)   

    def test_onepixel_white_image(self):
        """
        Tests the speed of rasterplotter for a one pixel image.

        :return:
        """
        image = Image.new("RGBA", (1, 1), "white")  # This is a one-pixel image
        cases = [
            ("One pixel empty image - Top to Bottom", RASTER_T2B, False, False),
            ("One pixel full image - Bottom to Top", RASTER_B2T, False, False),
            ("One pixel full image - Left to Right", RASTER_L2R, True, False ),
            ("One pixel full image - Right to Left", RASTER_R2L, True, False ),
            ("One pixel empty image - Top to Bottom", RASTER_T2B, False,True),
            ("One pixel full image - Bottom to Top", RASTER_B2T, False,True),
            ("One pixel full image - Left to Right", RASTER_L2R, True, True ),
            ("One pixel full image - Right to Left", RASTER_R2L, True, True ),
        ]
        for msg, method, horizontal, bidir in cases:
            img = copy(image)
            self._test_rasterplotter(img, msg, method=method, horizontal=horizontal, bidirectional=bidir)

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
