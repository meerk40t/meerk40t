"""
The RasterPlotter is a comprehensive raster plotting system that maps pixel data to various directional
and algorithmic raster methods for laser cutting/engraving applications.

This class supports multiple raster scanning algorithms including:
- Standard rastering (top-to-bottom, bottom-to-top, right-to-left, left-to-right)
- Diagonal scanning with corner-based starting positions and bidirectional support
- Greedy neighbor optimization for path efficiency
- Crossover algorithm for optimized row/column processing
- Spiral scanning from center outward
- Legacy methods for backward compatibility

Key Features:
- Pixel filtering and skip-pixel logic for accurate representation
- Corner-based diagonal scanning (top-left, top-right, bottom-left, bottom-right)
- Bidirectional and unidirectional scanning modes
- Type-safe implementation with None guards for robust operation
- Overlap compensation for laser spot diameter
- Distance tracking for travel and burn calculations
- Debug output and performance monitoring

The X_AXIS / Y_AXIS flag determines whether we raster across the X_AXIS or Y_AXIS. Standard
right-to-left rastering starting at the top edge on the left is the default. This would be
in the upper left hand corner proceeding right, and stepping towards bottom each scanline.

If the X_AXIS is set, the edge being used can be either TOP or BOTTOM. That flag means edge
with X_AXIS rastering. However, in Y_AXIS rastering the start edge can either be right-edge
or left-edge, for this the RIGHT and LEFT flags are used. However, the start point on either
edge can be TOP or BOTTOM if we're starting on a RIGHT or LEFT edge. So those flags mark
that. The same is true for RIGHT or LEFT on a TOP or BOTTOM edge.

The TOP, RIGHT, LEFT, BOTTOM combined give you the starting corner.

The rasters can either be BIDIRECTIONAL or UNIDIRECTIONAL meaning they raster on both swings
or only on forward swing.

Recent enhancements include:
- Fixed pixel processing logic using filtered values instead of raw pixel data
- Improved diagonal scanning with proper corner-based logic and bidirectional alternation
- Added comprehensive None guards to prevent runtime errors in all plotting methods
- Optimized diagonal algorithms using x+y=constant and x-y=constant equations
"""

from math import isinf, sqrt
from time import perf_counter, sleep

import numpy as np

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

METHODS = {
    RASTER_T2B: "Top2Bottom",
    RASTER_B2T: "Bottom2Top",
    RASTER_R2L: "Right2Left",
    RASTER_L2R: "Left2Right",
    RASTER_HATCH: "Hatch",
    RASTER_GREEDY_H: "Greedy Neighbor Hor",
    RASTER_GREEDY_V: "Greedy Neighbor Ver",
    RASTER_CROSSOVER: "Crossover",
    RASTER_SPIRAL: "Spiral",
    RASTER_DIAGONAL: "Diagonal",
}

BLANK = 255


