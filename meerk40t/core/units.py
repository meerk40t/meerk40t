import re
from copy import copy

from meerk40t.svgelements import Matrix

PATTERN_FLOAT = r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?"
REGEX_LENGTH = re.compile(r"(%s)([A-Za-z%%]*)" % PATTERN_FLOAT)
ERROR = 1e-12
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
        self._width = Length(self.width).value(ppi=UNITS_PER_INCH, unitless=1.0)
        self._height = Length(self.height).value(ppi=UNITS_PER_INCH, unitless=1.0)
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
        nm_x = Length(x).value(
            ppi=UNITS_PER_INCH, relative_length=self._width, unitless=unitless
        )
        nm_y = Length(y).value(
            ppi=UNITS_PER_INCH, relative_length=self._height, unitless=unitless
        )
        return nm_x, nm_y

    def physical_to_device_position(self, x, y, unitless=UNITS_PER_NM):
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
        if self.flip_y:
            ops.append("scale(1.0, -1.0)")
        if self.flip_x:
            ops.append("scale(-1.0, 1.0)")
        if self._scale_x != 1.0 or self._scale_y != 1.0:
            ops.append(
                "scale({sx:.13f}, {sy:.13f})".format(
                    sx=1.0 / self._scale_x, sy=1.0 / self._scale_y
                )
            )
        if self._offset_x != 0 or self._offset_y != 0:
            ops.append(
                "translate({dx:.13f}, {dy:.13f})".format(
                    dx=-self._offset_x, dy=-self._offset_y
                )
            )
        if self.swap_xy:
            ops.append("scale(-1.0, -1.0) rotate(180deg)")
        return " ".join(ops)

    def length(
        self,
        value,
        axis=None,
        new_units=None,
        relative_length=None,
        as_float=False,
        unitless=UNITS_PER_PIXEL,
        scale=None,
    ):
        """
        Axis 0 is X
        Axis 1 is Y

        Axis -1 is 1D in x, y space. eg. a line width.

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
        if new_units is None:
            length = Length(value)
            if scale is not None:
                length *= scale
            return length.value(
                ppi=UNITS_PER_INCH, relative_length=relative_length, unitless=unitless
            )
        elif new_units == "mm":
            return Length(value).to_mm(
                ppi=UNITS_PER_INCH, relative_length=relative_length, as_float=as_float, scale=scale,
            )
        elif new_units == "inch":
            return Length(value).to_inch(
                ppi=UNITS_PER_INCH, relative_length=relative_length, as_float=as_float, scale=scale,
            )
        elif new_units == "cm":
            return Length(value).to_cm(
                ppi=UNITS_PER_INCH, relative_length=relative_length, as_float=as_float, scale=scale,
            )
        elif new_units == "px":
            return Length(value).to_px(
                ppi=UNITS_PER_INCH, relative_length=relative_length, as_float=as_float, scale=scale,
            )
        elif new_units == "mil":
            return (
                Length(value).to_inch(
                    ppi=UNITS_PER_INCH,
                    relative_length=relative_length,
                    as_float=as_float,
                )
                / 1000.0
            )

    def contains(self, x, y):
        x = self.length(x, 0)
        y = self.length(y, 1)
        if x >= self.width:
            return False
        if y >= self.height:
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
    def width_as_mm(self):
        return Length(self.width).to_mm(ppi=UNITS_PER_INCH)

    @property
    def height_as_mm(self):
        return Length(self.height).to_mm(ppi=UNITS_PER_INCH)

    @property
    def width_as_inch(self):
        return Length(self.width).to_inch(ppi=UNITS_PER_INCH)

    @property
    def height_as_inch(self):
        return Length(self.height).to_inch(ppi=UNITS_PER_INCH)

    @property
    def unit_width(self):
        return Length(self.width).value(ppi=UNITS_PER_INCH)

    @property
    def unit_height(self):
        return Length(self.height).value(ppi=UNITS_PER_INCH)

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

        Let align be the align value of preserveAspectRatio, or 'xMidYMid' if preserveAspectRatio is not defined.
        Let meetOrSlice be the meetOrSlice value of preserveAspectRatio, or 'meet' if preserveAspectRatio is not defined
        or if meetOrSlice is missing from this value.

        :param e_x: element_x value
        :param e_y: element_y value
        :param e_width: element_width value
        :param e_height: element_height value
        :param vb_x: viewbox_x value
        :param vb_y: viewbox_y value
        :param vb_width: viewbox_width value
        :param vb_height: viewbox_height value
        :param aspect: preserve aspect ratio value
        :return: string of the SVG transform commands to account for the viewbox.
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
        return Length("{amount}{units}".format(units=units, amount=amount)).value(
            ppi=UNITS_PER_INCH
        )


class Length(object):
    def __init__(self, *args, **kwargs):
        if len(args) == 1:
            value = args[0]
            if value is None:
                self.amount = None
                self.units = None
                return
            s = str(value)
            for m in REGEX_LENGTH.findall(s):
                self.amount = float(m[0])
                self.units = m[1]
                return
        elif len(args) == 2:
            self.amount = args[0]
            self.units = args[1]
            return
        self.amount = 0.0
        self.units = ""

    def __float__(self):
        if self.amount is None:
            return None
        if self.units == "pt":
            return self.amount * 1.3333
        elif self.units == "pc":
            return self.amount * 16.0
        return self.amount

    def __imul__(self, other):
        if isinstance(other, (int, float)):
            self.amount *= other
            return self
        if self.amount == 0.0:
            return 0.0
        if isinstance(other, str):
            other = Length(other)
        if isinstance(other, Length):
            if other.amount == 0.0:
                self.amount = 0.0
                return self
            if self.units == other.units:
                self.amount *= other.amount
                return self
            if self.units == "%":
                self.units = other.units
                self.amount = self.amount * other.amount / 100.0
                return self
            elif other.units == "%":
                self.amount = self.amount * other.amount / 100.0
                return self
        raise ValueError

    def __iadd__(self, other):
        if not isinstance(other, Length):
            other = Length(other)
        if self.units == other.units:
            self.amount += other.amount
            return self
        if self.amount == 0:
            self.amount = other.amount
            self.units = other.units
            return self
        if other.amount == 0:
            return self
        if self.units == "px" or self.units == "":
            if other.units == "px" or other.units == "":
                self.amount += other.amount
            elif other.units == "pt":
                self.amount += other.amount * 1.3333
            elif other.units == "pc":
                self.amount += other.amount * 16.0
            else:
                raise ValueError
            return self
        if self.units == "pt":
            if other.units == "px" or other.units == "":
                self.amount += other.amount / 1.3333
            elif other.units == "pc":
                self.amount += other.amount * 12.0
            else:
                raise ValueError
            return self
        elif self.units == "pc":
            if other.units == "px" or other.units == "":
                self.amount += other.amount / 16.0
            elif other.units == "pt":
                self.amount += other.amount / 12.0
            else:
                raise ValueError
            return self
        elif self.units == "cm":
            if other.units == "mm":
                self.amount += other.amount / 10.0
            elif other.units == "in":
                self.amount += other.amount / 0.393701
            else:
                raise ValueError
            return self
        elif self.units == "mm":
            if other.units == "cm":
                self.amount += other.amount * 10.0
            elif other.units == "in":
                self.amount += other.amount / 0.0393701
            else:
                raise ValueError
            return self
        elif self.units == "in":
            if other.units == "cm":
                self.amount += other.amount * 0.393701
            elif other.units == "mm":
                self.amount += other.amount * 0.0393701
            else:
                raise ValueError
            return self
        raise ValueError("%s units were not determined." % self.units)

    def __abs__(self):
        c = self.__copy__()
        c.amount = abs(c.amount)
        return c

    def __truediv__(self, other):
        if isinstance(other, (int, float)):
            c = self.__copy__()
            c.amount /= other
            return c
        if self.amount == 0.0:
            return 0.0
        if isinstance(other, str):
            other = Length(other)
        if isinstance(other, Length):
            if self.units == other.units:
                q = self.amount / other.amount
                return q  # no units
        if self.units == "px" or self.units == "":
            if other.units == "px" or other.units == "":
                return self.amount / other.amount
            elif other.units == "pt":
                return self.amount / (other.amount * 1.3333)
            elif other.units == "pc":
                return self.amount / (other.amount * 16.0)
            else:
                raise ValueError
        if self.units == "pt":
            if other.units == "px" or other.units == "":
                return self.amount / (other.amount / 1.3333)
            elif other.units == "pc":
                return self.amount / (other.amount * 12.0)
            else:
                raise ValueError
        if self.units == "pc":
            if other.units == "px" or other.units == "":
                return self.amount / (other.amount / 16.0)
            elif other.units == "pt":
                return self.amount / (other.amount / 12.0)
            else:
                raise ValueError
        if self.units == "cm":
            if other.units == "mm":
                return self.amount / (other.amount / 10.0)
            elif other.units == "in":
                return self.amount / (other.amount / 0.393701)
            else:
                raise ValueError
        if self.units == "mm":
            if other.units == "cm":
                return self.amount / (other.amount * 10.0)
            elif other.units == "in":
                return self.amount / (other.amount / 0.0393701)
            else:
                raise ValueError
        if self.units == "in":
            if other.units == "cm":
                return self.amount / (other.amount * 0.393701)
            elif other.units == "mm":
                return self.amount / (other.amount * 0.0393701)
            else:
                raise ValueError
        raise ValueError

    __floordiv__ = __truediv__
    __div__ = __truediv__

    def __lt__(self, other):
        return (self - other).amount < 0.0

    def __le__(self, other):
        return (self - other).amount <= 0.0

    def __gt__(self, other):
        return (self - other).amount > 0.0

    def __ge__(self, other):
        return (self - other).amount >= 0.0

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
        c *= 1.0 / other.amount
        return c

    def __neg__(self):
        s = self.__copy__()
        s.amount = -s.amount
        return s

    def __isub__(self, other):
        if isinstance(other, (str, float, int)):
            other = Length(other)
        self += -other
        return self

    def __sub__(self, other):
        s = self.__copy__()
        s -= other
        return s

    def __rsub__(self, other):
        if isinstance(other, (str, float, int)):
            other = Length(other)
        return (-self) + other

    def __copy__(self):
        return Length(self.amount, self.units)

    __rmul__ = __mul__

    def __repr__(self):
        return "Length('%s')" % (str(self))

    def __str__(self):
        if self.amount is None:
            return "None"
        return "%s%s" % (Length.str(self.amount), self.units)

    def __eq__(self, other):
        if other is None:
            return False
        s = self.in_pixels()
        if isinstance(other, (float, int)):
            if s is not None:
                return abs(s - other) <= ERROR
            else:
                return other == 0 and self.amount == 0
        if isinstance(other, str):
            other = Length(other)
        if self.amount == other.amount and self.units == other.units:
            return True
        if s is not None:
            o = self.in_pixels()
            if abs(s - o) <= ERROR:
                return True
        s = self.in_inches()
        if s is not None:
            o = self.in_inches()
            if abs(s - o) <= ERROR:
                return True
        return False

    @property
    def value_in_units(self):
        return self.amount

    def in_pixels(self):
        if self.units == "px" or self.units == "":
            return self.amount
        if self.units == "pt":
            return self.amount / 1.3333
        if self.units == "pc":
            return self.amount / 16.0
        return None

    def in_inches(self):
        if self.units == "mm":
            return self.amount * 0.0393701
        if self.units == "cm":
            return self.amount * 0.393701
        if self.units == "in":
            return self.amount
        return None

    def to_mm(
        self,
        ppi=UNITS_PER_INCH,
        relative_length=None,
        font_size=None,
        font_height=None,
        viewbox=None,
        as_float=False,
        scale=None,
    ):
        value = self.value(
            ppi=ppi,
            relative_length=relative_length,
            font_size=font_size,
            font_height=font_height,
            viewbox=viewbox,
        )
        v = value / (ppi * 0.0393701)
        if scale is not None:
            v *= scale
        if as_float:
            return v
        return Length("%smm" % (Length.str(v)))

    def to_cm(
        self,
        ppi=UNITS_PER_INCH,
        relative_length=None,
        font_size=None,
        font_height=None,
        viewbox=None,
        as_float=False,
        scale=None,
    ):
        value = self.value(
            ppi=ppi,
            relative_length=relative_length,
            font_size=font_size,
            font_height=font_height,
            viewbox=viewbox,
        )
        v = value / (ppi * 0.393701)
        if scale is not None:
            v *= scale
        if as_float:
            return v
        return Length("%scm" % (Length.str(v)))

    def to_inch(
        self,
        ppi=UNITS_PER_INCH,
        relative_length=None,
        font_size=None,
        font_height=None,
        viewbox=None,
        as_float=False,
        scale=None,
    ):
        value = self.value(
            ppi=ppi,
            relative_length=relative_length,
            font_size=font_size,
            font_height=font_height,
            viewbox=viewbox,
        )
        v = value / ppi
        if scale is not None:
            v *= scale
        if as_float:
            return v
        return Length("%sin" % (Length.str(v)))

    def to_px(
        self,
        ppi=UNITS_PER_INCH,
        relative_length=None,
        font_size=None,
        font_height=None,
        viewbox=None,
        as_float=False,
        scale=None,
    ):
        value = self.value(
            ppi=ppi,
            relative_length=relative_length,
            font_size=font_size,
            font_height=font_height,
            viewbox=viewbox,
        )
        v = (value / ppi) / DEFAULT_PPI
        if scale is not None:
            v *= scale
        if as_float:
            return v
        return Length("%sin" % (Length.str(v)))

    def value(
        self,
        ppi=None,
        relative_length=None,
        font_size=None,
        font_height=None,
        unitless=None,
        **kwargs,
    ):
        if self.amount is None:
            return None
        if self.units == "":
            if unitless:
                return self.amount * unitless
            else:
                return self.amount
        if self.units == "%":
            if relative_length is None:
                return self
            fraction = self.amount / 100.0
            if isinstance(relative_length, (float, int)):
                return fraction * relative_length
            elif isinstance(relative_length, (str, Length)):
                length = relative_length * self
                if isinstance(length, Length):
                    return length.value(
                        ppi=ppi,
                        font_size=font_size,
                        font_height=font_height,
                    )
                return length
            return self
        if self.units == "mm":
            if ppi is None:
                return self
            return self.amount * ppi * 0.0393701
        if self.units == "cm":
            if ppi is None:
                return self
            return self.amount * ppi * 0.393701
        if self.units == "nm":
            if ppi is None:
                return self
            return self.amount * ppi * 3.93701e-8
        if self.units == "in":
            if ppi is None:
                return self
            return self.amount * ppi
        if self.units == "px":
            return self.amount
        if self.units == "pt":
            return self.amount * 1.3333
        if self.units == "pc":
            return self.amount * 16.0
        if self.units == "em":
            if font_size is None:
                return self
            return self.amount * float(font_size)
        if self.units == "ex":
            if font_height is None:
                return self
            return self.amount * float(font_height)
        try:
            return float(self)
        except ValueError:
            return self

    @staticmethod
    def str(s):
        if s is None:
            return "n/a"
        if isinstance(s, Length):
            if s.units == "":
                s = s.amount
            else:
                a = "%.12f" % s.amount
                if "." in a:
                    a = a.rstrip("0").rstrip(".")
                return "'%s%s'" % (a, s.units)
        try:
            s = "%.12f" % s
        except TypeError:
            return str(s)
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s
