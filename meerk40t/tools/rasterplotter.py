"""
The RasterPlotter is a plotter that maps particular raster pixels to directional and raster
methods. This class should be expanded to cover most raster situations.

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
"""

import numpy as np
from time import perf_counter

class RasterPlotter:
    def __init__(
        self,
        data,
        width,
        height,
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
        opt_method=False,
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
        @param opt_method: activate experimental greedy path optimisation
        """
        self.debug = False
        self.data = data
        self.width = width
        self.height = height
        self.horizontal = horizontal
        self.start_minimum_y = start_minimum_y
        self.start_minimum_x = start_minimum_x
        self.bidirectional = bidirectional
        self.use_integers = use_integers
        self.skip_pixel = skip_pixel
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
        self.opt_method = opt_method

    def px(self, x, y):
        """
        Returns the filtered pixel

        @param x:
        @param y:
        @return: Filtered Pixel
        """
        if 0 <= y < self.height and 0 <= x < self.width:
            if self.filter is None:
                return self.data[x, y]
            return self.filter(self.data[x, y])
        raise IndexError

    def leftmost_not_equal(self, y):
        """
        Determine the leftmost pixel that is not equal to the skip_pixel value.

        if all pixels skipped returns None
        """
        for x in range(0, self.width):
            pixel = self.px(x, y)
            if pixel != self.skip_pixel:
                return x
        return None

    def topmost_not_equal(self, x):
        """
        Determine the topmost pixel that is not equal to the skip_pixel value

        if all pixels skipped returns None
        """
        for y in range(0, self.height):
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

    # def nextcolor_left(self, x, y, default=None):
    #     """
    #     Determine the next pixel change going left from the (x,y) point.
    #     If no next pixel is found default is returned.
    #     """
    #     if x <= -1:
    #         return default
    #     if x == 0:
    #         return -1
    #     if x == self.width:
    #         return self.width - 1
    #     if self.width < x:
    #         return self.width

    #     v = self.px(x, y)
    #     for ix in range(x, -1, -1):
    #         pixel = self.px(ix, y)
    #         if pixel != v:
    #             return ix
    #     return 0

    # def nextcolor_top(self, x, y, default=None):
    #     """
    #     Determine the next pixel change going top from the (x,y) point.
    #     If no next pixel is found default is returned.
    #     """
    #     if y <= -1:
    #         return default
    #     if y == 0:
    #         return -1
    #     if y == self.height:
    #         return self.height - 1
    #     if self.height < y:
    #         return self.height

    #     v = self.px(x, y)
    #     for iy in range(y, -1, -1):
    #         pixel = self.px(x, iy)
    #         if pixel != v:
    #             return iy
    #     return 0

    # def nextcolor_right(self, x, y, default=None):
    #     """
    #     Determine the next pixel change going right from the (x,y) point.
    #     If no next pixel is found default is returned.
    #     """
    #     if x < -1:
    #         return -1
    #     if x == -1:
    #         return 0
    #     if x == self.width - 1:
    #         return self.width
    #     if self.width <= x:
    #         return default

    #     v = self.px(x, y)
    #     for ix in range(x, self.width):
    #         pixel = self.px(ix, y)
    #         if pixel != v:
    #             return ix
    #     return self.width - 1

    # def nextcolor_bottom(self, x, y, default=None):
    #     """
    #     Determine the next pixel change going bottom from the (x,y) point.
    #     If no next pixel is found default is returned.
    #     """
    #     if y < -1:
    #         return -1
    #     if y == -1:
    #         return 0
    #     if y == self.height - 1:
    #         return self.height
    #     if self.height <= y:
    #         return default

    #     v = self.px(x, y)
    #     for iy in range(y, self.height):
    #         pixel = self.px(x, iy)
    #         if pixel != v:
    #             return iy
    #     return self.height - 1

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
        if self.horizontal:
            y = 0 if self.start_minimum_y else self.height - 1
            dy = 1 if self.start_minimum_y else -1
            x, y = self.calculate_next_horizontal_pixel(y, dy, self.start_minimum_x)
            return x, y
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
        if self.horizontal:
            y = self.height - 1 if self.start_minimum_y else 0
            dy = -1 if self.start_minimum_y else 1
            start_on_left = (
                self.start_minimum_x if self.width & 1 else not self.start_minimum_x
            )
            x, y = self.calculate_next_horizontal_pixel(y, dy, start_on_left)
            return x, y
        else:
            x = self.width - 1 if self.start_minimum_x else 0
            dx = -1 if self.start_minimum_x else 1
            start_on_top = (
                self.start_minimum_y if self.height & 1 else not self.start_minimum_y
            )
            x, y = self.calculate_next_vertical_pixel(x, dx, start_on_top)
            return x, y

    def initial_position(self):
        """
        Returns raw initial position for the relevant pixel within the data.
        @return: initial position within the data.
        """
        if self.use_integers:
            return int(round(self.initial_x)), int(round(self.initial_y))
        else:
            return self.initial_x, self.initial_y

    def initial_position_in_scene(self):
        """
        Returns the initial position for this within the scene. Taking into account start corner, and step size.
        @return: initial position within scene. The first plot location.
        """
        if self.initial_x is None:  # image is blank.
            if self.use_integers:
                return int(round(self.offset_x)), int(round(self.offset_y))
            else:
                return self.offset_x, self.offset_y
        if self.use_integers:
            return (
                int(round(self.offset_x + self.initial_x * self.step_x)),
                int(round(self.offset_y + self.initial_y * self.step_y)),
            )
        else:
            return (
                self.offset_x + self.initial_x * self.step_x,
                self.offset_y + self.initial_y * self.step_y,
            )

    def final_position_in_scene(self):
        """
        Returns best guess of final position relative to the scene offset. Taking into account start corner, and parity
        of the width and height.
        @return:
        """
        if self.final_x is None:  # image is blank.
            if self.use_integers:
                return int(round(self.offset_x)), int(round(self.offset_y))
            else:
                return self.offset_x, self.offset_y
        if self.use_integers:
            return (
                int(round(self.offset_x + self.final_x * self.step_x)),
                int(round(self.offset_y + self.final_y * self.step_y)),
            )
        else:
            return (
                self.offset_x + self.final_x * self.step_x,
                self.offset_y + self.final_y * self.step_y,
            )

    def plot(self):
        """
        Plot the values yielded by following the given raster plotter in the traversal defined.
        """
        offset_x = self.offset_x
        offset_y = self.offset_y
        step_x = self.step_x
        step_y = self.step_y
        if self.initial_x is None:
            # There is no image.
            return
        # Debug code....
        if self.debug:
            data = list(self._plot_pixels())
            from time import perf_counter_ns
            from platform import system
            defaultdir = "c:\\temp\\" if system() == "Windows" else ""
            has_duplicates = 0
            with open(f"{defaultdir}plot_{perf_counter_ns()}.txt", mode="w") as f:
                f.write(f"0.9.6\n{'Bidirectional' if self.bidirectional else 'Unidirectional'} {'horizontal' if self.horizontal else 'vertical'} plot starting at {'top' if self.start_minimum_y else 'bottom'}-{'left' if self.start_minimum_x else 'right'}\n")
                f.write(f"Overscan: {self.overscan:.2f}, Stepx={step_x:.2f}, Stepy={step_y:.2f}\n")
                f.write(f"Image dimensions: {self.width}x{self.height}\n")
                f.write(f"Startpoint: {self.initial_x}, {self.initial_y}")
                f.write("-----------------------------------------------------------------------------------------------------------------------------\n")
                test_dict = {}
                lastx = self.initial_x
                lasty = self.initial_y
                for lineno, (x, y, on) in enumerate(data, start=1):
                    key = f"{x} - {y}"
                    if key in test_dict:
                        f.write (f"Duplicate coordinates in list at ({x}, {y})! 1st: #{test_dict[key][0]}, on={test_dict[key][1]}, 2nd: #{lineno}, on={on}\n")
                        has_duplicates += 1
                    else:
                        test_dict[key] = (lineno, on)
                    if lastx is not None:
                        dx = x - lastx
                        dy = y - lasty
                        if dx != 0 and dy != 0: # and abs(dx) != abs(dy):
                            f.write (f"You fucked up! No zigzag movement from line {lineno - 1} to {lineno}: {lastx}, {lasty} -> {x}, {y}\n")
                            print (f"You fucked up! No zigzag movement from line {lineno - 1} to {lineno}: {lastx}, {lasty} -> {x}, {y}")
                    lastx = x
                    lasty = y
                f.write("-----------------------------------------------------------------------------------------------------------------------------\n")
                for lineno, (x, y, on) in enumerate(data, start=1):
                    f.write(f"{lineno}: {x}, {y}, {on}\n")
                if has_duplicates:
                    print(f"Attention: the generated plot has {has_duplicates} duplicate coordinate values!")
                    print(f"{'Bidirectional' if self.bidirectional else 'Unidirectional'} {'horizontal' if self.horizontal else 'vertical'} plot starting at {'top' if self.start_minimum_y else 'bottom'}-{'left' if self.start_minimum_x else 'right'}")
                    print(f"Overscan: {self.overscan:.2f}, Stepx={step_x:.2f}, Stepy={step_y:.2f}")
                    print(f"Image dimensions: {self.width}x{self.height}")
            if self.use_integers:
                for x, y, on in data:
                    yield int(round(offset_x + step_x * x)), int(round(offset_y + y * step_y)), on
            else:
                for x, y, on in data:
                    yield offset_x + step_x * x, offset_y + y * step_y, on
        else:
            if self.use_integers:
                for x, y, on in self._plot_pixels():
                    yield int(round(offset_x + step_x * x)), int(round(offset_y + y * step_y)), on
            else:
                for x, y, on in self._plot_pixels():
                    yield offset_x + step_x * x, offset_y + y * step_y, on

    def _plot_pixels(self):
        if self.opt_method == 1:
            yield from self._plot_greedy_neighbour(horizontal=self.horizontal)
        elif self.opt_method == 2:
            yield from self._plot_crossover()
        elif self.horizontal:
            yield from self._plot_horizontal()
        else:
            yield from self._plot_vertical()
            # yield from self._plot_vertical()

    def _get_pixel_chains(self, xy:int, is_x : bool) -> list:
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
                    segments.append ([idx, idx, on])
            last_pixel = on
        return segments

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
        unidirectional = not self.bidirectional

        dx = 1 if self.start_minimum_x else -1
        dy = 1 if self.start_minimum_y else -1
        last_y = None
        had_a_segment = False
        lower = min(self.initial_x, self.final_x)
        upper = max(self.initial_x, self.final_x)
        x = lower if self.start_minimum_x else upper
        while lower <= x <= upper:
            segments = self._get_pixel_chains(x, False)
            if segments:
                had_a_segment = True
                if dy > 0:
                    # from top to bottom
                    idx = 0
                    start = 0
                    end = 1
                    edge_start = 0
                    edge_end = 1
                else:
                    idx = len(segments) - 1
                    end = 0
                    start = 1
                    edge_start = 1
                    edge_end = 0
                if last_y is None:
                    last_y = segments[idx][start] + edge_start
                # Goto next column, but make sure we end up outside our chain
                # We consider as well the overscan value
                overscan_top = 0 if dy >= 0 else self.overscan
                overscan_bottom = 0 if dy <= 0 else self.overscan
                if segments[0][0] - overscan_top <= last_y <= segments[-1][1] + overscan_bottom:
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
                    yield x - dx, last_y, 0
                yield x, last_y, 0
                while 0 <= idx < len(segments):
                    sy = segments[idx][start] + edge_start
                    ey = segments[idx][end] + edge_end
                    on = segments[idx][2]
                    if last_y != sy:
                        yield x, sy, 0
                    yield x, ey, on
                    last_y = ey
                    idx += dy
                if self.overscan:
                    last_y += dy * self.overscan
                    yield x, last_y, 0
                if not unidirectional:
                    dy = -dy
            else:
                # Just climb the line, and don't change directions
                if had_a_segment:
                    if last_y is None:
                        last_y = 0
                    yield x, last_y, 0

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
        unidirectional = not self.bidirectional

        dx = 1 if self.start_minimum_x else -1
        dy = 1 if self.start_minimum_y else -1
        last_x = None
        had_a_segment = False
        lower = min(self.initial_y, self.final_y)
        upper = max(self.initial_y, self.final_y)
        y = lower if self.start_minimum_y else upper
        while lower <= y <= upper:
            segments = self._get_pixel_chains(y, True)
            if segments:
                had_a_segment = True
                if dx > 0:
                    # from left to right
                    idx = 0
                    start = 0
                    end = 1
                    edge_start = 0
                    edge_end = 1
                else:
                    idx = len(segments) - 1
                    end = 0
                    start = 1
                    edge_start = 1
                    edge_end = 0
                if last_x is None:
                    last_x = segments[idx][start] + edge_start
                # Goto next line, but make sure we end up outside our chain
                # We consider as well the overscan value
                overscan_left = 0 if dx >= 0 else self.overscan
                overscan_right = 0 if dx <= 0 else self.overscan
                if segments[0][0] - overscan_left <= last_x <= segments[-1][1] + overscan_right:
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
                yield last_x, y, 0
                while 0 <= idx < len(segments):
                    sx = segments[idx][start] + edge_start
                    ex = segments[idx][end] + edge_end
                    on = segments[idx][2]
                    if last_x != sx:
                        yield sx, y, 0
                    yield ex, y, on
                    last_x = ex
                    idx += dx
                if self.overscan:
                    last_x += dx * self.overscan
                    yield last_x, y, 0
                if not unidirectional:
                    dx = -dx
            else:
                # Just climb the line, and don't change directions
                if had_a_segment:
                    if last_x is None:
                        last_x = 0
                    yield last_x, y, 0
            y += dy

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

        def walk_segments(segments, horizontal=True, xy_penalty=1, width=1, height=1):
            n:int = len(segments)
            visited = np.zeros(n, dtype=bool)
            path = []
            window_size = 10
            current_point = np.array(segments[0][0], dtype=float)
            segment_points = np.array([point for segment in segments for point in segment], dtype=float)
            mask = ~visited.repeat(2)
            while len(path) < n:
                # Find the range of segments within the x- and y-window
                x_min = current_point[0] - window_size
                x_max = current_point[0] + window_size
                y_min = current_point[1] - window_size
                y_max = current_point[1] + window_size
                unvisited_indices = np.where(
                    (segment_points[:, 0] >= x_min) &
                    (segment_points[:, 0] <= x_max) &
                    (segment_points[:, 1] >= y_min) &
                    (segment_points[:, 1] <= y_max) &
                    mask
                )[0]
                if len(unvisited_indices) == 0:
                    # If no segments are within the window, expand the window
                    window_size *= 2
                    # print (f"Did not find points: now window: {window_size}")
                    if window_size <= 2* height or window_size <= 2 * width: # Safety belt
                        continue

                unvisited_points = segment_points[unvisited_indices]

                # distances = distance_matrix(unvisited_points, current_point, y_penalty)
                diff = unvisited_points - current_point
                if horizontal:
                    diff[:, 1] *= xy_penalty # Apply penalty to y-distances
                else:
                    diff[:, 0] *= xy_penalty # Apply penalty to x-distances

                distances = np.sum(diff ** 2, axis=1) # Return squared distances

                min_distance_idx = np.argmin(distances)
                next_segment = unvisited_indices[min_distance_idx] // 2

                if not visited[next_segment]:
                    visited[next_segment] = True
                    # mask = ~visited.repeat(2)
                    mask[2 * next_segment] = False
                    mask[2 * next_segment + 1] = False
                    if min_distance_idx % 2 == 0:
                        path.append((next_segment, 'end'))
                        current_point = segment_points[next_segment * 2 + 1]  # Move to the other endpoint
                    else:
                        path.append((next_segment, 'start'))
                        current_point = segment_points[next_segment * 2]  # Move to the other endpoint
                    window_size = 10 # Reset window size

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
        if self.debug:
            print (f"{'horizontal' if horizontal else 'Vertical'} for {self.width}x{self.height} image. {'y' if horizontal else 'x'} from {lower} to {upper}")
        if horizontal:
            while lower <= y <= upper:
                segments = self._get_pixel_chains(y, True)
                for seg in segments:
                    # Append (xstart, y), (xend, y), on
                    line_parts.append( ( (seg[0], y), (seg[1], y) ) )
                    on_parts.append(seg[2])
                y += dy
        else:
            while lower <= x <= upper:
                segments = self._get_pixel_chains(x, False)
                for seg in segments:
                    # Append (xstart, y), (xend, y), on
                    line_parts.append( ( (x, seg[0]), (x, seg[1]) ) )
                    on_parts.append(seg[2])
                x += dx
        if self.debug:
            print (f"Created {len(line_parts)} segments")
        t1 = perf_counter()
        path = walk_segments(line_parts, horizontal=horizontal, xy_penalty=3, width=self.width, height=self.height)
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
            # print (f"[{idx}] -> {line_parts[abs(idx)]} -> {sx}, {sy} to {ex}, {ey} with {on:.2f}")
            if horizontal:
                dx = ex - sx
                if dx >= 0:
                    # from left to right
                    edge_start = 0
                    edge_end = 1
                else:
                    edge_start = 1
                    edge_end = 0
                sx += edge_start
                ex += edge_end
                if sy != last_y:
                    yield last_x, sy, 0
                if last_x != sx:
                    yield sx, sy, 0
            else:
                dy = ey - sy
                if dy >= 0:
                    # from left to right
                    edge_start = 0
                    edge_end = 1
                else:
                    edge_start = 1
                    edge_end = 0
                sy += edge_start
                ey += edge_end
                if sx != last_x:
                    yield sx, last_y, 0
                if last_y != sy:
                    yield sx, sy, 0

            yield ex, ey, on
            last_x = ex
            last_y = ey
        t3 = perf_counter()
        if self.debug:
            print (f"Overall time for {'horizontal' if horizontal else 'vertical'} consumption: {t3-t0:.2f}s - created: {len(line_parts)} segments")
            print (f"Computation: {t2-t0:.2f}s - Chain creation:{t1 - t0:.2f}s, Walk: {t2 - t1:.2f}s")
        self.final_x = last_x
        self.final_y = last_y

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
        ROW=0
        COL=1

        def process_image(image):
            # We will modify the image to keep track of deleted rows and columns
            # Get the dimensions of the image
            rows, cols = image.shape

            # Initialize a list to store the results
            results = []


            # Iterate through the matrix, we cover all rows and cols
            colidx = 0
            rowidx = 0
            covered_row = [False] * rows
            covered_col = [False] * cols
            stored_row = np.zeros(rows)
            stored_col = np.zeros(cols)
            recalc_row = True
            recalc_col = True
            while True:
                if recalc_col:
                    for i in range(cols):
                        if covered_col[i]:
                            count = 0
                        else:
                            count = np.count_nonzero(image[:, i])
                            if count == 0:
                                covered_col[i] = True
                        stored_col[i] = count
                if recalc_row:
                    for i in range(rows):
                        if covered_row[i]:
                            count = 0
                        else:
                            count = np.count_nonzero(image[i, :])
                            if count == 0:
                                covered_row[i] = True
                        stored_row[i] = count
                colidx = np.argmax(stored_col)
                rowidx = np.argmax(stored_row)
                col_count = stored_col[colidx]
                row_count = stored_row[rowidx]

                if row_count == col_count == 0:
                    break
                # Determine whether there are more pixels in the row or column
                if row_count >= col_count:
                    last_pixel = None
                    segments = []
                    counted = 0
                    for idx in range(cols):
                        on = image[rowidx, idx]
                        if on:
                            counted += 1
                            if on == last_pixel:
                                segments[-1][1] = idx
                            else:
                                segments.append ([idx, idx, on])
                        last_pixel = on
                    results.append((COL, rowidx, segments)) # Intentionally so, as the numpy array has x and y exchanged
                    # Clear the column
                    image[rowidx,:] = 0
                    covered_row[rowidx] = True
                    stored_row[rowidx] = 0
                    recalc_col = True
                else:
                    last_pixel = None
                    segments = []
                    counted = 0
                    msg = ""
                    for idx in range(rows):
                        on = image[idx, colidx]
                        msg = f"{msg}{'X' if on else '.'}"
                        if on:
                            counted += 1
                            if on == last_pixel:
                                segments[-1][1] = idx
                            else:
                                segments.append ([idx, idx, on])
                        last_pixel = on
                    results.append((ROW, colidx, segments))
                    # Clear the row
                    image[:, colidx] = 0
                    covered_col[colidx] = True
                    stored_col[colidx] = 0
                    recalc_row = True

            return results

        t0 = perf_counter()
        # initialize the matrix
        image = np.empty((self.width, self.height))
        # Apply filter and eliminate skip_pixel
        for x in range(self.width):
            for y in range(self.height):
                px = self.px(x, y)
                if px==self.skip_pixel:
                    px = 0
                image[x, y] = px
        t1 = perf_counter()
        results = process_image(image)
        results.sort()
        t2 = perf_counter()
        dx = 1
        dy = 1
        first_x = 0
        first_y = 0
        last_x = self.initial_x
        last_y = self.initial_y
        yield last_x, last_y, 0
        first = True
        for mode, idx, segments in results:
            # eliminate data and swap direction
            if not segments:
                continue
            if (mode==ROW and dx < 0) or (mode==COL and dy < 0):
                segments.reverse()
            if mode==ROW:
                line_start_x = segments[0][0] if dx >= 0 else segments[0][1]
                line_start_y = idx
            else:
                line_start_x = idx
                line_start_y = segments[0][0] if dy >= 0 else segments[0][1]
            if first:
                first = False
                first_x = line_start_x
                first_y = line_start_y
            covered = 0
            if line_start_y != last_y:
                last_y = line_start_y
                yield last_x, last_y, 0
                covered += 1
            if last_x != line_start_x:
                last_x = line_start_x
                yield last_x, last_y, 0
                covered += 1
            if covered != 2:
                last_x = line_start_x
                last_y = line_start_y
                yield last_x, last_y, 0
            for seg in segments:
                if mode==ROW:
                    sy = idx
                    ey = idx
                    if dx >= 0:
                        sx, ex, on = seg
                        edge_start = 0
                        edge_end = 1
                    else:
                        ex, sx, on = seg
                        edge_start = 1
                        edge_end = 0
                    sx += edge_start
                    ex += edge_end

                    if sx != last_x:
                        last_x = sx
                        yield last_x, last_y, 0
                    if last_y != sy:
                        last_y = sy
                        yield last_x, last_y, 0
                else:
                    sx = idx
                    ex = idx
                    if dy >= 0:
                        sy, ey, on = seg
                        edge_start = 0
                        edge_end = 1
                    else:
                        ey, sy, on = seg
                        edge_start = 1
                        edge_end = 0
                    # sy += edge_start
                    # ey += edge_end
                    if sy != last_y:
                        last_y = sy
                        yield last_x, last_y, 0
                    if last_x != sx:
                        last_x = sx
                        yield last_x, last_y, 0

                last_x = ex
                last_y = ey
                yield last_x, last_y, on
            # All segments done, do we need to go further aka overscan
            if self.overscan:
                if mode == ROW:
                    last_x += dx * self.overscan
                else:
                    last_y += dy * self.overscan
                yield last_x, last_y, 0

            if mode == ROW:
                dx = -dx
            else: # column
                dy = -dy

        # We need to set the final values so that the rastercut is able to carry on
        self.final_x = last_x
        self.final_y = last_y
        t3 = perf_counter()
        if self.debug:
            print (f"Overall time for crossover consumption: {t3-t0:.2f}s")
            print (f"Computation: {t2 - t0:.2f}s - Array creation:{t1 - t0:.2f}s, Algorithm: {t2 - t1:.2f}s")

