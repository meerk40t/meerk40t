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

Please note that the plot created needs to be always orthogonal or strictly diagonal
from point to point. So you can't 'jump' from (1, 1) to (2, 3) so you would need to
use a (1, 1) -> (1, 3) -> (2, 3) sequence.
"""


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
        shift_lines=0,
        filter=None,
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
        """
        self.data = data
        self.width = width
        self.height = height
        self.horizontal = horizontal
        self.start_minimum_x = start_minimum_x
        self.start_minimum_y = start_minimum_y
        self.bidirectional = bidirectional
        self.use_integers = use_integers
        self.skip_pixel = skip_pixel
        if horizontal:
            self.overscan = overscan / float(step_x)
            self.shift_lines = shift_lines/ float(step_x)
        else:
            self.overscan = overscan / float(step_y)
            self.shift_lines = shift_lines/ float(step_y)
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.step_x = step_x
        self.step_y = step_y
        self.filter = filter
        self.initial_x, self.initial_y = self.calculate_first_pixel()
        self.final_x, self.final_y = self.calculate_last_pixel()
        self._pixel_check = ""
        self._last_x = None
        self._last_y = None

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
        # print (f"Plot called: overscan: {self.overscan}, bidir={self.bidirectional}, start_x at min={self.start_minimum_x}, start_y at min={self.start_minimum_y}, dimension={self.width}x{self.height}")

        offset_x = self.offset_x
        offset_y = self.offset_y
        step_x = self.step_x
        step_y = self.step_y
        if self.initial_x is None:
            # There is no image.
            return
        # for x in range(self.width):
        #     for y in range(self.height):
        #         print (f"[{x}, {y}] = {self.px(x, y)} vs {self.data[x, y]}")
        if self.use_integers:
            for x, y, on in self._plot_pixels():
                yield int(round(offset_x + step_x * x)), int(
                    round(offset_y + y * step_y)
                ), on
        else:
            for x, y, on in self._plot_pixels():
                yield offset_x + step_x * x, offset_y + y * step_y, on

    def _plot_pixels(self):
        if self.horizontal:
            yield from self._plot_horizontal()
        else:
            yield from self._plot_vertical()

    def reset_pixel_check(self):
        self._last_x = None
        self._last_y = None

    def check_pixel_to_be_yielded(self, x, y, source=""):
        origin = "Horizontal" if self.horizontal else "Vertical"
        if self._last_x is None:
            self._last_x = x
            self._last_y = y
            return True
        total_dx = x - self._last_x
        total_dy = y - self._last_y
        # Prepare error message
        message = f"{origin} {source}: must be uniformly diagonal or orthogonal: ({total_dx}, {total_dy}) is not. Last: {self._last_x}, {self._last_y}, this: {x}, {y}"
        self._last_x = x
        self._last_y = y
        if total_dx == 0 and total_dy == 0:
            return True
        dx = 1 if total_dx > 0 else 0 if total_dx == 0 else -1
        dy = 1 if total_dy > 0 else 0 if total_dy == 0 else -1

        if total_dy * dx != total_dx * dy:
            # Check for cross-equality.
            print(message)
            return False

        return True

    def _plot_vertical(self):
        """
        This code is for vertical rastering.

        @return:
        """
        width = self.width
        unidirectional = not self.bidirectional
        shift_value = 0 if unidirectional else self.shift_lines
        skip_pixel = self.skip_pixel

        x, y = self.initial_position()
        dx = 1 if self.start_minimum_x else -1
        dy = 1 if self.start_minimum_y else -1

        shift_factor = 0 if self.start_minimum_y else 1
        self.reset_pixel_check()
        self.check_pixel_to_be_yielded(x, y + shift_factor * shift_value)
        yield x, y + shift_factor * shift_value, 0
        while 0 <= x < width:
            lower_bound = self.topmost_not_equal(x)
            if lower_bound is None:
                x += dx
                self.check_pixel_to_be_yielded(x, y + shift_value, "skipline")
                yield x, y + shift_value, 0
                continue
            upper_bound = self.bottommost_not_equal(x)
            traveling_bottom = self.start_minimum_y if unidirectional else dy >= 0
            next_traveling_bottom = self.start_minimum_y if unidirectional else dy <= 0

            next_x, next_y = self.calculate_next_vertical_pixel(
                x + dx, dx, topmost_pixel=next_traveling_bottom
            )
            if next_y is not None:
                # If we have a next scanline, we must end after the last pixel of that scanline too.
                upper_bound = max(next_y, upper_bound)
                lower_bound = min(next_y, lower_bound)
            last_pixel = 0
            if upper_bound == lower_bound: # Just one pixel, but hey a pixel is a pixel
                pixel = self.px(x, y)
                last_pixel = 0 if pixel == skip_pixel else pixel
                if last_pixel:
                    if traveling_bottom:
                        # Send half a pixel to make it register
                        self.check_pixel_to_be_yielded(x , y, "1px")
                        yield x, y, last_pixel
                        yield x, y + 0.5, last_pixel
                    else:
                        self.check_pixel_to_be_yielded(x, y + shift_value, "1px")
                        yield x, y + shift_value, last_pixel
                        yield x, y + shift_value + 0.5, last_pixel
            if traveling_bottom:
                # No shift from top to bottom
                while y < upper_bound:
                    try:
                        pixel = self.px(x, y)
                    except IndexError:
                        pixel = 0
                    y = self.nextcolor_bottom(x, y, upper_bound)
                    y = min(y, upper_bound)
                    last_pixel = 0 if pixel == skip_pixel else pixel
                    self.check_pixel_to_be_yielded(x, y, "v")
                    yield x, y, last_pixel
            else:
                # Optional shifting if bidirectional
                while lower_bound < y:
                    try:
                        pixel = self.px(x, y)
                    except IndexError:
                        pixel = 0
                    y = self.nextcolor_top(x, y, lower_bound)
                    y = max(y, lower_bound)
                    last_pixel = 0 if pixel == skip_pixel else pixel
                    self.check_pixel_to_be_yielded(x, y + shift_value, "^")
                    yield x, y + shift_value, last_pixel

            if next_y is None:
                # remaining image is blank, we stop right here.
                return
            lasty = y
            # Stop the line in all cases:
            gap = 0 if traveling_bottom else shift_value
            if last_pixel:
                lasty = upper_bound if traveling_bottom else lower_bound
                self.check_pixel_to_be_yielded(x, lasty + gap, "lineend")
                yield x, lasty + gap, 0
            # We are done and at the end of our scanline, so let's apply the overscan value
            if self.overscan:
                lasty = y + dy * self.overscan
                self.check_pixel_to_be_yielded(x, lasty + gap, "overscan")
                yield x, lasty + gap, 0
            # Lets go to the next line, this may be shifted
            self.check_pixel_to_be_yielded(next_x, lasty + gap, "nextline")
            yield next_x, lasty + gap, 0

            lasty += gap # For comparison
            gap = shift_value if traveling_bottom else 0
            if lasty != next_y + gap:
                self.check_pixel_to_be_yielded(next_x, next_y + gap, "move2nexty")
                yield next_x, next_y + gap, 0
            x = next_x
            y = next_y
            if not unidirectional:
                dy = -dy

    def _plot_horizontal(self):
        """
        This code is horizontal rastering.

        @return:
        """
        height = self.height
        unidirectional = not self.bidirectional
        shift_value = 0 if unidirectional else self.shift_lines
        skip_pixel = self.skip_pixel

        x, y = self.initial_position()
        dx = 1 if self.start_minimum_x else -1
        dy = 1 if self.start_minimum_y else -1
        shift_factor = 0 if self.start_minimum_x else 1

        self.reset_pixel_check()
        self.check_pixel_to_be_yielded(x + shift_factor * shift_value, y)
        yield x + shift_factor * shift_value, y, 0
        line_counter = 0
        while 0 <= y < height:
            lower_bound = self.leftmost_not_equal(y)
            if lower_bound is None:
                y += dy
                self.check_pixel_to_be_yielded(x + shift_value, y, "skipline")
                yield x + shift_value, y, 0
                continue
            upper_bound = self.rightmost_not_equal(y)
            traveling_right = self.start_minimum_x if unidirectional else dx >= 0
            next_traveling_right = self.start_minimum_x if unidirectional else dx <= 0

            next_x, next_y = self.calculate_next_horizontal_pixel(
                y + dy, dy, leftmost_pixel=next_traveling_right
            )
            if next_x is not None:
                # If we have a next scanline, we must end after the last pixel of that scanline too.
                upper_bound = max(next_x, upper_bound)
                lower_bound = min(next_x, lower_bound)

            last_pixel = 0
            if upper_bound == lower_bound: # Just one pixel, but hey a pixel is a pixel
                pixel = self.px(x, y)
                last_pixel = 0 if pixel == skip_pixel else pixel
                if last_pixel:
                    if traveling_right:
                        # Send half a pixel to make it register
                        self.check_pixel_to_be_yielded(x, y, "1px")
                        yield x, y, last_pixel
                        yield x + 0.5, y, last_pixel
                    else:
                        self.check_pixel_to_be_yielded(x + shift_value, y, "1px")
                        yield x + shift_value, y, last_pixel
                        yield x + shift_value + 0.5, y, last_pixel

            if traveling_right:
                # No shift from left to right
                while x < upper_bound:
                    try:
                        pixel = self.px(x, y)
                    except IndexError:
                        pixel = 0
                    x = self.nextcolor_right(x, y, upper_bound)
                    x = min(x, upper_bound)
                    last_pixel = 0 if pixel == skip_pixel else pixel
                    self.check_pixel_to_be_yielded(x , y, ">")
                    yield x, y, last_pixel
            else:
                # Optional shifting if bidirectional
                while lower_bound < x:
                    try:
                        pixel = self.px(x, y)
                    except IndexError:
                        pixel = 0
                    x = self.nextcolor_left(x, y, lower_bound)
                    x = max(x, lower_bound)
                    last_pixel = 0 if pixel == skip_pixel else pixel
                    self.check_pixel_to_be_yielded(x + shift_value, y, "<")
                    yield x + shift_value, y, last_pixel

            if next_y is None:
                # remaining image is blank, we stop right here.
                return
            # We are done and at the end of our scanline, so let's apply the overscan value
            # Stop the line in all cases:
            lastx = x
            gap = 0 if traveling_right else shift_value
            if last_pixel:
                lastx = upper_bound if traveling_right else lower_bound
                self.check_pixel_to_be_yielded(lastx + gap, y, "lineend")
                yield lastx + gap, y, 0
            if self.overscan:
                lastx = x + dx * self.overscan
                self.check_pixel_to_be_yielded(lastx + gap, y, "overscan")
                yield lastx + gap, y, 0
            # Lets go to the next line, this may be shifted
            self.check_pixel_to_be_yielded(lastx + gap, next_y, "nextline")
            yield lastx + gap, next_y, 0

            lastx += gap # For comparison
            gap = shift_value if traveling_right else 0
            if lastx != next_x + gap:
                self.check_pixel_to_be_yielded(next_x + gap, next_y, "move2nextx")
                yield next_x + gap, next_y, 0
            x = next_x
            y = next_y
            if not unidirectional:
                dx = -dx
            line_counter += 1
