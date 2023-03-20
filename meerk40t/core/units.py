"""
Device Specific Unit Conversion Objects

This defines a Viewport which all .device services are expected to implement. This provides the core functionality for
establishing the scene and mapping points from scene locations to device locations. This also provides functionality
for converting different length or angle units into other length or angle units.

The fundamental unit used for all the elements objects is that 1 inch is equal to 65535 native units called a Tat for
Tiger and Tatarize. This is basically a solid middle ground for providing significant rendering detail while not
overflowing the buffer in linux which starts react poorly for values greater than 16,777,216 (2^24). This should provide
enough detail for even the smallest lensed galvo laser while also allowing us to define objects as large as a football
stadium.
"""


import re
from copy import copy
from math import tau

from meerk40t.svgelements import Matrix

PATTERN_FLOAT = r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?"
REGEX_LENGTH = re.compile(r"(%s)\.?([A-Za-z%%]*)" % PATTERN_FLOAT)
ERROR = 1e-11
DEFAULT_PPI = 96.0
NATIVE_UNIT_PER_INCH = 65535

NM_PER_INCH = 25400000
NM_PER_MIL = 25400
NM_PER_NM = 1
NM_PER_uM = 1000
NM_PER_MM = 1000000
NM_PER_CM = 10000000
NM_PER_PIXEL = NM_PER_INCH / DEFAULT_PPI

MIL_PER_INCH = 1000
NM_PER_INCH = 2.54e7
uM_PER_INCH = 25400
MM_PER_INCH = 25.4
CM_PER_INCH = 2.54

PX_PER_INCH = DEFAULT_PPI
PX_PER_MIL = DEFAULT_PPI / MIL_PER_INCH
PX_PER_NM = DEFAULT_PPI / NM_PER_INCH
PX_PER_uM = DEFAULT_PPI / uM_PER_INCH
PX_PER_MM = DEFAULT_PPI / MM_PER_INCH
PX_PER_CM = DEFAULT_PPI / CM_PER_INCH
PX_PER_PIXEL = 1


UNITS_PER_TAT = 1
UNITS_PER_INCH = NATIVE_UNIT_PER_INCH
UNITS_PER_MIL = NATIVE_UNIT_PER_INCH / MIL_PER_INCH
UNITS_PER_uM = NATIVE_UNIT_PER_INCH / uM_PER_INCH
UNITS_PER_MM = NATIVE_UNIT_PER_INCH / MM_PER_INCH
UNITS_PER_CM = NATIVE_UNIT_PER_INCH / CM_PER_INCH
UNITS_PER_NM = NATIVE_UNIT_PER_INCH / NM_PER_INCH
UNITS_PER_PIXEL = NATIVE_UNIT_PER_INCH / DEFAULT_PPI
UNITS_PER_POINT = UNITS_PER_PIXEL * 4.0 / 3.0
PX_PER_UNIT = 1.0 / UNITS_PER_PIXEL

UNITS_NANOMETER = 0
UNITS_MM = 1
UNITS_CM = 2
UNITS_MILS = 3
UNITS_INCH = 4
UNITS_PERCENT = 100


