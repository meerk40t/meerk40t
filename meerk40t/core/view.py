from meerk40t.core.units import UNITS_PER_INCH, MM_PER_INCH, Length


class View:
    def __init__(
        self, width, height, dpi=float(UNITS_PER_INCH), dpi_x=None, dpi_y=None
    ):
        """
        This should init the simple width and height dimensions.

        The default coordinate system is (0,0), (width,0), (width,height), (0,height), In top_left, top_right,
        bottom_right, bottom_left ordering.

        @param width:
        @param height:
        """
        if dpi_x is None:
            dpi_x = dpi
        if dpi_y is None:
            dpi_y = dpi
        self.width = width
        self.height = height
        self.dpi_x = dpi_x
        self.dpi_y = dpi_y
        self.dpi = (dpi_x + dpi_y) / 2.0

        self.user_width = None
        self.user_height = None
        self.coords = None
        # self.reset()

    def __str__(self):
        return f"View('{self.width}', '{self.height}', @{self.dpi})"

    @property
    def mm(self):
        return self.dpi * MM_PER_INCH

    def set_dims(self, width, height):
        self.width = width
        self.height = height
        self.reset()

    def reset(self):
        self.user_width = self.length(self.width, axis=0)
        self.user_height = self.length(self.height, axis=1)

        top_left = 0, 0
        top_right = self.user_width, 0
        bottom_right = self.user_width, self.user_height
        bottom_left = 0, self.user_height
        self.coords = top_left, top_right, bottom_right, bottom_left

    def length(self, length, axis=0):
        if axis == 0:
            return (
                Length(length, relative_length=self.width, unitless=1.0).inches
                * self.dpi_x
            )
        else:
            return (
                Length(length, relative_length=self.height, unitless=1.0).inches
                * self.dpi_y
            )

    def physical(self, x, y):
        return self.length(x, axis=0), self.length(y, axis=1)

    def contains(self, x, y):
        """
        This solves the AABB of the container, not the strict solution. If a view is rotated by a non-tau/4 multiple
        amount, we could generate false positives.
        @param x:
        @param y:
        @return:
        """
        # This solves the AABB of the container, not the strict solution
        x0, y0, x1, y1 = self.bbox()
        return x0 < x < x1 and y0 < y < y1

    def bbox(self):
        return (
            min(
                self.coords[0][0],
                self.coords[1][0],
                self.coords[2][0],
                self.coords[3][0],
            ),
            min(
                self.coords[0][1],
                self.coords[1][1],
                self.coords[2][1],
                self.coords[3][1],
            ),
            max(
                self.coords[0][0],
                self.coords[1][0],
                self.coords[2][0],
                self.coords[3][0],
            ),
            max(
                self.coords[0][1],
                self.coords[1][1],
                self.coords[2][1],
                self.coords[3][1],
            ),
        )

    def scale(self, scale_x, scale_y):
        self.user_width *= scale_x
        self.user_height *= scale_y
        top_left, top_right, bottom_right, bottom_left = self.coords
        top_left, top_right, bottom_right, bottom_left = (
            (top_left[0] * scale_x, top_left[1] * scale_y),
            (top_right[0] * scale_x, top_right[1] * scale_y),
            (bottom_right[0] * scale_x, bottom_right[1] * scale_y),
            (bottom_left[0] * scale_x, bottom_left[1] * scale_y),
        )
        self.coords = top_left, top_right, bottom_right, bottom_left

    def origin(self, origin_x, origin_y):
        dx = self.user_width * -origin_x
        dy = self.user_height * -origin_y

        top_left, top_right, bottom_right, bottom_left = self.coords
        top_left, top_right, bottom_right, bottom_left = (
            (top_left[0] + dx, top_left[1] + dy),
            (top_right[0] + dx, top_right[1] + dy),
            (bottom_right[0] + dx, bottom_right[1] + dy),
            (bottom_left[0] + dx, bottom_left[1] + dy),
        )
        self.coords = top_left, top_right, bottom_right, bottom_left

    def flip_x(self):
        top_left, top_right, bottom_right, bottom_left = self.coords
        top_left, top_right, bottom_right, bottom_left = (
            top_right,
            top_left,
            bottom_left,
            bottom_right,
        )
        self.coords = top_left, top_right, bottom_right, bottom_left

    def flip_y(self):
        top_left, top_right, bottom_right, bottom_left = self.coords
        top_left, top_right, bottom_right, bottom_left = (
            bottom_left,
            bottom_right,
            top_right,
            top_left,
        )
        self.coords = top_left, top_right, bottom_right, bottom_left

    def swap_xy(self):
        top_left, top_right, bottom_right, bottom_left = self.coords
        top_left, top_right, bottom_right, bottom_left = (
            (top_left[1], top_left[0]),
            (top_right[1], top_right[0]),
            (bottom_right[1], bottom_right[0]),
            (bottom_left[1], bottom_left[0]),
        )
        self.coords = top_left, top_right, bottom_right, bottom_left

    def transform(
        self,
        origin_x=0.0,
        origin_y=0.0,
        user_scale_x=1.0,
        user_scale_y=1.0,
        flip_x=False,
        flip_y=False,
        swap_xy=False,
    ):
        self.reset()
        self.scale(1.0 / user_scale_x, 1.0 / user_scale_y)
        if flip_x:
            self.flip_x()
        if flip_y:
            self.flip_y()
        if origin_x != 0 or origin_y != 0:
            self.origin(origin_x, origin_y)
        if swap_xy:
            self.swap_xy()
