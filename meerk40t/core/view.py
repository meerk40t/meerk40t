from meerk40t.core.units import MM_PER_INCH, UNITS_PER_INCH, Length
from meerk40t.svgelements import Matrix


class View:
    def __init__(
        self,
        width,
        height,
        dpi=float(UNITS_PER_INCH),
        dpi_x=None,
        dpi_y=None,
        native_scale_x=None,
        native_scale_y=None,
    ):
        """
        This should init the simple width and height dimensions.

        The default coordinate system is (0,0), (width,0), (width,height), (0,height), In top_left, top_right,
        bottom_right, bottom_left ordering.

        @param width:
        @param height:
        """

        if native_scale_x is not None:
            dpi_x = UNITS_PER_INCH / native_scale_x
        if native_scale_y is not None:
            dpi_y = UNITS_PER_INCH / native_scale_y
        if dpi_x is None:
            dpi_x = dpi
        if dpi_y is None:
            dpi_y = dpi
        self.width = width
        self.height = height
        self.dpi_x = dpi_x
        self.dpi_y = dpi_y
        self.dpi = (dpi_x + dpi_y) / 2.0
        self.margin_x = 0.0
        self.margin_y = 0.0
        self._source = None
        self._destination = None
        self._matrix = None
        self.reset()

    def realize(self):
        self._matrix = None

    def __str__(self):
        return f"View('{self.width}', '{self.height}', @{self.dpi} {self._destination})"

    @property
    def native_scale_x(self):
        return UNITS_PER_INCH / self.dpi_x

    @property
    def native_scale_y(self):
        return UNITS_PER_INCH / self.dpi_y

    @property
    def mm(self):
        return self.dpi * MM_PER_INCH

    def set_native_scale(self, native_scale_x, native_scale_y):
        """
        Sets the native scaling for this view.

        @param native_scale_x:
        @param native_scale_y:
        @return:
        """
        dpi_x = UNITS_PER_INCH / native_scale_x
        dpi_y = UNITS_PER_INCH / native_scale_y
        self.dpi_x = dpi_x
        self.dpi_y = dpi_y
        self.dpi = (dpi_x + dpi_y) / 2.0
        self.reset()

    def set_dims(self, width, height):
        self.width = width
        self.height = height
        self.reset()

    def set_margins(self, offset_x, offset_y):
        self.margin_x = offset_x
        self.margin_y = offset_y
        # print (f"Margins were set to {offset_x}, {offset_y}")

    def reset(self):
        width = float(Length(self.width))
        height = float(Length(self.height))

        top_left = 0, 0
        top_right = width, 0
        bottom_right = width, height
        bottom_left = 0, height
        self._source = top_left, top_right, bottom_right, bottom_left
        self._destination = top_left, top_right, bottom_right, bottom_left
        # Pre-scale destination by reverse of native scale.
        self.scale(1.0 / self.native_scale_x, 1.0 / self.native_scale_y)

    def destination_contains(self, x, y):
        """
        This solves the AABB of the container, not the strict solution. If a view is rotated by a non-tau/4 multiple
        amount, we could generate false positives.
        @param x:
        @param y:
        @return:
        """
        # This solves the AABB of the container, not the strict solution
        x0, y0, x1, y1 = self.destination_bbox()
        return x0 <= x <= x1 and y0 <= y <= y1

    def destination_bbox(self):
        return (
            min(
                self._destination[0][0],
                self._destination[1][0],
                self._destination[2][0],
                self._destination[3][0],
            ),
            min(
                self._destination[0][1],
                self._destination[1][1],
                self._destination[2][1],
                self._destination[3][1],
            ),
            max(
                self._destination[0][0],
                self._destination[1][0],
                self._destination[2][0],
                self._destination[3][0],
            ),
            max(
                self._destination[0][1],
                self._destination[1][1],
                self._destination[2][1],
                self._destination[3][1],
            ),
        )

    def source_contains(self, x, y):
        """
        This solves the AABB of the container, not the strict solution. If a view is rotated by a non-tau/4 multiple
        amount, we could generate false positives.
        @param x:
        @param y:
        @return:
        """
        # This solves the AABB of the container, not the strict solution
        x0, y0, x1, y1 = self.source_bbox()
        return x0 <= x <= x1 and y0 <= y <= y1

    def source_bbox(self):
        return (
            min(
                self._source[0][0],
                self._source[1][0],
                self._source[2][0],
                self._source[3][0],
            ),
            min(
                self._source[0][1],
                self._source[1][1],
                self._source[2][1],
                self._source[3][1],
            ),
            max(
                self._source[0][0],
                self._source[1][0],
                self._source[2][0],
                self._source[3][0],
            ),
            max(
                self._source[0][1],
                self._source[1][1],
                self._source[2][1],
                self._source[3][1],
            ),
        )

    def scale(self, scale_x, scale_y):
        width = float(Length(self.width))
        height = float(Length(self.height))

        width *= scale_x
        height *= scale_y
        top_left, top_right, bottom_right, bottom_left = self._destination
        top_left, top_right, bottom_right, bottom_left = (
            (top_left[0] * scale_x, top_left[1] * scale_y),
            (top_right[0] * scale_x, top_right[1] * scale_y),
            (bottom_right[0] * scale_x, bottom_right[1] * scale_y),
            (bottom_left[0] * scale_x, bottom_left[1] * scale_y),
        )
        self._destination = top_left, top_right, bottom_right, bottom_left
        self._matrix = None

    def origin(self, origin_x, origin_y):
        width = float(Length(self.width) / self.native_scale_x)
        height = float(Length(self.height) / self.native_scale_x)

        dx = -width * origin_x
        dy = -height * origin_y

        top_left, top_right, bottom_right, bottom_left = self._destination
        self._destination = (
            (top_left[0] + dx, top_left[1] + dy),
            (top_right[0] + dx, top_right[1] + dy),
            (bottom_right[0] + dx, bottom_right[1] + dy),
            (bottom_left[0] + dx, bottom_left[1] + dy),
        )
        self._matrix = None

    def flip_x(self):
        top_left, top_right, bottom_right, bottom_left = self._destination
        self._destination = (
            top_right,
            top_left,
            bottom_left,
            bottom_right,
        )
        self._matrix = None

    def flip_y(self):
        top_left, top_right, bottom_right, bottom_left = self._destination
        self._destination = (
            bottom_left,
            bottom_right,
            top_right,
            top_left,
        )
        self._matrix = None

    def swap_xy(self):
        top_left, top_right, bottom_right, bottom_left = self._destination
        self._destination = (
            (top_left[1], top_left[0]),
            (top_right[1], top_right[0]),
            (bottom_right[1], bottom_right[0]),
            (bottom_left[1], bottom_left[0]),
        )
        self._matrix = None

    def transform(
        self,
        user_scale_x=1.0,
        user_scale_y=1.0,
        flip_x=False,
        flip_y=False,
        swap_xy=False,
        origin_x=0.0,
        origin_y=0.0,
    ):
        self.reset()
        if origin_x or origin_y:
            self.origin(origin_x, origin_y)
        self.scale(user_scale_x, user_scale_y)
        if flip_x:
            self.flip_x()
        if flip_y:
            self.flip_y()
        if swap_xy:
            self.swap_xy()

    def rotate_ccw(self):
        top_left, top_right, bottom_right, bottom_left = self._destination
        self._destination = (top_right, bottom_right, bottom_left, top_left)
        self._matrix = None

    def rotate_cw(self):
        top_left, top_right, bottom_right, bottom_left = self._destination
        self._destination = (bottom_left, top_left, top_right, bottom_right)
        self._matrix = None

    def _get_offset(self):
        try:
            off_x = Length(self.margin_x, relative_length=self.width, unitless=1).units
        except ValueError:
            off_x = 0
        try:
            off_y = Length(self.margin_y, relative_length=self.height, unitless=1).units
        except ValueError:
            off_y = 0
        return off_x, off_y

    def position(self, x, y, vector=False, margins=True):
        """
        Position from the source to the destination position. The result is in destination units.
        @param x:
        @param y:
        @param vector:
        @return:
        """
        if margins:
            off_x, off_y = self._get_offset()
        else:
            off_x = 0
            off_y = 0
        # print (f"Will apply offset: {off_x}, {off_y} to {x}, {y}")
        if not isinstance(x, (int, float)):
            x = Length(x, relative_length=self.width, unitless=1).units
        if not isinstance(y, (int, float)):
            y = Length(y, relative_length=self.height, unitless=1).units
        unit_x, unit_y = x, y
        if vector:
            res = self.matrix.transform_vector([unit_x, unit_y])
            res[0] = res[0] + off_x
            res[1] = res[1] + off_y
            return res
        res = self.matrix.point_in_matrix_space([unit_x, unit_y])
        res.x = res.x + off_x
        res.y = res.y + off_y
        return res

    def scene_position(self, x, y):
        if not isinstance(x, (int, float)):
            x = Length(x, relative_length=self.width, unitless=1).units
        if not isinstance(y, (int, float)):
            y = Length(y, relative_length=self.height, unitless=1).units
        return x, y

    def iposition(self, x, y, vector=False):
        """
        Position from the destination to the source position. The result is in source units.

        @param x:
        @param y:
        @param vector:
        @return:
        """
        off_x, off_y = self._get_offset()
        unit_x = x - off_x
        unit_y = y - off_y
        matrix = ~self.matrix
        if vector:
            return matrix.transform_vector([unit_x, unit_y])
        return matrix.point_in_matrix_space([unit_x, unit_y])

    @property
    def matrix(self):
        if self._matrix is None:
            self._matrix = Matrix.map(*self._source, *self._destination)
        return self._matrix

    def get_sensible_dpi_values(self) -> list:
        # Look for dpis beyond 100 where we have an integer step value.
        # We assume for this exercise that the x-axis is good enough
        candidates = []
        unit_x = UNITS_PER_INCH
        matrix = self.matrix
        oneinch_x = abs(complex(*matrix.transform_vector([unit_x, 0])))
        lastdpi = None
        for steps in range(1, 100):
            dpi = int(round(oneinch_x / steps, 0))
            if dpi < 75:
                break
            if dpi>1000:
                continue
            if lastdpi is None or dpi % 25 < 5 or dpi % 33 < 3:
                lastdpi = dpi
                candidates.append(dpi)
        # print (candidates)
        return candidates

    def dpi_to_steps(self, dpi):
        """
        Converts a DPI to a given step amount within the device length values. So M2 Nano will have 1 step per mil,
        the DPI of 500 therefore is step_x 2, step_y 2. A Galvo laser with a 200mm lens will have steps equal to
        200mm/65536 ~= 0.12 mils. So a DPI of 500 needs a step size of ~16.65 for x and y. Since 500 DPI is one dot
        per 2 mils.

        Note, steps size can be negative if our driver is x or y flipped.

        @param dpi:
        @return:
        """
        # We require vectors so any positional offsets are non-contributing.
        unit_x = UNITS_PER_INCH
        unit_y = UNITS_PER_INCH
        matrix = self.matrix
        oneinch_x = abs(complex(*matrix.transform_vector([unit_x, 0])))
        oneinch_y = abs(complex(*matrix.transform_vector([0, unit_y])))
        step_x = float(oneinch_x / dpi)
        step_y = float(oneinch_y / dpi)
        return step_x, step_y

    @property
    def unit_width(self):
        return float(Length(self.width))

    @property
    def unit_height(self):
        return float(Length(self.height))
