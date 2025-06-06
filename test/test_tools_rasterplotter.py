import time
import unittest

# from copy import copy
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
        msgstr: str,
        image: Image.Image,
    ):
        t = time.time()
        method_names = {
            RASTER_T2B: "Top to Bottom",
            RASTER_B2T: "Bottom to Top",
            RASTER_L2R: "Left to Right",
            RASTER_R2L: "Right to Left",
            RASTER_HATCH: "Hatching",
            RASTER_GREEDY_H: "Greedy Horizontal",
            RASTER_GREEDY_V: "Greedy Vertical",
            RASTER_CROSSOVER: "Crossover",
            RASTER_SPIRAL: "Spiral",
        }
        cases = []
        for case_method in method_names:
            for case_bidir in (False, True):
                for case_horizontal in (False, True):
                    for case_edge in (False, True):
                        testcase = method_names[case_method]
                        cases.append(
                            (
                                testcase,
                                case_method,
                                case_horizontal,
                                case_bidir,
                                case_edge,
                            )
                        )
        image = image.convert("L")
        width = image.width
        height = image.height
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
        special_cases = [
            {},  # default case
            {"legacy": True},  # legacy case for lihuiyu/moshi
        ]
        casecount = 0
        for special_case in special_cases:
            for case, method, horizontal, bidirectional, edge in cases:
                img = image.load()
                def_x, def_y, def_hor, def_bidir = parameters.get(
                    method, (None, None, None, None)
                )
                start_minimum_x = edge if def_x is None else def_x
                start_minimum_y = edge if def_y is None else def_y
                horizontal = horizontal if def_hor is None else def_hor
                bidirectional = bidirectional if def_bidir is None else def_bidir
                plotter = RasterPlotter(
                    img,
                    width,
                    height,
                    direction=method,
                    bidirectional=bidirectional,
                    start_minimum_x=start_minimum_x,
                    start_minimum_y=start_minimum_y,
                    special=special_case,
                )
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
                    f"{msgstr}.{case} (hor={horizontal}, bidir={bidirectional}, special={special_case}) found: {i} lines, {pixels} px, from ({ipos[0]}, {ipos[1]}) to ({lpos[0]}, {lpos[1]})"
                )
                casecount += 1
        print(
            f"Time taken to finish process for {msgstr} and {casecount} cases: {time.time() - t:.3f}s\n"
        )

    def test_onepixel_black_image(self):
        """
        Tests the speed of rasterplotter for a one pixel image.

        :return:
        """
        image = Image.new("RGBA", (1, 1), "black")  # This is an empty image
        self._test_rasterplotter("Empty 1x1", image)

    def test_onepixel_white_image(self):
        """
        Tests the speed of rasterplotter for a one pixel image.

        :return:
        """
        image = Image.new("RGBA", (1, 1), "white")  # This is a one-pixel image
        self._test_rasterplotter("Black 1x1", image)

    def test_line_image(self):
        """
        Tests the speed of rasterplotter for a one pixel image.

        :return:
        """
        image = Image.new("RGBA", (10, 1), "black")
        draw = ImageDraw.Draw(image)
        draw.line((1, 0, 8, 0), "white")
        self._test_rasterplotter("8 pixel line", image)

    def test_rasterplotter_largecircle(self):
        """
        Tests the speed of rasterplotter for large circle.

        :return:
        """
        width = 2560
        height = 2560
        image = Image.new("RGBA", (width, height), "white")
        draw = ImageDraw.Draw(image)
        draw.ellipse((0, 0, width, height), "black")
        testcase = "Large circle"
        horizontal = True
        method = RASTER_L2R
        bidirectional = False
        start_minimum_x = True
        start_minimum_y = True
        plotter = RasterPlotter(
            image.load(),
            width,
            height,
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
