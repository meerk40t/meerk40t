from meerk40t.core.units import Length, MM_PER_INCH
from meerk40t.svgelements import Matrix


class ViewMap:
    def __init__(self, source, destination):
        """
        We map two different views together generating the matrix to warp the views together as well as using
        values like DPI to provide useful information about the given space.

        @param source: view of source
        @param destination: view of destination
        """
        self._source = source
        self._destination = destination
        self._matrix = None

    def revalidate(self):
        self._matrix = None

    def position(self, x, y, vector=False):
        if not isinstance(x, (int, float)):
            width = self._destination.width
            height = self._destination.height
            x = Length(x, relative_length=width, unitless=1).units
            y = Length(y, relative_length=height, unitless=1).units
        unit_x, unit_y = x, y
        if vector:
            return self.matrix.transform_vector([unit_x, unit_y])
        return self.matrix.point_in_matrix_space([unit_x, unit_y])

    @property
    def matrix(self):
        if self._matrix is None:
            self._matrix = Matrix.map(*self._source.coords, *self._destination.coords)
        return self._matrix

    def mm(self):
        x, y = self.position(0, self._source.dpi / MM_PER_INCH, vector=True)
        return abs(complex(x, y))

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
        unit_x = self._source.dpi
        unit_y = self._source.dpi
        matrix = self.matrix
        oneinch_x = abs(complex(*matrix.transform_vector([unit_x, 0])))
        oneinch_y = abs(complex(*matrix.transform_vector([0, unit_y])))
        step_x = float(oneinch_x / dpi)
        step_y = float(oneinch_y / dpi)
        return step_x, step_y