class ViewPort:
    """
    The width and height are of the viewport are stored in MK native units (1/65535) in.
    Origin_x and origin_y are the location of the machine home position in factors of 1.
    This is to say 1,1 is the bottom left, and 0.5 0.5 is the middle of the bed.
    * user_scale is a scale factor for applied by the user rather than the driver.
    * native_scale is the scale factor of the driver units to MK native units
    * flip_x, flip_y, and swap_xy are used to apply whatever flips and swaps are needed.
    * show_origin is the 0,0 point as seen, for example galvo lasers call 0,0 center of the screen, but the machine
        units actually have 0,0 as the upper-left corner (depending on the flips and rotates)
    """

    def __init__(
        self,
        width,
        height,
        origin_x=0.0,
        origin_y=0.0,
        user_scale_x=1.0,
        user_scale_y=1.0,
        native_scale_x=1.0,
        native_scale_y=1.0,
        flip_x=False,
        flip_y=False,
        swap_xy=False,
        show_origin_x=None,
        show_origin_y=None,
        show_flip_x=None,
        show_flip_y=None,
        show_swap_xy=None,
        rotary_active=False,
        rotary_scale_x=1.0,
        rotary_scale_y=1.0,
        rotary_flip_x=False,
        rotary_flip_y=False,
    ):
        self._device_to_scene_matrix = None
        self._device_to_show_matrix = None
        self._scene_to_device_matrix = None
        self._scene_to_show_matrix = None
        self._show_to_device_matrix = None
        self._show_to_scene_matrix = None

        self.width = width
        self.height = height
        self.origin_x = origin_x
        self.origin_y = origin_y
        self.user_scale_x = user_scale_x
        self.user_scale_y = user_scale_y
        self.native_scale_x = native_scale_x
        self.native_scale_y = native_scale_y
        self.flip_x = flip_x
        self.flip_y = flip_y
        self.rotary_active = rotary_active
        self.rotary_flip_x = rotary_flip_x
        self.rotary_flip_y = rotary_flip_y
        self.rotary_scale_x = rotary_scale_x
        self.rotary_scale_y = rotary_scale_y
        self.swap_xy = swap_xy
        if show_origin_x is None:
            show_origin_x = origin_x
        if show_origin_y is None:
            show_origin_y = origin_y
        if show_flip_x is None:
            show_flip_x = flip_x
        if show_flip_y is None:
            show_flip_y = flip_y
        if show_swap_xy is None:
            show_swap_xy = swap_xy
        self.show_origin_x = show_origin_x
        self.show_origin_y = show_origin_y
        self.show_flip_x = show_flip_x
        self.show_flip_y = show_flip_y
        self.show_swap_xy = show_swap_xy

        self._width = None
        self._height = None
        self.scene_coords = None
        self.laser_coords = None
        self.show_coords = None
        self.realize()

    def realize(self):
        self._device_to_scene_matrix = None
        self._device_to_show_matrix = None
        self._scene_to_device_matrix = None
        self._scene_to_show_matrix = None
        self._show_to_device_matrix = None
        self._show_to_scene_matrix = None
        self._width = self.unit_width
        self._height = self.unit_height

        # Write laser and scene coords.
        s_top_left = (0, 0)
        s_top_right = (self._width, 0)
        s_bottom_right = (self._width, self._height)
        s_bottom_left = (0, self._height)
        self.scene_coords = (
            s_top_left,
            s_top_right,
            s_bottom_right,
            s_bottom_left,
        )
        if self.show_flip_x:
            s_top_left, s_top_right, s_bottom_right, s_bottom_left = (
                s_top_right,
                s_top_left,
                s_bottom_left,
                s_bottom_right,
            )
        if self.show_flip_y:
            s_top_left, s_top_right, s_bottom_right, s_bottom_left = (
                s_bottom_left,
                s_bottom_right,
                s_top_right,
                s_top_left,
            )
        if self.show_swap_xy:
            s_top_left, s_top_right, s_bottom_right, s_bottom_left = (
                (s_top_left[1], s_top_left[0]),
                (s_top_right[1], s_top_right[0]),
                (s_bottom_right[1], s_bottom_right[0]),
                (s_bottom_left[1], s_bottom_left[0]),
            )
        dx = self._width * -self.show_origin_x
        dy = self._height * -self.show_origin_y
        if dx != 0 or dy != 0:
            s_top_left, s_top_right, s_bottom_right, s_bottom_left = (
                (s_top_left[0] + dx, s_top_left[1] + dy),
                (s_top_right[0] + dx, s_top_right[1] + dy),
                (s_bottom_right[0] + dx, s_bottom_right[1] + dy),
                (s_bottom_left[0] + dx, s_bottom_left[1] + dy),
            )
        self.show_coords = s_top_left, s_top_right, s_bottom_right, s_bottom_left
        self._scene_to_show_matrix = Matrix.map(
            *self.scene_coords, *self.show_coords
        )

        # Calculate regular device matrix
        sx = self.native_scale_x
        sy = self.native_scale_y
        if self.rotary_active:
            sx *= self.rotary_scale_x
            sy *= self.rotary_scale_y
        bed_width = (self.unit_width / sx) / self.user_scale_x
        bed_height = (self.unit_height / sy) / self.user_scale_y
        dx = bed_width * -self.origin_x
        dy = bed_height * -self.origin_y

        top_left = (0, 0)
        top_right = (bed_width, 0)
        bottom_right = (bed_width, bed_height)
        bottom_left = (0, bed_height)

        if self.flip_x:
            top_left, top_right, bottom_right, bottom_left = (
                top_right,
                top_left,
                bottom_left,
                bottom_right,
            )
        if self.flip_y:
            top_left, top_right, bottom_right, bottom_left = (
                bottom_left,
                bottom_right,
                top_right,
                top_left,
            )
        if self.swap_xy:
            top_left, top_right, bottom_right, bottom_left = (
                (top_left[1], top_left[0]),
                (top_right[1], top_right[0]),
                (bottom_right[1], bottom_right[0]),
                (bottom_left[1], bottom_left[0]),
            )
        if dx != 0 or dy != 0:
            top_left, top_right, bottom_right, bottom_left = (
                (top_left[0] + dx, top_left[1] + dy),
                (top_right[0] + dx, top_right[1] + dy),
                (bottom_right[0] + dx, bottom_right[1] + dy),
                (bottom_left[0] + dx, bottom_left[1] + dy),
            )

        self.laser_coords = top_left, top_right, bottom_right, bottom_left
        self._scene_to_device_matrix = Matrix.map(
            *self.scene_coords, *self.laser_coords
        )

    def physical_to_device_position(self, x, y, unitless=1):
        """
        Converts a physical X,Y position into device units.

        @param x:
        @param y:
        @param unitless:
        @return:
        """
        x, y = self.physical_to_scene_position(x, y, unitless)
        return self.scene_to_device_position(x, y)

    def physical_to_scene_position(self, x, y, unitless=1):
        """
        Converts a physical X,Y position into viewport units.

        This does not depend on the device except for the width/height for converting percent values.

        @param x:
        @param y:
        @param unitless:
        @return:
        """
        unit_x = Length(x, relative_length=self._width, unitless=unitless).units
        unit_y = Length(y, relative_length=self._height, unitless=unitless).units
        # if self.swap_xy:
        #     return unit_y, unit_x
        return unit_x, unit_y

    def physical_to_show_position(self, x, y, unitless=1):
        """
        Converts a physical X,Y position into show units.

        @param x:
        @param y:
        @param unitless:
        @return:
        """
        x, y = self.physical_to_scene_position(x, y, unitless)
        return self.scene_to_show_position(x, y)

    def physical_to_device_length(self, x, y, unitless=1):
        """
        Converts a physical X,Y vector into device vector (dx, dy).

        This natively assumes device coordinate systems are affine. If we convert (0, 1in) as a vector into
        machine units we are converting the length of 1in into the equal length in machine units. Positionally this
        could be flipped or moved anywhere in the machine. But, the distance should be the same. However, in some cases
        due to belt stretching etc. we can have scaled x vs y coord systems so (1in, 0) could be a different length
        than (0, 1in).

        @param x:
        @param y:
        @param unitless:
        @return:
        """
        x, y = self.physical_to_scene_position(x, y, unitless)
        return self.scene_to_device_position(x, y, vector=True)

    def device_to_scene_position(self, x, y, vector=False):
        """
        Converts a device position x, y into a scene position of native units (1/65535) inches.
        @param x:
        @param y:
        @param vector:
        @return:
        """
        if vector:
            point = self.device_to_scene_matrix().transform_vector((x, y))
            return point.x, point.y
        else:
            point = self.device_to_scene_matrix().point_in_matrix_space((x, y))
            return point.x, point.y

    def device_to_show_position(self, x, y, vector=False):
        """
        @param x:
        @param y:
        @param vector:
        @return:
        """
        if vector:
            point = self.device_to_show_matrix().transform_vector((x, y))
            return point.x, point.y
        else:
            point = self.device_to_show_matrix().point_in_matrix_space((x, y))
            return point.x, point.y

    def scene_to_device_position(self, x, y, vector=False):
        """
        Converts scene to a device position (or vector). Converts x, y from scene units (1/65535) inches into
        device specific units. Optionally allows the calculation of a vector distance.

        @param x:
        @param y:
        @param vector:
        @return:
        """
        if vector:
            point = self.scene_to_device_matrix().transform_vector([x, y])
            return point[0], point[1]
        else:
            point = self.scene_to_device_matrix().point_in_matrix_space((x, y))
            return point.x, point.y

    def scene_to_show_position(self, x, y, vector=False):
        """
        @param x:
        @param y:
        @param vector:
        @return:
        """
        if vector:
            point = self.scene_to_show_matrix().transform_vector([x, y])
            return point[0], point[1]
        else:
            point = self.scene_to_show_matrix().point_in_matrix_space((x, y))
            return point.x, point.y

    def show_to_device_position(self, x, y, vector=False):
        """
        @param x:
        @param y:
        @param vector:
        @return:
        """
        if vector:
            point = self.show_to_device_matrix().transform_vector((x, y))
            return point.x, point.y
        else:
            point = self.show_to_device_matrix().point_in_matrix_space((x, y))
            return point.x, point.y

    def show_to_scene_position(self, x, y, vector=False):
        """
        @param x:
        @param y:
        @param vector:
        @return:
        """
        if vector:
            point = self.show_to_scene_matrix().transform_vector((x, y))
            return point.x, point.y
        else:
            point = self.show_to_scene_matrix().point_in_matrix_space((x, y))
            return point.x, point.y

    def device_position(self, x, y):
        m = self.scene_to_device_matrix()
        return m.point_in_matrix_space((x, y))

    def _calculate_matrices(self):
        """
        Calculate the matrices between the scene and device units.
        """
        self._scene_to_device_matrix = Matrix.map(
            *self.scene_coords, *self.laser_coords
        )
        # self._scene_to_device_matrix = Matrix(self._scene_to_device_transform())
        self._device_to_scene_matrix = ~self._scene_to_device_matrix

        self._scene_to_show_matrix = Matrix.map(
            *self.scene_coords, *self.show_coords
        )
        # self._scene_to_show_matrix = Matrix(self._scene_to_show_transform())
        self._show_to_scene_matrix = ~self._scene_to_show_matrix
        self._show_to_device_matrix = (
            self._show_to_scene_matrix * self._scene_to_device_matrix
        )
        self._device_to_show_matrix = ~self._show_to_device_matrix

    def device_to_scene_matrix(self):
        """
        Returns the device-to-scene matrix.
        """
        if self._device_to_scene_matrix is None:
            self._calculate_matrices()
        return self._device_to_scene_matrix

    def device_to_show_matrix(self):
        """
        Returns the device-to-scene matrix.
        """
        if self._device_to_show_matrix is None:
            self._calculate_matrices()
        return self._device_to_show_matrix

    def scene_to_device_matrix(self):
        """
        Returns the scene-to-device matrix.
        """
        if self._scene_to_device_matrix is None:
            self._calculate_matrices()
        return self._scene_to_device_matrix

    def scene_to_show_matrix(self):
        """
        Returns the scene-to-device matrix.
        """
        if self._scene_to_show_matrix is None:
            self._calculate_matrices()
        return self._scene_to_show_matrix

    def show_to_device_matrix(self):
        """
        Returns the scene-to-device matrix.
        """
        if self._show_to_device_matrix is None:
            self._calculate_matrices()
        return self._show_to_device_matrix

    def show_to_scene_matrix(self):
        """
        Returns the device-to-scene matrix.
        """
        if self._show_to_scene_matrix is None:
            self._calculate_matrices()
        return self._show_to_scene_matrix

    # def _scene_to_device_transform(self):
    #     """
    #     Transform for moving from scene units to device units. This takes into account the user and native scaling, the
    #     shift in origin point, flips to the y-axis, flips to the x-axis, and axis_swapping.
    #
    #     @return:
    #     """
    #     sx = self.user_scale_x * self.native_scale_x
    #     sy = self.user_scale_y * self.native_scale_y
    #     if self.rotary_active:
    #         sx *= self.rotary_scale_x
    #         sy *= self.rotary_scale_y
    #     dx = self.unit_width * self.origin_x
    #     dy = self.unit_height * self.origin_y
    #     ops = []
    #     if sx != 1.0 or sy != 1.0:
    #         try:
    #             ops.append(f"scale({1.0 / sx:.13f}, {1.0 / sy:.13f})")
    #         except ZeroDivisionError:
    #             pass
    #     if self.flip_y:
    #         ops.append("scale(1.0, -1.0)")
    #     if self.rotary_active and self.rotary_flip_y:
    #         ops.append("scale(1.0, -1.0)")
    #
    #     if self.flip_x:
    #         ops.append("scale(-1.0, 1.0)")
    #     if self.rotary_active and self.rotary_flip_x:
    #         ops.append("scale(-1.0, 1.0)")
    #     if dx != 0 or dy != 0:
    #         ops.append(f"translate({-dx:.13f}, {-dy:.13f})")
    #     if self.swap_xy:
    #         ops.append("scale(-1.0, 1.0) rotate(90deg)")
    #     return " ".join(ops)

    # def _scene_to_show_transform(self):
    #     """
    #     @return:
    #     """
    #     dx = self.unit_width * self.show_origin_x
    #     dy = self.unit_height * self.show_origin_y
    #     ops = []
    #     if self.show_flip_x:
    #         ops.append("scale(-1.0, 1.0)")
    #     if self.show_flip_y:
    #         ops.append("scale(1.0, -1.0)")
    #     if dx != 0 or dy != 0:
    #         ops.append(f"translate({-dx:.13f}, {-dy:.13f})")
    #     if self.swap_xy:
    #         ops.append("scale(-1.0, 1.0) rotate(90deg)")
    #     return " ".join(ops)

    def native_mm(self):
        matrix = self.scene_to_device_matrix()
        return abs(complex(*matrix.transform_vector([0, UNITS_PER_MM])))

    def length(
        self,
        value,
        axis=None,
        new_units=None,
        relative_length=None,
        as_float=False,
        unitless=1,
        digits=None,
        scale=None,
    ):
        """
        Axis 0 is X
        Axis 1 is Y

        Axis -1 is 1D in x, y space. e.g. a line width.

        Convert a length of distance {value} to new native values.

        @param value:
        @param axis:
        @param new_units:
        @param relative_length:
        @param as_float:
        @param unitless: factor for units with no units sets.
        @param scale: scale length by given factor.
        @return:
        """
        if axis == 0:
            if relative_length is None:
                relative_length = self.width
        else:
            if relative_length is None:
                relative_length = self.height
        length = Length(
            value, relative_length=relative_length, unitless=unitless, digits=digits
        )
        if scale is not None:
            length *= scale

        if new_units == "mm":
            if as_float:
                return length.mm
            else:
                return length.length_mm
        elif new_units == "inch":
            if as_float:
                return length.inches
            else:
                return length.length_inches
        elif new_units == "cm":
            if as_float:
                return length.cm
            else:
                return length.length_cm
        elif new_units == "px":
            if as_float:
                return length.pixels
            else:
                return length.length_pixels
        elif new_units == "mil":
            if as_float:
                return length.mil
            else:
                return length.length_mil
        else:
            return length.units

    def contains(self, x, y):
        x = self.length(x, 0)
        y = self.length(y, 1)
        if x > self._width:
            return False
        if y > self._height:
            return False
        if x < 0:
            return False
        if y < 0:
            return False
        return True

    def bbox(self):
        return (
            0,
            0,
            self.unit_width,
            self.unit_height,
        )

    def dpi_to_steps(self, dpi, matrix=None):
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
        unit_x = UNITS_PER_INCH
        unit_y = UNITS_PER_INCH
        if matrix is None:
            matrix = self.scene_to_device_matrix()
        oneinch_x = abs(complex(*matrix.transform_vector([unit_x, 0])))
        oneinch_y = abs(complex(*matrix.transform_vector([0, unit_y])))
        step_x = float(oneinch_x / dpi)
        step_y = float(oneinch_y / dpi)
        return step_x, step_y

    @property
    def length_width(self):
        return Length(self.width)

    @property
    def length_height(self):
        return Length(self.height)

    @property
    def unit_width(self):
        return float(Length(self.width))

    @property
    def unit_height(self):
        return float(Length(self.height))

    @staticmethod
    def viewbox_transform(
        e_x, e_y, e_width, e_height, vb_x, vb_y, vb_width, vb_height, aspect
    ):
        """
        SVG 1.1 7.2, SVG 2.0 8.2 equivalent transform of an SVG viewport.
        With regards to https://github.com/w3c/svgwg/issues/215 use 8.2 version.

        It creates transform commands equal to that viewport expected.

        Let e-x, e-y, e-width, e-height be the position and size of the element respectively.
        Let vb-x, vb-y, vb-width, vb-height be the min-x, min-y, width and height values of the viewBox attribute
        respectively.

        Let align be align value of preserveAspectRatio, or 'xMidYMid' if preserveAspectRatio is not defined.
        Let meetOrSlice be the meetOrSlice value of preserveAspectRatio, or 'meet' if preserveAspectRatio is not defined
        or if meetOrSlice is missing from this value.

        @param e_x: element_x value
        @param e_y: element_y value
        @param e_width: element_width value
        @param e_height: element_height value
        @param vb_x: viewbox_x value
        @param vb_y: viewbox_y value
        @param vb_width: viewbox_width value
        @param vb_height: viewbox_height value
        @param aspect: preserve aspect ratio value
        @return: string of the SVG transform commands to account for the viewbox.
        """
        if (
            e_x is None
            or e_y is None
            or e_width is None
            or e_height is None
            or vb_x is None
            or vb_y is None
            or vb_width is None
            or vb_height is None
        ):
            return ""
        if aspect is not None:
            aspect_slice = aspect.split(" ")
            try:
                align = aspect_slice[0]
            except IndexError:
                align = "xMidyMid"
            try:
                meet_or_slice = aspect_slice[1]
            except IndexError:
                meet_or_slice = "meet"
        else:
            align = "xMidyMid"
            meet_or_slice = "meet"
        # Initialize scale-x to e-width/vb-width.
        scale_x = e_width / vb_width
        # Initialize scale-y to e-height/vb-height.
        scale_y = e_height / vb_height

        # If align is not 'none' and meetOrSlice is 'meet', set the larger of scale-x and scale-y to the smaller.
        if align != "none" and meet_or_slice == "meet":
            scale_x = scale_y = min(scale_x, scale_y)
        # Otherwise, if align is not 'none' and meetOrSlice is 'slice', set the smaller of scale-x and scale-y to the larger
        elif align != "none" and meet_or_slice == "slice":
            scale_x = scale_y = max(scale_x, scale_y)
        # Initialize translate-x to e-x - (vb-x * scale-x).
        translate_x = e_x - (vb_x * scale_x)
        # Initialize translate-y to e-y - (vb-y * scale-y)
        translate_y = e_y - (vb_y * scale_y)
        # If align contains 'xMid', add (e-width - vb-width * scale-x) / 2 to translate-x.
        align = align.lower()
        if "xmid" in align:
            translate_x += (e_width - vb_width * scale_x) / 2.0
        # If align contains 'xMax', add (e-width - vb-width * scale-x) to translate-x.
        if "xmax" in align:
            translate_x += e_width - vb_width * scale_x
        # If align contains 'yMid', add (e-height - vb-height * scale-y) / 2 to translate-y.
        if "ymid" in align:
            translate_y += (e_height - vb_height * scale_y) / 2.0
        # If align contains 'yMax', add (e-height - vb-height * scale-y) to translate-y.
        if "ymax" in align:
            translate_y += e_height - vb_height * scale_y
        # The transform applied to content contained by the element is given by:
        # translate(translate-x, translate-y) scale(scale-x, scale-y)
        if isinstance(scale_x, Length) or isinstance(scale_y, Length):
            raise ValueError
        if translate_x == 0 and translate_y == 0:
            if scale_x == 1 and scale_y == 1:
                return ""  # Nothing happens.
            else:
                return f"scale({scale_x:.12f}, {scale_y:.12f})"
        else:
            if scale_x == 1 and scale_y == 1:
                return f"translate({translate_x:.12f}, {translate_y:.12f})"
            else:
                return (
                    f"translate({translate_x:.12f}, {translate_y:.12f}) "
                    f"scale({scale_x:.12f}, {scale_y:.12f})"
                )

    @staticmethod
    def conversion(units, amount=1):
        return Length(f"{amount}{units}").preferred


