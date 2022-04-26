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


class RasterPlotter:
    def __init__(
        self,
        data,
        width,
        height,
        traverse_x_axis=True,
        traverse_top=True,
        traverse_left=True,
        traverse_bidirectional=True,
        use_integers=True,
        skip_pixel=0,
        overscan=0,
        offset_x=0,
        offset_y=0,
        step_x=1,
        step_y=1,
        filter=None,
        alt_filter=None,
    ):
        """
        Initialization for the Raster Plotter function. This should set all the needed parameters for plotting.

        @param data: pixel data accessed through data[x,y] parameters
        @param width: Width of the given data.
        @param height: Height of the given data.
        @param traverse_x_axis: Flags for how the pixel traversal should be conducted.
        @param traverse_top: Flags for how the pixel traversal should be conducted.
        @param traverse_left: Flags for how the pixel traversal should be conducted.
        @param traverse_bidirectional: Flags for how the pixel traversal should be conducted.
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
        @param alt_filter: Pixel filter for the backswing of a unidirectional raster. The data[x,y] values are
                            static. But, an alternative backswing filter could allow for that some plotting to occur
                            on the backswing based on a different criteria than forward swing. By default, this returns
                            skip pixels, which will not plot anything.
        """
        self.data = data
        self.width = width
        self.height = height
        self.traverse_x_axis = traverse_x_axis
        self.traverse_top = traverse_top
        self.traverse_left = traverse_left
        self.traverse_bidirectional = traverse_bidirectional
        self.use_integers = use_integers
        self.skip_pixel = skip_pixel
        if traverse_x_axis:
            self.overscan = round(overscan / float(step_x))
        else:
            self.overscan = round(overscan / float(step_y))
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.step_x = step_x
        self.step_y = step_y
        self.filter = filter
        self.main_filter = filter
        self.alt_filter = alt_filter
        self.initial_x, self.initial_y = self.calculate_first_pixel()
        self.final_x, self.final_y = self.calculate_last_pixel()

    def swap(self):
        """
        Swaps the px_filter
        @return:
        """
        if self.filter == self.main_filter:
            self.filter = self.alt_filter
        else:
            self.filter = self.main_filter

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

    def calculate_next_horizontal_pixel(self, y, dy=1, rightside=False):
        """
        Find the horizontal extreme at the given y-scanline, stepping by dy in the target image.
        This can be done on either the rightside (True) or leftside (False).

        @param y: y-scanline
        @param dy: dy-step amount (usually should be -1 or 1)
        @param rightside: rightside / leftside.
        @return:
        """
        try:
            if rightside:
                while True:
                    x = self.rightmost_not_equal(y)
                    if x is not None:
                        break
                    y += dy
            else:
                while True:
                    x = self.leftmost_not_equal(y)
                    if x is not None:
                        break
                    y += dy
        except IndexError:
            # Remaining image is blank
            return None, None
        return x, y

    def calculate_next_vertical_pixel(self, x, dx=1, bottomside=False):
        """
        Find the vertical extreme at the given x-scanline, stepping by dx in the target image.
        This can be done on either the bottomside (True) or topide (False).

        @param x: x-scanline
        @param dx: dx-step amount (usually should be -1 or 1)
        @param bottomside: bottomside / topside.
        @return:
        """
        try:
            if bottomside:
                while True:
                    # find that the bottommost pixel in that row.
                    y = self.bottommost_not_equal(x)

                    if y is not None:
                        # This is a valid pixel.
                        break
                    # No pixel in that row was valid. Move to the next row.
                    x += dx
            else:
                while True:
                    y = self.topmost_not_equal(x)
                    if y is not None:
                        break
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
        if self.vertical:
            x = 0
            dx = 1
            if self.right:  # Start on Right Edge?
                x = self.width - 1
                dx = -1
            x, y = self.calculate_next_vertical_pixel(x, dx, self.bottom)
            return x, y
        else:
            y = 0
            dy = 1
            if self.bottom:  # Start on Bottom Edge?
                y = self.height - 1
                dy = -1
            x, y = self.calculate_next_horizontal_pixel(y, dy, self.right)
            return x, y

    def calculate_last_pixel(self):
        """
        Find the last non-skipped pixel in the rastering.

        This takes into account the traversal values of X_AXIS or Y_AXIS and BOTTOM and RIGHT

        @return: x,y coordinates of last pixel.
        """
        if self.vertical:
            x = 0
            dx = 1
            if self.left and self.height & 1:
                x = self.width - 1
                dx = -1
            x, y = self.calculate_next_vertical_pixel(x, dx, self.top)
            return x, y
        else:
            y = 0
            dy = 1
            if self.top and self.width & 1:
                y = self.height - 1
                dy = -1
            x, y = self.calculate_next_horizontal_pixel(y, dy, self.left)
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

    @property
    def top(self):
        return self.traverse_top

    @property
    def bottom(self):
        return not self.traverse_top

    @property
    def right(self):
        return not self.traverse_left

    @property
    def left(self):
        return self.traverse_left

    @property
    def horizontal(self):
        """
        Major raster axis is horizontal
        @return:
        """
        return self.traverse_x_axis

    @property
    def vertical(self):
        """
        Major raster axis is vertical
        @return:
        """
        return not self.traverse_x_axis

    @property
    def rightward(self):
        """
        Raster will progress towards right
        @return:
        """
        return self.left  # starting on left and moving horizontal.

    @property
    def leftward(self):
        """
        Raster will progress towards left
        @return:
        """
        return self.right

    @property
    def topward(self):
        """
        Raster will progress towards top
        @return:
        """
        return self.bottom

    @property
    def bottomward(self):
        """
        Raster will progress towards bottom
        @return:
        """
        return self.top

    @property
    def rightward_major(self):
        """
        Raster major movements are right.
        @return:
        """
        return self.left and self.horizontal  # starting on left and moving horizontal.

    @property
    def leftward_major(self):
        """
        Raster major movements are left
        @return:
        """
        return self.right and self.horizontal

    @property
    def topward_major(self):
        """
        Raster major movements are top
        @return:
        """
        return self.bottom and self.vertical

    @property
    def bottomward_major(self):
        """
        Raster major movements are bottom.
        @return:
        """
        return self.top and self.vertical

    @property
    def rightward_minor(self):
        """
        Raster minor scanline ticks are right.
        @return:
        """
        return self.left and self.vertical  # starting on left and moving horizontal.

    @property
    def leftward_minor(self):
        """
        Raster minor scanline ticks are left.
        @return:
        """
        return self.right and self.vertical

    @property
    def topward_minor(self):
        """
        Raster minor scanline ticks are top.
        @return:
        """
        return self.bottom and self.horizontal

    @property
    def bottomward_minor(self):
        """
        Raster minor scanline ticks are bottom.
        @return:
        """
        return self.top and self.horizontal

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
        if self.use_integers:
            for x, y, on in self.plot_pixels():
                yield int(round(offset_x + step_x * x)), int(
                    round(offset_y + y * step_y)
                ), on
        else:
            for x, y, on in self.plot_pixels():
                yield offset_x + step_x * x, offset_y + y * step_y, on

    def plot_pixels(self):
        width = self.width
        height = self.height

        skip_pixel = self.skip_pixel

        x, y = self.initial_position()
        dx = 1
        dy = 1
        if self.right:
            dx = -1
        if self.bottom:
            dy = -1
        yield x, y, 0
        if self.vertical:
            # This code is for vertical rastering.
            while 0 <= x < width:
                lower_bound = self.topmost_not_equal(x)
                if lower_bound is None:
                    x += dx
                    yield x, y, 0
                    continue
                upper_bound = self.bottommost_not_equal(x)

                next_x, next_y = self.calculate_next_vertical_pixel(x + dx, dx, dy > 0)
                if next_y is not None:
                    upper_bound = max(next_y, upper_bound) + self.overscan
                    lower_bound = min(next_y, lower_bound) - self.overscan

                while (dy > 0 and y <= upper_bound) or (dy < 0 and lower_bound <= y):
                    if dy > 0:  # going right
                        bound = upper_bound
                        try:
                            pixel = self.px(x, y)
                        except IndexError:
                            pixel = 0
                        y = self.nextcolor_bottom(x, y, upper_bound)
                        y = min(y, upper_bound)
                    else:
                        bound = lower_bound
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
                    if y == bound:
                        break
                if next_x is None:
                    # remaining image is blank, we stop right here.
                    break
                x = next_x
                yield x, y, 0
                dy = -dy
        else:
            # This code is horizontal rastering.
            while 0 <= y < height:
                lower_bound = self.leftmost_not_equal(y)
                if lower_bound is None:
                    y += dy
                    yield x, y, 0
                    continue
                upper_bound = self.rightmost_not_equal(y)

                next_x, next_y = self.calculate_next_horizontal_pixel(
                    y + dy, dy, dx > 0
                )
                if next_x is not None:
                    upper_bound = max(next_x, upper_bound) + self.overscan
                    lower_bound = min(next_x, lower_bound) - self.overscan

                while (dx > 0 and x <= upper_bound) or (dx < 0 and lower_bound <= x):
                    if dx > 0:  # going right
                        bound = upper_bound
                        try:
                            pixel = self.px(x, y)
                        except IndexError:
                            pixel = 0
                        x = self.nextcolor_right(x, y, upper_bound)
                        x = min(x, upper_bound)
                    else:
                        bound = lower_bound
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
                    if x == bound:
                        break
                if next_y is None:
                    # remaining image is blank, we stop right here.
                    break
                y = next_y
                yield x, y, 0
                dx = -dx
