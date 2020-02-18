X_AXIS = 0
TOP = 0
LEFT = 0
BIDIRECTIONAL = 0
SKIPPING = 0
Y_AXIS = 1
BOTTOM = 2
RIGHT = 4
UNIDIRECTIONAL = 8
NO_SKIP = 16


class RasterPlotter:
    def __init__(self, data, width, height, traversal=0, skip_pixel=0, overscan=0,
                 offset_x=0, offset_y=0, step=1, px_filter=None):
        if px_filter is None:
            px_filter = self.null_filter
        self.data = data
        self.width = width
        self.height = height
        self.traversal = traversal
        self.skip_pixel = skip_pixel
        self.overscan = overscan
        self.offset_x = int(offset_x)
        self.offset_y = int(offset_y)
        self.step = step
        self.px_filter = px_filter
        x, y = self.calculate_first_pixel()
        self.initial_x = x
        self.initial_y = y

    def px(self, x, y):
        if 0 <= y < self.height and 0 <= x < self.width:
            return self.px_filter(self.data[x, y])
        raise IndexError  # For some unknown reason -y pixel access values work for a while

    def null_filter(self, p):
        """Default no op filter."""
        return p

    def leftmost_not_equal(self, y):
        """"Determine the leftmost pixel that is not equal to the skip_pixel value."""
        for x in range(0, self.width):
            pixel = self.px(x, y)
            if pixel != self.skip_pixel:
                return x
        return -1

    def topmost_not_equal(self, x):
        """Determine the topmost pixel that is not equal to the skip_pixel value"""
        for y in range(0, self.height):
            pixel = self.px(x, y)
            if pixel != self.skip_pixel:
                return y
        return -1

    def rightmost_not_equal(self, y):
        """Determine the rightmost pixel that is not equal to the skip_pixel value"""
        for x in range(self.width - 1, -1, -1):
            pixel = self.px(x, y)
            if pixel != self.skip_pixel:
                return x
        return self.width

    def bottommost_not_equal(self, x):
        """Determine the bottommost pixel that is not equal to teh skip_pixel value"""
        for y in range(self.height - 1, -1, -1):
            pixel = self.px(x, y)
            if pixel != self.skip_pixel:
                return y
        return self.height

    def nextcolor_left(self, x, y, default):
        """Determine the next pixel change going left from the (x,y) point.
        If no next pixel is found default is returned."""
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

    def nextcolor_top(self, x, y, default):
        """Determine the next pixel change going top from the (x,y) point.
            If no next pixel is found default is returned."""
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

    def nextcolor_right(self, x, y, default):
        """Determine the next pixel change going right from the (x,y) point.
            If no next pixel is found default is returned."""
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

    def nextcolor_bottom(self, x, y, default):
        """Determine the next pixel change going bottom from the (x,y) point.
            If no next pixel is found default is returned."""
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
        return self.width - 1

    def calculate_next_horizontal_pixel(self, y, dy=1, right=False):
        try:
            if right:
                while True:
                    x = self.rightmost_not_equal(y)
                    if x != self.width:
                        break
                    y += dy
            else:
                while True:
                    x = self.leftmost_not_equal(y)
                    if x != -1:
                        break
                    y += dy
        except IndexError:
            # Remaining image is blank
            return None, None
        return x, y

    def calculate_first_pixel(self):
        if (self.traversal & Y_AXIS) != 0:
            pass
        else:
            y = 0
            dy = 1
            if (self.traversal & BOTTOM) != 0:
                y = self.height - 1
                dy = -1
            x, y = self.calculate_next_horizontal_pixel(y, dy, self.traversal & RIGHT != 0)
            return x, y

    def initial_position(self):
        return self.initial_x, self.initial_y

    def initial_position_in_scene(self):
        if self.initial_x is None:  # image is blank.
            return self.offset_x, self.offset_y
        return self.offset_x + self.initial_x * self.step, self.offset_y + self.initial_y * self.step

    def initial_direction(self):
        """Returns the initial direction in the form of Left, Top, X-Momentum, Y-Momentum
        If we are rastering across the y, the x will have momentum.
        """
        t = self.traversal
        return (t & RIGHT) != 0, (t & BOTTOM) != 0, (t & Y_AXIS) == 0, (t & Y_AXIS) != 0

    def plot(self):
        """
        Plot the values relative to offset_x, offset_y with the traversal.
        px_filter is called to transform the pixels into their real values.
        Skip_pixel determines the pixel value that should not be traversed.
        """
        if self.initial_x is None:
            # There is no image.
            return
        width = self.width
        height = self.height

        traversal = self.traversal
        skip_pixel = self.skip_pixel
        overscan = self.overscan
        offset_x = int(self.offset_x)
        offset_y = int(self.offset_y)
        step = self.step

        x, y = self.initial_position()
        dx = 1
        dy = 1
        if (self.traversal & RIGHT) != 0:
            dx = -1
        if (self.traversal & BOTTOM) != 0:
            dy = -1
        yield offset_x + x * step, offset_y + y * step, 0
        if (traversal & Y_AXIS) != 0:
            # This code is for up/down across rastering.
            raise ValueError("This code is gone for now.")
        else:
            # This code is for top to bottom or bottom to top rastering.
            while 0 <= y < height:
                lower_bound = self.leftmost_not_equal(y)
                if lower_bound == -1:
                    y += dy
                    yield offset_x + x * step, offset_y + y * step, 0
                    continue
                upper_bound = self.rightmost_not_equal(y)

                next_x, next_y = self.calculate_next_horizontal_pixel(y + dy, dy, dx > 0)
                if next_x is not None:
                    upper_bound = max(next_x, upper_bound) + overscan
                    lower_bound = min(next_x, lower_bound) - overscan

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
                        yield offset_x + x * step, offset_y + y * step, 0
                    else:
                        yield offset_x + x * step, offset_y + y * step, pixel
                    if x == bound:
                        break
                if next_y is None:
                    # remaining image is blank, we stop right here.
                    break
                y = next_y
                yield offset_x + x * step, offset_y + y * step, 0
                dx = -dx