ACCEPTED_UNITS = (
    "",
    "cm",
    "mm",
    "in",
    "inch",
    "inches",
    "mil",
    "pt",
    "pc",
    "px",
    "%",
    "tat",
)


class Length:
    """
    Amounts are converted to UNITS.
    Initial unit is saved as preferred units.
    """

    def __init__(
        self,
        *args,
        amount=None,
        relative_length=None,
        unitless=1.0,
        preferred_units=None,
        digits=None,
    ):
        self._digits = digits
        self._amount = amount
        if self._amount is None:
            if len(args) == 2:
                value = str(args[0]) + str(args[1])
            elif len(args) == 1:
                value = args[0]
            else:
                raise ValueError("Arguments not acceptable")
            s = str(value)
            match = REGEX_LENGTH.match(s)
            if not match:
                raise ValueError("Length was not parsable.")
            amount = float(match.group(1))
            units = match.group(2)
            if units == "inch" or units == "inches":
                units = "in"
            scale = 1.0
            if units == "":
                if unitless:
                    scale = unitless
            elif units == "tat":
                scale = UNITS_PER_TAT
            elif units == "mm":
                scale = UNITS_PER_MM
            elif units == "cm":
                scale = UNITS_PER_CM
            elif units == "um":
                scale = UNITS_PER_uM
            elif units == "nm":
                scale = UNITS_PER_NM
            elif units == "in":
                scale = UNITS_PER_INCH
            elif units == "mil":
                scale = UNITS_PER_MIL
            elif units == "px":
                scale = UNITS_PER_PIXEL
            elif units == "pt":
                scale = UNITS_PER_POINT
            elif units == "pc":
                scale = UNITS_PER_PIXEL * 16.0
            elif units == "%":
                if relative_length is not None:
                    fraction = amount / 100.0
                    if isinstance(relative_length, (str, Length)):
                        relative_length = Length(
                            relative_length, unitless=unitless
                        ).units
                    amount = relative_length
                    scale = fraction
                    units = ""
                else:
                    raise ValueError("Percent without relative length is meaningless.")
            else:
                raise ValueError("Units was not recognized")
            self._amount = scale * amount
            if preferred_units is None:
                preferred_units = units
        if preferred_units is None:
            preferred_units = ""
        if preferred_units == "inch" or preferred_units == "inches":
            preferred_units = "in"
        self._preferred_units = preferred_units

    def __float__(self):
        return self._amount

    def __imul__(self, other):
        if isinstance(other, (int, float)):
            self._amount *= other
            return self
        if self._amount == 0.0:
            return 0.0
        raise ValueError

    def __iadd__(self, other):
        if not isinstance(other, Length):
            other = Length(other)
        self._amount += other._amount
        return self

    def __abs__(self):
        c = self.__copy__()
        c._amount = abs(c._amount)
        return c

    def __truediv__(self, other):
        if not isinstance(other, Length):
            other = Length(other)
        return self._amount / other._amount

    __floordiv__ = __truediv__
    __div__ = __truediv__

    def __lt__(self, other):
        return (self - other)._amount - ERROR < 0

    def __gt__(self, other):
        return (self - other)._amount + ERROR > 0

    def __le__(self, other):
        return (self - other)._amount - ERROR <= 0

    def __ge__(self, other):
        return (self - other)._amount + ERROR >= 0

    def __ne__(self, other):
        return not self.__eq__(other)

    def __add__(self, other):
        if isinstance(other, (str, float, int)):
            other = Length(other)
        c = self.__copy__()
        c += other
        return c

    __radd__ = __add__

    def __mul__(self, other):
        c = copy(self)
        c *= other
        return c

    def __rdiv__(self, other):
        c = copy(self)
        c *= 1.0 / other._amount
        return c

    def __neg__(self):
        s = self.__copy__()
        s._amount = -s._amount
        return s

    def __isub__(self, other):
        if not isinstance(other, Length):
            other = Length(other)
        self += -other
        return self

    def __sub__(self, other):
        s = self.__copy__()
        s -= other
        return s

    def __round__(self, ndigits=0):
        return round(self._amount, ndigits=ndigits)

    def __rsub__(self, other):
        if not isinstance(other, Length):
            other = Length(other)
        return (-self) + other

    def __copy__(self):
        return Length(
            None,
            amount=self._amount,
            preferred_units=self._preferred_units,
            digits=self._digits,
        )

    __rmul__ = __mul__

    def __repr__(self):
        c = self.__copy__()
        c._digits = None
        return c.preferred_length

    def __str__(self):
        return self.preferred_length

    def __eq__(self, other):
        if other is None:
            return False
        if isinstance(other, (int, float)):
            return self._amount == other
        if not isinstance(other, Length):
            other = Length(other)
        return abs(self._amount - other._amount) <= ERROR

    @property
    def preferred(self):
        if self._preferred_units == "px":
            return self.pixels
        elif self._preferred_units == "in":
            return self.inches
        elif self._preferred_units == "cm":
            return self.cm
        elif self._preferred_units == "mm":
            return self.mm
        elif self._preferred_units == "nm":
            return self.nm
        elif self._preferred_units == "mil":
            return self.mil
        elif self._preferred_units == "um":
            return self.um
        elif self._preferred_units == "pt":
            return self.pt
        else:
            return self.units

    @property
    def preferred_length(self):
        if self._preferred_units == "px":
            return self.length_pixels
        elif self._preferred_units == "in":
            return self.length_inches
        elif self._preferred_units == "cm":
            return self.length_cm
        elif self._preferred_units == "mm":
            return self.length_mm
        elif self._preferred_units == "nm":
            return self.length_nm
        elif self._preferred_units == "mil":
            return self.length_mil
        elif self._preferred_units == "um":
            return self.length_um
        elif self._preferred_units == "pt":
            return self.length_pt
        else:
            return self.length_units

    @property
    def pixels(self):
        amount = self._amount / UNITS_PER_PIXEL
        if self._digits:
            amount = round(amount, self._digits)
        return amount

    @property
    def inches(self):
        amount = self._amount / UNITS_PER_INCH
        if self._digits:
            amount = round(amount, self._digits)
        return amount

    @property
    def cm(self):
        amount = self._amount / UNITS_PER_CM
        if self._digits:
            amount = round(amount, self._digits)
        return amount

    @property
    def mm(self):
        amount = self._amount / UNITS_PER_MM
        if self._digits:
            amount = round(amount, self._digits)
        return amount

    @property
    def nm(self):
        amount = self._amount / UNITS_PER_NM
        if self._digits:
            amount = round(amount, self._digits)
        return amount

    @property
    def mil(self):
        amount = self._amount / UNITS_PER_MIL
        if self._digits:
            amount = round(amount, self._digits)
        return amount

    @property
    def um(self):
        amount = self._amount / UNITS_PER_uM
        if self._digits:
            amount = round(amount, self._digits)
        return amount

    @property
    def pt(self):
        amount = self._amount / UNITS_PER_POINT
        if self._digits:
            amount = round(amount, self._digits)
        return amount

    @property
    def units(self):
        amount = self._amount
        if self._digits:
            amount = round(amount, self._digits)
        return amount

    @property
    def length_pixels(self):
        amount = self.pixels
        return f"{round(amount, 8)}px"

    @property
    def length_inches(self):
        amount = self.inches
        return f"{round(amount, 8)}in"

    @property
    def length_cm(self):
        amount = self.cm
        return f"{round(amount, 8)}cm"

    @property
    def length_mm(self):
        amount = self.mm
        return f"{round(amount, 8)}mm"

    @property
    def length_nm(self):
        amount = self.nm
        return f"{round(amount, 8)}nm"

    @property
    def length_mil(self):
        amount = self.mil
        return f"{round(amount, 8)}mil"

    @property
    def length_um(self):
        amount = self.um
        return f"{round(amount, 8)}um"

    @property
    def length_pt(self):
        amount = self.pt
        return f"{round(amount, 8)}pt"

    @property
    def length_units(self):
        return f"{self.units}"

    def as_percent(self, relative_length):
        return 100.00 * self._amount / Length(relative_length).units


