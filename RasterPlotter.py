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

    def null_filter(self, p):
        """Default no op filter."""
        return p

    def leftmost_not_equal(self, y):
        """"Determine the leftmost pixel that is not equal to the skip_pixel value."""
        for x in range(0, self.width):
            pixel = self.px_filter(self.data[x, y])
            if pixel != self.skip_pixel:
                return x
        return -1

    def topmost_not_equal(self, x):
        """Determine the topmost pixel that is not equal to the skip_pixel value"""
        for y in range(0, self.height):
            pixel = self.px_filter(self.data[x, y])
            if pixel != self.skip_pixel:
                return y
        return -1

    def rightmost_not_equal(self, y):
        """Determine the rightmost pixel that is not equal to the skip_pixel value"""
        for x in range(self.width - 1, -1, -1):
            pixel = self.px_filter(self.data[x, y])
            if pixel != self.skip_pixel:
                return x
        return self.width

    def bottommost_not_equal(self, x):
        """Determine the bottommost pixel that is not equal to teh skip_pixel value"""
        for y in range(self.height - 1, -1, -1):
            pixel = self.px_filter(self.data[x, y])
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

        v = self.px_filter(self.data[x, y])
        for ix in range(x, -1, -1):
            pixel = self.px_filter(self.data[ix, y])
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

        v = self.px_filter(self.data[x, y])
        for iy in range(y, -1, -1):
            pixel = self.px_filter(self.data[x, iy])
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

        v = self.px_filter(self.data[x, y])
        for ix in range(x, self.width):
            pixel = self.px_filter(self.data[ix, y])
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

        v = self.px_filter(self.data[x, y])
        for iy in range(y, self.height):
            pixel = self.px_filter(self.data[x, iy])
            if pixel != v:
                return iy
        return self.width - 1

    def initial_position(self):
        x = 0
        y = 0
        if (self.traversal & RIGHT) != 0:
            x = self.width - 1
        if (self.traversal & BOTTOM) != 0:
            y = self.height - 1
        return x, y

    def initial_position_in_scene(self):
        x = 0
        y = 0
        if (self.traversal & RIGHT) != 0:
            x = self.width - 1
        if (self.traversal & BOTTOM) != 0:
            y = self.height - 1
        return self.offset_x + x, self.offset_y + y

    def initial_direction(self):
        dx = 1
        dy = 1
        if (self.traversal & RIGHT) != 0:
            dx = -1
        if (self.traversal & BOTTOM) != 0:
            dy = -1
        return dx, dy

    def plot(self):
        """
        Plot the values relative to offset_x, offset_y with the traversal.
        px_filter is called to transform the pixels into their real values.
        Skip_pixel determines the pixel value that should not be traversed.
        """
        data = self.data
        width = self.width
        height = self.height

        traversal = self.traversal
        skip_pixel = self.skip_pixel
        overscan = self.overscan
        offset_x = int(self.offset_x)
        offset_y = int(self.offset_y)
        step = self.step
        px_filter = self.px_filter

        offset_x = int(offset_x)
        offset_y = int(offset_y)
        x, y = self.initial_position()
        dx, dy = self.initial_direction()
        yield offset_x + x * step, offset_y + y * step, 0
        if (traversal & Y_AXIS) != 0:
            # This code is for up/down across rastering.
            while 0 <= x < width:
                lower_bound = self.topmost_not_equal(x)
                if lower_bound == -1:
                    x += dx
                    yield offset_x + x * step, offset_y + y * step, 0
                    continue
                upper_bound = self.bottommost_not_equal(x)
                while (dy > 0 and y <= upper_bound) or (dy < 0 and lower_bound <= y):
                    if dy > 0:  # going bottom
                        end = upper_bound + overscan
                        if 0 <= x + dx < width:
                            end = max(end,
                                      self.bottommost_not_equal(x + dx))
                        pixel = px_filter(data[x, y])
                        y = self.nextcolor_bottom(x, y, end)
                        y = min(y, end)
                    else:
                        end = lower_bound - overscan
                        if 0 <= x + dx < width:
                            end = min(end, self.topmost_not_equal(x + dx))
                        pixel = px_filter(data[x, y])
                        y = self.nextcolor_top(x, y, end)
                        y = max(y, end)
                    if pixel == skip_pixel:
                        yield offset_x + x * step, offset_y + y * step, 0
                    else:
                        yield offset_x + x * step, offset_y + y * step, pixel
                    if y == end:
                        break
                x += dx
                yield offset_x + x * step, offset_y + y * step, 0
                dy = -dy
        else:
            # This code is for top to bottom or bottom to top rastering.
            while 0 <= y < height:
                lower_bound = self.leftmost_not_equal(y)
                if lower_bound == -1:
                    y += dy
                    yield offset_x + x * step, offset_y + y * step, 0
                    continue
                upper_bound = self.rightmost_not_equal(y)
                while (dx > 0 and x <= upper_bound) or (dx < 0 and lower_bound <= x):
                    if dx > 0:  # going right
                        end = upper_bound + overscan
                        if 0 <= y + dy < height:
                            end = max(end, self.rightmost_not_equal(y + dy))
                        try:
                            pixel = px_filter(data[x, y])
                        except IndexError:
                            pixel = 0
                        x = self.nextcolor_right(x, y, end)
                        x = min(x, end)
                    else:
                        end = lower_bound - overscan
                        if 0 <= y + dy < height:
                            end = min(end, self.leftmost_not_equal(y + dy))
                        try:
                            pixel = px_filter(data[x, y])
                        except IndexError:
                            pixel = 0
                        x = self.nextcolor_left(x, y, end)
                        x = max(x, end)
                    if pixel == skip_pixel:
                        yield offset_x + x * step, offset_y + y * step, 0
                        #print("(%d, %d) %f" % (offset_x + x * step, offset_y + y * step, 0.0))
                    else:
                        yield offset_x + x * step, offset_y + y * step, pixel
                        #print("(%d, %d) %f" % (offset_x + x * step, offset_y + y * step, pixel))
                    if x == end:
                        break
                y += dy
                yield offset_x + x * step, offset_y + y * step, 0
                #print("(%d, %d) %f" % (offset_x + x * step, offset_y + y * step, 0))
                dx = -dx
