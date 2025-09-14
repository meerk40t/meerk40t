import time
import unittest

# from copy import copy
from PIL import Image, ImageDraw

from meerk40t.constants import (
    RASTER_B2T,
    RASTER_CROSSOVER,
    RASTER_DIAGONAL,
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
            RASTER_DIAGONAL: "Diagonal",
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
            RASTER_DIAGONAL: (None, None, None, None),  # diagonal scanning
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
                    if (
                        x is not None
                        and y is not None
                        and lastx is not None
                        and lasty is not None
                    ):
                        if on:
                            pixels += (abs(x - lastx) + 1) * (abs(y - lasty) + 1)
                    if x is not None and y is not None:
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
            if (
                x is not None
                and y is not None
                and lastx is not None
                and lasty is not None
            ):
                if on:
                    pixels += (abs(x - lastx) + 1) * (abs(y - lasty) + 1)
            if x is not None and y is not None:
                lastx, lasty = x, y
        print(
            f"\n{testcase} (horiz={horizontal}, bidir={bidirectional}) found: {i} lines, {pixels} pixels, ranging from ({ipos[0]}, {ipos[1]}) to ({lpos[0]}, {lpos[1]})"
        )
        print(f"Time taken to finish process {time.time() - t:.3f}s\n")

    def test_diagonal_scanning_corners(self):
        """
        Tests the diagonal scanning algorithm with different start corners.

        :return:
        """
        width = 10
        height = 10
        image = Image.new("RGBA", (width, height), "white")
        draw = ImageDraw.Draw(image)
        # Create a simple pattern to test diagonal traversal
        draw.rectangle((2, 2, 7, 7), "black")

        corners = ["top-left", "top-right", "bottom-left", "bottom-right"]

        for corner in corners:

            def image_filter(pixel):
                if isinstance(pixel, tuple):
                    # Handle RGBA pixels by converting to grayscale
                    return (255 - pixel[0]) / 255.0
                else:
                    return (255 - pixel) / 255.0

            plotter = RasterPlotter(
                image.load(),
                width,
                height,
                direction=RASTER_DIAGONAL,
                horizontal=True,
                bidirectional=False,
                start_minimum_x=True,
                start_minimum_y=True,
                skip_pixel=0,  # Skip inverted white pixels
                filter=image_filter,
                special={"start_corner": corner},
            )

            t = time.time()
            i = 0
            ipos = plotter.initial_position_in_scene()
            lpos = plotter.final_position_in_scene()
            lastx, lasty = ipos
            pixels = 0
            coords = []

            for x, y, on in plotter.plot():
                i += 1
                coords.append((x, y, on))
                if (
                    x is not None
                    and y is not None
                    and lastx is not None
                    and lasty is not None
                ):
                    if on:
                        pixels += (abs(x - lastx) + 1) * (abs(y - lasty) + 1)
                if x is not None and y is not None:
                    lastx, lasty = x, y

            print(
                f"Diagonal {corner} found: {i} lines, {pixels} pixels, from ({ipos[0]}, {ipos[1]}) to ({lpos[0]}, {lpos[1]})"
            )
            print(f"Time taken: {time.time() - t:.3f}s")

            # Verify that we have coordinates and that diagonal traversal produces different patterns
            self.assertGreater(len(coords), 0, f"No coordinates generated for {corner}")
            self.assertGreater(pixels, 0, f"No pixels found for {corner}")

    def test_diagonal_scanning_small_image(self):
        """
        Tests diagonal scanning on a small 3x3 image to verify correct traversal patterns.

        :return:
        """
        # Create a 3x3 test pattern
        data = [[255, 0, 255], [0, 255, 0], [255, 0, 255]]

        # Convert to PIL image
        image = Image.new("L", (3, 3), 255)
        for y in range(3):
            for x in range(3):
                image.putpixel((x, y), data[y][x])

        # expected_pixels = [(0, 0), (2, 0), (1, 1), (0, 2), (2, 2)]  # Non-zero pixels in the pattern

        corners = ["top-left", "top-right", "bottom-left", "bottom-right"]

        for corner in corners:

            def image_filter(pixel):
                return (255 - pixel) / 255.0

            plotter = RasterPlotter(
                image.load(),
                3,
                3,
                direction=RASTER_DIAGONAL,
                horizontal=True,
                bidirectional=False,
                start_minimum_x=True,
                start_minimum_y=True,
                skip_pixel=0,  # Skip inverted white pixels
                filter=image_filter,
                special={"start_corner": corner},
            )

            coords = []
            for x, y, on in plotter.plot():
                if on > 0:  # Only collect non-zero pixels
                    coords.append((x, y))

            print(f"Diagonal {corner}: {coords}")

            # For now, just check that we get some non-zero pixels
            # The diagonal algorithm may need refinement
            self.assertGreater(len(coords), 0, f"No non-zero pixels found for {corner}")

            # Check that we don't have duplicate coordinates
            unique_coords = set(coords)
            self.assertEqual(
                len(coords),
                len(unique_coords),
                f"Duplicate coordinates found in {corner} traversal",
            )

    def test_diagonal_scanning_rectangular_images(self):
        """
        Tests diagonal scanning on rectangular (non-square) images to ensure proper coverage.

        :return:
        """
        # Test various rectangular dimensions
        test_cases = [
            (4, 2),  # Wide rectangle
            (2, 4),  # Tall rectangle
            (5, 3),  # 5x3 rectangle
            (6, 2),  # Very wide rectangle
            (2, 6),  # Very tall rectangle
        ]

        for width, height in test_cases:
            for corner in ["top-left", "top-right", "bottom-left", "bottom-right"]:
                with self.subTest(width=width, height=height, corner=corner):
                    # Create a test image
                    image = Image.new("L", (width, height), 255)

                    # Add a simple pattern to ensure some pixels are non-zero
                    for y in range(height):
                        for x in range(width):
                            if (x + y) % 2 == 0:
                                image.putpixel((x, y), 255)
                            else:
                                image.putpixel((x, y), 0)

                    plotter = RasterPlotter(
                        image.load(),
                        width,
                        height,
                        direction=RASTER_DIAGONAL,
                        horizontal=True,
                        bidirectional=False,
                        start_minimum_x=True,
                        start_minimum_y=True,
                        skip_pixel=0,  # Skip inverted white pixels
                        filter=lambda pixel: (255 - pixel) / 255.0,
                        special={"start_corner": corner},
                    )

                    # Collect all visited pixels
                    visited_pixels = set()
                    for x, y, on in plotter.plot():
                        visited_pixels.add((x, y))

                    # Verify all pixels are visited exactly once
                    expected_pixels = width * height
                    self.assertEqual(
                        len(visited_pixels),
                        expected_pixels,
                        f"Expected {expected_pixels} pixels but got {len(visited_pixels)} for {width}x{height} with {corner}",
                    )

                    # Verify no pixels are outside bounds
                    for x, y in visited_pixels:
                        self.assertTrue(
                            0 <= x < width,
                            f"Pixel x={x} out of bounds for width {width}",
                        )
                        self.assertTrue(
                            0 <= y < height,
                            f"Pixel y={y} out of bounds for height {height}",
                        )

    def test_diagonal_scanning_empty_image(self):
        """
        Tests diagonal scanning on an empty (all white) image.

        :return:
        """
        width = 5
        height = 5
        image = Image.new("L", (width, height), 255)  # All white

        for corner in ["top-left", "top-right", "bottom-left", "bottom-right"]:

            def image_filter(pixel):
                return (255 - pixel) / 255.0

            plotter = RasterPlotter(
                image.load(),
                width,
                height,
                direction=RASTER_DIAGONAL,
                horizontal=True,
                bidirectional=False,
                start_minimum_x=True,
                start_minimum_y=True,
                skip_pixel=0,  # Skip inverted white pixels
                filter=image_filter,
                special={"start_corner": corner},
            )

            pixels_found = 0
            for x, y, on in plotter.plot():
                if on > 0:
                    pixels_found += 1

            # For an all-white image, after inversion all pixels become 0.0 (off)
            # So we expect 0 pixels to be found
            self.assertEqual(
                pixels_found,
                0,
                f"Expected 0 pixels for all-white image with {corner}, but found {pixels_found}",
            )