class RasterPlotter:
    """
    A comprehensive raster plotting system for laser cutting/engraving applications.

    This class implements multiple raster scanning algorithms to convert pixel data into
    optimized laser movement paths. It supports various traversal patterns including
    standard rastering, diagonal scanning, greedy neighbor optimization, crossover
    algorithms, and spiral patterns.

    Supported Raster Methods:
    - Standard Rastering: Top-to-bottom, bottom-to-top, right-to-left, left-to-right
    - Diagonal Scanning: Corner-based diagonal traversal with bidirectional alternation
    - Greedy Neighbor: Path optimization using distance-based segment ordering
    - Crossover: Alternating row/column processing for efficiency
    - Spiral: Center-outward spiral pattern
    - Legacy Methods: Backward-compatible implementations for specific controllers

    Key Features:
    - Pixel filtering and skip-pixel logic for accurate representation
    - Corner-based starting positions (top-left, top-right, bottom-left, bottom-right)
    - Bidirectional and unidirectional scanning modes
    - Overlap compensation for laser spot diameter
    - Distance tracking for travel and burn calculations
    - Debug output and performance monitoring
    - Type-safe implementation with None guards

    The class handles coordinate transformations, pixel processing, and path optimization
    to ensure efficient laser movement while maintaining image fidelity.
    """

    def __init__(
        self,
        data,
        width,
        height,
        direction=0,
        horizontal=True,
        start_minimum_y=True,
        start_minimum_x=True,
        bidirectional=True,
        use_integers=True,
        skip_pixel=0,
        overscan=0,
        offset_x=0,
        offset_y=0,
        step_x=1,
        step_y=1,
        filter=None,
        laserspot=0,
        special=None,
    ):
        """
        Initialization for the Raster Plotter function. This should set all the needed parameters for plotting.

        @param data: pixel data accessed through data[x,y] parameters
        @param width: Width of the given data.
        @param height: Height of the given data.
        @param horizontal: Flags for how the pixel traversal should be conducted.
        @param start_minimum_y: Flags for how the pixel traversal should be conducted.
        @param start_minimum_x: Flags for how the pixel traversal should be conducted.
        @param bidirectional: Flags for how the pixel traversal should be conducted.
        @param skip_pixel: Skip pixel. If this value is the pixel value, we skip travel in that direction.
        @param use_integers: return integer values rather than floating point values.
        @param overscan: The extra amount of padding to add to the end scanline.
        @param offset_x: The offset in x of the rastering location. This will be added to x values returned in plot.
        @param offset_y: The offset in y of the rastering location. This will be added to y values returned in plot.
        @param step_x: The amount units per pixel.
        @param step_y: The amount scanline gap.
        @param filter: Pixel filter is called for each pixel to transform or alter it as needed. The actual
                    implementation is agnostic regarding what data is provided. The filter is expected
                    to convert the data[x,y] into some form which will be expressed by plot. Unless skipped as
                    part of the skip pixel.
        @param direction: 0 top 2 bottom, 1 bottom 2 top, 2 right 2 left, 3 left 2 right, 4 greedy path optimisation, 5 crossover
                    a) greedy will keep the main direction, a bit time intensive for larger images
                    b) crossover draws first all majority lines, then all majority columns
                       (to be decided by looping over the matrix and looking at the amount
                       of black pixels on the same line / on the same column), timewise okayish
        @param laserspot: the laserbeam diameter in pixels (low dpi = irrelevant, high dpi very relevant)
        @param special: a dict of special treatment instructions for the different algorithms
        """
        # Don't try to plot from two different sources at the same time...
        self._locked = False

        if special is None:
            special = {}
        self.debug_level = 0  # 0 Nothing, 1 file creation, 2 file + summary, 3 file + summary + details
        self.data = data
        self.width = width
        self.height = height
        self.direction = direction
        self._cache = None
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
            RASTER_DIAGONAL: (None, None, None, True),  # true diagonal
        }
        def_x, def_y, def_hor, def_bidir = parameters.get(
            direction, (None, None, None, None)
        )
        self.start_minimum_x = start_minimum_x if def_x is None else def_x
        self.start_minimum_y = start_minimum_y if def_y is None else def_y
        self.horizontal = horizontal if def_hor is None else def_hor
        self.bidirectional = bidirectional if def_bidir is None else def_bidir

        self.use_integers = use_integers
        self.skip_pixel = skip_pixel
        # laserspot = width in pixels, so the surrounding logic needs to calculate it
        # We consider an overlap only in the enclosed square of the circle
        # and calculate the overlap in pixels to the left / to the right
        self.overlap = int(laserspot / sqrt(2) / 2)
        # self.overlap = 1
        self.special = dict(special)  # Copy it so it wont be changed
        if horizontal:
            self.overscan = round(overscan / float(step_x))
        else:
            self.overscan = round(overscan / float(step_y))
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.step_x = step_x
        self.step_y = step_y
        self.filter = filter
        self.initial_x, self.initial_y = self.calculate_first_pixel()
        self.final_x, self.final_y = self.calculate_last_pixel()
        self._distance_travel = 0
        self._distance_burn = 0

    def __repr__(self):
        if self.direction in METHODS:
            s_meth = f"Rasterplotter ({self.width}x{self.height}): {METHODS[self.direction]} ({self.direction})"
        else:
            s_meth = (
                f"Rasterplotter ({self.width}x{self.height}): Unknown {self.direction}"
            )
        s_direc = "Bidirectional" if self.bidirectional else "Unidirectional"
        s_axis = "horizontal" if self.horizontal else "vertical"
        s_ystart = "top" if self.start_minimum_y else "bottom"
        s_xstart = "left" if self.start_minimum_x else "right"
        return f"{s_meth}, {s_direc} {s_axis} plot starting at {s_ystart}-{s_xstart}"

    def reset(self):
        self._cache = None

    def px(self, x, y):
        """
        Returns the filtered pixel value at the given coordinates.

        @param x: The x-coordinate of the pixel
        @param y: The y-coordinate of the pixel
        @return: The filtered pixel value, or raises IndexError if coordinates are out of bounds
        """
        if 0 <= y < self.height and 0 <= x < self.width:
            return (
                self.data[x, y] if self.filter is None else self.filter(self.data[x, y])
            )
        raise IndexError

    def leftmost_not_equal(self, y):
        """
        Determine the leftmost pixel that is not equal to the skip_pixel value.

        if all pixels skipped returns None
        """
        for x in range(self.width):
            pixel = self.px(x, y)
            if pixel != self.skip_pixel:
                return x
        return None

    def topmost_not_equal(self, x):
        """
        Determine the topmost pixel that is not equal to the skip_pixel value

        if all pixels skipped returns None
        """
        for y in range(self.height):
            pixel = self.px(x, y)
            if pixel != self.skip_pixel:
                return y
        return None

    def rightmost_not_equal(self, y):
        """
        Determine the rightmost pixel that is not equal to the skip_pixel value

        if all pixels skipped returns None
        """
        for x in range(self.width - 1, -1, -1):
            pixel = self.px(x, y)
            if pixel != self.skip_pixel:
                return x
        return None

    def bottommost_not_equal(self, x):
        """
        Determine the bottommost pixel that is not equal to the skip_pixel value

        if all pixels skipped returns None
        """
        for y in range(self.height - 1, -1, -1):
            pixel = self.px(x, y)
            if pixel != self.skip_pixel:
                return y
        return None

    @property
    def distance_travel(self):
        return self._distance_travel

    @property
    def distance_burn(self):
        return self._distance_burn

    def nextcolor_left(self, x, y, default=None):
        """
        Determine the next pixel change going left from the (x,y) point.
        If no next pixel is found default is returned.
        """
        if x <= -1:
            return default
        if x == 0:
            return -1
        if x == self.width:
            return self.width - 1
        if self.width < x:
            return self.width

        v = self.px(x, y)
        for ix in range(x, -1, -1):
            pixel = self.px(ix, y)
            if pixel != v:
                return ix
        return 0

    def nextcolor_top(self, x, y, default=None):
        """
        Determine the next pixel change going top from the (x,y) point.
        If no next pixel is found default is returned.
        """
        if y <= -1:
            return default
        if y == 0:
            return -1
        if y == self.height:
            return self.height - 1
        if self.height < y:
            return self.height

        v = self.px(x, y)
        for iy in range(y, -1, -1):
            pixel = self.px(x, iy)
            if pixel != v:
                return iy
        return 0

    def nextcolor_right(self, x, y, default=None):
        """
        Determine the next pixel change going right from the (x,y) point.
        If no next pixel is found default is returned.
        """
        if x < -1:
            return -1
        if x == -1:
            return 0
        if x == self.width - 1:
            return self.width
        if self.width <= x:
            return default

        v = self.px(x, y)
        for ix in range(x, self.width):
            pixel = self.px(ix, y)
            if pixel != v:
                return ix
        return self.width - 1

    def nextcolor_bottom(self, x, y, default=None):
        """
        Determine the next pixel change going bottom from the (x,y) point.
        If no next pixel is found default is returned.
        """
        if y < -1:
            return -1
        if y == -1:
            return 0
        if y == self.height - 1:
            return self.height
        if self.height <= y:
            return default

        v = self.px(x, y)
        for iy in range(y, self.height):
            pixel = self.px(x, iy)
            if pixel != v:
                return iy
        return self.height - 1

    def calculate_next_horizontal_pixel(self, y, dy=1, leftmost_pixel=True):
        """
        Find the horizontal extreme at the given y-scanline, stepping by dy in the target image.
        This can be done on either the leftmost (True) or rightmost (False).

        @param y: y-scanline
        @param dy: dy-step amount (usually should be -1 or 1)
        @param leftmost_pixel: find pixel from the left
        @return:
        """
        try:
            if leftmost_pixel:
                while True:
                    x = self.leftmost_not_equal(y)
                    if x is not None:
                        break
                    y += dy
            else:
                while True:
                    x = self.rightmost_not_equal(y)
                    if x is not None:
                        break
                    y += dy
        except IndexError:
            # Remaining image is blank
            return None, None
        return x, y

    def calculate_next_vertical_pixel(self, x, dx=1, topmost_pixel=True):
        """
        Find the vertical extreme at the given x-scanline, stepping by dx in the target image.
        This can be done on either the topmost (True) or bottommost (False).

        @param x: x-scanline
        @param dx: dx-step amount (usually should be -1 or 1)
        @param topmost_pixel: find the pixel from the top
        @return:
        """
        try:
            if topmost_pixel:
                while True:
                    y = self.topmost_not_equal(x)
                    if y is not None:
                        break
                    x += dx
            else:
                while True:
                    # find that the bottommost pixel in that row.
                    y = self.bottommost_not_equal(x)

                    if y is not None:
                        # This is a valid pixel.
                        break
                    # No pixel in that row was valid. Move to the next row.
                    x += dx
        except IndexError:
            # Remaining image was blank, there are no more relevant pixels.
            return None, None
        return x, y

    def calculate_first_pixel(self):
        """
        Find the first non-skipped pixel in the rastering.

        This takes into account the traversal values of X_AXIS or Y_AXIS and BOTTOM and RIGHT
        The start edge and the start point.

        @return: x,y coordinates of first pixel.
        """
        if self.direction == RASTER_DIAGONAL:
            x = 0 if self.start_minimum_x else self.width - 1
            y = 0 if self.start_minimum_y else self.height - 1
        elif self.direction == RASTER_SPIRAL:
            x = int(self.width / 2)
            y = int(self.height / 2)
        else:
            if self.horizontal:
                y = 0 if self.start_minimum_y else self.height - 1
                dy = 1 if self.start_minimum_y else -1
                x, y = self.calculate_next_horizontal_pixel(y, dy, self.start_minimum_x)
            else:
                x = 0 if self.start_minimum_x else self.width - 1
                dx = 1 if self.start_minimum_x else -1
                x, y = self.calculate_next_vertical_pixel(x, dx, self.start_minimum_y)
        return x, y

    def calculate_last_pixel(self):
        """
        Find the last non-skipped pixel in the rastering.

        First and last scanlines start from the same side when scanline count is odd

        @return: x,y coordinates of last pixel.
        """
        if self.direction == RASTER_DIAGONAL:
            x = self.width - 1 if self.start_minimum_x else 0
            y = self.height - 1 if self.start_minimum_y else 0
        elif self.direction == RASTER_SPIRAL:
            x = self.width - 1
            y = self.height - 1
        else:
            if self.horizontal:
                y = self.height - 1 if self.start_minimum_y else 0
                dy = -1 if self.start_minimum_y else 1
                start_on_left = (
                    self.start_minimum_x if self.width & 1 else not self.start_minimum_x
                )
                x, y = self.calculate_next_horizontal_pixel(y, dy, start_on_left)
            else:
                x = self.width - 1 if self.start_minimum_x else 0
                dx = -1 if self.start_minimum_x else 1
                start_on_top = (
                    self.start_minimum_y
                    if self.height & 1
                    else not self.start_minimum_y
                )
                x, y = self.calculate_next_vertical_pixel(x, dx, start_on_top)
        return x, y

    def initial_position(self):
        """
        Returns raw initial position for the relevant pixel within the data.
        @return: initial position within the data.
        """
        if self.initial_x is None or self.initial_y is None:
            raise ValueError("Initial position is not set")
        if self.use_integers:
            return int(round(self.initial_x)), int(round(self.initial_y))
        else:
            return self.initial_x, self.initial_y

    def initial_position_in_scene(self):
        """
        Returns the initial position for this within the scene. Taking into account start corner, and step size.
        @return: initial position within scene. The first plot location.
        """
        if self.initial_x is None or isinf(self.initial_x):  # image is blank.
            if self.use_integers:
                return int(round(self.offset_x)), int(round(self.offset_y))
            else:
                return self.offset_x, self.offset_y
        if self.use_integers:
            return (
                int(round(self.offset_x + (self.initial_x or 0) * self.step_x)),
                int(round(self.offset_y + (self.initial_y or 0) * self.step_y)),
            )
        else:
            return (
                self.offset_x + (self.initial_x or 0) * self.step_x,
                self.offset_y + (self.initial_y or 0) * self.step_y,
            )

    def final_position_in_scene(self):
        """
        Returns best guess of final position relative to the scene offset. Taking into account start corner, and parity
        of the width and height.
        @return:
        """
        if self.final_x is None or isinf(self.final_x):  # image is blank.
            if self.use_integers:
                return int(round(self.offset_x)), int(round(self.offset_y))
            else:
                return self.offset_x, self.offset_y
        if self.use_integers:
            return (
                int(round(self.offset_x + (self.final_x or 0) * self.step_x)),
                int(round(self.offset_y + (self.final_y or 0) * self.step_y)),
            )
        else:
            return (
                self.offset_x + (self.final_x or 0) * self.step_x,
                self.offset_y + (self.final_y or 0) * self.step_y,
            )

    def plot(self):
        """
        Plot the values yielded by following the given raster plotter in the traversal defined.
        """
        while self._locked:
            sleep(0.1)
        self._locked = True
        offset_x = self.offset_x
        offset_y = self.offset_y
        step_x = self.step_x
        step_y = self.step_y
        self._distance_travel = 0
        self._distance_burn = 0

        if self.initial_x is None:
            # There is no image.
            return
        # Debug code....
        testmethods = (
            "Test: Horizontal Rectangle",
            "Test: Vertical Rectangle",
            "Test: Horizontal Snake",
            "Test: Vertical Snake",
            "Test: Spiral",
        )
        if self._cache is None:
            if self.debug_level > 0:
                try:
                    if self.direction >= 0:
                        m = METHODS.get(self.direction, "Unknown")
                    else:
                        m = testmethods[abs(self.direction) - 1]
                    s_meth = f"Method: {m} ({self.direction})"
                except IndexError:
                    s_meth = f"Method: Unknown {self.direction}"
                print(s_meth)
                data = list(self._plot_pixels())
                from platform import system

                defaultdir = "c:\\temp\\" if system() == "Windows" else ""
                has_duplicates = 0
                tstamp = int(perf_counter() * 100)
                with open(f"{defaultdir}plot_{tstamp}.txt", mode="w") as f:
                    f.write(
                        f"0.9.7\n{s_meth}\n{'Bidirectional' if self.bidirectional else 'Unidirectional'} {'horizontal' if self.horizontal else 'vertical'} plot starting at {'top' if self.start_minimum_y else 'bottom'}-{'left' if self.start_minimum_x else 'right'}\n"
                    )
                    f.write(
                        f"Overscan: {self.overscan:.2f}, Stepx={step_x:.2f}, Stepy={step_y:.2f}\n"
                    )
                    f.write(f"Image dimensions: {self.width}x{self.height}\n")
                    f.write(f"Startpoint: {self.initial_x}, {self.initial_y}\n")
                    f.write(f"Overlapping pixels to any side: {self.overlap}\n")
                    if self.special:
                        f.write("Special instructions:\n")
                        for key, value in self.special.items():
                            f.write(f"  {key} = {value}\n")
                    f.write(
                        "----------------------------------------------------------------------\n"
                    )
                    test_dict = {}
                    lastx = self.initial_x
                    lasty = self.initial_y
                    failed = False
                    for lineno, (x, y, on) in enumerate(data, start=1):
                        if lastx is not None:
                            dx = x - lastx
                            dy = y - lasty
                            if dx != 0 and dy != 0:  # and abs(dx) != abs(dy):
                                f.write(
                                    f"You f**ed up! No zigzag movement from line {lineno - 1} to {lineno}: {lastx}, {lasty} -> {x}, {y}\n"
                                )
                                print(
                                    f"You f**ed up! No zigzag movement from line {lineno - 1} to {lineno}: {lastx}, {lasty} -> {x}, {y}"
                                )
                                failed = True
                        lastx = x
                        lasty = y
                    if not failed:
                        f.write("Good news, no zig-zag movements identified!\n")
                    f.write(
                        "----------------------------------------------------------------------\n"
                    )
                    for lineno, (x, y, on) in enumerate(data, start=1):
                        if x is None or y is None:
                            continue
                        key = f"{x} - {y}"
                        if key in test_dict:
                            f.write(
                                f"Duplicate coordinates in list at ({x}, {y})! 1st: #{test_dict[key][0]}, on={test_dict[key][1]}, 2nd: #{lineno}, on={on}\n"
                            )
                            has_duplicates += 1
                        else:
                            test_dict[key] = (lineno, on)
                    if has_duplicates:
                        f.write(
                            "----------------------------------------------------------------------\n"
                        )
                    for lineno, (x, y, on) in enumerate(data, start=1):
                        f.write(f"{lineno}: {x}, {y}, {on}\n")
                    if has_duplicates:
                        print(
                            f"Attention: the generated plot has {has_duplicates} duplicate coordinate values!"
                        )
                        print(
                            f"{'Bidirectional' if self.bidirectional else 'Unidirectional'} {'horizontal' if self.horizontal else 'vertical'} plot starting at {'top' if self.start_minimum_y else 'bottom'}-{'left' if self.start_minimum_x else 'right'}"
                        )
                        print(
                            f"Overscan: {self.overscan:.2f}, Stepx={step_x:.2f}, Stepy={step_y:.2f}"
                        )
                        print(f"Image dimensions: {self.width}x{self.height}")
            else:
                data = list(self._plot_pixels())
            self._cache = data
        else:
            data = self._cache
        last_x = offset_x
        last_y = offset_y
        if self.use_integers:
            for x, y, on in data:
                if x is None or y is None:
                    # Passthrough
                    yield x, y, on
                else:
                    nx = int(round(offset_x + step_x * x))
                    ny = int(round(offset_y + y * step_y))
                    self._distance_burn += (
                        0
                        if on == 0
                        else sqrt(
                            (nx - last_x) * (nx - last_x)
                            + (ny - last_y) * (ny - last_y)
                        )
                    )
                    self._distance_travel += (
                        0
                        if on != 0
                        else sqrt(
                            (nx - last_x) * (nx - last_x)
                            + (ny - last_y) * (ny - last_y)
                        )
                    )
                    yield nx, ny, on
                    last_x = nx
                    last_y = ny
        else:
            for x, y, on in data:
                if x is None or y is None:
                    # Passthrough
                    yield x, y, on
                else:
                    nx = round(offset_x + step_x * x)
                    ny = round(offset_y + y * step_y)
                    self._distance_burn += (
                        0
                        if on == 0
                        else sqrt(
                            (nx - last_x) * (nx - last_x)
                            + (ny - last_y) * (ny - last_y)
                        )
                    )
                    self._distance_travel += (
                        0
                        if on != 0
                        else sqrt(
                            (nx - last_x) * (nx - last_x)
                            + (ny - last_y) * (ny - last_y)
                        )
                    )
                    yield offset_x + step_x * x, offset_y + y * step_y, on
                    last_x = nx
                    last_y = ny
        self._locked = False

    def _plot_pixels(self):
        legacy = self.special.get("legacy", False)
        if self.direction in (RASTER_GREEDY_H, RASTER_GREEDY_V):
            yield from self._plot_greedy_neighbour(horizontal=self.horizontal)
        elif self.direction == RASTER_CROSSOVER:
            yield from self._plot_crossover()
        elif self.direction == RASTER_SPIRAL:
            yield from self._plot_spiral()
        elif self.direction == RASTER_DIAGONAL:
            yield from self._plot_diagonal()
        # elif self.direction < 0:
        #     yield from self.testpattern_generator()
        elif self.horizontal:
            if legacy:
                yield from self._legacy_plot_horizontal()
            else:
                yield from self._plot_horizontal()
        else:
            if legacy:
                yield from self._legacy_plot_vertical()
            else:
                yield from self._plot_vertical()
            # yield from self._plot_vertical()

    def _debug_data(self, force=False):
        if self.debug_level < 3 and not force:
            return
        for y in range(self.height):
            msg: str = f"{y:3d}: "
            for x in range(self.width):
                msg += "." if self.data[x, y] == BLANK else "X"
            print(msg)

    def _get_pixel_chains(self, xy: int, is_x: bool) -> list:
        last_pixel = None
        segments = []
        upper = self.width if is_x else self.height
        for idx in range(upper):
            pixel = self.px(idx, xy) if is_x else self.px(xy, idx)
            on = 0 if pixel == self.skip_pixel else pixel
            if on:
                if on == last_pixel:
                    segments[-1][1] = idx
                else:
                    segments.append([idx, idx, on])
            last_pixel = on
        return segments

    def _consume_pixel_chains(self, segments: list, xy: int, is_x: bool):
        # for x in range(5):
        #     msg1 = f"{x}: "
        #     msg2 = ""
        #     for y in range(5):
        #         msg1 += "." if self.data[x, y] == BLANK else "X"
        #         msg2 += f" {self.data[x, y]}"
        #     print (msg1, msg2)

        for seg in segments:
            c_start = seg[0]
            c_end = seg[1]
            for idx in range(c_start, c_end + 1):
                if is_x:
                    px = idx
                    py = xy
                else:
                    px = xy
                    py = idx
                self._overlap_pixel(px, py)

        self._debug_data()

    def _overlap_pixel(self, px, py):
        for x_idx in range(-self.overlap, self.overlap + 1):
            for y_idx in range(-self.overlap, self.overlap + 1):
                nx = px + x_idx
                ny = py + y_idx
                if nx < 0 or nx >= self.width or ny < 0 or ny >= self.height:
                    continue
                self.data[nx, ny] = BLANK

    def _plot_vertical(self):
        """
        This code is for vertical rastering.
        We are looking first for all consecutive pixel chains with the same pixel value
        Then we loop through the segments and yield the 'end edge' of the 'last' pixel
        'end edge' and 'last' are dependent on the sweep direction.
        There is one peculiarity though that is required for K40 lasers:
        a) We may only move from one yielded (x,y,on) tuple in a pure horizontal or pure
           vertical fashion (we could as well go perfectly diagonal but we are not using
           this feature). So at the end of one sweepline we need to change to the
           next scanline by going directly up/down/left/right and then move to the first
           relevant pixel.
        b) we need to take care that we are not landing on the same pixel twice. So we move
           outside the new chain to avoid this
        """
        if (
            self.initial_x is None
            or self.final_x is None
            or self.initial_y is None
            or self.final_y is None
        ):
            return

        unidirectional = not self.bidirectional

        dx = 1 if self.start_minimum_x else -1
        dy = 1 if self.start_minimum_y else -1
        lower = min(self.initial_x, self.final_x)
        upper = max(self.initial_x, self.final_x)
        last_x = self.initial_x
        last_y = self.initial_y
        x = lower if self.start_minimum_x else upper
        first = True
        while lower <= x <= upper:
            segments = self._get_pixel_chains(x, False)
            self._consume_pixel_chains(segments, x, False)
            if segments:
                if dy > 0:
                    # from top to bottom
                    idx = 0
                    start = 0
                    end = 1
                    edge_start = -0.5
                    edge_end = 0.5
                else:
                    idx = len(segments) - 1
                    end = 0
                    start = 1
                    edge_start = 0.5
                    edge_end = -0.5
                # Goto next column, but make sure we end up outside our chain
                # We consider as well the overscan value
                overscan_top = 0 if dy >= 0 else self.overscan
                overscan_bottom = 0 if dy <= 0 else self.overscan
                if not first and (
                    segments[0][0] - overscan_top
                    <= last_y
                    <= segments[-1][1] + overscan_bottom
                ):
                    # inside the chain!
                    # So lets move a bit to the side
                    if dy > 0:
                        if self.bidirectional:
                            # Previous was sweep from right to left, so we go beyond first point
                            last_y = segments[0][0] - overscan_top - 1
                        else:
                            # We go beyond last point
                            last_y = segments[-1][1] + overscan_bottom + 1
                    else:
                        # Previous was sweep from left to right, so we go beyond last point
                        last_y = segments[-1][1] + overscan_bottom + 1
                    last_x = x - dx
                    yield last_x, last_y, 0
                last_x = x
                yield last_x, last_y, 0
                while 0 <= idx < len(segments):
                    sy = segments[idx][start] + edge_start
                    ey = segments[idx][end] + edge_end
                    on = segments[idx][2]
                    if last_y != sy:
                        yield last_x, sy, 0
                    last_y = ey
                    yield last_x, last_y, on
                    idx += dy
                if self.overscan:
                    last_y += dy * self.overscan
                    yield last_x, last_y, 0
                if not unidirectional:
                    dy = -dy
                first = False
            else:
                # Just climb the line, and don't change directions
                last_x = x
                yield last_x, last_y, 0

            x += dx

    def _plot_horizontal(self):
        """
        This code is horizontal rastering.
        We are looking first for all consecutive pixel chains with the same pixel value
        Then we loop through the segments and yield the 'end edge' of the 'last' pixel
        'end edge' and 'last' are dependent on the sweep direction.
        There is one peculiarity though that is required for K40 lasers:
        a) We may only move from one yielded (x,y,on) tuple in a pure horizontal or pure
           vertical fashion (we could as well go perfectly diagonal but we are not using
           this feature). So at the end of one sweepline we need to change to the
           next scanline by going directly up/down/left/right and then move to the first
           relevant pixel.
        b) we need to take care that we are not landing on the same pixel twice. So we move
           outside the new chain to avoid this
        """
        if (
            self.initial_x is None
            or self.final_x is None
            or self.initial_y is None
            or self.final_y is None
        ):
            return

        unidirectional = not self.bidirectional

        dx = 1 if self.start_minimum_x else -1
        dy = 1 if self.start_minimum_y else -1
        last_x = self.initial_x
        last_y = self.initial_y
        lower = min(self.initial_y, self.final_y)
        upper = max(self.initial_y, self.final_y)
        y = lower if self.start_minimum_y else upper
        first = True
        while lower <= y <= upper:
            segments = self._get_pixel_chains(y, True)
            self._consume_pixel_chains(segments, y, True)
            if segments:
                if dx > 0:
                    # from left to right
                    idx = 0
                    start = 0
                    end = 1
                    edge_start = -0.5
                    edge_end = 0.5
                else:
                    idx = len(segments) - 1
                    end = 0
                    start = 1
                    edge_start = 0.5
                    edge_end = -0.5
                if last_x is None:
                    last_x = segments[idx][start] + edge_start
                # Goto next line, but make sure we end up outside our chain
                # We consider as well the overscan value
                overscan_left = 0 if dx >= 0 else self.overscan
                overscan_right = 0 if dx <= 0 else self.overscan
                if not first and (
                    segments[0][0] - overscan_left
                    <= last_x
                    <= segments[-1][1] + overscan_right
                ):
                    # inside the chain!
                    # So lets move a bit to the side
                    if dx > 0:
                        if self.bidirectional:
                            # Previous was sweep from right to left, so we go beyond first point
                            last_x = segments[0][0] - overscan_left - 1
                        else:
                            # We go beyond last point
                            last_x = segments[-1][1] + overscan_right + 1
                    else:
                        # Previous was sweep from left to right, so we go beyond last point
                        last_x = segments[-1][1] + overscan_right + 1
                    yield last_x, y - dy, 0
                last_y = y
                yield last_x, last_y, 0
                while 0 <= idx < len(segments):
                    sx = segments[idx][start] + edge_start
                    ex = segments[idx][end] + edge_end
                    on = segments[idx][2]
                    if last_x != sx:
                        yield sx, last_y, 0
                    last_x = ex
                    yield last_x, last_y, on
                    idx += dx
                if self.overscan:
                    last_x += dx * self.overscan
                    yield last_x, last_y, 0
                if not unidirectional:
                    dx = -dx
                first = False
            else:
                # Just climb the line, and don't change directions
                last_y = y
                yield last_x, last_y, 0
            y += dy

    # Legacy code for the m2nano - yes this has deficits for low dpi but it seems
    # to be finetuned to the needs of the m2nano controller.
    # This will be called if the appropriate device setting is in place
    def _legacy_plot_vertical(self):
        """
        Legacy vertical rastering implementation for m2nano controller compatibility.

        This method provides backward-compatible vertical rastering that has been optimized
        for the m2nano controller's specific requirements. It includes comprehensive None guards
        to prevent runtime errors when initial/final coordinates are not properly set.

        The algorithm processes pixels column by column, finding pixel chains and consuming
        overlapping pixels to prevent duplicate engraving. It supports bidirectional scanning
        and handles edge cases where scanlines may be empty.

        Key features:
        - Early return if initial/final coordinates are None (type safety)
        - Pixel chain detection and consumption for overlap handling
        - Bidirectional scanning support with direction alternation
        - Overscan compensation for multi-pass engraving
        - Boundary detection for efficient scanning

        Note: This is a legacy implementation maintained for device compatibility.
        For new applications, consider using the standard _plot_vertical method.

        Yields:
            tuple: (x, y, on) coordinates and laser on/off state
        """
        if (
            self.initial_x is None
            or self.final_x is None
            or self.initial_y is None
            or self.final_y is None
        ):
            return

        width = self.width
        unidirectional = not self.bidirectional
        skip_pixel = self.skip_pixel

        x, y = self.initial_position()
        dx = 1 if self.start_minimum_x else -1
        dy = 1 if self.start_minimum_y else -1

        yield x, y, 0
        while 0 <= x < width:
            lower_bound = self.topmost_not_equal(x)
            if lower_bound is None:
                x += dx
                yield x, y, 0
                continue
            upper_bound = self.bottommost_not_equal(x)
            traveling_bottom = self.start_minimum_y if unidirectional else dy >= 0
            next_traveling_bottom = self.start_minimum_y if unidirectional else dy <= 0

            next_x, next_y = self.calculate_next_vertical_pixel(
                x + dx, dx, topmost_pixel=next_traveling_bottom
            )
            if next_y is not None:
                # If we have a next scanline, we must end after the last pixel of that scanline too.
                upper_bound = max(next_y, upper_bound) + self.overscan
                lower_bound = min(next_y, lower_bound) - self.overscan
            pixel_chain = []
            last_y = lower_bound if traveling_bottom else upper_bound
            if traveling_bottom:
                while y < upper_bound:
                    try:
                        pixel = self.px(x, y)
                    except IndexError:
                        pixel = 0
                    y = self.nextcolor_bottom(x, y, upper_bound)
                    y = min(y, upper_bound)
                    if pixel == skip_pixel:
                        yield x, y, 0
                    else:
                        yield x, y, pixel
                        pixel_chain.append([last_y, y, pixel])
                    last_y = y + 1
            else:
                while lower_bound < y:
                    try:
                        pixel = self.px(x, y)
                    except IndexError:
                        pixel = 0
                    y = self.nextcolor_top(x, y, lower_bound)
                    y = max(y, lower_bound)
                    if pixel == skip_pixel:
                        yield x, y, 0
                    else:
                        yield x, y, pixel
                        pixel_chain.append([y, last_y, pixel])
                    last_y = y - 1
            if pixel_chain:
                self._consume_pixel_chains(pixel_chain, x, False)
            if next_y is None:
                # remaining image is blank, we stop right here.
                return
            yield next_x, y, 0
            if y != next_y:
                yield next_x, next_y, 0
            x = next_x
            y = next_y
            dy = -dy

    def _legacy_plot_horizontal(self):
        """
        This code is horizontal rastering.

        @return:
        """
        if (
            self.initial_x is None
            or self.final_x is None
            or self.initial_y is None
            or self.final_y is None
        ):
            return

        height = self.height
        unidirectional = not self.bidirectional
        skip_pixel = self.skip_pixel

        x, y = self.initial_position()
        dx = 1 if self.start_minimum_x else -1
        dy = 1 if self.start_minimum_y else -1
        yield x, y, 0
        while 0 <= y < height:
            lower_bound = self.leftmost_not_equal(y)
            if lower_bound is None:
                y += dy
                yield x, y, 0
                continue
            upper_bound = self.rightmost_not_equal(y)
            traveling_right = self.start_minimum_x if unidirectional else dx >= 0
            next_traveling_right = self.start_minimum_x if unidirectional else dx <= 0

            next_x, next_y = self.calculate_next_horizontal_pixel(
                y + dy, dy, leftmost_pixel=next_traveling_right
            )
            if next_x is not None:
                # If we have a next scanline, we must end after the last pixel of that scanline too.
                upper_bound = max(next_x, upper_bound) + self.overscan
                lower_bound = min(next_x, lower_bound) - self.overscan
            pixel_chain = []
            last_x = lower_bound if traveling_right else upper_bound
            if traveling_right:
                while x < upper_bound:
                    try:
                        pixel = self.px(x, y)
                    except IndexError:
                        pixel = 0
                    x = self.nextcolor_right(x, y, upper_bound)
                    x = min(x, upper_bound)
                    if pixel == skip_pixel:
                        yield x, y, 0
                    else:
                        yield x, y, pixel
                        pixel_chain.append([last_x, x, pixel])
                    last_x = x + 1
            else:
                while lower_bound < x:
                    try:
                        pixel = self.px(x, y)
                    except IndexError:
                        pixel = 0
                    x = self.nextcolor_left(x, y, lower_bound)
                    x = max(x, lower_bound)
                    if pixel == skip_pixel:
                        yield x, y, 0
                    else:
                        yield x, y, pixel
                        pixel_chain.append([x, last_x, pixel])
                    last_x = x - 1
            if pixel_chain:
                self._consume_pixel_chains(pixel_chain, y, True)
            if next_y is None:
                # remaining image is blank, we stop right here.
                return
            yield x, next_y, 0
            if x != next_x:
                yield next_x, next_y, 0
            x = next_x
            y = next_y
            dx = -dx

    def _plot_greedy_neighbour(self, horizontal: bool = True):
        """
        Distance Matrix Function: The distance_matrix function calculates the squared distances from the
        current point to all other points, applying a penalty to the y-distances to prefer movements in the x-direction.

        Initialization: We initialize the visited array to keep track of visited segments, the path list
        to store the order of segments along with the relevant point (start or end),
        and the current_point as the starting point.

        Sliding Window: We use a sliding window to limit the number of segments we need to consider at each step.
        The window size is controlled by the window_size parameter and is applied to both x and y coordinates.

        Main Loop: In the main loop, we calculate the distances from the current point to all unvisited points
        within the sliding window using the distance_matrix function.
        We then use np.argmin to find the index of the smallest distance.
        We update the current_point to the next point and mark the segment as visited.
        The path list is updated with the segment index and whether the start or end point is relevant.
        """
        # Guard against None values in initial/final coordinates
        if (
            self.initial_x is None
            or self.final_x is None
            or self.initial_y is None
            or self.final_y is None
        ):
            return

        def walk_segments(segments, horizontal=True, xy_penalty=1, width=1, height=1):
            n: int = len(segments)
            visited = np.zeros(n, dtype=bool)
            path = []
            window_size = 10
            current_point = np.array(segments[0][0], dtype=float)
            segment_points = np.array(
                [point for segment in segments for point in segment], dtype=float
            )
            mask = ~visited.repeat(2)
            while len(path) < n:
                # Find the range of segments within the x- and y-window
                x_min = current_point[0] - window_size
                x_max = current_point[0] + window_size
                y_min = current_point[1] - window_size
                y_max = current_point[1] + window_size
                unvisited_indices = np.where(
                    (segment_points[:, 0] >= x_min)
                    & (segment_points[:, 0] <= x_max)
                    & (segment_points[:, 1] >= y_min)
                    & (segment_points[:, 1] <= y_max)
                    & mask
                )[0]
                if len(unvisited_indices) == 0:
                    # If no segments are within the window, expand the window
                    window_size *= 2
                    # print (f"Did not find points: now window: {window_size}")
                    if (
                        window_size <= 2 * height or window_size <= 2 * width
                    ):  # Safety belt
                        continue

                unvisited_points = segment_points[unvisited_indices]

                # distances = distance_matrix(unvisited_points, current_point, y_penalty)
                diff = unvisited_points - current_point
                if horizontal:
                    diff[:, 1] *= xy_penalty  # Apply penalty to y-distances
                else:
                    diff[:, 0] *= xy_penalty  # Apply penalty to x-distances

                distances = np.sum(diff**2, axis=1)  # Return squared distances

                min_distance_idx = np.argmin(distances)
                next_segment = unvisited_indices[min_distance_idx] // 2

                if not visited[next_segment]:
                    visited[next_segment] = True
                    # mask = ~visited.repeat(2)
                    mask[2 * next_segment] = False
                    mask[2 * next_segment + 1] = False
                    if min_distance_idx % 2 == 0:
                        path.append((next_segment, "end"))
                        current_point = segment_points[
                            next_segment * 2 + 1
                        ]  # Move to the other endpoint
                    else:
                        path.append((next_segment, "start"))
                        current_point = segment_points[
                            next_segment * 2
                        ]  # Move to the other endpoint
                    window_size = 10  # Reset window size

            return path

        t0 = perf_counter()
        # An experimental routine
        if horizontal:
            dy = 1 if self.start_minimum_y else -1
            lower = min(self.initial_y, self.final_y)
            upper = max(self.initial_y, self.final_y)
            y = lower if self.start_minimum_y else upper
        else:
            dx = 1 if self.start_minimum_x else -1
            lower = min(self.initial_x, self.final_x)
            upper = max(self.initial_x, self.final_x)
            x = lower if self.start_minimum_x else upper

        line_parts = []
        on_parts = []
        if self.debug_level > 2:
            print(
                f"{'horizontal' if horizontal else 'Vertical'} for {self.width}x{self.height} image. {'y' if horizontal else 'x'} from {lower} to {upper}"
            )
        if horizontal:
            while lower <= y <= upper:
                segments = self._get_pixel_chains(y, True)
                self._consume_pixel_chains(segments, y, True)
                for seg in segments:
                    # Append (xstart, y), (xend, y), on
                    line_parts.append(((seg[0], y), (seg[1], y)))
                    on_parts.append(seg[2])
                y += dy
        else:
            while lower <= x <= upper:
                segments = self._get_pixel_chains(x, False)
                self._consume_pixel_chains(segments, x, False)
                for seg in segments:
                    # Append (xstart, y), (xend, y), on
                    line_parts.append(((x, seg[0]), (x, seg[1])))
                    on_parts.append(seg[2])
                x += dx
        if self.debug_level > 2:
            print(f"Created {len(line_parts)} segments")
        t1 = perf_counter()
        penalty = 3 if self.special.get("gantry", False) else 1
        path = walk_segments(
            line_parts,
            horizontal=horizontal,
            xy_penalty=penalty,
            width=self.width,
            height=self.height,
        )
        # print("Order of segments:", path)
        t2 = perf_counter()
        if horizontal:
            last_x = self.initial_x
            last_y = lower
        else:
            last_x = lower
            last_y = self.initial_y
        for idx, mode in path:
            if mode == "end":
                # end was closer
                (ex, ey), (sx, sy) = line_parts[idx]
            else:
                (sx, sy), (ex, ey) = line_parts[idx]
            on = on_parts[idx]
            if horizontal:
                dx = ex - sx
                if dx >= 0:
                    # from left to right
                    edge_start = -0.5
                    edge_end = 0.5
                else:
                    edge_start = 0.5
                    edge_end = -0.5
                sx += edge_start
                ex += edge_end
                if sy != last_y:
                    last_y = sy
                    yield last_x, last_y, 0
                if last_x != sx:
                    yield sx, last_y, 0
            else:
                dy = ey - sy
                if dy >= 0:
                    # from left to right
                    edge_start = -0.5
                    edge_end = 0.5
                else:
                    edge_start = 0.5
                    edge_end = -0.5
                sy += edge_start
                ey += edge_end
                if sx != last_x:
                    last_x = sx
                    yield last_x, last_y, 0
                if last_y != sy:
                    last_y = sy
                    yield sx, sy, 0

            yield ex, ey, on
            last_x = ex
            last_y = ey
        t3 = perf_counter()
        if self.debug_level > 1:
            print(
                f"Overall time for {'horizontal' if horizontal else 'vertical'} consumption: {t3 - t0:.2f}s - created: {len(line_parts)} segments"
            )
            print(
                f"Computation: {t2 - t0:.2f}s - Chain creation:{t1 - t0:.2f}s, Walk: {t2 - t1:.2f}s"
            )
        self.final_x = last_x
        self.final_y = last_y

    def _plot_spiral(self):
        rows = self.height
        cols = self.width
        center_row, center_col = rows // 2, cols // 2
        self.initial_x = center_col
        self.initial_y = center_row

        directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]  # Right, Down, Left, Up
        edges = [(0.5, 0), (0, 0.5), (-0.5, 0), (0, -0.5)]
        direction_index = 0
        steps = 1

        row, col = center_row, center_col
        # is the very first pixel an on?
        last_x = col
        last_y = row
        count = 1
        pixel = self.px(col, row)
        if pixel == self.skip_pixel:
            pixel = 0
        last_pixel = pixel
        if pixel:
            yield col - 0.5, row, 0
            last_x = col + 0.5
            yield last_x, row, pixel
        while count < rows * cols:
            for _ in range(2):
                segments = []
                dx, dy = edges[direction_index]
                edge_start_x = -dx
                edge_start_y = -dy
                edge_end_x = dx
                edge_end_y = dy
                # msg = f"[({col}, {row}) - {steps}] "
                for _ in range(steps):
                    row += directions[direction_index][1]
                    col += directions[direction_index][0]
                    if 0 <= row < rows and 0 <= col < cols:
                        pixel = self.px(col, row)
                        on = 0 if pixel == self.skip_pixel else pixel
                        # msg = f"{msg} {'X' if on else '.'}"
                        if on:
                            if on == last_pixel and len(segments):
                                segments[-1][1] = (col, row)
                            else:
                                segments.append([(col, row), (col, row), on])

                        last_pixel = on
                        count += 1
                        if count == rows * cols:
                            break
                # Deal with segments
                # print (msg)
                # print (segments)
                for (sx, sy), (ex, ey), pixel in segments:
                    sx += edge_start_x
                    sy += edge_start_y
                    ex += edge_end_x
                    ey += edge_end_y
                    if last_y != sy:
                        yield last_x, sy, 0
                        last_y = sy
                    if last_x != sx:
                        yield sx, last_y, 0
                    last_x = ex
                    last_y = ey
                    yield last_x, last_y, pixel
                    self.final_x, self.final_y = last_x, last_y
                # Now we need to empty overlapping pixels...
                if self.overlap > 0:
                    for (start_x, start_y), (end_x, end_y), on in segments:
                        sx = min(start_x, end_x)
                        ex = max(start_x, end_x)
                        sy = min(start_y, end_y)
                        ey = max(start_y, end_y)

                        if direction_index in (0, 2):  # horizontal
                            for y_idx in range(-self.overlap, self.overlap + 1):
                                ny = sy + y_idx
                                for nx in range(sx, ex + 1):
                                    if 0 <= nx < self.width and 0 <= ny < self.height:
                                        self.data[nx, ny] = BLANK
                        else:
                            for x_idx in range(-self.overlap, self.overlap + 1):
                                nx = sx + x_idx
                                for ny in range(sy, ey + 1):
                                    if 0 <= nx < self.width and 0 <= ny < self.height:
                                        self.data[nx, ny] = BLANK

                direction_index = (direction_index + 1) % 4
            steps += 1

    def _plot_crossover(self):
        """
        This algorithm scans through the image looking for the row or the column with the most pixels.
        It will hand back this information together with a precompiled list of
        state changes (start, end, pixel), ie a non-blank pixel with a different on value
        than the previous pixel
        It will then clean the row / column and start again.
        This happens until no more non-empty rows / cols can be found

        The receiving routine takes these values, orders them according to
        type (row/col) and row/col number and generates plot instructions
        that will be yielded.

        Yields:
            list of tuples with (x, y, on)
        """
        ROW = 0
        COL = 1

        def process_image(image):
            # We will modify the image to keep track of deleted rows and columns
            # Get the dimensions of the image
            rows, cols = image.shape
            # We prefer cols (which is the x-axis and that is normally
            # slightly advantageous for gantry lasers)
            if self.special.get("gantry", False):
                colfactor = 1.0
                rowfactor = 0.8
            else:
                colfactor = 1.0
                rowfactor = 1.0

            # Initialize a list to store the results
            results = []

            # Iterate through the matrix, we cover all rows and cols
            colidx = 0
            rowidx = 0
            covered_row = [None] * rows
            covered_col = [None] * cols
            stored_row = np.zeros(rows)
            stored_col = np.zeros(cols)
            stored_row_len = np.zeros(rows)
            stored_col_len = np.zeros(cols)
            recalc_row = True
            recalc_col = True
            while True:
                if recalc_col:
                    for i in range(cols):
                        col_len = cols
                        if covered_col[i] is None:
                            nonzero_indices = np.nonzero(image[:, i])[0]
                            count = len(nonzero_indices)
                            if count == 0:
                                covered_col[i] = True
                            else:
                                col_len = nonzero_indices[-1] - nonzero_indices[0] + 1
                                covered_col[i] = False
                            stored_col[i] = count
                            stored_col_len[i] = col_len
                if recalc_row:
                    for i in range(rows):
                        row_len = rows
                        if covered_row[i] is None:
                            nonzero_indices = np.nonzero(image[i, :])[0]
                            count = len(nonzero_indices)
                            if count == 0:
                                covered_row[i] = True
                            else:
                                row_len = nonzero_indices[-1] - nonzero_indices[0] + 1
                                covered_row[i] = False
                            stored_row[i] = count
                            stored_row_len[i] = row_len

                colidx = np.argmax(stored_col)
                rowidx = np.argmax(stored_row)

                col_count = stored_col[colidx]
                col_len = stored_col_len[colidx]
                row_count = stored_row[rowidx]
                row_len = stored_row_len[rowidx]

                if row_count == col_count == 0:
                    break
                # Determine whether there are more pixels in the row or column

                row_ratio = row_count * row_count / row_len * rowfactor
                col_ratio = col_count * col_count / col_len * colfactor
                # print (f"Col #{rowidx}: {int(row_count):3d} pixel over {int(row_len):3d} length, ratio: {row_ratio:.3f} {'winner' if row_ratio >= col_ratio else 'loser'}")
                # print (f"Row #{colidx}: {int(col_count):3d} pixel over {int(col_len):3d} length, ratio: {col_ratio:.3f} {'winner' if row_ratio < col_ratio else 'loser'}")
                # if row_count >= col_count:
                if row_ratio >= col_ratio:
                    last_pixel = None
                    segments = []
                    # msg = ""
                    for idx in range(cols):
                        on = image[rowidx, idx]
                        # msg = f"{msg}{'X' if on else '.'}"
                        if on:
                            if not covered_col[idx]:
                                covered_col[idx] = None  # needs recalc
                            if on == last_pixel:
                                segments[-1][1] = idx
                            else:
                                segments.append([idx, idx, on])
                        last_pixel = on
                    results.append(
                        (COL, rowidx, segments)
                    )  # Intentionally so, as the numpy array has x and y exchanged
                    # print (f"Col #{rowidx}: {msg} -> {segments}")

                    # Clear the column
                    image[rowidx, :] = 0
                    covered_row[rowidx] = True
                    stored_row[rowidx] = 0
                    for rc in range(self.overlap):
                        r = rowidx - rc
                        if 0 <= r < rows:
                            image[r, :] = 0
                            covered_row[r] = True
                            stored_row[r] = 0
                        r = rowidx + rc
                        if 0 <= r < rows:
                            image[r, :] = 0
                            covered_row[r] = True
                            stored_row[r] = 0
                    recalc_col = True
                else:
                    last_pixel = None
                    segments = []
                    # msg = ""
                    for idx in range(rows):
                        on = image[idx, colidx]
                        # msg = f"{msg}{'X' if on else '.'}"
                        if on:
                            if not covered_row[idx]:
                                covered_row[idx] = None  # needs recalc
                            if on == last_pixel:
                                segments[-1][1] = idx
                            else:
                                segments.append([idx, idx, on])
                        last_pixel = on
                    results.append((ROW, colidx, segments))
                    # print (f"Row #{colidx}: {msg} -> {segments}")
                    # Clear the row
                    image[:, colidx] = 0
                    covered_col[colidx] = True
                    stored_col[colidx] = 0
                    for rc in range(self.overlap):
                        r = colidx - rc
                        if 0 <= r < cols:
                            image[:, r] = 0
                            covered_col[r] = True
                            stored_col[r] = 0
                        r = rowidx + rc
                        if 0 <= r < cols:
                            image[:, r] = 0
                            covered_col[r] = True
                            stored_col[r] = 0
                    recalc_row = True
                if self.debug_level > 1:
                    for cidx in range(cols):
                        msg = ""
                        for ridx in range(rows):
                            on = image[ridx, cidx]
                            msg = f"{msg}{'X' if on else '.'}"
                        print(f"{cidx:3d}: {msg}")

            return results

        t0 = perf_counter()
        # initialize the matrix
        image = np.empty((self.width, self.height))
        # Apply filter and eliminate skip_pixel
        for x in range(self.width):
            for y in range(self.height):
                px = self.px(x, y)
                if px == self.skip_pixel:
                    px = 0
                image[x, y] = px
        t1 = perf_counter()
        results = process_image(image)
        results.sort()
        t2 = perf_counter()
        dx = +1
        dy = +1
        last_x = self.initial_x
        last_y = self.initial_y
        yield last_x, last_y, 0
        for mode, xy, segments in results:
            # eliminate data and swap direction
            if self.special.get("mode_filter", "") == "ROW" and mode != ROW:
                continue
            if self.special.get("mode_filter", "") == "COL" and mode != COL:
                continue

            if not segments:
                continue
            # NB: Axis change indication is no longer required,
            # the m2nano does not support it, the other devices do not need it...
            if mode == ROW:
                if xy != last_y:
                    last_y = xy
                    yield last_x, last_y, 0
                if dx > 0:
                    # from left to right
                    idx = 0
                    start = 0
                    end = 1
                    edge_start = -0.5
                    edge_end = 0.5
                else:
                    idx = len(segments) - 1
                    end = 0
                    start = 1
                    edge_start = 0.5
                    edge_end = -0.5
                while 0 <= idx < len(segments):
                    sx = segments[idx][start] + edge_start
                    ex = segments[idx][end] + edge_end
                    on = segments[idx][2]
                    if last_x != sx:
                        yield sx, last_y, 0
                    last_x = ex
                    yield last_x, last_y, on
                    idx += dx
            else:
                if xy != last_x:
                    last_x = xy
                    yield last_x, last_y, 0
                if dy > 0:
                    # from top to bottom
                    idx = 0
                    start = 0
                    end = 1
                    edge_start = -0.5
                    edge_end = 0.5
                else:
                    idx = len(segments) - 1
                    end = 0
                    start = 1
                    edge_start = 0.5
                    edge_end = -0.5
                while 0 <= idx < len(segments):
                    sy = segments[idx][start] + edge_start
                    ey = segments[idx][end] + edge_end
                    on = segments[idx][2]
                    if last_y != sy:
                        yield last_x, sy, 0
                    last_y = ey
                    yield last_x, last_y, on
                    idx += dy
            if self.bidirectional:
                if mode == ROW:
                    dx = -dx
                else:  # column
                    dy = -dy

        # We need to set the final values so that the rastercut is able to carry on
        self.final_x = last_x
        self.final_y = last_y
        t3 = perf_counter()
        if self.debug_level > 1:
            print(f"Overall time for crossover consumption: {t3 - t0:.2f}s")
            print(
                f"Computation: {t2 - t0:.2f}s - Array creation:{t1 - t0:.2f}s, Algorithm: {t2 - t1:.2f}s"
            )

    def _plot_diagonal(self):
        """
        Diagonal scanning algorithm that traverses the image diagonally using pixel chains.

        This method implements diagonal rastering that supports all four corner starting positions
        with bidirectional scanning and proper pixel overlap handling. Uses pixel chains for
        efficiency like other raster methods.

        Yields:
            tuple: (x, y, on) coordinates and laser on/off state (0=off, pixel_value=on)
        """
        # Determine start corner and diagonal equation parameters
        start_corner = f"{'top' if self.start_minimum_y else 'bottom'}-{'left' if self.start_minimum_x else 'right'}"

        # Configure diagonal scanning parameters based on start corner
        if start_corner in ("top-left", "bottom-right"):
            equation_func = self._diagonal_sum
            min_diag = 0
            max_diag = self.width + self.height - 2
            reverse_order = start_corner == "bottom-right"
        else:  # top-right, bottom-left
            equation_func = self._diagonal_diff
            min_diag = -(self.height - 1)
            max_diag = self.width - 1
            reverse_order = start_corner == "top-right"

        # Set up diagonal range
        diagonal_range = (
            range(max_diag, min_diag - 1, -1)
            if reverse_order
            else range(min_diag, max_diag + 1)
        )

        # Track current position
        current_x, current_y = self.initial_x, self.initial_y
        first_diagonal = True

        for diagonal_idx, diag_value in enumerate(diagonal_range):
            # Collect pixels on this diagonal
            pixels_on_diagonal = self._get_diagonal_pixels(diag_value, equation_func)

            # Sort pixels based on start corner and bidirectional setting
            pixels_on_diagonal = self._sort_diagonal_pixels(
                pixels_on_diagonal, start_corner, diagonal_idx
            )

            # Get pixel chains for this diagonal
            segments = self._get_diagonal_pixel_chains(pixels_on_diagonal)

            if segments:
                # Determine direction based on start corner and bidirectional setting
                alternate = self.bidirectional and diagonal_idx % 2 == 1

                if start_corner == "top-left":
                    reverse_segments = alternate
                elif start_corner == "top-right":
                    reverse_segments = alternate
                elif start_corner == "bottom-left":
                    reverse_segments = not alternate
                else:  # bottom-right
                    reverse_segments = not alternate

                if reverse_segments:
                    segments = segments[::-1]

                # Move to start of first segment
                start_x, start_y = segments[0][0]
                if first_diagonal or start_x != current_x or start_y != current_y:
                    yield start_x, start_y, 0
                    current_x, current_y = start_x, start_y

                # Process each segment
                for segment in segments:
                    (sx, sy), (ex, ey), on = segment

                    # Move to segment start if needed
                    if sx != current_x or sy != current_y:
                        yield sx, sy, 0
                        current_x, current_y = sx, sy

                    # Move to segment end with laser on
                    yield ex, ey, on
                    current_x, current_y = ex, ey

                first_diagonal = False

            # Consume overlapping pixels
            for px, py in pixels_on_diagonal:
                pixel = self.px(px, py)
                on = 0 if pixel == self.skip_pixel else pixel
                if on and self.overlap > 0:
                    self._overlap_pixel(px, py)

        # Update final position
        self.final_x, self.final_y = current_x, current_y

    def _diagonal_sum(self, x, y):
        """Calculate x + y for diagonal equations."""
        return x + y

    def _diagonal_diff(self, x, y):
        """Calculate x - y for diagonal equations."""
        return x - y

    def _get_diagonal_pixels(self, diag_value, equation_func):
        """Get all pixels that lie on a given diagonal."""
        pixels = []
        if equation_func(0, 0) == 0:  # x + y equation
            for x in range(
                max(0, diag_value - self.height + 1), min(diag_value + 1, self.width)
            ):
                y = diag_value - x
                if 0 <= y < self.height:
                    pixels.append((x, y))
        else:  # x - y equation
            for x in range(
                max(0, diag_value), min(self.width, diag_value + self.height)
            ):
                y = x - diag_value
                if 0 <= y < self.height:
                    pixels.append((x, y))
        return pixels

    def _get_diagonal_pixel_chains(self, pixels):
        """Group consecutive pixels on a diagonal into chains with the same pixel value."""
        if not pixels:
            return []

        last_pixel = None
        segments = []
        current_chain = []

        for x, y in pixels:
            pixel = self.px(x, y)
            on = 0 if pixel == self.skip_pixel else pixel

            if on:
                if on == last_pixel and current_chain:
                    current_chain.append((x, y))
                else:
                    if current_chain:
                        segments.append(
                            [current_chain[0], current_chain[-1], last_pixel]
                        )
                    current_chain = [(x, y)]
                last_pixel = on
            else:
                if current_chain:
                    segments.append([current_chain[0], current_chain[-1], last_pixel])
                    current_chain = []
                last_pixel = on

        if current_chain:
            segments.append([current_chain[0], current_chain[-1], last_pixel])

        return segments

    def _sort_diagonal_pixels(self, pixels, start_corner, diagonal_idx):
        """Sort pixels within a diagonal based on start corner and bidirectional settings."""
        alternate = self.bidirectional and diagonal_idx % 2 == 1

        # Define sorting keys for each corner
        def sort_top_left(p):
            return (-p[0], -p[1]) if alternate else (p[0], p[1])

        def sort_top_right(p):
            return (p[0], -p[1]) if alternate else (-p[0], p[1])

        def sort_bottom_left(p):
            return (-p[0], p[1]) if alternate else (p[0], -p[1])

        def sort_bottom_right(p):
            return (p[0], p[1]) if alternate else (-p[0], -p[1])

        sort_keys = {
            "top-left": sort_top_left,
            "top-right": sort_top_right,
            "bottom-left": sort_bottom_left,
            "bottom-right": sort_bottom_right,
        }

        return sorted(pixels, key=sort_keys[start_corner])

    def _process_diagonal_pixels(self, pixels, visited, position):
        """Process all pixels on a diagonal, yielding coordinates and handling overlaps."""
        current_x, current_y = position

        # Move to first pixel (travel move)
        first_x, first_y = pixels[0]
        if first_x != current_x or first_y != current_y:
            yield (first_x, first_y, 0)
            current_x, current_y = first_x, first_y

        # Process each pixel
        for x, y in pixels:
            if not visited[x, y]:
                visited[x, y] = True

                pixel = self.px(x, y)
                on = 0 if pixel == self.skip_pixel else pixel

                yield (x, y, on)
                current_x, current_y = x, y

        # Update position for caller
        position[0], position[1] = current_x, current_y

    """
    # Testpattern generation
    def testpattern_generator(self):
        def rectangle_h():
            # simple rectangle
            self.initial_x = 0
            self.initial_y = 0
            self.final_x = 0
            self.final_y = 0
            self.horizontal = True

            yield 0, 0, off
            yield self.width - 1, 0, on

            yield self.width - 1, self.height - 1, on

            yield 0, self.height - 1, on

            yield 0, 0, on

        def rectangle_v():
            # simple rectangle but start with y movements first
            self.initial_x = 0
            self.initial_y = 0
            self.final_x = 0
            self.final_y = 0
            self.horizontal = True

            yield 0, 0, off
            yield 0, self.height - 1, on

            yield self.width - 1, self.height - 1, on

            yield self.width - 1, 0, on

            yield 0, 0, on


        def snake_h():
            # horizontal snake
            self.initial_x = 0
            self.initial_y = 0
            x = 0
            y = 0
            self.horizontal = True
            yield 0, 0, off
            wd = self.width - 1
            left = True
            while y < self.height - 2:
                x = wd if left else 0
                self.horizontal = True
                yield x, y, on
                self.horizontal = False
                yield x, y + 2, on
                left = not left
                y += 2
                self.final_x = x
                self.final_y = y

        def snake_v():
            # vertical snake
            self.initial_x = 0
            self.initial_y = 0
            x = 0
            yield 0, 0, off
            ht = self.height - 1
            top = True
            while x < self.width - 2:
                y = ht if top else 0
                self.horizontal = False
                yield x, y, on
                self.horizontal = True
                yield x + 2, y, on
                top = not top
                x += 2
                self.final_x = x
                self.final_y = y

        def spiral():
            # Spiral to inside
            self.initial_x = 0
            self.initial_y = 0
            yield 0, 0, off

            x = -2 # start
            y = 0
            width = self.width + 1
            height = self.height - 1
            while width > 0 and height > 0:
                x += width
                y += 0
                self.horizontal = True
                yield x, y, on
                x += 0
                y += height
                self.horizontal = False
                yield x, y, on
                x -=(width - 2)
                y += 0
                self.horizontal = True
                yield x, y, on
                x += 0
                y -= (height - 2)
                self.horizontal = False
                yield x, y, on
                width -= 4
                height -= 4
                self.final_x = x
                self.final_y = y

        on = self.filter(0)
        off = 0
        # print (f"on={on}, off={off}")
        method = abs(self.direction) - 1
        methods = (rectangle_h, rectangle_v, snake_h, snake_v, spiral)
        try:
            yield from methods[method]()
        except IndexError:
            print (f"Unknown testgenerator for {self.direction}")
    """
