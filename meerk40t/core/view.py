from meerk40t.core.units import UNITS_PER_INCH, Length, MM_PER_INCH
from meerk40t.svgelements import Matrix


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
        self._source = None
        self._destination = None
        self._matrix = None

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
        width = float(Length(self.width))
        height = float(Length(self.height))

        top_left = 0, 0
        top_right = width, 0
        bottom_right = width, height
        bottom_left = 0, height
        self._source = top_left, top_right, bottom_right, bottom_left
        self._destination = top_left, top_right, bottom_right, bottom_left

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
        width = float(Length(self.width))
        height = float(Length(self.height))

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

    def position(self, x, y, vector=False):
        if not isinstance(x, (int, float)):
            x = Length(x, relative_length=self.width, unitless=1).units
        if not isinstance(y, (int, float)):
            y = Length(y, relative_length=self.height, unitless=1).units
        unit_x, unit_y = x, y
        if vector:
            return self.matrix.transform_vector([unit_x, unit_y])
        return self.matrix.point_in_matrix_space([unit_x, unit_y])

    def iposition(self, x, y, vector=False):
        if not isinstance(x, (int, float)):
            x = Length(x, relative_length=self.width, unitless=1).units
        if not isinstance(y, (int, float)):
            y = Length(y, relative_length=self.height, unitless=1).units
        unit_x, unit_y = x, y
        matrix = ~self.matrix
        if vector:
            return matrix.transform_vector([unit_x, unit_y])
        return matrix.point_in_matrix_space([unit_x, unit_y])

    @property
    def matrix(self):
        if self._matrix is None:
            self._matrix = Matrix.map(*self._source, *self._destination)
        return self._matrix

    def dpi_to_steps(self, dpi):
        """
        Converts a DPI to a given step amount within the device length values. So M2 Nano will have 1 step per mil,
        the DPI of 500 therefore is step_x 2, step_y 2. A Galvo laser with a 200mm lens will have steps equal to
        200mm/65536 ~= 0.12 mils. So a DPI of 500 needs a step size of ~16.65 for x and y. Since 500 DPI is one dot
        per 2 mils.

        Note, steps size can be negative if our driver is x or y flipped.

        @param dpi:
        @param matrix: matrix to use rather than the scene to device matrix if supplied.
        @return:
        """
        # We require vectors so any positional offsets are non-contributing.
        unit_x = self.dpi_x
        unit_y = self.dpi_y
        matrix = self.matrix
        oneinch_x = abs(complex(*matrix.transform_vector([unit_x, 0])))
        oneinch_y = abs(complex(*matrix.transform_vector([0, unit_y])))
        step_x = float(oneinch_x / dpi)
        step_y = float(oneinch_y / dpi)
        return step_x, step_y
