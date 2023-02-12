from ...svgelements import Point
from ...tools.zinglplotter import ZinglPlotter
from .cutobject import CutObject


class PlotCut(CutObject):
    """
    Plot cuts are a series of lineto values with laser on and off info. These positions are not necessarily next
    to each other and can be any distance apart. This is a compact way of writing a large series of line positions.

    There is a raster-create value.
    """

    def __init__(self, settings=None, passes=1, color=None):
        CutObject.__init__(self, settings=settings, passes=passes, color=color)
        self._points = []
        self._powers = []
        self.max_dx = None
        self.max_dy = None
        self.min_x = None
        self.min_y = None
        self.max_x = None
        self.max_y = None
        self.v_raster = False
        self.h_raster = False
        self.travels_top = False
        self.travels_bottom = False
        self.travels_right = False
        self.travels_left = False
        self._calc_lengths = None
        self._length = None
        self.first = True  # Plot cuts are standalone
        self.last = True

    def __len__(self):
        return len(self._points)

    def __str__(self):
        parts = list()
        parts.append(f"{len(self._points)} points")
        parts.append(f"xmin: {self.min_x}")
        parts.append(f"ymin: {self.min_y}")
        parts.append(f"xmax: {self.max_x}")
        parts.append(f"ymax: {self.max_y}")
        return f"PlotCut({', '.join(parts)})"

    def __bool__(self):
        return bool(self._points)

    def check_if_rasterable(self):
        """
        Rasterable plotcuts are heuristically defined as having a max step of less than 15 and
        must have an unused travel direction.

        @return: whether the plot can travel
        """
        # Default to vector settings.
        self.settings["raster_step_x"] = 0
        self.settings["raster_step_y"] = 0
        if self.settings.get("speed", 0) < 80:
            # Twitchless gets sketchy at 80.
            self.settings["_force_twitchless"] = True
            return False
        if self.max_dx is None:
            return False
        if self.max_dy is None:
            return False
        # Above 80 we're likely dealing with a raster.
        if -15 < self.max_dx <= 15:
            self.v_raster = True
            self.settings["raster_step_x"] = self.max_dx
        if -15 < self.max_dy <= 15:
            self.h_raster = True
            self.settings["raster_step_y"] = self.max_dy
        return True

    def transform(self, matrix):
        for i in range(len(self._points)):
            x, y = self._points[i]
            x, y = matrix.transform_point([x, y])
            self._points[i] = int(x), int(y)

    def plot_init(self, x, y):
        self._points.append((x, y))

    def plot_extend(self, plot):
        for x, y, laser in plot:
            self.plot_append(x, y, laser)

    def plot_append(self, x, y, laser):
        self._length = None
        self._calc_lengths = None
        if self._points:
            last_x, last_y = self._points[-1]
            dx = x - last_x
            dy = y - last_y
            if self.max_dx is None or abs(dx) > abs(self.max_dx):
                self.max_dx = dx
            if self.max_dy is None or abs(dy) > abs(self.max_dy):
                self.max_dy = dy
            if dy > 0:
                self.travels_bottom = True
            if dy < 0:
                self.travels_top = True
            if dx > 0:
                self.travels_right = True
            if dx < 0:
                self.travels_left = True
        self._points.append((x,y))
        self._powers.append(laser)
        if self.min_x is None or x < self.min_x:
            self.min_x = x
        if self.min_y is None or y < self.min_y:
            self.min_y = y
        if self.max_x is None or x > self.max_x:
            self.max_x = x
        if self.max_y is None or y > self.max_y:
            self.max_y = y

    def major_axis(self):
        """
        If both vertical and horizontal are set we prefer vertical as major axis because vertical rastering is heavier
        with the movement of the gantry bar.
        @return:
        """
        if self.v_raster:
            return 1
        if self.h_raster:
            return 0

        if len(self._points) < 2:
            return 0
        start = Point(self._points[0])
        end = Point(self._points[1])
        if abs(start.x - end.x) > abs(start.y - end.y):
            return 0  # X-Axis
        else:
            return 1  # Y-Axis

    def x_dir(self):
        if self.travels_left and not self.travels_right:
            return -1  # right
        if self.travels_right and not self.travels_left:
            return 1  # left

        if len(self._points) < 2:
            return 0
        start = Point(self._points[0])
        for i in range(1, len(self._points)):
            end = Point(self._points[i])
            if start.x < end.x:
                return 1
            elif start.x > end.x:
                return -1
        return 0

    def y_dir(self):
        if self.travels_top and not self.travels_bottom:
            return -1  # top
        if self.travels_bottom and not self.travels_top:
            return 1  # bottom

        if len(self._points) < 2:
            return 0
        start = Point(self._points[0])
        for i in range(1, len(self._points)):
            end = Point(self._points[i])
            if start.y < end.y:
                return 1
            elif start.y > end.y:
                return -1
        return 0

    def upper(self):
        return self.min_x

    def lower(self):
        return self.max_x

    def left(self):
        return self.min_y

    def right(self):
        return self.max_y

    def length(self):
        length = 0
        last_x = None
        last_y = None
        for x, y in self._points:
            if last_x is not None:
                length += Point.distance((x, y), (last_x, last_y))
            last_x = 0
            last_y = 0
        return length

    def reverse(self):
        self._points = list(reversed(self._points))
        self._powers = list(reversed(self._powers))

    @property
    def start(self):
        try:
            return Point(self._points[0])
        except IndexError:
            return None

    @property
    def end(self):
        try:
            return Point(self._points[-1])
        except IndexError:
            return None

    @property
    def plot(self):
        x1 = None
        y1 = None
        for i in range(0, len(self._points)):
            x0, y0 = self._points[i]
            if x1 is not None:
                power = self._powers[i-1]
                if self.h_raster and y0 != y1:
                    yield x0, y0, power, x1, y0
                    yield x1, y0, power, x1, y1
                elif self.v_raster and x0 != x1:
                    yield x0, y0, power, x0, y1
                    yield x0, y1, power, x1, y1
                else:
                    yield x0, y0, power, x1, y1
            x1 = x0
            y1 = y0

    def generator(self):
        last_xx = None
        last_yy = None
        ix = 0
        iy = 0
        for i in range(0, len(self._points)):
            x, y = self._points[i]
            idx = int(round(x - ix))
            idy = int(round(y - iy))
            ix += idx
            iy += idy
            if last_xx is not None:
                # Will not happen if i == 0
                power = self._powers[i-1]
                for zx, zy in ZinglPlotter.plot_line(last_xx, last_yy, ix, iy):
                    yield zx, zy, power
            last_xx = ix
            last_yy = iy

    def point(self, t):
        if len(self._points) == 0:
            raise ValueError
        if t == 0:
            return self._points[0]
        if t == 1:
            return self._points[-1]
        if self._calc_lengths is None:
            # Need to calculate lengths
            lengths = list()
            total_length = 0
            for i in range(len(self._points) - 1):
                x0, y0 = self._points[i]
                x1, y1 = self._points[i + 1]
                length = abs(complex(x0, y0) - complex(x1, y1))
                lengths.append(length)
                total_length += length
            self._calc_lengths = lengths
            self._length = total_length
        if self._length == 0:
            # Degenerate fallback. (All points are coincident)
            v = int((len(self._points) - 1) * t)
            return self._points[v]
        v = t * self._length
        for length in self._calc_lengths:
            if v < length:
                x0, y0 = self.start
                x1, y1 = self.end
                x = x1 * v + x0
                y = y1 * v + y0
                return x, y
            v -= length
        raise ValueError
