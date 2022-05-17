import re
from copy import copy

from meerk40t.svgelements import Matrix

PATTERN_FLOAT = r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?"
REGEX_LENGTH = re.compile(r"(%s)([A-Za-z%%]*)" % PATTERN_FLOAT)
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
PX_PER_uM = DEFAULT_PPI / NM_PER_INCH

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


UNITS_PER_INCH = NATIVE_UNIT_PER_INCH
UNITS_PER_MIL = NATIVE_UNIT_PER_INCH / MIL_PER_INCH
UNITS_PER_uM = NATIVE_UNIT_PER_INCH / uM_PER_INCH
UNITS_PER_MM = NATIVE_UNIT_PER_INCH / MM_PER_INCH
UNITS_PER_CM = NATIVE_UNIT_PER_INCH / CM_PER_INCH
UNITS_PER_NM = NATIVE_UNIT_PER_INCH / NM_PER_INCH
UNITS_PER_PIXEL = NATIVE_UNIT_PER_INCH / DEFAULT_PPI
PX_PER_UNIT = 1.0 / UNITS_PER_PIXEL

UNITS_NANOMETER = 0
UNITS_MM = 1
UNITS_CM = 2
UNITS_MILS = 3
UNITS_INCH = 4
UNITS_PERCENT = 100

"""
Device Specific Unit Conversion Objects

This should exist on any device located at .length accepting coordinate and axis. This is callable with any str length
and should convert the given length relative to the viewport provided by the native values of the device into
nanometers.
"""