class Angle:
    """
    Angle conversion and math, stores angle as a float in radians and
    converts to other forms of angle. Failures to parse raise ValueError.
    """

    def __init__(self, angle, digits=None):
        if isinstance(angle, Angle):
            self._digits = angle._digits
            self.angle = angle.angle
            self.preferred_units = angle.preferred_units
            return
        self._digits = digits
        if not isinstance(angle, str):
            self.angle = float(angle)
            self.preferred_units = "rad"
            return
        angle = angle.lower()
        if angle.endswith("deg"):
            self.angle = float(angle[:-3]) * tau / 360.0
            self.preferred_units = "deg"
        elif angle.endswith("grad"):
            self.angle = float(angle[:-4]) * tau / 400.0
            self.preferred_units = "grad"
        elif angle.endswith("rad"):
            # Must be after 'grad' since 'grad' ends with 'rad' too.
            self.angle = float(angle[:-3])
            self.preferred_units = "rad"
        elif angle.endswith("turn"):
            self.angle = float(angle[:-4]) * tau
            self.preferred_units = "turn"
        elif angle.endswith("%"):
            self.angle = float(angle[:-1]) * tau / 100.0
            self.preferred_units = "%"
        else:
            self.angle = float(angle)
            self.preferred_units = "rad"

    def __str__(self):
        return self.angle_preferred

    def __copy__(self):
        return Angle(self.angle)

    def __eq__(self, other):
        if hasattr(other, "angle"):
            other = other.angle
        c1 = abs((self.angle % tau) - (other % tau)) <= 1e-11
        return c1

    def normalize(self):
        self.angle /= tau

    @property
    def angle_preferred(self):
        if self.preferred_units == "rad":
            return self.angle_radians
        elif self.preferred_units == "grad":
            return self.angle_gradians
        elif self.preferred_units == "deg":
            return self.angle_degrees
        elif self.preferred_units == "turn":
            return self.angle_turns

    @property
    def radians(self):
        amount = self.angle
        if self._digits:
            amount = round(amount, self._digits)
        return amount

    @property
    def degrees(self):
        amount = self.angle * 360.0 / tau
        if self._digits:
            amount = round(amount, self._digits)
        return amount

    @property
    def gradians(self):
        amount = self.angle * 400.0 / tau
        if self._digits:
            amount = round(amount, self._digits)
        return amount

    @property
    def turns(self):
        amount = self.angle / tau
        if self._digits:
            amount = round(amount, self._digits)
        return amount

    @property
    def angle_radians(self):
        return f"{self.radians}rad"

    @property
    def angle_degrees(self):
        return f"{self.degrees}deg"

    @property
    def angle_gradians(self):
        return f"{self.gradians}grad"

    @property
    def angle_turns(self):
        return f"{self.turns}turn"

    def is_orthogonal(self):
        return (self.angle % (tau / 4.0)) == 0


# TODO: Add in speed for units. mm/s in/s mm/minute.
