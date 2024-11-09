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

ACCEPTED_ANGLE_UNITS = (
    "",
    "deg",
    "grad",
    "rad",
    "turn",
    "%",
)


class Length:
    """
    Amounts are converted to UNITS.
    Initial unit is saved as preferred units.
    """

    units_per_spx = 50

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
        if relative_length:
            self._relative = Length(relative_length, unitless=unitless).units
        else:
            self._relative = None
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
                raise ValueError(f"Length was not parsable: '{s}'.")
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
            elif units == "spx":
                scale = self.units_per_spx
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
                raise ValueError(f"Units '{units}' was not recognized for '{s}'")
            self._amount = scale * amount
            if preferred_units is None:
                preferred_units = units
        else:
            # amount is only ever a number.
            if not isinstance(amount, (float, int)):
                raise ValueError("Amount must be an number.")
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
            try:
                other = Length(other)
            except ValueError:
                # Not a length, we do not equal this.
                return False
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
        elif self._preferred_units == "spx":
            return self.spx
        elif self._preferred_units == "%":
            return self.percent
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
        elif self._preferred_units == "%":
            return self.length_percent
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
    def spx(self):
        amount = self._amount / self.units_per_spx
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
    def percent(self):
        if self._relative is None or self._relative == 0:
            raise ValueError("Percent without relative length is meaningless.")
        amount = 100.0 * self._amount / self._relative
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
    def length_spx(self):
        amount = self.spx
        return f"{round(amount, 8)}spx"

    @property
    def length_percent(self):
        amount = self.percent
        return f"{round(amount, 8)}%"

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

    def __init__(self, angle, digits=None, preferred_units="rad"):
        if isinstance(angle, Angle):
            self._digits = angle._digits
            self.angle = angle.angle
            self.preferred_units = angle.preferred_units
            return
        self._digits = digits
        if not isinstance(angle, str):
            self.angle = float(angle)
            self.preferred_units = preferred_units
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
            self.preferred_units = preferred_units

    def __str__(self):
        return self.angle_preferred

    def __copy__(self):
        return Angle(
            self.angle, preferred_units=self.preferred_units, digits=self._digits
        )

    def __eq__(self, other):
        if hasattr(other, "angle"):
            other = other.angle
        c1 = abs((self.angle % tau) - (other % tau)) <= 1e-11
        return c1

    def __add__(self, other):
        if isinstance(other, Angle):
            return Angle(
                self.angle + other.angle,
                preferred_units=self.preferred_units,
                digits=self._digits,
            )
        return Angle(
            self.angle + other,
            preferred_units=self.preferred_units,
            digits=self._digits,
        )

    def __sub__(self, other):
        return -self + other

    def __truediv__(self, other):
        return Angle(
            self.radians / other,
            preferred_units=self.preferred_units,
            digits=self._digits,
        )

    def __mul__(self, other):
        return Angle(
            self.radians * other,
            preferred_units=self.preferred_units,
            digits=self._digits,
        )

    def __radd__(self, other):
        return self.__add__(other)

    def __rsub__(self, other):
        return self.__neg__().__add__(other)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __iadd__(self, other):
        if isinstance(other, Angle):
            other = other.angle
        self.angle += other
        return self

    def __isub__(self, other):
        if isinstance(other, Angle):
            other = other.angle
        self.angle -= other
        return self

    def __imul__(self, other):
        if isinstance(other, Angle):
            other = other.angle
        self.angle *= other
        return self

    def __idiv__(self, other):
        if isinstance(other, Angle):
            other = other.angle
        self.angle /= other
        return self

    def __float__(self):
        return self.angle

    def __neg__(self):
        return Angle(
            -self.angle, preferred_units=self.preferred_units, digits=self._digits
        )

    def normalize(self):
        self.angle /= tau

    @classmethod
    def from_radians(cls, radians):
        return cls(radians)

    @classmethod
    def from_degrees(cls, degrees):
        return cls(tau * degrees / 360.0)

    @classmethod
    def from_gradians(cls, gradians):
        return cls(tau * gradians / 400.0)

    @classmethod
    def from_turns(cls, turns):
        return cls(tau * turns)

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
        return self.angle

    @property
    def degrees(self):
        return self.angle * 360.0 / tau

    @property
    def gradians(self):
        return self.angle * 400.0 / tau

    @property
    def turns(self):
        return self.angle / tau

    @property
    def angle_radians(self):
        digits = 4 if self._digits is None else self._digits
        angle = f"{self.radians:.{digits}f}".rstrip("0").rstrip(".")
        return f"{angle}rad"

    @property
    def angle_degrees(self):
        digits = 4 if self._digits is None else self._digits
        angle = f"{self.degrees:.{digits}f}".rstrip("0").rstrip(".")
        return f"{angle}deg"

    @property
    def angle_gradians(self):
        digits = 4 if self._digits is None else self._digits
        angle = f"{self.gradians:.{digits}f}".rstrip("0").rstrip(".")
        return f"{angle}grad"

    @property
    def angle_turns(self):
        digits = 4 if self._digits is None else self._digits
        angle = f"{self.turns:.{digits}f}".rstrip("0").rstrip(".")
        return f"{angle}turn"

    def is_orthogonal(self):
        return (self.angle % (tau / 4.0)) == 0


def viewbox_transform(
    e_x, e_y, e_width, e_height, vb_x, vb_y, vb_width, vb_height, aspect
):
    """
    SVG 1.1 7.2, SVG 2.0 8.2 equivalent transform of an SVG viewport.
    Regarding https://github.com/w3c/svgwg/issues/215 use 8.2 version.

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


# TODO: Add in speed for units. mm/s in/s mm/minute.