class ViewPort:
    """
    The width and height are of the viewport are stored in MK native units (nm).

    Origin_x and origin_y are the location of the home position in unit square values.
    This is to say 1,1 is the bottom left, and 0.5 0.5 is the middle of the bed.

    user_scale is a scale factor for applied by the user rather than the driver.

    native_scale is the scale factor of the driver units to MK native units

    flip_x, flip_y, and swap_xy are used to apply whatever flips and swaps are needed.
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
    ):
        self._matrix = None
        self._imatrix = None
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
        self.swap_xy = swap_xy
        if show_origin_x is None:
            show_origin_x = origin_x
        if show_origin_y is None:
            show_origin_y = origin_y
        self.show_origin_x = show_origin_x
        self.show_origin_y = show_origin_y

        self._width = None
        self._height = None
        self._offset_x = None
        self._offset_y = None
        self._scale_x = None
        self._scale_y = None
        self.realize()

    def realize(self):
        self._imatrix = None
        self._matrix = None
        self._width = Length(self.width, unitless=1.0).units
        self._height = Length(self.height, unitless=1.0).units
        self._offset_x = self._width * self.origin_x
        self._offset_y = self._height * self.origin_y
        self._scale_x = self.user_scale_x * self.native_scale_x
        self._scale_y = self.user_scale_y * self.native_scale_y

    def physical_to_scene_position(self, x, y, unitless=UNITS_PER_PIXEL):
        """
        Converts an X,Y position into viewport units.

        @param x:
        @param y:
        @param as_float:
        @param unitless:
        @return:
        """
        unit_x = Length(x, relative_length=self._width, unitless=unitless).units
        unit_y = Length(y, relative_length=self._height, unitless=unitless).units
        return unit_x, unit_y

    def physical_to_device_position(self, x, y, unitless=UNITS_PER_PIXEL):
        """
        Converts an X,Y position into viewport units.
        @param x:
        @param y:
        @param unitless:
        @return:
        """
        x, y = self.physical_to_scene_position(x, y, unitless)
        return self.scene_to_device_position(x, y)

    def physical_to_device_length(self, x, y, unitless=UNITS_PER_PIXEL):
        """
        Converts an X,Y position into dx, dy.
        @param x:
        @param y:
        @param unitless:
        @return:
        """
        x, y = self.physical_to_scene_position(x, y, unitless)
        return self.scene_to_device_position(x, y, vector=True)

    def device_to_scene_position(self, x, y):
        if self._imatrix is None:
            self.calculate_matrices()
        point = self._imatrix.point_in_matrix_space((x, y))
        return point.x, point.y

    def scene_to_device_position(self, x, y, vector=False):
        if self._matrix is None:
            self.calculate_matrices()
        if vector:
            point = self._matrix.transform_vector([x, y])
            return point[0], point[1]
        else:
            point = self._matrix.point_in_matrix_space((x, y))
            return point.x, point.y

    def calculate_matrices(self):
        self._matrix = Matrix(self.scene_to_device_matrix())
        self._imatrix = Matrix(self._matrix)
        self._imatrix.inverse()

    def device_to_scene_matrix(self):
        if self._matrix is None:
            self.calculate_matrices()
        return self._imatrix

    def scene_to_device_matrix(self):
        ops = []
        if self._scale_x != 1.0 or self._scale_y != 1.0:
            ops.append(
                "scale({sx:.13f}, {sy:.13f})".format(
                    sx=1.0 / self._scale_x, sy=1.0 / self._scale_y
                )
            )
        if self._offset_x != 0 or self._offset_y != 0:
            ops.append(
                "translate({dx:.13f}, {dy:.13f})".format(
                    dx=self._offset_x, dy=self._offset_y
                )
            )
        if self.flip_y:
            ops.append("scale(1.0, -1.0)")
        if self.flip_x:
            ops.append("scale(-1.0, 1.0)")
        if self.swap_xy:
            ops.append("scale(-1.0, 1.0) rotate(90deg)")
        return " ".join(ops)

    def length(
        self,
        value,
        axis=None,
        new_units=None,
        relative_length=None,
        as_float=False,
        unitless=UNITS_PER_PIXEL,
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
        length = Length(value, relative_length=relative_length, unitless=unitless, digits=digits)
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
        if x >= self._width:
            return False
        if y >= self._height:
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
                return "scale(%s, %s)" % (Length.str(scale_x), Length.str(scale_y))
        else:
            if scale_x == 1 and scale_y == 1:
                return "translate(%s, %s)" % (
                    Length.str(translate_x),
                    Length.str(translate_y),
                )
            else:
                return "translate(%s, %s) scale(%s, %s)" % (
                    Length.str(translate_x),
                    Length.str(translate_y),
                    Length.str(scale_x),
                    Length.str(scale_y),
                )

    @staticmethod
    def conversion(units, amount=1):
        return Length("{amount}{units}".format(units=units, amount=amount)).preferred


ACCEPTED_UNITS = ("", "cm", "mm", "in", "mil", "pt", "pc", "px", "%")


class Length(object):
    """
    Amounts are converted to UNITS.
    Initial unit is saved as preferred units.
    """

    def __init__(
        self,
        *args,
        amount=None,
        relative_length=None,
        unitless=PX_PER_UNIT,
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
                scale = UNITS_PER_PIXEL * 1.3333
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
    def units(self):
        amount = self._amount
        if self._digits:
            amount = round(amount, self._digits)
        return amount

    @property
    def length_pixels(self):
        return "{amount}px".format(amount=self.pixels)

    @property
    def length_inches(self):
        return "{amount}in".format(amount=self.inches)

    @property
    def length_cm(self):
        return "{amount}cm".format(amount=self.cm)

    @property
    def length_mm(self):
        return "{amount}mm".format(amount=self.mm)

    @property
    def length_nm(self):
        return "{amount}nm".format(amount=self.nm)

    @property
    def length_mil(self):
        return "{amount}mil".format(amount=self.mil)

    @property
    def length_um(self):
        return "{amount}um".format(amount=self.um)

    @property
    def length_units(self):
        return "{amount}".format(amount=self.units)

    def as_percent(self, relative_length):
        return 100.00 * self._amount / Length(relative_length).units


# TODO: Add in speed for units. mm/s in/s mm/minute.
