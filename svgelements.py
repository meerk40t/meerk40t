from __future__ import division

import re

try:
    from collections.abc import MutableSequence  # noqa
except ImportError:
    from collections import MutableSequence  # noqa
from copy import copy
from math import *

from xml.etree.ElementTree import iterparse

try:
    from math import tau
except ImportError:
    tau = pi * 2

"""
The path elements are derived from regebro's svg.path project ( https://github.com/regebro/svg.path ) with
some of the math from mathandy's svgpathtools project ( https://github.com/mathandy/svgpathtools ).

The Zingl-Bresenham plotting algorithms are from Alois Zingl's "The Beauty of Bresenham's Algorithm"
( http://members.chello.at/easyfilter/bresenham.html ). They are all MIT Licensed and this library is
also MIT licensed. In the case of Zingl's work this isn't explicit from his website, however from personal
correspondence "'Free and open source' means you can do anything with it like the MIT licence."

The goal is to provide svg like path objects and structures. The svg standard 1.1 and elements of 2.0 will
be used to provide much of the decisions within path objects. Such that if there is a question on
implementation if the SVG documentation has a methodology it should be used.
"""

MIN_DEPTH = 5
ERROR = 1e-12

max_depth = 0

# SVG STATIC VALUES
DEFAULT_PPI = 96.0
SVG_NAME_TAG = 'svg'
SVG_ATTR_VERSION = 'version'
SVG_VALUE_VERSION = '1.1'
SVG_ATTR_XMLNS = 'xmlns'
SVG_VALUE_XMLNS = 'http://www.w3.org/2000/svg'
SVG_ATTR_XMLNS_LINK = 'xmlns:xlink'
SVG_VALUE_XLINK = 'http://www.w3.org/1999/xlink'
SVG_ATTR_XMLNS_EV = 'xmlns:ev'
SVG_VALUE_XMLNS_EV = 'http://www.w3.org/2001/xml-events'

XLINK_HREF = '{http://www.w3.org/1999/xlink}href'
SVG_HREF = "href"
SVG_ATTR_WIDTH = 'width'
SVG_ATTR_HEIGHT = 'height'
SVG_ATTR_VIEWBOX = 'viewBox'
SVG_VIEWBOX_TRANSFORM = 'viewbox_transform'
SVG_TAG_PATH = 'path'
SVG_TAG_GROUP = 'g'
SVG_TAG_RECT = 'rect'
SVG_TAG_CIRCLE = 'circle'
SVG_TAG_ELLIPSE = 'ellipse'
SVG_TAG_LINE = 'line'
SVG_TAG_POLYLINE = 'polyline'
SVG_TAG_POLYGON = 'polygon'
SVG_TAG_TEXT = 'text'
SVG_TAG_IMAGE = 'image'
SVG_TAG_DESC = 'desc'
SVG_ATTR_ID = 'id'
SVG_ATTR_DATA = 'd'
SVG_ATTR_COLOR = 'color'
SVG_ATTR_FILL = 'fill'
SVG_ATTR_STROKE = 'stroke'
SVG_ATTR_STROKE_WIDTH = 'stroke-width'
SVG_ATTR_TRANSFORM = 'transform'
SVG_ATTR_STYLE = 'style'
SVG_ATTR_CENTER_X = 'cx'
SVG_ATTR_CENTER_Y = 'cy'
SVG_ATTR_RADIUS_X = 'rx'
SVG_ATTR_RADIUS_Y = 'ry'
SVG_ATTR_RADIUS = 'r'
SVG_ATTR_POINTS = 'points'
SVG_ATTR_PRESERVEASPECTRATIO = 'preserveAspectRatio'
SVG_ATTR_X = 'x'
SVG_ATTR_Y = 'y'
SVG_ATTR_X0 = 'x0'
SVG_ATTR_Y0 = 'y0'
SVG_ATTR_X1 = 'x1'
SVG_ATTR_Y1 = 'y1'
SVG_ATTR_X2 = 'x2'
SVG_ATTR_Y2 = 'y2'
SVG_ATTR_DX = 'dx'
SVG_ATTR_DY = 'dy'
SVG_ATTR_TAG = 'tag'
SVG_ATTR_FONT = 'font'
SVG_TRANSFORM_MATRIX = 'matrix'
SVG_TRANSFORM_TRANSLATE = 'translate'
SVG_TRANSFORM_SCALE = 'scale'
SVG_TRANSFORM_ROTATE = 'rotate'
SVG_TRANSFORM_SKEW_X = 'skewx'
SVG_TRANSFORM_SKEW_Y = 'skewy'
SVG_TRANSFORM_SKEW = 'skew'
SVG_TRANSFORM_TRANSLATE_X = 'translatex'
SVG_TRANSFORM_TRANSLATE_Y = 'translatey'
SVG_TRANSFORM_SCALE_X = 'scalex'
SVG_TRANSFORM_SCALE_Y = 'scaley'
SVG_VALUE_NONE = 'none'
SVG_VALUE_CURRENT_COLOR = 'currentColor'

PATTERN_WS = r'[\s\t\n]*'
PATTERN_COMMA = r'(?:\s*,\s*|\s+|(?=-))'
PATTERN_FLOAT = '[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?'
PATTERN_LENGTH_UNITS = 'cm|mm|Q|in|pt|pc|px|em|cx|ch|rem|vw|vh|vmin|vmax'
PATTERN_ANGLE_UNITS = 'deg|grad|rad|turn'
PATTERN_TIME_UNITS = 's|ms'
PATTERN_FREQUENCY_UNITS = 'Hz|kHz'
PATTERN_RESOLUTION_UNITS = 'dpi|dpcm|dppx'
PATTERN_PERCENT = '%'
PATTERN_TRANSFORM = SVG_TRANSFORM_MATRIX + '|' \
                    + SVG_TRANSFORM_TRANSLATE + '|' \
                    + SVG_TRANSFORM_TRANSLATE_X + '|' \
                    + SVG_TRANSFORM_TRANSLATE_Y + '|' \
                    + SVG_TRANSFORM_SCALE + '|' \
                    + SVG_TRANSFORM_SCALE_X + '|' \
                    + SVG_TRANSFORM_SCALE_Y + '|' \
                    + SVG_TRANSFORM_ROTATE + '|' \
                    + SVG_TRANSFORM_SKEW + '|' \
                    + SVG_TRANSFORM_SKEW_X + '|' \
                    + SVG_TRANSFORM_SKEW_Y
PATTERN_TRANSFORM_UNITS = PATTERN_LENGTH_UNITS + '|' \
                          + PATTERN_ANGLE_UNITS + '|' \
                          + PATTERN_PERCENT

REGEX_FLOAT = re.compile(PATTERN_FLOAT)
REGEX_COORD_PAIR = re.compile('(%s)%s(%s)' % (PATTERN_FLOAT, PATTERN_COMMA, PATTERN_FLOAT))
REGEX_TRANSFORM_TEMPLATE = re.compile('(?u)(%s)%s\(([^)]+)\)' % (PATTERN_TRANSFORM, PATTERN_WS))
REGEX_TRANSFORM_PARAMETER = re.compile('(%s)%s(%s)?' % (PATTERN_FLOAT, PATTERN_WS, PATTERN_TRANSFORM_UNITS))
REGEX_COLOR_HEX = re.compile(r'^#?([0-9A-Fa-f]{3,8})$')
REGEX_COLOR_RGB = re.compile(
    r'rgba?\(\s*(%s)\s*,\s*(%s)\s*,\s*(%s)\s*(?:,\s*(%s)\s*)?\)' % (
        PATTERN_FLOAT, PATTERN_FLOAT, PATTERN_FLOAT, PATTERN_FLOAT))
REGEX_COLOR_RGB_PERCENT = re.compile(
    r'rgba?\(\s*(%s)%%\s*,\s*(%s)%%\s*,\s*(%s)%%\s*(?:,\s*(%s)\s*)?\)' % (
        PATTERN_FLOAT, PATTERN_FLOAT, PATTERN_FLOAT, PATTERN_FLOAT))
REGEX_COLOR_HSL = re.compile(
    r'hsla?\(\s*(%s)\s*,\s*(%s)%%\s*,\s*(%s)%%\s*(?:,\s*(%s)\s*)?\)' % (
        PATTERN_FLOAT, PATTERN_FLOAT, PATTERN_FLOAT, PATTERN_FLOAT))
REGEX_LENGTH = re.compile('(%s)([A-Za-z%%]*)' % PATTERN_FLOAT)


# PathTokens class.
class PathTokens:
    """Path Tokens is the class for the general outline of how SVG Pathd objects
    are stored. Namely, a single non-'e' character and a collection of floating
    point numbers. While this is explicitly used for SVG pathd objects the method
    for serializing command data in this fashion is also useful as a standalone
    class."""

    def __init__(self, command_elements):
        self.command_elements = command_elements
        commands = ''
        for k in command_elements:
            commands += k
        self.COMMAND_RE = re.compile("([%s])" % (commands))
        self.elements = None
        self.command = None
        self.last_command = None
        self.parser = None

    def _tokenize_path(self, pathdef):
        for x in self.COMMAND_RE.split(pathdef):
            if x in self.command_elements:
                yield x
            for token in REGEX_FLOAT.findall(x):
                yield token

    def get(self):
        """Gets the element from the stack."""
        return self.elements.pop()

    def pre_execute(self):
        """Called before any command element is executed."""
        pass

    def post_execute(self):
        """Called after any command element is executed."""
        pass

    def new_command(self):
        """Called when command element is switched."""
        pass

    def parse(self, pathdef):
        self.elements = list(self._tokenize_path(pathdef))
        # Reverse for easy use of .pop()
        self.elements.reverse()

        while self.elements:
            if self.elements[-1] in self.command_elements:
                self.last_command = self.command
                self.command = self.get()
                self.new_command()
            else:
                if self.command is None:
                    raise ValueError("Invalid command.")  # could be faulty implicit or unaccepted element.
            self.pre_execute()
            self.command_elements[self.command]()
            self.post_execute()


# SVG Path Tokens.
class SVGPathTokens(PathTokens):
    """Utilizes the general PathTokens class to parse SVG pathd strings.
    This class has been updated to account for SVG 2.0 version of the zZ command."""

    def __init__(self):
        PathTokens.__init__(self, {
            'M': self.move_to,
            'm': self.move_to,
            'L': self.line_to,
            'l': self.line_to,
            "H": self.h_to,
            "h": self.h_to,
            "V": self.v_to,
            "v": self.v_to,
            "C": self.cubic_to,
            "c": self.cubic_to,
            "S": self.smooth_cubic_to,
            "s": self.smooth_cubic_to,
            "Q": self.quad_to,
            "q": self.quad_to,
            "T": self.smooth_quad_to,
            "t": self.smooth_quad_to,
            "A": self.arc_to,
            "a": self.arc_to,
            "Z": self.close,
            "z": self.close
        })
        self.parser = None
        self.absolute = False

    def svg_parse(self, parser, pathdef):
        self.parser = parser
        self.absolute = False
        self.parser.start()
        self.parse(pathdef)
        self.parser.end()

    def get_pos(self):
        if self.command == 'Z':
            return "z"  # After Z, all further expected values are also Z.
        coord0 = self.get()
        if coord0 == 'z' or coord0 == 'Z':
            self.command = 'Z'
            return "z"
        coord1 = self.get()
        position = (float(coord0), float(coord1))
        if not self.absolute:
            current_pos = self.parser.current_point
            if current_pos is None:
                return position
            return [position[0] + current_pos[0], position[1] + current_pos[1]]
        return position

    def move_to(self):
        # Moveto command.
        pos = self.get_pos()
        self.parser.move(pos)

        # Implicit moveto commands are treated as lineto commands.
        # So we set command to lineto here, in case there are
        # further implicit commands after this moveto.
        self.command = 'L'

    def line_to(self):
        pos = self.get_pos()
        self.parser.line(pos)

    def h_to(self):
        x = float(self.get())
        if self.absolute:
            self.parser.absolute_h(x)
        else:
            self.parser.relative_h(x)

    def v_to(self):
        y = float(self.get())
        if self.absolute:
            self.parser.absolute_v(y)
        else:
            self.parser.relative_v(y)

    def cubic_to(self):
        control1 = self.get_pos()
        control2 = self.get_pos()
        end = self.get_pos()
        self.parser.cubic(control1, control2, end)

    def smooth_cubic_to(self):
        control2 = self.get_pos()
        end = self.get_pos()
        self.parser.smooth_cubic(control2, end)

    def quad_to(self):
        control = self.get_pos()
        end = self.get_pos()
        self.parser.quad(control, end)

    def smooth_quad_to(self):
        end = self.get_pos()
        self.parser.smooth_quad(end)

    def arc_to(self):
        rx = float(self.get())
        ry = float(self.get())
        rotation = float(self.get())
        arc = float(self.get())
        sweep = float(self.get())
        end = self.get_pos()

        self.parser.arc(rx, ry, rotation, arc, sweep, end)

    def close(self):
        # Close path
        self.parser.closed()
        self.command = None

    def new_command(self):
        self.absolute = self.command.isupper()

    def post_execute(self):
        pass


class Length(object):
    """
    SVGLength as used in SVG

    Length are lazy solving values. Several conversion values are typically unknown by default and length simply
    stores that ambiguity. So we can have a length of 50% and without calling .value(relative_length=3000) it will
    simply store as 50%. Likewise you can have discrete values like 30cm or 20in which have knowable discrete values
    but are not knowable in pixels unless a PPI value is supplied. We can say .value(relative_length=30cm, PPI=96) and
    solve this for a value like 12%. We can also convert values between knowable lengths. So 30cm in 300mm regardless
    whether we know how to convert this to pixels. 0% is 0 in any units or relative values. We can convert pixels to
    pc and pt without issue. We can convert vh, vw, vmax, vmin values if we know viewbox values. We can convert em
    values if we know the font_size. We can add values together if they are convertible units. Length("20in") + "3cm".

    If .value() cannot solve for the value with the given information then it will return a Length value. If it can
    be solved it will return a float.
    """

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
        self.units = ''

    def __float__(self):
        if self.amount is None:
            return None
        if self.units == 'pt':
            return self.amount * 1.3333
        elif self.units == 'pc':
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
            if self.units == '%':
                self.units = other.units
                self.amount = self.amount * other.amount / 100.0
                return self
            elif other.units == '%':
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
        if self.units == 'px' or self.units == '':
            if other.units == 'px' or other.units == '':
                self.amount += other.amount
            elif other.units == 'pt':
                self.amount += other.amount * 1.3333
            elif other.units == 'pc':
                self.amount += other.amount * 16.0
            else:
                raise ValueError
            return self
        if self.units == 'pt':
            if other.units == 'px' or other.units == '':
                self.amount += other.amount / 1.3333
            elif other.units == 'pc':
                self.amount += other.amount * 12.0
            else:
                raise ValueError
            return self
        elif self.units == 'pc':
            if other.units == 'px' or other.units == '':
                self.amount += other.amount / 16.0
            elif other.units == 'pt':
                self.amount += other.amount / 12.0
            else:
                raise ValueError
            return self
        elif self.units == 'cm':
            if other.units == 'mm':
                self.amount += other.amount / 10.0
            elif other.units == 'in':
                self.amount += other.amount / 0.393701
            else:
                raise ValueError
            return self
        elif self.units == 'mm':
            if other.units == 'cm':
                self.amount += other.amount * 10.0
            elif other.units == 'in':
                self.amount += other.amount / 0.0393701
            else:
                raise ValueError
            return self
        elif self.units == 'in':
            if other.units == 'cm':
                self.amount += other.amount * 0.393701
            elif other.units == 'mm':
                self.amount += other.amount * 0.0393701
            else:
                raise ValueError
            return self
        raise ValueError

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
        if self.units == 'px' or self.units == '':
            if other.units == 'px' or other.units == '':
                return self.amount / other.amount
            elif other.units == 'pt':
                return self.amount / (other.amount * 1.3333)
            elif other.units == 'pc':
                return self.amount / (other.amount * 16.0)
            else:
                raise ValueError
        if self.units == 'pt':
            if other.units == 'px' or other.units == '':
                return self.amount / (other.amount / 1.3333)
            elif other.units == 'pc':
                return self.amount / (other.amount * 12.0)
            else:
                raise ValueError
        if self.units == 'pc':
            if other.units == 'px' or other.units == '':
                return self.amount / (other.amount / 16.0)
            elif other.units == 'pt':
                return self.amount / (other.amount / 12.0)
            else:
                raise ValueError
        if self.units == 'cm':
            if other.units == 'mm':
                return self.amount / (other.amount / 10.0)
            elif other.units == 'in':
                return self.amount / (other.amount / 0.393701)
            else:
                raise ValueError
        if self.units == 'mm':
            if other.units == 'cm':
                return self.amount / (other.amount * 10.0)
            elif other.units == 'in':
                return self.amount / (other.amount / 0.0393701)
            else:
                raise ValueError
        if self.units == 'in':
            if other.units == 'cm':
                return self.amount / (other.amount * 0.393701)
            elif other.units == 'mm':
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
        return 'Length(\'%s\')' % (str(self))

    def __str__(self):
        if self.amount is None:
            return SVG_VALUE_NONE
        return '%s%s' % (Length.str(self.amount), self.units)

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
        if self.units == 'px' or self.units == '':
            return self.amount
        if self.units == 'pt':
            return self.amount / 1.3333
        if self.units == 'pc':
            return self.amount / 16.0
        return None

    def in_inches(self):
        if self.units == 'mm':
            return self.amount * 0.0393701
        if self.units == 'cm':
            return self.amount * 0.393701
        if self.units == 'in':
            return self.amount
        return None

    def to_mm(self, ppi=DEFAULT_PPI, relative_length=None, font_size=None, font_height=None, viewbox=None):
        value = self.value(ppi=ppi, relative_length=relative_length, font_size=font_size,
                           font_height=font_height, viewbox=viewbox)
        v = value / (ppi * 0.0393701)
        return Length("%smm" % (Length.str(v)))

    def to_cm(self, ppi=DEFAULT_PPI, relative_length=None, font_size=None, font_height=None, viewbox=None):
        value = self.value(ppi=ppi, relative_length=relative_length,
                           font_size=font_size, font_height=font_height, viewbox=viewbox)
        v = value / (ppi * 0.393701)
        return Length("%scm" % (Length.str(v)))

    def to_inch(self, ppi=DEFAULT_PPI, relative_length=None, font_size=None, font_height=None, viewbox=None):
        value = self.value(ppi=ppi, relative_length=relative_length,
                           font_size=font_size, font_height=font_height, viewbox=viewbox)
        v = value / ppi
        return Length("%sin" % (Length.str(v)))

    def value(self, ppi=None, relative_length=None, font_size=None, font_height=None, viewbox=None):
        if self.amount is None:
            return None
        if self.units == '%':
            if relative_length is None:
                return self
            fraction = self.amount / 100.0
            if isinstance(relative_length, (float, int)):
                return fraction * relative_length
            elif isinstance(relative_length, (str, Length)):
                length = relative_length * self
                if isinstance(length, Length):
                    return length.value(ppi=ppi, font_size=font_size, font_height=font_height, viewbox=viewbox)
                return length
            return self
        if self.units == 'mm':
            if ppi is None:
                return self
            return self.amount * ppi * 0.0393701
        if self.units == 'cm':
            if ppi is None:
                return self
            return self.amount * ppi * 0.393701
        if self.units == 'in':
            if ppi is None:
                return self
            return self.amount * ppi
        if self.units == 'px' or self.units == '':
            return self.amount
        if self.units == 'pt':
            return self.amount * 1.3333
        if self.units == 'pc':
            return self.amount * 16.0
        if self.units == 'em':
            if font_size is None:
                return self
            return self.amount * float(font_size)
        if self.units == 'ex':
            if font_height is None:
                return self
            return self.amount * float(font_height)
        if self.units == 'vw':
            if viewbox is None:
                return self
            v = Viewbox(viewbox)
            return self.amount * v.viewbox_width / 100.0
        if self.units == 'vh':
            if viewbox is None:
                return self
            v = Viewbox(viewbox)
            return self.amount * v.viewbox_height / 100.0
        if self.units == 'vmin':
            if viewbox is None:
                return self
            v = Viewbox(viewbox)
            m = min(v.viewbox_height, v.viewbox_height)
            return self.amount * m / 100.0
        if self.units == 'vmax':
            if viewbox is None:
                return self
            v = Viewbox(viewbox)
            m = max(v.viewbox_height, v.viewbox_height)
            return self.amount * m / 100.0
        try:
            return float(self)
        except ValueError:
            return self

    @staticmethod
    def str(s):
        if isinstance(s, Length):
            if s.units == '':
                s = s.amount
            else:
                a = '%.12f' % (s.amount)
                if '.' in a:
                    a = a.rstrip('0').rstrip('.')
                return '\'%s%s\'' % (a, s.units)
        s = '%.12f' % (s)
        if '.' in s:
            s = s.rstrip('0').rstrip('.')
        return s


class Color(object):
    """
    SVG Color Parsing
    Parses different forms of defining colors.

    Including keyword: https://www.w3.org/TR/SVG11/types.html#ColorKeywords
    """

    def __init__(self, *args):
        if len(args) == 1:
            v = args[0]
            if isinstance(v, Color):
                self.value = v.value
            elif isinstance(v, int):
                self.value = v
            else:
                self.value = Color.parse(v)
        elif len(args) == 3:
            r = args[0]
            g = args[1]
            b = args[2]
            self.value = Color.rgb_to_int(r, g, b)
        elif len(args) == 4:
            r = args[0]
            g = args[1]
            b = args[2]
            opacity = args[3] / 255.0
            self.value = Color.rgb_to_int(r, g, b, opacity)
        else:
            self.value = 0

    def __int__(self):
        return self.value

    def __str__(self):
        if self.value is None:
            return str(self.value)
        return self.hex

    def __repr__(self):
        if self.value is None:
            return 'Color(\'%s\')' % (self.value)
        return 'Color(\'%s\')' % (self.hex)

    def __eq__(self, other):
        if self is other:
            return True
        first = self.value
        second = other
        if isinstance(second, str):
            second = Color(second)
        if isinstance(second, Color):
            second = second.value
        return first == second

    def __ne__(self, other):
        return not self == other

    @staticmethod
    def rgb_to_int(r, g, b, opacity=1.0):
        if opacity > 1:
            opacity = 1.0
        if opacity < 0:
            opacity = 0
        r = Color.crimp(r)
        g = Color.crimp(g)
        b = Color.crimp(b)
        a = Color.crimp(opacity * 255.0)
        if a & 0x80 != 0:
            a ^= 0x80
            a <<= 24
            a = ~a
            a ^= 0x7FFFFFFF
        else:
            a <<= 24
        r <<= 16
        g <<= 8
        c = r | g | b | a
        return c

    @staticmethod
    def hsl_to_int(h, s, l, opacity=1.0):
        c = Color()
        c.opacity = opacity
        c.hsl = h, s, l
        return c.value

    @staticmethod
    def parse(color_string):
        """Parse SVG color, will return a set value."""
        if color_string is None or color_string == SVG_VALUE_NONE:
            return None
        match = REGEX_COLOR_HEX.match(color_string)
        if match:
            return Color.parse_color_hex(color_string)
        match = REGEX_COLOR_RGB.match(color_string)
        if match:
            return Color.parse_color_rgb(match.groups())
        match = REGEX_COLOR_RGB_PERCENT.match(color_string)
        if match:
            return Color.parse_color_rgbp(match.groups())
        match = REGEX_COLOR_HSL.match(color_string)
        if match:
            return Color.parse_color_hsl(match.groups())
        return Color.parse_color_lookup(color_string)

    @staticmethod
    def parse_color_lookup(v):
        """Parse SVG Color by Keyword on dictionary lookup"""
        if not isinstance(v, str):
            return Color.rgb_to_int(0, 0, 0)
        else:
            v = v.replace(' ', '').lower()
        if v == "transparent":
            return Color.rgb_to_int(0, 0, 0, 0.0)
        if v == "aliceblue":
            return Color.rgb_to_int(250, 248, 255)
        if v == "aliceblue":
            return Color.rgb_to_int(240, 248, 255)
        if v == "antiquewhite":
            return Color.rgb_to_int(250, 235, 215)
        if v == "aqua":
            return Color.rgb_to_int(0, 255, 255)
        if v == "aquamarine":
            return Color.rgb_to_int(127, 255, 212)
        if v == "azure":
            return Color.rgb_to_int(240, 255, 255)
        if v == "beige":
            return Color.rgb_to_int(245, 245, 220)
        if v == "bisque":
            return Color.rgb_to_int(255, 228, 196)
        if v == "black":
            return Color.rgb_to_int(0, 0, 0)
        if v == "blanchedalmond":
            return Color.rgb_to_int(255, 235, 205)
        if v == "blue":
            return Color.rgb_to_int(0, 0, 255)
        if v == "blueviolet":
            return Color.rgb_to_int(138, 43, 226)
        if v == "brown":
            return Color.rgb_to_int(165, 42, 42)
        if v == "burlywood":
            return Color.rgb_to_int(222, 184, 135)
        if v == "cadetblue":
            return Color.rgb_to_int(95, 158, 160)
        if v == "chartreuse":
            return Color.rgb_to_int(127, 255, 0)
        if v == "chocolate":
            return Color.rgb_to_int(210, 105, 30)
        if v == "coral":
            return Color.rgb_to_int(255, 127, 80)
        if v == "cornflowerblue":
            return Color.rgb_to_int(100, 149, 237)
        if v == "cornsilk":
            return Color.rgb_to_int(255, 248, 220)
        if v == "crimson":
            return Color.rgb_to_int(220, 20, 60)
        if v == "cyan":
            return Color.rgb_to_int(0, 255, 255)
        if v == "darkblue":
            return Color.rgb_to_int(0, 0, 139)
        if v == "darkcyan":
            return Color.rgb_to_int(0, 139, 139)
        if v == "darkgoldenrod":
            return Color.rgb_to_int(184, 134, 11)
        if v == "darkgray":
            return Color.rgb_to_int(169, 169, 169)
        if v == "darkgreen":
            return Color.rgb_to_int(0, 100, 0)
        if v == "darkgrey":
            return Color.rgb_to_int(169, 169, 169)
        if v == "darkkhaki":
            return Color.rgb_to_int(189, 183, 107)
        if v == "darkmagenta":
            return Color.rgb_to_int(139, 0, 139)
        if v == "darkolivegreen":
            return Color.rgb_to_int(85, 107, 47)
        if v == "darkorange":
            return Color.rgb_to_int(255, 140, 0)
        if v == "darkorchid":
            return Color.rgb_to_int(153, 50, 204)
        if v == "darkred":
            return Color.rgb_to_int(139, 0, 0)
        if v == "darksalmon":
            return Color.rgb_to_int(233, 150, 122)
        if v == "darkseagreen":
            return Color.rgb_to_int(143, 188, 143)
        if v == "darkslateblue":
            return Color.rgb_to_int(72, 61, 139)
        if v == "darkslategray":
            return Color.rgb_to_int(47, 79, 79)
        if v == "darkslategrey":
            return Color.rgb_to_int(47, 79, 79)
        if v == "darkturquoise":
            return Color.rgb_to_int(0, 206, 209)
        if v == "darkviolet":
            return Color.rgb_to_int(148, 0, 211)
        if v == "deeppink":
            return Color.rgb_to_int(255, 20, 147)
        if v == "deepskyblue":
            return Color.rgb_to_int(0, 191, 255)
        if v == "dimgray":
            return Color.rgb_to_int(105, 105, 105)
        if v == "dimgrey":
            return Color.rgb_to_int(105, 105, 105)
        if v == "dodgerblue":
            return Color.rgb_to_int(30, 144, 255)
        if v == "firebrick":
            return Color.rgb_to_int(178, 34, 34)
        if v == "floralwhite":
            return Color.rgb_to_int(255, 250, 240)
        if v == "forestgreen":
            return Color.rgb_to_int(34, 139, 34)
        if v == "fuchsia":
            return Color.rgb_to_int(255, 0, 255)
        if v == "gainsboro":
            return Color.rgb_to_int(220, 220, 220)
        if v == "ghostwhite":
            return Color.rgb_to_int(248, 248, 255)
        if v == "gold":
            return Color.rgb_to_int(255, 215, 0)
        if v == "goldenrod":
            return Color.rgb_to_int(218, 165, 32)
        if v == "gray":
            return Color.rgb_to_int(128, 128, 128)
        if v == "grey":
            return Color.rgb_to_int(128, 128, 128)
        if v == "green":
            return Color.rgb_to_int(0, 128, 0)
        if v == "greenyellow":
            return Color.rgb_to_int(173, 255, 47)
        if v == "honeydew":
            return Color.rgb_to_int(240, 255, 240)
        if v == "hotpink":
            return Color.rgb_to_int(255, 105, 180)
        if v == "indianred":
            return Color.rgb_to_int(205, 92, 92)
        if v == "indigo":
            return Color.rgb_to_int(75, 0, 130)
        if v == "ivory":
            return Color.rgb_to_int(255, 255, 240)
        if v == "khaki":
            return Color.rgb_to_int(240, 230, 140)
        if v == "lavender":
            return Color.rgb_to_int(230, 230, 250)
        if v == "lavenderblush":
            return Color.rgb_to_int(255, 240, 245)
        if v == "lawngreen":
            return Color.rgb_to_int(124, 252, 0)
        if v == "lemonchiffon":
            return Color.rgb_to_int(255, 250, 205)
        if v == "lightblue":
            return Color.rgb_to_int(173, 216, 230)
        if v == "lightcoral":
            return Color.rgb_to_int(240, 128, 128)
        if v == "lightcyan":
            return Color.rgb_to_int(224, 255, 255)
        if v == "lightgoldenrodyellow":
            return Color.rgb_to_int(250, 250, 210)
        if v == "lightgray":
            return Color.rgb_to_int(211, 211, 211)
        if v == "lightgreen":
            return Color.rgb_to_int(144, 238, 144)
        if v == "lightgrey":
            return Color.rgb_to_int(211, 211, 211)
        if v == "lightpink":
            return Color.rgb_to_int(255, 182, 193)
        if v == "lightsalmon":
            return Color.rgb_to_int(255, 160, 122)
        if v == "lightseagreen":
            return Color.rgb_to_int(32, 178, 170)
        if v == "lightskyblue":
            return Color.rgb_to_int(135, 206, 250)
        if v == "lightslategray":
            return Color.rgb_to_int(119, 136, 153)
        if v == "lightslategrey":
            return Color.rgb_to_int(119, 136, 153)
        if v == "lightsteelblue":
            return Color.rgb_to_int(176, 196, 222)
        if v == "lightyellow":
            return Color.rgb_to_int(255, 255, 224)
        if v == "lime":
            return Color.rgb_to_int(0, 255, 0)
        if v == "limegreen":
            return Color.rgb_to_int(50, 205, 50)
        if v == "linen":
            return Color.rgb_to_int(250, 240, 230)
        if v == "magenta":
            return Color.rgb_to_int(255, 0, 255)
        if v == "maroon":
            return Color.rgb_to_int(128, 0, 0)
        if v == "mediumaquamarine":
            return Color.rgb_to_int(102, 205, 170)
        if v == "mediumblue":
            return Color.rgb_to_int(0, 0, 205)
        if v == "mediumorchid":
            return Color.rgb_to_int(186, 85, 211)
        if v == "mediumpurple":
            return Color.rgb_to_int(147, 112, 219)
        if v == "mediumseagreen":
            return Color.rgb_to_int(60, 179, 113)
        if v == "mediumslateblue":
            return Color.rgb_to_int(123, 104, 238)
        if v == "mediumspringgreen":
            return Color.rgb_to_int(0, 250, 154)
        if v == "mediumturquoise":
            return Color.rgb_to_int(72, 209, 204)
        if v == "mediumvioletred":
            return Color.rgb_to_int(199, 21, 133)
        if v == "midnightblue":
            return Color.rgb_to_int(25, 25, 112)
        if v == "mintcream":
            return Color.rgb_to_int(245, 255, 250)
        if v == "mistyrose":
            return Color.rgb_to_int(255, 228, 225)
        if v == "moccasin":
            return Color.rgb_to_int(255, 228, 181)
        if v == "navajowhite":
            return Color.rgb_to_int(255, 222, 173)
        if v == "navy":
            return Color.rgb_to_int(0, 0, 128)
        if v == "oldlace":
            return Color.rgb_to_int(253, 245, 230)
        if v == "olive":
            return Color.rgb_to_int(128, 128, 0)
        if v == "olivedrab":
            return Color.rgb_to_int(107, 142, 35)
        if v == "orange":
            return Color.rgb_to_int(255, 165, 0)
        if v == "orangered":
            return Color.rgb_to_int(255, 69, 0)
        if v == "orchid":
            return Color.rgb_to_int(218, 112, 214)
        if v == "palegoldenrod":
            return Color.rgb_to_int(238, 232, 170)
        if v == "palegreen":
            return Color.rgb_to_int(152, 251, 152)
        if v == "paleturquoise":
            return Color.rgb_to_int(175, 238, 238)
        if v == "palevioletred":
            return Color.rgb_to_int(219, 112, 147)
        if v == "papayawhip":
            return Color.rgb_to_int(255, 239, 213)
        if v == "peachpuff":
            return Color.rgb_to_int(255, 218, 185)
        if v == "peru":
            return Color.rgb_to_int(205, 133, 63)
        if v == "pink":
            return Color.rgb_to_int(255, 192, 203)
        if v == "plum":
            return Color.rgb_to_int(221, 160, 221)
        if v == "powderblue":
            return Color.rgb_to_int(176, 224, 230)
        if v == "purple":
            return Color.rgb_to_int(128, 0, 128)
        if v == "red":
            return Color.rgb_to_int(255, 0, 0)
        if v == "rosybrown":
            return Color.rgb_to_int(188, 143, 143)
        if v == "royalblue":
            return Color.rgb_to_int(65, 105, 225)
        if v == "saddlebrown":
            return Color.rgb_to_int(139, 69, 19)
        if v == "salmon":
            return Color.rgb_to_int(250, 128, 114)
        if v == "sandybrown":
            return Color.rgb_to_int(244, 164, 96)
        if v == "seagreen":
            return Color.rgb_to_int(46, 139, 87)
        if v == "seashell":
            return Color.rgb_to_int(255, 245, 238)
        if v == "sienna":
            return Color.rgb_to_int(160, 82, 45)
        if v == "silver":
            return Color.rgb_to_int(192, 192, 192)
        if v == "skyblue":
            return Color.rgb_to_int(135, 206, 235)
        if v == "slateblue":
            return Color.rgb_to_int(106, 90, 205)
        if v == "slategray":
            return Color.rgb_to_int(112, 128, 144)
        if v == "slategrey":
            return Color.rgb_to_int(112, 128, 144)
        if v == "snow":
            return Color.rgb_to_int(255, 250, 250)
        if v == "springgreen":
            return Color.rgb_to_int(0, 255, 127)
        if v == "steelblue":
            return Color.rgb_to_int(70, 130, 180)
        if v == "tan":
            return Color.rgb_to_int(210, 180, 140)
        if v == "teal":
            return Color.rgb_to_int(0, 128, 128)
        if v == "thistle":
            return Color.rgb_to_int(216, 191, 216)
        if v == "tomato":
            return Color.rgb_to_int(255, 99, 71)
        if v == "turquoise":
            return Color.rgb_to_int(64, 224, 208)
        if v == "violet":
            return Color.rgb_to_int(238, 130, 238)
        if v == "wheat":
            return Color.rgb_to_int(245, 222, 179)
        if v == "white":
            return Color.rgb_to_int(255, 255, 255)
        if v == "whitesmoke":
            return Color.rgb_to_int(245, 245, 245)
        if v == "yellow":
            return Color.rgb_to_int(255, 255, 0)
        if v == "yellowgreen":
            return Color.rgb_to_int(154, 205, 50)
        return Color.rgb_to_int(0, 0, 0)

    @staticmethod
    def parse_color_hex(hex_string):
        """Parse SVG Color by Hex String"""
        h = hex_string.lstrip('#')
        size = len(h)
        if size == 8:
            return int(h[:8], 16)
        elif size == 6:
            s = '{0}'.format(h[:6])
            q = (~int(s, 16) & 0xFFFFFF)
            v = -1 ^ q
            return v
        elif size == 4:
            s = h[0] + h[0] + h[1] + h[1] + h[2] + h[2] + h[3] + h[3]
            return int(s, 16)
        elif size == 3:
            s = '{0}{0}{1}{1}{2}{2}'.format(h[0], h[1], h[2])
            q = (~int(s, 16) & 0xFFFFFF)
            v = -1 ^ q
            return v
        return Color.rgb_to_int(0, 0, 0)

    @staticmethod
    def parse_color_rgb(values):
        """Parse SVG Color, RGB value declarations """
        r = int(values[0])
        g = int(values[1])
        b = int(values[2])
        if values[3] is not None:
            opacity = float(values[3])
        else:
            opacity = 1
        return Color.rgb_to_int(r, g, b, opacity)

    @staticmethod
    def parse_color_rgbp(values):
        """Parse SVG color, RGB percent value declarations"""
        ratio = 255.0 / 100.0
        r = round(float(values[0]) * ratio)
        g = round(float(values[1]) * ratio)
        b = round(float(values[2]) * ratio)
        if values[3] is not None:
            opacity = float(values[3])
        else:
            opacity = 1
        return Color.rgb_to_int(r, g, b, opacity)

    @staticmethod
    def parse_color_hsl(values):
        """Parse SVG color, HSL value declarations"""
        h = Angle.parse(values[0])
        h = h.as_turns
        s = float(values[1]) / 100.0
        if s > 1:
            s = 1.0
        if s < 0:
            s = 0.0
        l = float(values[2]) / 100.0
        if l > 1:
            l = 1.0
        if l < 0:
            l = 0.0
        if values[3] is not None:
            opacity = float(values[3])
        else:
            opacity = 1
        return Color.hsl_to_int(h, s, l, opacity)

    @property
    def opacity(self):
        return self.alpha / 255.0

    @opacity.setter
    def opacity(self, opacity):
        a = int(round(opacity * 255.0))
        a = Color.crimp(a)
        self.alpha = a

    @property
    def alpha(self):
        return (self.value >> 24) & 0xFF

    @alpha.setter
    def alpha(self, a):
        a = Color.crimp(a)
        self.value &= 0xFFFFFF
        self.value = int(self.value)
        if a & 0x80 != 0:
            a ^= 0x80
            a <<= 24
            a = ~a
            a ^= 0x7FFFFFFF
        else:
            a <<= 24
        self.value |= a

    @property
    def red(self):
        return (self.value >> 16) & 0xFF

    @red.setter
    def red(self, r):
        r = int(r & 0xFF)
        self.value &= ~0xFF0000
        r <<= 16
        self.value |= r

    @property
    def green(self):
        return (self.value >> 8) & 0xFF

    @green.setter
    def green(self, g):
        g = int(g & 0xFF)
        self.value &= ~0xFF00
        g <<= 8
        self.value |= g

    @property
    def blue(self):
        return self.value & 0xFF

    @blue.setter
    def blue(self, b):
        b = int(b & 0xFF)
        self.value &= ~0xFF
        self.value |= b

    @property
    def hexa(self):
        return '#%02x%02x%02x%02x' % (self.alpha, self.red, self.green, self.blue)

    @property
    def hex(self):
        if self.alpha == 0xFF:
            return '#%02x%02x%02x' % (self.red, self.green, self.blue)
        else:
            return '#%02x%02x%02x%02x' % (self.alpha, self.red, self.green, self.blue)

    @property
    def hue(self):
        r = self.red / 255.0
        g = self.green / 255.0
        b = self.blue / 255.0
        var_min = min(r, g, b)
        var_max = max(r, g, b)
        delta_max = var_max - var_min
        if delta_max == 0:
            return 0
        dr = (((var_max - r) / 6.0) + delta_max / 2.0) / delta_max
        dg = (((var_max - g) / 6.0) + delta_max / 2.0) / delta_max
        db = (((var_max - b) / 6.0) + delta_max / 2.0) / delta_max
        if r == var_max:
            h = db - dg
        elif g == var_max:
            h = (1.0 / 3.0) + dr - db
        else:  # db == max_v
            h = (2.0 / 3.0) + dg - dr
        if h < 0:
            h += 1
        if h > 1:
            h -= 1
        return h

    @hue.setter
    def hue(self, v):
        h, s, l = self.hsl
        self.hsl = v, s, l

    @property
    def saturation(self):
        r = self.red / 255.0
        g = self.green / 255.0
        b = self.blue / 255.0
        min_v = min(r, g, b)
        max_v = max(r, g, b)
        delta = max_v - min_v
        if max_v == min_v:
            return 0.0
        if (max_v + min_v) < 1:
            return delta / (max_v + min_v)
        else:
            return delta / (2.0 - max_v - min_v)

    @saturation.setter
    def saturation(self, v):
        h, s, l = self.hsl
        self.hsl = h, v, l

    @property
    def lightness(self):
        r = self.red / 255.0
        g = self.green / 255.0
        b = self.blue / 255.0
        min_v = min(r, g, b)
        max_v = max(r, g, b)
        return (max_v + min_v) / 2.0

    @lightness.setter
    def lightness(self, v):
        h, s, l = self.hsl
        self.hsl = h, s, v

    @property
    def intensity(self):
        r = self.red
        g = self.green
        b = self.blue
        return (r + b + g) / 768.0

    @property
    def brightness(self):
        r = self.red
        g = self.green
        b = self.blue
        cmax = max(r, g, b)
        return cmax / 255.0

    @property
    def blackness(self):
        return 1.0 - self.brightness

    @property
    def luminance(self):
        r = self.red / 255.0
        g = self.green / 255.0
        b = self.blue / 255.0
        return r * 0.3 + g * 0.59 + b * 0.11

    @property
    def luma(self):
        r = self.red / 255.0
        g = self.green / 255.0
        b = self.blue / 255.0
        return r * 0.2126 + g * 0.7152 + b * 0.0722

    @staticmethod
    def over(c1, c2):
        """
        Porter Duff Alpha compositing operation over.
        Returns c1 over c2. This is the standard painter algorithm.
        """
        if isinstance(c1, str):
            c1 = Color.parse(c1)
        elif isinstance(c1, int):
            c1 = Color(c1)
        if isinstance(c2, str):
            c2 = Color.parse(c2)
        elif isinstance(c2, int):
            c2 = Color(c2)
        r1 = c1.red
        g1 = c1.green
        b1 = c1.blue
        a1 = c1.alpha
        if a1 == 255:
            return c1.value
        if a1 == 0:
            return c2.value
        r2 = c2.red
        g2 = c2.green
        b2 = c2.blue
        a2 = c2.alpha

        q = 255.0 - a1

        sr = r1 * a1 * 255.0 + r2 * a2 * q
        sg = g1 * a1 * 255.0 + g2 * a2 * q
        sb = b1 * a1 * 255.0 + b2 * a2 * q
        sa = a1 * 255.0 + a2 * q
        sr /= sa
        sg /= sa
        sb /= sa
        sa /= (255.0 * 255.0)
        return Color.rgb_to_int(sr, sg, sb, sa)

    @staticmethod
    def distance(c1, c2):
        return sqrt(Color.distance_sq(c1, c2))

    @staticmethod
    def distance_sq(c1, c2):
        """
        Function returns the square of colordistance. The square of the color distance will always be closer than the
        square of another color distance.

        Rather than naive Euclidean distance we use Compuphase's Redmean color distance.
        https://www.compuphase.com/cmetric.htm

        It's computationally simple, and empirical tests finds it to be on par with LabDE2000.

        :param c1: first color
        :param c2: second color
        :return: square of color distance
        """
        if isinstance(c1, str):
            c1 = Color(c1)
        elif isinstance(c1, int):
            c1 = Color(c1)
        if isinstance(c2, str):
            c2 = Color(c2)
        elif isinstance(c2, int):
            c2 = Color(c2)
        red_mean = int((c1.red + c2.red) / 2.0)
        r = c1.red - c2.red
        g = c1.green - c2.green
        b = c1.blue - c2.blue
        return (((512 + red_mean) * r * r) >> 8) + 4 * g * g + ((767 - red_mean) * b * b) >> 8

    @staticmethod
    def crimp(v):
        if v > 255:
            return 255
        if v < 0:
            return 0
        return int(v)

    @property
    def hsl(self):
        return self.hue, self.saturation, self.lightness

    @hsl.setter
    def hsl(self, value):
        if not isinstance(value, tuple):
            return
        h, s, l = value

        def hue_2_rgb(v1, v2, vh):
            if vh < 0:
                vh += 1
            if vh > 1:
                vh -= 1
            if 6.0 * vh < 1.0:
                return v1 + (v2 - v1) * 6.0 * vh
            if 2.0 * vh < 1:
                return v2
            if 3 * vh < 2.0:
                return v1 + (v2 - v1) * ((2.0 / 3.0) - vh) * 6.0
            return v1

        if s == 0.0:
            r = 255.0 * l
            g = 255.0 * l
            b = 255.0 * l
        else:
            if l < 0.5:
                v2 = l * (1.0 + s)
            else:
                v2 = (l + s) - (s * l)
            v1 = 2 * l - v2
            r = 255.0 * hue_2_rgb(v1, v2, h + (1.0 / 3.0))
            g = 255.0 * hue_2_rgb(v1, v2, h)
            b = 255.0 * hue_2_rgb(v1, v2, h - (1.0 / 3.0))
        self.value = self.rgb_to_int(r, g, b)

    def distance_to(self, other):
        return Color.distance(self, other)

    def blend(self, other, opacity=None):
        """
        Blends the given color with the current color.
        """
        if opacity is None:
            self.value = Color.over(other, self)
        else:
            color = Color(other)
            color.opacity = opacity
            self.value = Color.over(color, self)


class Point:
    """Point is a general subscriptable point class with .x and .y as well as [0] and [1]

    For compatibility with regebro svg.path we accept complex numbers as points x + yj,
    and provide .real and .imag as properties. As well as float and integer values as (v,0) elements.

    With regard to SVG 7.15.1 defining SVGPoint this class provides for matrix transformations.

    Points are only positions in real Euclidean space. This class is not intended to interact with
    the Length class.
    """

    def __init__(self, x, y=None):
        if x is not None and y is None:
            if isinstance(x, str):
                string_x, string_y = REGEX_COORD_PAIR.findall(x)[0]
                x = float(string_x)
                y = float(string_y)
            else:
                try:  # try subscription.
                    y = x[1]
                    x = x[0]
                except TypeError:
                    try:  # Try .x .y
                        y = x.y
                        x = x.x
                    except AttributeError:
                        try:  # try .imag .real complex values.
                            y = x.imag
                            x = x.real
                        except AttributeError:
                            # Unknown.
                            x = 0
                            y = 0
        self.x = x
        self.y = y

    def __key(self):
        return (self.x, self.y)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        a0 = self[0]
        a1 = self[1]
        if isinstance(other, str):
            try:
                other = Point(other)
            except IndexError:  # This string doesn't parse to a point.
                return False
        if isinstance(other, (Point, list, tuple)):
            b0 = other[0]
            b1 = other[1]
        elif isinstance(other, complex):
            b0 = other.real
            b1 = other.imag
        else:
            return NotImplemented
        try:
            c0 = abs(a0 - b0) <= ERROR
            c1 = abs(a1 - b1) <= ERROR
        except TypeError:
            return False
        return c0 and c1

    def __ne__(self, other):
        return not self == other

    def __getitem__(self, item):
        if item == 0:
            return self.x
        elif item == 1:
            return self.y
        else:
            raise IndexError

    def __setitem__(self, key, value):
        if key == 0:
            self.x = value
        elif key == 1:
            self.y = value
        else:
            raise IndexError

    def __repr__(self):
        x_str = Length.str(self.x)
        y_str = Length.str(self.y)
        return 'Point(%s,%s)' % (x_str, y_str)

    def __copy__(self):
        return Point(self.x, self.y)

    def __str__(self):
        x_str = ('%.12G' % (self.x))
        if '.' in x_str:
            x_str = x_str.rstrip('0').rstrip('.')
        y_str = ('%.12G' % (self.y))
        if '.' in y_str:
            y_str = y_str.rstrip('0').rstrip('.')
        return "%s,%s" % (x_str, y_str)

    def __imul__(self, other):
        if isinstance(other, str):
            other = Matrix(other)
        if isinstance(other, Matrix):
            v = other.point_in_matrix_space(self)
            self[0] = v[0]
            self[1] = v[1]
        elif isinstance(other, (int, float)):  # Emulates complex point multiplication by real.
            self.x *= other
            self.y *= other
        else:
            return NotImplemented
        return self

    def __mul__(self, other):
        if isinstance(other, (Matrix, str, int, float)):
            n = copy(self)
            n *= other
            return n

    __rmul__ = __mul__

    def __iadd__(self, other):
        if isinstance(other, (Point, tuple, list)):
            self[0] += other[0]
            self[1] += other[1]
        elif isinstance(other, complex):
            self[0] += other.real
            self[1] += other.imag
        elif isinstance(other, (float, int)):
            self[0] += other
        else:
            return NotImplemented
        return self

    def __add__(self, other):
        if isinstance(other, (Point, tuple, list, complex, int, float)):
            n = copy(self)
            n += other
            return n

    __radd__ = __add__

    def __isub__(self, other):
        if isinstance(other, (Point, tuple, list)):
            self[0] -= other[0]
            self[1] -= other[1]
        elif isinstance(other, complex):
            self[0] -= other.real
            self[1] -= other.imag
        elif isinstance(other, (float, int)):
            self[0] -= other
        else:
            return NotImplemented
        return self

    def __sub__(self, other):
        if isinstance(other, (Point, tuple, list, complex, int, float)):
            n = copy(self)
            n -= other
            return n

    def __rsub__(self, other):
        if isinstance(other, (Point, tuple, list)):
            x = other[0] - self[0]
            y = other[1] - self[1]
        elif isinstance(other, complex):
            x = other.real - self[0]
            y = other.imag - self[1]
        elif isinstance(other, (float, int)):
            x = other - self[0]
            y = self[1]
        else:
            return NotImplemented
        return Point(x, y)

    def __abs__(self):
        return hypot(self.x, self.y)

    def __pow__(self, other):
        r_raised = abs(self) ** other
        argz_multiplied = self.argz() * other

        real_part = round(r_raised * cos(argz_multiplied))
        imag_part = round(r_raised * sin(argz_multiplied))
        return self.__class__(real_part, imag_part)

    def conjugate(self):
        return self.__class__(self.real, -self.imag)

    def argz(self):
        return atan(self.imag / self.real)

    @property
    def real(self):
        """Emulate svg.path use of complex numbers"""
        return self.x

    @property
    def imag(self):
        """Emulate svg.path use of complex numbers"""
        return self.y

    def matrix_transform(self, matrix):
        v = matrix.point_in_matrix_space(self)
        self[0] = v[0]
        self[1] = v[1]
        return self

    def move_towards(self, p2, amount=1):
        if not isinstance(p2, Point):
            p2 = Point(p2)
        self.x = amount * (p2[0] - self[0]) + self[0]
        self.y = amount * (p2[1] - self[1]) + self[1]

    def distance_to(self, p2):
        if not isinstance(p2, Point):
            p2 = Point(p2)
        return Point.distance(self, p2)

    def angle_to(self, p2):
        if not isinstance(p2, Point):
            p2 = Point(p2)
        return Point.angle(self, p2)

    def polar_to(self, angle, distance):
        return Point.polar(self, angle, distance)

    def reflected_across(self, p):
        m = Point(p)
        m += p
        m -= self
        return m

    @staticmethod
    def orientation(p, q, r):
        """Determine the clockwise, linear, or counterclockwise orientation of the given points"""
        val = (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])
        if val == 0:
            return 0
        elif val > 0:
            return 1
        else:
            return 2

    @staticmethod
    def convex_hull(pts):
        if len(pts) == 0:
            return
        points = sorted(set(pts), key=lambda p: p[0])
        first_point_on_hull = points[0]
        point_on_hull = first_point_on_hull
        while True:
            yield point_on_hull
            endpoint = point_on_hull
            for t in points:
                if point_on_hull is endpoint \
                        or Point.orientation(point_on_hull, t, endpoint) == 2:
                    endpoint = t
            point_on_hull = endpoint
            if first_point_on_hull is point_on_hull:
                break

    @staticmethod
    def distance(p1, p2):
        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]
        dx *= dx
        dy *= dy
        return sqrt(dx + dy)

    @staticmethod
    def polar(p1, angle, r):
        dx = cos(angle) * r
        dy = sin(angle) * r
        return Point(p1[0] + dx, p1[1] + dy)

    @staticmethod
    def angle(p1, p2):
        return Angle.radians(atan2(p2[1] - p1[1], p2[0] - p1[0]))

    @staticmethod
    def towards(p1, p2, amount):
        tx = amount * (p2[0] - p1[0]) + p1[0]
        ty = amount * (p2[1] - p1[1]) + p1[1]
        return Point(tx, ty)


class Angle(float):
    """CSS Angle defines as used in SVG/CSS"""

    def __repr__(self):
        return 'Angle(%.12f)' % self

    def __copy__(self):
        return Angle(self)

    def __eq__(self, other):
        # Python 2
        c1 = abs((self % tau) - (other % tau)) <= 1e-11
        return c1

    def normalized(self):
        return Angle(self % tau)

    @classmethod
    def parse(cls, angle_string):
        if not isinstance(angle_string, str):
            return
        angle_string = angle_string.lower()
        if angle_string.endswith('deg'):
            return Angle.degrees(float(angle_string[:-3]))
        if angle_string.endswith('grad'):
            return Angle.gradians(float(angle_string[:-4]))
        if angle_string.endswith('rad'):  # Must be after 'grad' since 'grad' ends with 'rad' too.
            return Angle.radians(float(angle_string[:-3]))
        if angle_string.endswith('turn'):
            return Angle.turns(float(angle_string[:-4]))
        return Angle.degrees(float(angle_string))

    @classmethod
    def radians(cls, radians):
        return cls(radians)

    @classmethod
    def degrees(cls, degrees):
        return cls(tau * degrees / 360.0)

    @classmethod
    def gradians(cls, gradians):
        return cls(tau * gradians / 400.0)

    @classmethod
    def turns(cls, turns):
        return cls(tau * turns)

    @property
    def as_radians(self):
        return self

    @property
    def as_degrees(self):
        return self * 360.0 / tau

    @property
    def as_positive_degrees(self):
        v = self.as_degrees
        while v < 0:
            v += 360.0
        return v

    @property
    def as_gradians(self):
        return self * 400.0 / tau

    @property
    def as_turns(self):
        return self / tau

    def is_orthogonal(self):
        return (self % (tau / 4)) == 0


class Matrix:
    """"
    Provides svg matrix interfacing.

    SVG 7.15.3 defines the matrix form as:
    [a c  e]
    [b d  f]

    While e and f are defined as floats, they can be for limited periods defined as a Length.
    With regard to CSS, it's reasonable to perform operations like 'transform(20cm, 20cm)' and
    expect these to be treated consistently. Performing other matrix operations in a consistent
    way. However, render must be called to change these parameters into float locations prior to
    any operation which might be used to transform a point or polyline or path object.
    """

    def __init__(self, *components, **kwargs):
        self.a = 1.0
        self.b = 0.0
        self.c = 0.0
        self.d = 1.0
        self.e = 0.0
        self.f = 0.0
        len_args = len(components)
        if len_args == 0:
            pass
        elif len_args == 1:
            m = components[0]
            if isinstance(m, str):
                self.parse(m)
                self.render(**kwargs)
            else:
                self.a = m[0]
                self.b = m[1]
                self.c = m[2]
                self.d = m[3]
                self.e = m[4]
                self.f = m[5]
        else:
            self.a = components[0]
            self.b = components[1]
            self.c = components[2]
            self.d = components[3]
            self.e = components[4]
            self.f = components[5]
            self.render(**kwargs)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __eq__(self, other):
        if other is None:
            return False
        if isinstance(other, str):
            other = Matrix(other)
        if not isinstance(other, Matrix):
            return False
        if abs(self.a - other.a) > 1e-12:
            return False
        if abs(self.b - other.b) > 1e-12:
            return False
        if abs(self.c - other.c) > 1e-12:
            return False
        if abs(self.d - other.d) > 1e-12:
            return False
        if self.e != other.e and abs(self.e - other.e) > 1e-12:
            return False
        if self.f != other.f and abs(self.f - other.f) > 1e-12:
            return False
        return True

    def __len__(self):
        return 6

    def __invert__(self):
        m = self.__copy__()
        return m.inverse()

    def __matmul__(self, other):
        m = copy(self)
        m.__imatmul__(other)
        return m

    def __rmatmul__(self, other):
        m = copy(other)
        m.__imatmul__(self)
        return m

    def __imatmul__(self, other):
        if isinstance(other, str):
            other = Matrix(other)
        self.a, self.b, self.c, self.d, self.e, self.f = Matrix.matrix_multiply(self, other)
        return self

    __mul__ = __matmul__
    __rmul__ = __rmatmul__
    __imul__ = __imatmul__

    def __getitem__(self, item):
        if item == 0:
            return float(self.a)
        elif item == 1:
            return float(self.b)
        elif item == 2:
            return float(self.c)
        elif item == 3:
            return float(self.d)
        elif item == 4:
            return self.e
        elif item == 5:
            return self.f

    def __setitem__(self, key, value):
        if key == 0:
            self.a = value
        elif key == 1:
            self.b = value
        elif key == 2:
            self.c = value
        elif key == 3:
            self.d = value
        elif key == 4:
            self.e = value
        elif key == 5:
            self.f = value

    def __repr__(self):
        return 'Matrix(%s, %s, %s, %s, %s, %s)' % \
               (Length.str(self.a), Length.str(self.b),
                Length.str(self.c), Length.str(self.d),
                Length.str(self.e), Length.str(self.f))

    def __copy__(self):
        return Matrix(self.a, self.b, self.c, self.d, self.e, self.f)

    def __str__(self):
        """
        Many of SVG's graphics operations utilize 2x3 matrices of the form:

        :returns string representation of matrix.
        """
        return "[%3f, %3f,\n %3f, %3f,   %s, %s]" % \
               (self.a, self.c, self.b, self.d, self.e, self.f)

    def parse(self, transform_str):
        """Parses the svg transform string.

        Transforms from SVG 1.1 have a smaller complete set of operations. Whereas in SVG 2.0 they gain
        the CSS transforms and the additional functions and parsing that go with that. This parse is
        compatible with SVG 1.1 and the SVG 2.0 which includes the CSS 2d superset.

        CSS transforms have scalex() scaley() translatex(), translatey(), and skew() (deprecated).
        2D CSS angles haves units: "deg" tau / 360, "rad" tau/tau, "grad" tau/400, "turn" tau.
        2D CSS distances have length/percentages: "px", "cm", "mm", "in", "pt", etc. (+|-)?d+%

        In the case of percentages there must be a known height and width to properly create a matrix out of that.

        """
        if not transform_str:
            return
        if not isinstance(transform_str, str):
            raise TypeError('Must provide a string to parse')

        for sub_element in REGEX_TRANSFORM_TEMPLATE.findall(transform_str.lower()):
            name = sub_element[0]
            params = tuple(REGEX_TRANSFORM_PARAMETER.findall(sub_element[1]))
            params = [mag + units for mag, units in params]
            if SVG_TRANSFORM_MATRIX == name:
                params = map(float, params)
                self.pre_cat(*params)
            elif SVG_TRANSFORM_TRANSLATE == name:
                try:
                    x_param = Length(params[0]).value()
                except IndexError:
                    continue
                try:
                    y_param = Length(params[1]).value()
                    self.pre_translate(x_param, y_param)
                except IndexError:
                    self.pre_translate(x_param)
            elif SVG_TRANSFORM_TRANSLATE_X == name:
                self.pre_translate(Length(params[0]).value(), 0)
            elif SVG_TRANSFORM_TRANSLATE_Y == name:
                self.pre_translate(0, Length(params[0]).value())
            elif SVG_TRANSFORM_SCALE == name:
                params = map(float, params)
                self.pre_scale(*params)
            elif SVG_TRANSFORM_SCALE_X == name:
                self.pre_scale(float(params[0]), 1)
            elif SVG_TRANSFORM_SCALE_Y == name:
                self.pre_scale(1, float(params[0]))
            elif SVG_TRANSFORM_ROTATE == name:
                angle = Angle.parse(params[0])
                try:
                    x_param = Length(params[1]).value()
                except IndexError:
                    self.pre_rotate(angle)
                    continue
                try:
                    y_param = Length(params[2]).value()
                    self.pre_rotate(angle, x_param, y_param)
                except IndexError:
                    self.pre_rotate(angle, x_param)
            elif SVG_TRANSFORM_SKEW == name:
                angle_a = Angle.parse(params[0])
                angle_b = Angle.parse(params[1])
                try:
                    x_param = Length(params[2]).value()
                except IndexError:
                    self.pre_skew(angle_a, angle_b)
                    continue
                try:
                    y_param = Length(params[3]).value()
                    self.pre_skew(angle_a, angle_b, x_param, y_param)
                except IndexError:
                    self.pre_skew(angle_a, angle_b, x_param)
            elif SVG_TRANSFORM_SKEW_X == name:
                angle_a = Angle.parse(params[0])
                try:
                    x_param = Length(params[1]).value()
                except IndexError:
                    self.pre_skew_x(angle_a)
                    continue
                try:
                    y_param = Length(params[2]).value()
                    self.pre_skew_x(angle_a, x_param, y_param)
                except IndexError:
                    self.pre_skew_x(angle_a, x_param)
            elif SVG_TRANSFORM_SKEW_Y == name:
                angle_b = Angle.parse(params[0])
                try:
                    x_param = Length(params[1]).value()
                except IndexError:
                    self.pre_skew_y(angle_b)
                    continue
                try:
                    y_param = Length(params[2]).value()
                    self.pre_skew_y(angle_b, x_param, y_param)
                except IndexError:
                    self.pre_skew_y(angle_b, x_param)
        return self

    def render(self, ppi=None, relative_length=None, width=None, height=None,
               font_size=None, font_height=None, viewbox=None, **kwargs):
        """
        Provides values to turn trans_x and trans_y values into user units floats rather
        than Lengths by giving the required information to perform the conversions.
        """

        if width is None and relative_length is not None:
            width = relative_length
        if height is None and relative_length is not None:
            height = relative_length

        if isinstance(self.e, Length):
            self.e = self.e.value(ppi=ppi, relative_length=width, font_size=font_size,
                                  font_height=font_height, viewbox=viewbox)

        if isinstance(self.f, Length):
            self.f = self.f.value(ppi=ppi, relative_length=height, font_size=font_size,
                                  font_height=font_height, viewbox=viewbox)
        return self

    def value_trans_x(self):
        return self.e

    def value_trans_y(self):
        return self.f

    def value_scale_x(self):
        return float(self.a)

    def value_scale_y(self):
        return float(self.d)

    def value_skew_x(self):
        return float(self.b)

    def value_skew_y(self):
        return float(self.c)

    def reset(self):
        """Resets matrix to identity."""
        self.a = 1.0
        self.b = 0.0
        self.c = 0.0
        self.d = 1.0

        self.e = 0.0
        self.f = 0.0

    def inverse(self):
        """
        SVG Matrix:
        [a c e]
        [b d f]
        """
        m00 = self.a
        m01 = self.c
        m02 = self.e
        m10 = self.b
        m11 = self.d
        m12 = self.f
        determinant = m00 * m11 - m01 * m10
        inverse_determinant = 1.0 / determinant
        self.a = m11 * inverse_determinant
        self.c = -m01 * inverse_determinant
        self.b = -m10 * inverse_determinant
        self.d = m00 * inverse_determinant

        self.e = (m01 * m12 - m02 * m11) * inverse_determinant
        self.f = (m10 * m02 - m00 * m12) * inverse_determinant
        return self

    def vector(self):
        """
        provide the matrix suitable for multiplying vectors. This will be the matrix with the same rotation and scale
        aspects but with no translation. This matrix is for multiplying vector elements where the position doesn't
        matter but the scaling and rotation do.
        :return:
        """
        return Matrix(self.a, self.b, self.c, self.d, 0.0, 0.0)

    def is_identity(self):
        return self.a == 1 and self.b == 0 and self.c == 0 and self.d == 1 and self.e == 0 and self.f == 0

    def post_cat(self, *components):
        mx = Matrix(*components)
        self.__imatmul__(mx)

    def post_scale(self, sx=1.0, sy=None, x=0.0, y=0.0):
        if sy is None:
            sy = sx
        if x is None:
            x = 0.0
        if y is None:
            y = 0.0
        if x == 0 and y == 0:
            self.post_cat(Matrix.scale(sx, sy))
        else:
            self.post_translate(-x, -y)
            self.post_scale(sx, sy)
            self.post_translate(x, y)

    def post_scale_x(self, sx=1.0, x=0.0, y=0.0):
        self.post_scale(sx, 1, x, y)

    def post_scale_y(self, sy=1.0, x=0.0, y=0.0):
        self.post_scale(1, sy, x, y)

    def post_translate(self, tx=0.0, ty=0.0):
        self.post_cat(Matrix.translate(tx, ty))

    def post_translate_x(self, tx=0.0):
        self.post_translate(tx, 0.0)

    def post_translate_y(self, ty=0.0):
        self.post_translate(0.0, ty)

    def post_rotate(self, angle, x=0.0, y=0.0):
        if x is None:
            x = 0.0
        if y is None:
            y = 0.0
        if x == 0 and y == 0:
            self.post_cat(Matrix.rotate(angle))  # self %= self.get_rotate(theta)
        else:
            matrix = Matrix()
            matrix.post_translate(-x, -y)
            matrix.post_cat(Matrix.rotate(angle))
            matrix.post_translate(x, y)
            self.post_cat(matrix)

    def post_skew(self, angle_a=0.0, angle_b=0.0, x=0.0, y=0.0):
        if x is None:
            x = 0
        if y is None:
            y = 0
        if x == 0 and y == 0:
            self.post_cat(Matrix.skew(angle_a, angle_b))
        else:
            self.post_translate(-x, -y)
            self.post_skew(angle_a, angle_b)
            self.post_translate(x, y)

    def post_skew_x(self, angle_a=0.0, x=0.0, y=0.0):
        self.post_skew(angle_a, 0.0, x, y)

    def post_skew_y(self, angle_b=0.0, x=0.0, y=0.0):
        self.post_skew(0.0, angle_b, x, y)

    def pre_cat(self, *components):
        mx = Matrix(*components)
        self.a, self.b, self.c, self.d, self.e, self.f = Matrix.matrix_multiply(mx, self)

    def pre_scale(self, sx=1.0, sy=None, x=0.0, y=0.0):
        if sy is None:
            sy = sx
        if x is None:
            x = 0.0
        if y is None:
            y = 0.0
        if x == 0 and y == 0:
            self.pre_cat(Matrix.scale(sx, sy))
        else:
            self.pre_translate(x, y)
            self.pre_scale(sx, sy)
            self.pre_translate(-x, -y)

    def pre_scale_x(self, sx=1.0, x=0.0, y=0.0):
        self.pre_scale(sx, 1, x, y)

    def pre_scale_y(self, sy=1.0, x=0.0, y=0.0):
        self.pre_scale(1, sy, x, y)

    def pre_translate(self, tx=0.0, ty=0.0):
        self.pre_cat(Matrix.translate(tx, ty))

    def pre_translate_x(self, tx=0.0):
        self.pre_translate(tx, 0.0)

    def pre_translate_y(self, ty=0.0):
        self.pre_translate(0.0, ty)

    def pre_rotate(self, angle, x=0.0, y=0.0):
        if x is None:
            x = 0
        if y is None:
            y = 0
        if x == 0 and y == 0:
            self.pre_cat(Matrix.rotate(angle))
        else:
            self.pre_translate(x, y)
            self.pre_rotate(angle)
            self.pre_translate(-x, -y)

    def pre_skew(self, angle_a=0.0, angle_b=0.0, x=0.0, y=0.0):
        if x is None:
            x = 0
        if y is None:
            y = 0
        if x == 0 and y == 0:
            self.pre_cat(Matrix.skew(angle_a, angle_b))
        else:
            self.pre_translate(x, y)
            self.pre_skew(angle_a, angle_b)
            self.pre_translate(-x, -y)

    def pre_skew_x(self, angle_a=0.0, x=0.0, y=0.0):
        self.pre_skew(angle_a, 0, x, y)

    def pre_skew_y(self, angle_b=0.0, x=0.0, y=0.0):
        self.pre_skew(0.0, angle_b, x, y)

    def point_in_inverse_space(self, v0):
        inverse = Matrix(self)
        inverse.inverse()
        return inverse.point_in_matrix_space(v0)

    def point_in_matrix_space(self, v0):
        return Point(v0[0] * self.a + v0[1] * self.c + 1 * self.e,
                     v0[0] * self.b + v0[1] * self.d + 1 * self.f)

    def transform_point(self, v):
        nx = v[0] * self.a + v[1] * self.c + 1 * self.e
        ny = v[0] * self.b + v[1] * self.d + 1 * self.f
        v[0] = nx
        v[1] = ny

    @classmethod
    def scale(cls, sx=1.0, sy=None):
        if sy is None:
            sy = sx
        return cls(sx, 0,
                   0, sy, 0, 0)

    @classmethod
    def scale_x(cls, sx=1.0):
        return cls.scale(sx, 1.0)

    @classmethod
    def scale_y(cls, sy=1.0):
        return cls.scale(1.0, sy)

    @classmethod
    def translate(cls, tx=0.0, ty=0.0):
        """SVG Matrix:
                [a c e]
                [b d f]
                """
        return cls(1.0, 0.0,
                   0.0, 1.0, tx, ty)

    @classmethod
    def translate_x(cls, tx=0.0):
        return cls.translate(tx, 0)

    @classmethod
    def translate_y(cls, ty=0.0):
        return cls.translate(0.0, ty)

    @classmethod
    def rotate(cls, angle=0.0):
        ct = cos(angle)
        st = sin(angle)
        return cls(ct, st,
                   -st, ct, 0.0, 0.0)

    @classmethod
    def skew(cls, angle_a=0.0, angle_b=0.0):
        aa = tan(angle_a)
        bb = tan(angle_b)
        return cls(1.0, bb,
                   aa, 1.0, 0.0, 0.0)

    @classmethod
    def skew_x(cls, angle=0.0):
        return cls.skew(angle, 0.0)

    @classmethod
    def skew_y(cls, angle=0.0):
        return cls.skew(0.0, angle)

    @classmethod
    def identity(cls):
        """
        1, 0, 0,
        0, 1, 0,
        """
        return cls()

    @staticmethod
    def matrix_multiply(m, s):
        """
        [a c e]      [a c e]   [a b 0]
        [b d f]   %  [b d f] = [c d 0]
        [0 0 1]      [0 0 1]   [e f 1]

        :param m0: matrix operand
        :param m1: matrix operand
        :return: muliplied matrix.
        """
        r0 = s.a * m.a + s.c * m.b + s.e * 0, \
             s.a * m.c + s.c * m.d + s.e * 0, \
             s.a * m.e + s.c * m.f + s.e * 1

        r1 = s.b * m.a + s.d * m.b + s.f * 0, \
             s.b * m.c + s.d * m.d + s.f * 0, \
             s.b * m.e + s.d * m.f + s.f * 1

        return float(r0[0]), float(r1[0]), float(r0[1]), float(r1[1]), r0[2], r1[2]


class SVGElement(object):
    """
    Any element within the SVG namespace.
    """

    def __init__(self, *args, **kwargs):
        self.id = None
        self.values = None
        if len(args) == 1:
            if isinstance(args[0], dict):
                v = args[0]
                if SVG_ATTR_TRANSFORM in v:
                    self.transform = Matrix(v[SVG_ATTR_TRANSFORM])
                if SVG_ATTR_ID in v:
                    self.id = v[SVG_ATTR_ID]
                self.values = dict(v)
            elif isinstance(args[0], SVGElement):
                s = args[0]
                self.id = s.id
                self.values = dict(s.values)
                return
        if SVG_ATTR_ID in kwargs:
            self.id = kwargs[SVG_ATTR_ID]
        if self.values is not None:
            self.values.update(kwargs)
        else:
            self.values = dict(kwargs)


class Transformable(SVGElement):
    """Any element that is transformable and has a transform property."""

    def __init__(self, *args, **kwargs):
        SVGElement.__init__(self, *args, **kwargs)
        self.transform = Matrix()
        self.apply = True
        if len(args) == 1:
            if isinstance(args[0], dict):
                v = args[0]
                if SVG_ATTR_TRANSFORM in v:
                    self.transform = Matrix(v[SVG_ATTR_TRANSFORM])
                if SVG_ATTR_ID in v:
                    self.id = v[SVG_ATTR_ID]
            elif isinstance(args[0], Transformable):
                s = args[0]
                self.apply = s.apply
                self.transform = Matrix(s.transform)
                self.id = s.id
                return
        if SVG_ATTR_TRANSFORM in kwargs:
            self.transform = Matrix(kwargs[SVG_ATTR_TRANSFORM])
        if 'apply' in kwargs:
            self.apply = bool(kwargs['apply'])

    def __mul__(self, other):
        if isinstance(other, (Matrix, str)):
            n = copy(self)
            n *= other
            return n
        return NotImplemented

    __rmul__ = __mul__

    def __imul__(self, other):
        if isinstance(other, str):
            other = Matrix(other)
        if isinstance(other, Matrix):
            self.transform *= other
        return self

    def __abs__(self):
        """
        The absolute value is taken to be the actual shape transformed.
        :return: transformed version of the given shape.
        """
        m = copy(self)
        m.reify()
        return m

    def reify(self):
        """
        Realizes the transform to the attributes. Such that the attributes become actualized and the transform
        simplifies towards the identity matrix. In many cases it will become the identity matrix. In other cases the
        transformed shape cannot be represented through the properties alone. And shall keep those parts of the
        transform required preserve equivalency.
        """
        return self

    def render(self, **kwargs):
        """
        Renders the transformable by performing any required length conversion operations into pixels. The element
        will be the pixel-length form.
        """
        self.transform.render(**kwargs)
        return self

    def bbox(self, transformed=True):
        """
        Returns the bounding box of the given object.

        :param transformed: whether this is the transformed bounds or default.
        :return:
        """
        raise NotImplementedError

    @property
    def rotation(self):
        if not self.apply:
            return Angle.degrees(0)
        prx = Point(1, 0)
        prx *= self.transform
        origin = Point(0, 0)
        origin *= self.transform
        return origin.angle_to(prx)


class GraphicObject:
    """Any drawn element."""

    def __init__(self, *args, **kwargs):
        self.stroke = None
        self.fill = None
        if len(args) == 1:
            if isinstance(args[0], dict):
                v = args[0]
                if SVG_ATTR_STROKE in v:
                    stroke = v[SVG_ATTR_STROKE]
                    if stroke is None or stroke == SVG_VALUE_NONE:
                        self.stroke = None
                    else:
                        self.stroke = Color(stroke)
                if SVG_ATTR_FILL in v:
                    fill = v[SVG_ATTR_FILL]
                    if fill is None or fill == SVG_VALUE_NONE:
                        self.fill = None
                    else:
                        self.fill = Color(fill)
            elif isinstance(args[0], GraphicObject):
                s = args[0]
                if s.fill is None:
                    self.fill = None
                else:
                    self.fill = Color(s.fill)
                if s.stroke is None:
                    self.stroke = None
                else:
                    self.stroke = Color(s.stroke)
        if SVG_ATTR_STROKE in kwargs:
            stroke = kwargs[SVG_ATTR_STROKE]
            if stroke is None:
                self.stroke = None
            else:
                self.stroke = Color(stroke)
        if SVG_ATTR_FILL in kwargs:
            fill = kwargs[SVG_ATTR_FILL]
            if fill is None:
                self.fill = None
            else:
                self.fill = Color(fill)


class Shape(GraphicObject, Transformable):
    """
    SVG Shapes are several SVG items defined in SVG 1.1 9.1
    https://www.w3.org/TR/SVG11/shapes.html

    These shapes are circle, ellipse, line, polyline, polygon, and path.

    All shapes have methods:
    d(relative, transform): provides path_d string for the shape.
    reify(): Applies transform of the shape to modify the shape attributes.
    render(): Ensure that the shape properties have real space values.
    bbox(transformed): Provides the bounding box for the given shape.

    All shapes must implement:
    __repr__(), with a call to _repr_shape()
    __copy__()

    All shapes have attributes:
    id: SVG ID attributes. (SVGElement)
    transform: SVG Matrix to apply to this shape. (Transformable)
    apply: Determine whether transform should be applied. (Transformable)
    fill: SVG color of the shape fill. (GraphicObject)
    stroke: SVG color of the shape stroke. (GraphicObject)
    """

    def __init__(self, *args, **kwargs):
        Transformable.__init__(self, *args, **kwargs)
        GraphicObject.__init__(self, *args, **kwargs)

    def __eq__(self, other):
        if not isinstance(other, Shape):
            return NotImplemented
        if self.fill != other.fill or self.stroke != other.stroke:
            return False
        first = self
        if not isinstance(first, Path):
            first = Path(first)
        second = other
        if not isinstance(second, Path):
            second = Path(second)
        return first == second

    def __ne__(self, other):
        if not isinstance(other, Shape):
            return NotImplemented
        return not self == other

    def __iadd__(self, other):
        if isinstance(other, Shape):
            return Path(self) + Path(other)
        return NotImplemented

    __add__ = __iadd__

    def __matmul__(self, other):
        m = copy(self)
        m.__imatmul__(other)
        return m

    def __rmatmul__(self, other):
        m = copy(other)
        m.__imatmul__(self)
        return m

    def __imatmul__(self, other):
        """
        The % operation with a matrix works much like multiplication except that it automatically reifies the shape.
        """
        if isinstance(other, str):
            other = Matrix(other)
        if isinstance(other, Matrix):
            self.transform *= other
        self.reify()
        return self

    def segments(self, transformed=True):
        """
        Returns PathSegments which correctly produce this shape.

        This should be implemented by subclasses.
        """
        raise NotImplementedError

    def d(self, relative=False, transformed=True):
        """
        Returns the path_d string of the shape.

        :param relative: Returns path_d in relative form.
        :param transformed: Return path_d, with applied transform.
        :return: path_d string
        """
        return Path(self.segments(transformed=transformed)).d(relative=relative)

    def bbox(self, transformed=True):
        """
        Get the bounding box for the given shape.
        """
        bbs = [seg.bbox() for seg in self.segments(transformed=transformed) if not isinstance(Close, Move)]
        try:
            xmins, ymins, xmaxs, ymaxs = list(zip(*bbs))
        except ValueError:
            return None  # No bounding box items existed. So no bounding box.
        xmin = min(xmins)
        xmax = max(xmaxs)
        ymin = min(ymins)
        ymax = max(ymaxs)
        return xmin, ymin, xmax, ymax

    def _init_shape(self, *args):
        """
        Generic SVG parsing of args. In those cases where the shape accepts finite elements we can process the last
        four elements of the shape with this code. This will happen in simpleline, roundshape, and rect. It will not
        happen in polyshape or paths since these can accept infinite arguments.
        """
        arg_length = len(args)

        if arg_length >= 1:
            if args[0] is not None:
                self.transform = Matrix(args[0])
        if arg_length >= 2:
            if args[1] is not None:
                self.stroke = Color(args[1])
        if arg_length >= 3:
            if args[2] is not None:
                self.fill = Color(args[2])
        if arg_length >= 4:
            if args[3] is not None:
                self.apply = bool(args[3])

    def _repr_shape(self, values):
        """
        Generic pieces of repr shape.
        """
        if not self.transform.is_identity():
            values.append('transform=%s' % repr(self.transform))
        if self.stroke is not None:
            values.append('stroke=\'%s\'' % self.stroke)
        if self.fill is not None:
            values.append('fill=\'%s\'' % self.fill)
        if self.apply is not None and not self.apply:
            values.append('apply=%s' % self.apply)
        if self.id is not None:
            values.append('id=\'%s\'' % self.id)

    def _name(self):
        return self.__class__.__name__


class PathSegment:
    """
    Path Segments are the base class for all the segment within a Path.
    These are defined in SVG 1.1 8.3 and SVG 2.0 9.3
    https://www.w3.org/TR/SVG11/paths.html#PathData
    https://www.w3.org/TR/SVG2/paths.html#PathElement

    These segments define a 1:1 relationship with the path_d or path data attribute, denoted in
    SVG by the 'd' attribute. These are moveto, closepath, lineto, and the curves which are cubic
    bezier curves, quadratic bezier curves, and elliptical arc. These are classed as Move, Close,
    Line, CubicBezier, QuadraticBezier, and Arc. And in path_d are denoted as M, Z, L, C, Q, A.

    There are lowercase versions of these commands. And for C, and Q there are S and T which are
    smooth versions. For lines there are also V and H commands which denote vertical and horizontal
    versions of the line command.

    The major difference between paths in 1.1 and 2.0 is the use of Z to truncate a command to close.
    "M0,0C 0,100 100,0 z is valid in 2.0 since the last z replaces the 0,0. These are read by
    svg.elements but they are not written.
    """

    def __init__(self):
        self.start = None
        self.end = None

    def __mul__(self, other):
        if isinstance(other, (Matrix, str)):
            n = copy(self)
            n *= other
            return n
        return NotImplemented

    __rmul__ = __mul__

    def __iadd__(self, other):
        if isinstance(other, PathSegment):
            path = Path(self, other)
            return path
        elif isinstance(other, str):
            path = Path(self) + other
            return path
        return NotImplemented

    __add__ = __iadd__

    def __str__(self):
        d = self.d()
        if self.start is not None:
            return 'M %s %s' % (self.start, d)
        return d

    def __iter__(self):
        self.n = -1
        return self

    def __next__(self):
        self.n += 1
        try:
            val = self[self.n]
            if val is None:
                self.n += 1
                val = self[self.n]
            return val
        except IndexError:
            raise StopIteration

    next = __next__

    @staticmethod
    def segment_length(curve, start=0.0, end=1.0, start_point=None, end_point=None, error=ERROR, min_depth=MIN_DEPTH,
                       depth=0):
        """Recursively approximates the length by straight lines"""
        if start_point is None:
            start_point = curve.point(start)
        if end_point is None:
            end_point = curve.point(end)
        mid = (start + end) / 2
        mid_point = curve.point(mid)
        length = abs(end_point - start_point)
        first_half = abs(mid_point - start_point)
        second_half = abs(end_point - mid_point)

        length2 = first_half + second_half
        if (length2 - length > error) or (depth < min_depth):
            # Calculate the length of each segment:
            depth += 1
            return (PathSegment.segment_length(curve, start, mid, start_point, mid_point,
                                               error, min_depth, depth) +
                    PathSegment.segment_length(curve, mid, end, mid_point, end_point,
                                               error, min_depth, depth))
        # This is accurate enough.
        return length2

    def _line_length(self, start=0.0, end=1.0, error=ERROR, min_depth=MIN_DEPTH):
        return PathSegment.segment_length(self, start, end, error=error, min_depth=min_depth)

    def plot(self):
        pass

    def bbox(self):
        """returns the bounding box for the segment.
        xmin, ymin, xmax, ymax
        """
        xs = [p[0] for p in self if p is not None]
        ys = [p[1] for p in self if p is not None]
        xmin = min(xs)
        xmax = max(xs)
        ymin = min(ys)
        ymax = max(ys)
        return xmin, ymin, xmax, ymax

    def reverse(self):
        end = self.end
        self.end = self.start
        self.start = end

    def point(self, position):
        return self.end

    def length(self, error=ERROR, min_depth=MIN_DEPTH):
        return 0

    def d(self, current_point=None, smooth=False):
        """If current point is None, the function will return the absolute form. If it contains a point,
        it will give the value relative to that point."""
        raise NotImplementedError


class Move(PathSegment):
    """Represents move commands. Does nothing, but is there to handle
    paths that consist of only move commands, which is valid, but pointless.
    Also serve as a bridge to make discontinuous paths into continuous paths
    with non-drawn sections.
    """

    def __init__(self, *args, **kwargs):
        """
        Move commands most importantly go to a place. So if one location is given, that's the end point.
        If two locations are given then first is the start location.

        Move(p) where p is the End point.
        Move(s,e) where s is the Start point, e is the End point.
        Move(p, start=s) where p is End point, s is the Start point.
        Move(p, end=e) where p is the Start point, e is the End point.
        Move(start=s, end=e) where s is the Start point, e is the End point.
        """
        PathSegment.__init__(self)
        self.end = None
        self.start = None
        if len(args) == 0:
            if 'end' in kwargs:
                self.end = kwargs['end']
            if 'start' in kwargs:
                self.start = kwargs['start']
        elif len(args) == 1:
            if len(kwargs) == 0:
                self.end = args[0]
            else:
                if 'end' in kwargs:
                    self.start = args[0]
                    self.end = kwargs['end']
                elif 'start' in kwargs:
                    self.start = kwargs['start']
                    self.end = args[0]
        elif len(args) == 2:
            self.start = args[0]
            self.end = args[1]
        if self.start is not None:
            self.start = Point(self.start)
        if self.end is not None:
            self.end = Point(self.end)

    def __imul__(self, other):
        if isinstance(other, str):
            other = Matrix(other)
        if isinstance(other, Matrix):
            if self.start is not None:
                self.start *= other
            if self.end is not None:
                self.end *= other
        return self

    def __repr__(self):
        if self.start is None:
            return 'Move(end=%s)' % repr(self.end)
        else:
            return 'Move(start=%s, end=%s)' % (repr(self.start), repr(self.end))

    def __copy__(self):
        return Move(self.start, self.end)

    def __eq__(self, other):
        if not isinstance(other, Move):
            return NotImplemented
        return self.start == other.start and self.end == other.end

    def __ne__(self, other):
        if not isinstance(other, Move):
            return NotImplemented
        return not self == other

    def __len__(self):
        return 2

    def __getitem__(self, item):
        if item == 0:
            return self.start
        elif item == 1:
            return self.end
        else:
            raise IndexError

    def plot(self):
        if self.start is not None:
            for x, y in Line.plot_line(self.start[0], self.start[1], self.end[0], self.end[1]):
                yield x, y, 0

    def d(self, current_point=None, smooth=False):
        if current_point is None:
            return 'M %s' % (self.end)
        else:
            return 'm %s' % (self.end - current_point)


class Close(PathSegment):
    """Represents close commands. If this exists at the end of the shape then the shape is closed.
    the methodology of a single flag close fails in a couple ways. You can have multi-part shapes
    which can close or not close several times.
    """

    def __init__(self, start=None, end=None):
        PathSegment.__init__(self)
        self.end = None
        self.start = None
        if start is not None:
            self.start = Point(start)
        if end is not None:
            self.end = Point(end)

    def __imul__(self, other):
        if isinstance(other, str):
            other = Matrix(other)
        if isinstance(other, Matrix):
            if self.start is not None:
                self.start *= other
            if self.end is not None:
                self.end *= other
        return self

    def __repr__(self):
        if self.start is None and self.end is None:
            return 'Close()'
        s = self.start
        if s is not None:
            s = repr(s)
        e = self.end
        if e is not None:
            e = repr(e)
        return 'Close(start=%s, end=%s)' % (s, e)

    def __copy__(self):
        return Close(self.start, self.end)

    def __eq__(self, other):
        if not isinstance(other, Close):
            return NotImplemented
        return self.start == other.start and self.end == other.end

    def __ne__(self, other):
        if not isinstance(other, Close):
            return NotImplemented
        return not self == other

    def __len__(self):
        return 2

    def __getitem__(self, item):
        if item == 0:
            return self.start
        elif item == 1:
            return self.end
        else:
            raise IndexError

    def plot(self):
        if self.start is not None and self.end is not None:
            for x, y in Line.plot_line(self.start[0], self.start[1], self.end[0], self.end[1]):
                yield x, y, 1

    def length(self, error=None, min_depth=None):
        if self.start is not None and self.end is not None:
            return Point.distance(self.end, self.start)
        else:
            return 0

    def d(self, current_point=None, smooth=False):
        if current_point is None:
            return 'Z'
        else:
            return 'z'


class Line(PathSegment):
    """Represents line commands."""

    def __init__(self, start, end):
        PathSegment.__init__(self)
        self.end = None
        self.start = None
        if start is not None:
            self.start = Point(start)
        if end is not None:
            self.end = Point(end)

    def __repr__(self):
        if self.start is None:
            return 'Line(end=%s)' % (repr(self.end))
        return 'Line(start=%s, end=%s)' % (repr(self.start), repr(self.end))

    def __copy__(self):
        return Line(self.start, self.end)

    def __eq__(self, other):
        if not isinstance(other, Line):
            return NotImplemented
        return self.start == other.start and self.end == other.end

    def __ne__(self, other):
        if not isinstance(other, Line):
            return NotImplemented
        return not self == other

    def __imul__(self, other):
        if isinstance(other, str):
            other = Matrix(other)
        if isinstance(other, Matrix):
            if self.start is not None:
                self.start *= other
            if self.end is not None:
                self.end *= other
        return self

    def __len__(self):
        return 2

    def __getitem__(self, item):
        if item == 0:
            return self.start
        elif item == 1:
            return self.end
        else:
            raise IndexError

    def point(self, position):
        return Point.towards(self.start, self.end, position)

    def length(self, error=None, min_depth=None):
        return Point.distance(self.end, self.start)

    def closest_segment_point(self, p, respect_bounds=True):
        """ Gives the t value of the point on the line closest to the given point. """
        a = self.start
        b = self.end
        vAPx = p[0] - a[0]
        vAPy = p[1] - a[1]
        vABx = b[0] - a[0]
        vABy = b[1] - a[1]
        sqDistanceAB = vABx * vABx + vABy * vABy
        ABAPproduct = vABx * vAPx + vABy * vAPy
        if sqDistanceAB == 0:
            return 0  # Line is point.
        amount = ABAPproduct / sqDistanceAB
        if respect_bounds:
            if amount > 1:
                amount = 1
            if amount < 0:
                amount = 0
        return self.point(amount)

    def d(self, current_point=None, smooth=False):
        if current_point is None:
            return 'L %s' % (self.end)
        else:
            return 'l %s' % (self.end - current_point)

    def plot(self):
        for x, y in Line.plot_line(self.start[0], self.start[1], self.end[0], self.end[1]):
            yield x, y, 1

    @staticmethod
    def plot_line(x0, y0, x1, y1):
        """Zingl-Bresenham line draw algorithm"""
        x0 = int(x0)
        y0 = int(y0)
        x1 = int(x1)
        y1 = int(y1)
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)

        if x0 < x1:
            sx = 1
        else:
            sx = -1
        if y0 < y1:
            sy = 1
        else:
            sy = -1

        err = dx + dy  # error value e_xy

        while True:  # /* loop */
            yield x0, y0
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:  # e_xy+e_y < 0
                err += dy
                x0 += sx
            if e2 <= dx:  # e_xy+e_y < 0
                err += dx
                y0 += sy


class QuadraticBezier(PathSegment):
    """Represents Quadratic Bezier commands."""

    def __init__(self, start, control, end):
        PathSegment.__init__(self)
        self.end = None
        self.control = None
        self.start = None
        if start is not None:
            self.start = Point(start)
        if control is not None:
            self.control = Point(control)
        if end is not None:
            self.end = Point(end)

    def __repr__(self):
        return 'QuadraticBezier(start=%s, control=%s, end=%s)' % (
            repr(self.start), repr(self.control), repr(self.end))

    def __copy__(self):
        return QuadraticBezier(self.start, self.control, self.end)

    def __eq__(self, other):
        if not isinstance(other, QuadraticBezier):
            return NotImplemented
        return self.start == other.start and self.end == other.end and \
               self.control == other.control

    def __ne__(self, other):
        if not isinstance(other, QuadraticBezier):
            return NotImplemented
        return not self == other

    def __imul__(self, other):
        if isinstance(other, str):
            other = Matrix(other)
        if isinstance(other, Matrix):
            if self.start is not None:
                self.start *= other
            if self.control is not None:
                self.control *= other
            if self.end is not None:
                self.end *= other
        return self

    def __len__(self):
        return 3

    def __getitem__(self, item):
        if item == 0:
            return self.start
        elif item == 1:
            return self.control
        elif item == 2:
            return self.end
        raise IndexError

    def point(self, position):
        """Calculate the x,y position at a certain position of the path"""
        x0, y0 = self.start
        x1, y1 = self.control
        x2, y2 = self.end
        x = (1 - position) * (1 - position) * x0 + 2 * (1 - position) * position * x1 + position * position * x2
        y = (1 - position) * (1 - position) * y0 + 2 * (1 - position) * position * y1 + position * position * y2
        return Point(x, y)

    def length(self, error=None, min_depth=None):
        """Calculate the length of the path up to a certain position"""
        a = self.start - 2 * self.control + self.end
        b = 2 * (self.control - self.start)
        a_dot_b = a.real * b.real + a.imag * b.imag

        if abs(a) < 1e-12:
            s = abs(b)
        elif abs(a_dot_b + abs(a) * abs(b)) < 1e-12:
            k = abs(b) / abs(a)
            if k >= 2:
                s = abs(b) - abs(a)
            else:
                s = abs(a) * (k ** 2 / 2 - k + 1)
        else:
            # For an explanation of this case, see
            # http://www.malczak.info/blog/quadratic-bezier-curve-length/
            A = 4 * (a.real ** 2 + a.imag ** 2)
            B = 4 * (a.real * b.real + a.imag * b.imag)
            C = b.real ** 2 + b.imag ** 2

            Sabc = 2 * sqrt(A + B + C)
            A2 = sqrt(A)
            A32 = 2 * A * A2
            C2 = 2 * sqrt(C)
            BA = B / A2

            s = (A32 * Sabc + A2 * B * (Sabc - C2) + (4 * C * A - B ** 2) *
                 log((2 * A2 + BA + Sabc) / (BA + C2))) / (4 * A32)
        return s

    def is_smooth_from(self, previous):
        """Checks if this segment would be a smooth segment following the previous"""
        if isinstance(previous, QuadraticBezier):
            return (self.start == previous.end and
                    (self.control - self.start) == (previous.end - previous.control))
        else:
            return self.control == self.start

    def d(self, current_point=None, smooth=False):
        if smooth:
            if current_point is None:
                return 'T %s' % (self.end)
            else:
                return 't %s' % (self.end - current_point)
        else:
            if current_point is None:
                return 'Q %s %s' % (self.control, self.end)
            else:
                return 'q %s %s' % (self.control - current_point, self.end - current_point)

    def plot(self):
        for x, y in QuadraticBezier.plot_quad_bezier(self.start[0], self.start[1],
                                                     self.control[0], self.control[1],
                                                     self.end[0], self.end[1]):
            yield x, y, 1

    @staticmethod
    def plot_quad_bezier_seg(x0, y0, x1, y1, x2, y2):
        """plot a limited quadratic Bezier segment
        This algorithm can plot curves that do not inflect.
        It is used as part of the general algorithm, which breaks at the infection points"""
        sx = x2 - x1
        sy = y2 - y1
        xx = x0 - x1
        yy = y0 - y1
        xy = 0  # relative values for checks */
        dx = 0
        dy = 0
        err = 0
        cur = xx * sy - yy * sx  # /* curvature */
        points = None

        assert (xx * sx <= 0 and yy * sy <= 0)  # /* sign of gradient must not change */

        if sx * sx + sy * sy > xx * xx + yy * yy:  # /* begin with shorter part */
            x2 = x0
            x0 = sx + x1
            y2 = y0
            y0 = sy + y1
            cur = -cur  # /* swap P0 P2 */
            points = []
        if cur != 0:  # /* no straight line */
            xx += sx
            if x0 < x2:
                sx = 1  # /* x step direction */
            else:
                sx = -1  # /* x step direction */
            xx *= sx
            yy += sy
            if y0 < y2:
                sy = 1
            else:
                sy = -1
            yy *= sy  # /* y step direction */
            xy = 2 * xx * yy
            xx *= xx
            yy *= yy  # /* differences 2nd degree */
            if cur * sx * sy < 0:  # /* negated curvature? */
                xx = -xx
                yy = -yy
                xy = -xy
                cur = -cur
            dx = 4.0 * sy * cur * (x1 - x0) + xx - xy  # /* differences 1st degree */
            dy = 4.0 * sx * cur * (y0 - y1) + yy - xy
            xx += xx
            yy += yy
            err = dx + dy + xy  # /* error 1st step */
            while True:
                if points is None:
                    yield x0, y0  # /* plot curve */
                else:
                    points.append((x0, y0))
                if x0 == x2 and y0 == y2:
                    if points is not None:
                        for plot in reversed(points):
                            yield plot
                    return  # /* last pixel -> curve finished */
                y1 = 2 * err < dx  # /* save value for test of y step */
                if 2 * err > dy:
                    x0 += sx
                    dx -= xy
                    dy += yy
                    err += dy
                    # /* x step */
                if y1 != 0:
                    y0 += sy
                    dy -= xy
                    dx += xx
                    err += dx
                    # /* y step */
                if not (dy < 0 < dx):  # /* gradient negates -> algorithm fails */
                    break
        for plot in Line.plot_line(x0, y0, x2, y2):  # /* plot remaining part to end */:
            if points is None:
                yield plot  # /* plot curve */
            else:
                points.append(plot)  # plotLine(x0,y0, x2,y2) #/* plot remaining part to end */
        if points is not None:
            for plot in reversed(points):
                yield plot

    @staticmethod
    def plot_quad_bezier(x0, y0, x1, y1, x2, y2):
        """Zingl-Bresenham quad bezier draw algorithm.
        plot any quadratic Bezier curve"""
        x0 = int(x0)
        y0 = int(y0)
        # control points are permitted fractional elements.
        x2 = int(x2)
        y2 = int(y2)
        x = x0 - x1
        y = y0 - y1
        t = x0 - 2 * x1 + x2
        r = 0

        if x * (x2 - x1) > 0:  # /* horizontal cut at P4? */
            if y * (y2 - y1) > 0:  # /* vertical cut at P6 too? */
                if abs((y0 - 2 * y1 + y2) / t * x) > abs(y):  # /* which first? */
                    x0 = x2
                    x2 = x + x1
                    y0 = y2
                    y2 = y + y1  # /* swap points */
                    # /* now horizontal cut at P4 comes first */
            t = (x0 - x1) / t
            r = (1 - t) * ((1 - t) * y0 + 2.0 * t * y1) + t * t * y2  # /* By(t=P4) */
            t = (x0 * x2 - x1 * x1) * t / (x0 - x1)  # /* gradient dP4/dx=0 */
            x = floor(t + 0.5)
            y = floor(r + 0.5)
            r = (y1 - y0) * (t - x0) / (x1 - x0) + y0  # /* intersect P3 | P0 P1 */
            for plot in QuadraticBezier.plot_quad_bezier_seg(x0, y0, x, floor(r + 0.5), x, y):
                yield plot
            r = (y1 - y2) * (t - x2) / (x1 - x2) + y2  # /* intersect P4 | P1 P2 */
            x0 = x1 = x
            y0 = y
            y1 = floor(r + 0.5)  # /* P0 = P4, P1 = P8 */
        if (y0 - y1) * (y2 - y1) > 0:  # /* vertical cut at P6? */
            t = y0 - 2 * y1 + y2
            t = (y0 - y1) / t
            r = (1 - t) * ((1 - t) * x0 + 2.0 * t * x1) + t * t * x2  # /* Bx(t=P6) */
            t = (y0 * y2 - y1 * y1) * t / (y0 - y1)  # /* gradient dP6/dy=0 */
            x = floor(r + 0.5)
            y = floor(t + 0.5)
            r = (x1 - x0) * (t - y0) / (y1 - y0) + x0  # /* intersect P6 | P0 P1 */
            for plot in QuadraticBezier.plot_quad_bezier_seg(x0, y0, floor(r + 0.5), y, x, y):
                yield plot
            r = (x1 - x2) * (t - y2) / (y1 - y2) + x2  # /* intersect P7 | P1 P2 */
            x0 = x
            x1 = floor(r + 0.5)
            y0 = y1 = y  # /* P0 = P6, P1 = P7 */
        for plot in QuadraticBezier.plot_quad_bezier_seg(x0, y0, x1, y1, x2, y2):  # /* remaining part */
            yield plot


class CubicBezier(PathSegment):
    """Represents Cubic Bezier commands."""

    def __init__(self, start, control1, control2, end):
        PathSegment.__init__(self)
        self.end = None
        self.control1 = None
        self.control2 = None
        self.start = None
        if start is not None:
            self.start = Point(start)
        if control1 is not None:
            self.control1 = Point(control1)
        if control2 is not None:
            self.control2 = Point(control2)
        if end is not None:
            self.end = Point(end)

    def __repr__(self):
        return 'CubicBezier(start=%s, control1=%s, control2=%s, end=%s)' % (
            repr(self.start), repr(self.control1), repr(self.control2), repr(self.end))

    def __copy__(self):
        return CubicBezier(self.start, self.control1, self.control2, self.end)

    def __eq__(self, other):
        if not isinstance(other, CubicBezier):
            return NotImplemented
        return self.start == other.start and self.end == other.end and \
               self.control1 == other.control1 and self.control2 == other.control2

    def __ne__(self, other):
        if not isinstance(other, CubicBezier):
            return NotImplemented
        return not self == other

    def __imul__(self, other):
        if isinstance(other, str):
            other = Matrix(other)
        if isinstance(other, Matrix):
            if self.start is not None:
                self.start *= other
            if self.control1 is not None:
                self.control1 *= other
            if self.control2 is not None:
                self.control2 *= other
            if self.end is not None:
                self.end *= other
        return self

    def __len__(self):
        return 4

    def __getitem__(self, item):
        if item == 0:
            return self.start
        elif item == 1:
            return self.control1
        elif item == 2:
            return self.control2
        elif item == 3:
            return self.end
        else:
            raise IndexError

    def reverse(self):
        PathSegment.reverse(self)
        c2 = self.control2
        self.control2 = self.control1
        self.control1 = c2

    def point(self, position):
        """Calculate the x,y position at a certain position of the path"""
        x0, y0 = self.start
        x1, y1 = self.control1
        x2, y2 = self.control2
        x3, y3 = self.end
        x = (1 - position) * (1 - position) * (1 - position) * x0 + \
            3 * (1 - position) * (1 - position) * position * x1 + \
            3 * (1 - position) * position * position * x2 + \
            position * position * position * x3
        y = (1 - position) * (1 - position) * (1 - position) * y0 + \
            3 * (1 - position) * (1 - position) * position * y1 + \
            3 * (1 - position) * position * position * y2 + \
            position * position * position * y3
        return Point(x, y)

    def length(self, error=ERROR, min_depth=MIN_DEPTH):
        """Calculate the length of the path up to a certain position"""
        return self._line_length(0, 1, error, min_depth)

    def is_smooth_from(self, previous):
        """Checks if this segment would be a smooth segment following the previous"""
        if isinstance(previous, CubicBezier):
            return (self.start == previous.end and
                    (self.control1 - self.start) == (previous.end - previous.control2))
        else:
            return self.control1 == self.start

    def d(self, current_point=None, smooth=False):
        if smooth:
            if current_point is None:
                return 'S %s %s' % (self.control2, self.end)
            else:
                return 's %s %s' % (self.control2 - current_point, self.end - current_point)
        else:
            if current_point is None:
                return 'C %s %s %s' % (self.control1, self.control2, self.end)
            else:
                return 'c %s %s %s' % (
                    self.control1 - current_point, self.control2 - current_point, self.end - current_point)

    def plot(self):
        for e in CubicBezier.plot_cubic_bezier(self.start[0], self.start[1],
                                               self.control1[0], self.control1[1],
                                               self.control2[0], self.control2[1],
                                               self.end[0], self.end[1]):
            yield e

    @staticmethod
    def plot_cubic_bezier_seg(x0, y0, x1, y1, x2, y2, x3, y3):
        """plot limited cubic Bezier segment
        This algorithm can plot curves that do not inflect.
        It is used as part of the general algorithm, which breaks at the infection points"""
        second_leg = []
        f = 0
        fx = 0
        fy = 0
        leg = 1
        if x0 < x3:
            sx = 1
        else:
            sx = -1
        if y0 < y3:
            sy = 1  # /* step direction */
        else:
            sy = -1  # /* step direction */
        xc = -abs(x0 + x1 - x2 - x3)
        xa = xc - 4 * sx * (x1 - x2)
        xb = sx * (x0 - x1 - x2 + x3)
        yc = -abs(y0 + y1 - y2 - y3)
        ya = yc - 4 * sy * (y1 - y2)
        yb = sy * (y0 - y1 - y2 + y3)
        ab = 0
        ac = 0
        bc = 0
        cb = 0
        xx = 0
        xy = 0
        yy = 0
        dx = 0
        dy = 0
        ex = 0
        pxy = 0
        EP = 0.01
        # /* check for curve restrains */
        # /* slope P0-P1 == P2-P3 and  (P0-P3 == P1-P2    or  no slope change)
        # if (x1 - x0) * (x2 - x3) < EP and ((x3 - x0) * (x1 - x2) < EP or xb * xb < xa * xc + EP):
        #     return
        # if (y1 - y0) * (y2 - y3) < EP and ((y3 - y0) * (y1 - y2) < EP or yb * yb < ya * yc + EP):
        #     return

        if xa == 0 and ya == 0:  # /* quadratic Bezier */
            # return plot_quad_bezier_seg(x0, y0, (3 * x1 - x0) >> 1, (3 * y1 - y0) >> 1, x3, y3)
            sx = floor((3 * x1 - x0 + 1) / 2)
            sy = floor((3 * y1 - y0 + 1) / 2)  # /* new midpoint */

            for plot in QuadraticBezier.plot_quad_bezier_seg(x0, y0, sx, sy, x3, y3):
                yield plot
            return
        x1 = (x1 - x0) * (x1 - x0) + (y1 - y0) * (y1 - y0) + 1  # /* line lengths */
        x2 = (x2 - x3) * (x2 - x3) + (y2 - y3) * (y2 - y3) + 1

        while True:  # /* loop over both ends */
            ab = xa * yb - xb * ya
            ac = xa * yc - xc * ya
            bc = xb * yc - xc * yb
            ex = ab * (ab + ac - 3 * bc) + ac * ac  # /* P0 part of self-intersection loop? */
            if ex > 0:
                f = 1  # /* calc resolution */
            else:
                f = floor(sqrt(1 + 1024 / x1))  # /* calc resolution */
            ab *= f
            ac *= f
            bc *= f
            ex *= f * f  # /* increase resolution */
            xy = 9 * (ab + ac + bc) / 8
            cb = 8 * (xa - ya)  # /* init differences of 1st degree */
            dx = 27 * (8 * ab * (yb * yb - ya * yc) + ex * (ya + 2 * yb + yc)) / 64 - ya * ya * (xy - ya)
            dy = 27 * (8 * ab * (xb * xb - xa * xc) - ex * (xa + 2 * xb + xc)) / 64 - xa * xa * (xy + xa)
            # /* init differences of 2nd degree */
            xx = 3 * (3 * ab * (3 * yb * yb - ya * ya - 2 * ya * yc) - ya * (3 * ac * (ya + yb) + ya * cb)) / 4
            yy = 3 * (3 * ab * (3 * xb * xb - xa * xa - 2 * xa * xc) - xa * (3 * ac * (xa + xb) + xa * cb)) / 4
            xy = xa * ya * (6 * ab + 6 * ac - 3 * bc + cb)
            ac = ya * ya
            cb = xa * xa
            xy = 3 * (xy + 9 * f * (cb * yb * yc - xb * xc * ac) - 18 * xb * yb * ab) / 8

            if ex < 0:  # /* negate values if inside self-intersection loop */
                dx = -dx
                dy = -dy
                xx = -xx
                yy = -yy
                xy = -xy
                ac = -ac
                cb = -cb  # /* init differences of 3rd degree */
            ab = 6 * ya * ac
            ac = -6 * xa * ac
            bc = 6 * ya * cb
            cb = -6 * xa * cb
            dx += xy
            ex = dx + dy
            dy += xy  # /* error of 1st step */
            try:
                pxy = 0
                fx = fy = f
                while x0 != x3 and y0 != y3:
                    if leg == 0:
                        second_leg.append((x0, y0))  # /* plot curve */
                    else:
                        yield x0, y0  # /* plot curve */
                    while True:  # /* move sub-steps of one pixel */
                        if pxy == 0:
                            if dx > xy or dy < xy:
                                raise StopIteration  # /* confusing */
                        if pxy == 1:
                            if dx > 0 or dy < 0:
                                raise StopIteration  # /* values */
                        y1 = 2 * ex - dy  # /* save value for test of y step */
                        if 2 * ex >= dx:  # /* x sub-step */
                            fx -= 1
                            dx += xx
                            ex += dx
                            xy += ac
                            dy += xy
                            yy += bc
                            xx += ab
                        elif y1 > 0:
                            raise StopIteration
                        if y1 <= 0:  # /* y sub-step */
                            fy -= 1
                            dy += yy
                            ex += dy
                            xy += bc
                            dx += xy
                            xx += ac
                            yy += cb
                        if not (fx > 0 and fy > 0):  # /* pixel complete? */
                            break
                    if 2 * fx <= f:
                        x0 += sx
                        fx += f  # /* x step */
                    if 2 * fy <= f:
                        y0 += sy
                        fy += f  # /* y step */
                    if pxy == 0 and dx < 0 and dy > 0:
                        pxy = 1  # /* pixel ahead valid */
            except StopIteration:
                pass
            xx = x0
            x0 = x3
            x3 = xx
            sx = -sx
            xb = -xb  # /* swap legs */
            yy = y0
            y0 = y3
            y3 = yy
            sy = -sy
            yb = -yb
            x1 = x2
            if not (leg != 0):
                break
            leg -= 1  # /* try other end */
        for plot in Line.plot_line(x3, y3, x0, y0):  # /* remaining part in case of cusp or crunode */
            second_leg.append(plot)
        for plot in reversed(second_leg):
            yield plot

    @staticmethod
    def plot_cubic_bezier(x0, y0, x1, y1, x2, y2, x3, y3):
        """Zingl-Bresenham cubic bezier draw algorithm
        plot any quadratic Bezier curve"""
        x0 = int(x0)
        y0 = int(y0)
        # control points are permitted fractional elements.
        x3 = int(x3)
        y3 = int(y3)
        n = 0
        i = 0
        xc = x0 + x1 - x2 - x3
        xa = xc - 4 * (x1 - x2)
        xb = x0 - x1 - x2 + x3
        xd = xb + 4 * (x1 + x2)
        yc = y0 + y1 - y2 - y3
        ya = yc - 4 * (y1 - y2)
        yb = y0 - y1 - y2 + y3
        yd = yb + 4 * (y1 + y2)
        fx0 = x0
        fx1 = 0
        fx2 = 0
        fx3 = 0
        fy0 = y0
        fy1 = 0
        fy2 = 0
        fy3 = 0
        t1 = xb * xb - xa * xc
        t2 = 0
        t = [0] * 5
        # /* sub-divide curve at gradient sign changes */
        if xa == 0:  # /* horizontal */
            if abs(xc) < 2 * abs(xb):
                t[n] = xc / (2.0 * xb)  # /* one change */
                n += 1
        elif t1 > 0.0:  # /* two changes */
            t2 = sqrt(t1)
            t1 = (xb - t2) / xa
            if abs(t1) < 1.0:
                t[n] = t1
                n += 1
            t1 = (xb + t2) / xa
            if abs(t1) < 1.0:
                t[n] = t1
                n += 1
        t1 = yb * yb - ya * yc
        if ya == 0:  # /* vertical */
            if abs(yc) < 2 * abs(yb):
                t[n] = yc / (2.0 * yb)  # /* one change */
                n += 1
        elif t1 > 0.0:  # /* two changes */
            t2 = sqrt(t1)
            t1 = (yb - t2) / ya
            if abs(t1) < 1.0:
                t[n] = t1
                n += 1
            t1 = (yb + t2) / ya
            if abs(t1) < 1.0:
                t[n] = t1
                n += 1
        i = 1
        while i < n:  # /* bubble sort of 4 points */
            t1 = t[i - 1]
            if t1 > t[i]:
                t[i - 1] = t[i]
                t[i] = t1
                i = 0
            i += 1
        t1 = -1.0
        t[n] = 1.0  # /* begin / end point */
        for i in range(0, n + 1):  # /* plot each segment separately */
            t2 = t[i]  # /* sub-divide at t[i-1], t[i] */
            fx1 = (t1 * (t1 * xb - 2 * xc) - t2 * (t1 * (t1 * xa - 2 * xb) + xc) + xd) / 8 - fx0
            fy1 = (t1 * (t1 * yb - 2 * yc) - t2 * (t1 * (t1 * ya - 2 * yb) + yc) + yd) / 8 - fy0
            fx2 = (t2 * (t2 * xb - 2 * xc) - t1 * (t2 * (t2 * xa - 2 * xb) + xc) + xd) / 8 - fx0
            fy2 = (t2 * (t2 * yb - 2 * yc) - t1 * (t2 * (t2 * ya - 2 * yb) + yc) + yd) / 8 - fy0
            fx3 = (t2 * (t2 * (3 * xb - t2 * xa) - 3 * xc) + xd) / 8
            fx0 -= fx3
            fy3 = (t2 * (t2 * (3 * yb - t2 * ya) - 3 * yc) + yd) / 8
            fy0 -= fy3
            x3 = floor(fx3 + 0.5)
            y3 = floor(fy3 + 0.5)  # /* scale bounds */
            if fx0 != 0.0:
                fx0 = (x0 - x3) / fx0
                fx1 *= fx0
                fx2 *= fx0
            if fy0 != 0.0:
                fy0 = (y0 - y3) / fy0
                fy1 *= fy0
                fy2 *= fy0
            if x0 != x3 or y0 != y3:  # /* segment t1 - t2 */
                # plotCubicBezierSeg(x0,y0, x0+fx1,y0+fy1, x0+fx2,y0+fy2, x3,y3)
                for plot in CubicBezier.plot_cubic_bezier_seg(x0, y0, x0 + fx1, y0 + fy1, x0 + fx2, y0 + fy2, x3, y3):
                    yield plot
            x0 = x3
            y0 = y3
            fx0 = fx3
            fy0 = fy3
            t1 = t2


class Arc(PathSegment):
    def __init__(self, *args, **kwargs):
        """
        Represents Arc commands.

        Arc objects can take different parameters to create arcs.
        Since we expect taking in SVG parameters. We accept SVG parameterization which is:
        start, rx, ry, rotation, arc_flag, sweep_flag, end.

        To do matrix transitions, the native parameterization is start, end, center, prx, pry, sweep

        'start, end, center, prx, pry' are points and sweep amount is a t value in tau radians.
        If points are modified by an affine transformation, the arc is transformed.
        There is a special case for when the scale factor inverts, it inverts the sweep.

        Note: t-values are not angles from center in ellipical arcs. These are the same thing in
        circular arcs. But, here t is a parameterization around the ellipse, as if it were a circle.
        The position on the arc is (a * cos(t), b * sin(t)). If r-major was 0 for example. The
        positions would all fall on the x-axis. And the angle from center would all be either 0 or
        tau/2. However, since t is the parameterization we can conceptualize it as a position on a
        circle which is then scaled and rotated by a matrix.

        prx is the point at t 0 in the ellipse.
        pry is the point at t tau/4 in the ellipse.
        prx -> center -> pry should form a right triangle.

        The rotation can be defined as the angle from center to prx. Since prx is located at
        t(0) its deviation can only be the result of a rotation.

        Sweep is a value in t.
        The sweep angle can be a value greater than tau and less than -tau.
        However if this is the case, conversion back to Path.d() is expected to fail.
        We can denote these arc events but not as a single command.
        should equal sweep or mod thereof.
        start_t + sweep = end_t
        """

        PathSegment.__init__(self)
        self.start = None
        self.end = None
        self.center = None
        self.prx = None
        self.pry = None
        self.sweep = None
        if len(args) == 6 and isinstance(args[1], complex):
            self._svg_complex_parameterize(*args)
            return
        elif len(kwargs) == 6 and 'rotation' in kwargs:
            self._svg_complex_parameterize(**kwargs)
            return
        elif len(args) == 7:
            # This is an svg parameterized call.
            # A: rx ry x-axis-rotation large-arc-flag sweep-flag x y
            self._svg_parameterize(args[0], args[1], args[2], args[3], args[4], args[5], args[6])
            return
        if 'left' in kwargs and 'right' in kwargs and 'top' in kwargs and 'bottom' in kwargs:
            left = kwargs['left']
            right = kwargs['right']
            top = kwargs['top']
            bottom = kwargs['bottom']
            self.center = Point((left + right) / 2.0, (top + bottom) / 2.0)
            rx = (right - left) / 2.0
            ry = (bottom - top) / 2.0
            self.prx = Point(self.center[0] + rx, self.center[1])
            self.pry = Point(self.center[0], self.center[1] + ry)
        len_args = len(args)
        if len_args > 0:
            if args[0] is not None:
                self.start = Point(args[0])
        if len_args > 1:
            if args[1] is not None:
                self.end = Point(args[1])
        if len_args > 2:
            if args[2] is not None:
                self.center = Point(args[2])
        if len_args > 3:
            if args[3] is not None:
                self.prx = Point(args[3])
        if len_args > 4:
            if args[4] is not None:
                self.pry = Point(args[4])
        if len_args > 5:
            self.sweep = args[5]
            return  # The args gave us everything.
        if 'start' in kwargs:
            self.start = Point(kwargs['start'])
        if 'end' in kwargs:
            self.end = Point(kwargs['end'])
        if 'center' in kwargs:
            self.center = Point(kwargs['center'])
        if 'prx' in kwargs:
            self.prx = Point(kwargs['prx'])
        if 'pry' in kwargs:
            self.pry = Point(kwargs['pry'])
        if 'sweep' in kwargs:
            self.sweep = kwargs['sweep']
        if self.start is not None and self.end is not None and self.center is None:
            # Start and end, but no center. Solutions require either a radius or a control point.
            if 'control' in kwargs:  # Control is any additional point on the arc.
                control = Point(kwargs['control'])
                delta_a = control - self.start
                delta_b = self.end - control
                slope_a = delta_a[1] / delta_a[0]
                slope_b = delta_b[1] / delta_b[0]
                ab_mid = Point.towards(self.start, control, 0.5)
                bc_mid = Point.towards(control, self.end, 0.5)
                if delta_a[1] == 0:  # slope_a == 0
                    cx = ab_mid[0]
                    if delta_b[0] == 0:  # slope_b == inf
                        cy = bc_mid[1]
                    else:
                        cy = bc_mid[1] + (bc_mid.x - cx) / slope_b
                elif delta_b[1] == 0:  # slope_b == 0
                    cx = bc_mid[0]
                    if delta_a[1] == 0:  # slope_a == inf
                        cy = ab_mid[1]
                    else:
                        cy = ab_mid[1] + (ab_mid[0] - cx) / slope_a
                elif delta_a[0] == 0:  # slope_a == inf
                    cy = ab_mid[1]
                    cx = slope_b * (bc_mid[1] - cy) + bc_mid[0]
                elif delta_b[0] == 0:  # slope_b == inf
                    cy = bc_mid[1]
                    cx = slope_a * (ab_mid[1] - cy) + ab_mid[0]
                elif slope_a == slope_b:
                    cx = ab_mid[0]
                    cy = ab_mid[1]
                else:
                    cx = (slope_a * slope_b * (ab_mid[1] - bc_mid[1])
                          - slope_a * bc_mid[0]
                          + slope_b * ab_mid[0]) / (slope_b - slope_a)
                    cy = ab_mid[1] - (cx - ab_mid[0]) / slope_a
                self.center = Point(cx, cy)
            elif 'r' in kwargs:
                r = kwargs['r']
                mid = Point((self.start[0] + self.end[0]) / 2.0, (self.start[1] + self.end[1]) / 2.0)
                q = Point.distance(self.start, self.end)
                hq = q / 2.0
                if r < hq:
                    kwargs['r'] = r = hq  # Correct potential math domain error.
                self.center = Point(
                    mid[0] + sqrt(r ** 2 - hq ** 2) * (self.start[1] - self.end[1]) / q,
                    mid[1] + sqrt(r ** 2 - hq ** 2) * (self.end[0] - self.start[0]) / q
                )
                cw = bool(Point.orientation(self.start, self.center, self.end) == 1)
                if 'ccw' in kwargs and kwargs['ccw'] and cw or not cw:
                    # ccw arg exists, is true, and we found the cw center, or we didn't find the cw center.
                    self.center = Point(
                        mid[0] - sqrt(r ** 2 - hq ** 2) * (self.start[1] - self.end[1]) / q,
                        mid[1] - sqrt(r ** 2 - hq ** 2) * (self.end[0] - self.start[0]) / q
                    )
            elif 'rx' in kwargs and 'ry' in kwargs:
                # This formulation will assume p1 and p2 are both axis aligned.
                rx = kwargs['rx']
                ry = kwargs['ry']
                # We will assume rx == abs(self.start[0] - self.end[0])
                self.center = Point(self.start[0], self.end[1])
                cw = bool(Point.orientation(self.start, self.center, self.end) == 1)
                if 'ccw' in kwargs and kwargs['ccw'] and cw or not cw:
                    self.center = Point(self.end[0], self.start[1])
                self.sweep = tau / 4.0

        if self.center is None:
            return  # Center must be solvable.
        if 'r' in kwargs:
            r = kwargs['r']
            if self.prx is None:
                self.prx = Point(self.center[0] + r, self.center[1])
            if self.pry is None:
                self.pry = Point(self.center[0], self.center[1] + r)
        if 'rx' in kwargs:
            rx = kwargs['rx']
            if self.prx is None:
                if 'rotation' in kwargs:
                    theta = kwargs['rotation']
                    self.prx = Point.polar(self.center, theta, rx)
                else:
                    self.prx = Point(self.center[0] + rx, self.center[1])
        if 'ry' in kwargs:
            ry = kwargs['ry']
            if self.pry is None:
                if 'rotation' in kwargs:
                    theta = kwargs['rotation']
                    theta += tau / 4.0
                    self.pry = Point.polar(self.center, theta, ry)
                else:
                    self.pry = Point(self.center[0], self.center[1] + ry)
        if self.start is not None and (self.prx is None or self.pry is None):
            radius_s = Point.distance(self.center, self.start)
            self.prx = Point(self.center[0] + radius_s, self.center[1])
            self.pry = Point(self.center[0], self.center[1] + radius_s)
        if self.end is not None and (self.prx is None or self.pry is None):
            radius_e = Point.distance(self.center, self.end)
            self.prx = Point(self.center[0] + radius_e, self.center[1])
            self.pry = Point(self.center[0], self.center[1] + radius_e)
        if self.sweep is None and self.start is not None and self.end is not None:
            start_t = self.get_start_t()
            end_t = self.get_end_t()
            self.sweep = end_t - start_t
            cw = True  # Clockwise default.
            if 'ccw' in kwargs:
                cw = not bool(kwargs['ccw'])
            elif 'control' in kwargs:
                control = Point(kwargs['control'])
                cw = bool(Point.orientation(self.start, control, self.end) == 2)
            if cw and self.sweep < 0:
                self.sweep += tau
            if not cw and self.sweep > 0:
                self.sweep -= tau
        if self.sweep is not None and self.start is not None and self.end is None:
            start_t = self.get_start_t()
            end_t = start_t + self.sweep
            self.end = self.point_at_t(end_t)
        if self.sweep is not None and self.start is None and self.end is not None:
            end_t = self.get_end_t()
            start_t = end_t - self.sweep
            self.end = self.point_at_t(start_t)

    def __repr__(self):
        return 'Arc(%s, %s, %s, %s, %s, %s)' % (
            repr(self.start), repr(self.end), repr(self.center), repr(self.prx), repr(self.pry), self.sweep)

    def __copy__(self):
        return Arc(self.start, self.end, self.center, self.prx, self.pry, self.sweep)

    def __eq__(self, other):
        if not isinstance(other, Arc):
            return NotImplemented
        return self.start == other.start and self.end == other.end and \
               self.prx == other.prx and self.pry == other.pry and \
               self.center == other.center and self.sweep == other.sweep

    def __ne__(self, other):
        if not isinstance(other, Arc):
            return NotImplemented
        return not self == other

    def __imul__(self, other):
        if isinstance(other, str):
            other = Matrix(other)
        if isinstance(other, Matrix):
            if self.start is not None:
                self.start *= other
            if self.center is not None:
                self.center *= other
            if self.end is not None:
                self.end *= other
            if self.prx is not None:
                self.prx *= other
            if self.pry is not None:
                self.pry *= other
            if other.value_scale_x() < 0:
                self.sweep = -self.sweep
            if other.value_scale_y() < 0:
                self.sweep = -self.sweep
        return self

    def __len__(self):
        return 5

    def __getitem__(self, item):
        if item == 0:
            return self.start
        elif item == 1:
            return self.end
        elif item == 2:
            return self.center
        elif item == 3:
            return self.prx
        elif item == 4:
            return self.pry
        raise IndexError

    @property
    def theta(self):
        """legacy property"""
        return Angle.radians(self.get_start_t()).as_positive_degrees

    @property
    def delta(self):
        """legacy property"""
        return Angle.radians(self.sweep).as_degrees

    def reverse(self):
        PathSegment.reverse(self)
        self.sweep = -self.sweep

    def point(self, position):
        if self.start == self.end and self.sweep == 0:
            # This is equivalent of omitting the segment
            return self.start

        t = self.get_start_t() + self.sweep * position
        return self.point_at_t(t)

    def _integral_length(self):
        def ellipse_part_integral(t1, t2, a, b, n=100000):
            # function to integrate
            def f(t):
                return sqrt(1 - (1 - a ** 2 / b ** 2) * sin(t) ** 2)

            start = min(t1, t2)
            seg_len = abs(t1 - t2) / n
            return b * sum(f(start + seg_len * i) * seg_len for i in range(1, n + 1))

        start_angle = self.get_start_t()
        end_angle = start_angle + self.sweep
        return ellipse_part_integral(start_angle, end_angle, self.rx, self.ry)

    def _exact_length(self):
        """scipy is not a dependency. However, if scipy exists this function will find the
        exact arc length. By default .length() delegates to here and on failure uses the
        fallback method."""
        from scipy.special import ellipeinc
        a = self.rx
        b = self.ry
        phi = self.get_start_t()
        m = 1 - (a / b) ** 2
        d1 = ellipeinc(phi, m)
        phi = phi + self.sweep
        m = 1 - (a / b) ** 2
        d2 = ellipeinc(phi, m)
        return b * abs(d2 - d1)

    def length(self, error=ERROR, min_depth=MIN_DEPTH):
        """The length of an elliptical arc segment requires numerical
        integration, and in that case it's simpler to just do a geometric
        approximation, as for cubic bezier curves.
        """
        if self.sweep == 0:
            return 0
        if self.start == self.end and self.sweep == 0:
            # This is equivalent of omitting the segment
            return 0
        a = self.rx
        b = self.ry
        d = abs(a - b)

        if d < ERROR:  # This is a circle.
            return abs(self.rx * self.sweep)
        try:
            return self._exact_length()
        except ImportError:
            return self._line_length(error=error, min_depth=min_depth)

    def _svg_complex_parameterize(self, start, radius, rotation, arc, sweep, end):
        """Parameterization with complex radius and having rotation factors."""
        self._svg_parameterize(Point(start), radius.real, radius.imag, rotation, bool(arc), bool(sweep), Point(end))

    def _svg_parameterize(self, start, rx, ry, rotation, large_arc_flag, sweep_flag, end):
        """Conversion from svg parameterization, our chosen native native form.
        http://www.w3.org/TR/SVG/implnote.html#ArcImplementationNotes """

        start = Point(start)
        self.start = start
        end = Point(end)
        self.end = end
        if start == end or rx == 0 or ry == 0:
            # If start is equal to end, there are infinite number of circles so these void out.
            # We still permit this kind of arc, but SVG parameterization cannot be used to achieve it.
            self.sweep = 0
            self.prx = Point(start)
            self.pry = Point(start)
            self.center = Point(start)
            return
        cosr = cos(radians(rotation))
        sinr = sin(radians(rotation))
        dx = (start.real - end.real) / 2
        dy = (start.imag - end.imag) / 2
        x1prim = cosr * dx + sinr * dy
        x1prim_sq = x1prim * x1prim
        y1prim = -sinr * dx + cosr * dy
        y1prim_sq = y1prim * y1prim

        rx_sq = rx * rx
        ry_sq = ry * ry

        # Correct out of range radii
        radius_check = (x1prim_sq / rx_sq) + (y1prim_sq / ry_sq)
        if radius_check > 1:
            rx *= sqrt(radius_check)
            ry *= sqrt(radius_check)
            rx_sq = rx * rx
            ry_sq = ry * ry

        t1 = rx_sq * y1prim_sq
        t2 = ry_sq * x1prim_sq
        c = sqrt(abs((rx_sq * ry_sq - t1 - t2) / (t1 + t2)))

        if large_arc_flag == sweep_flag:
            c = -c
        cxprim = c * rx * y1prim / ry
        cyprim = -c * ry * x1prim / rx

        center = Point((cosr * cxprim - sinr * cyprim) +
                       ((start.real + end.real) / 2),
                       (sinr * cxprim + cosr * cyprim) +
                       ((start.imag + end.imag) / 2))

        ux = (x1prim - cxprim) / rx
        uy = (y1prim - cyprim) / ry
        vx = (-x1prim - cxprim) / rx
        vy = (-y1prim - cyprim) / ry
        n = sqrt(ux * ux + uy * uy)
        p = ux
        theta = degrees(acos(p / n))
        if uy < 0:
            theta = -theta
        theta = theta % 360

        n = sqrt((ux * ux + uy * uy) * (vx * vx + vy * vy))
        p = ux * vx + uy * vy
        d = p / n
        # In certain cases the above calculation can through inaccuracies
        # become just slightly out of range, f ex -1.0000000000000002.
        if d > 1.0:
            d = 1.0
        elif d < -1.0:
            d = -1.0
        delta = degrees(acos(d))
        if (ux * vy - uy * vx) < 0:
            delta = -delta
        delta = delta % 360
        if not sweep_flag:
            delta -= 360
        # built parameters, delta, theta, center

        rotate_matrix = Matrix()
        rotate_matrix.post_rotate(Angle.degrees(rotation).as_radians, center[0], center[1])

        self.center = center
        self.prx = Point(center[0] + rx, center[1])
        self.pry = Point(center[0], center[1] + ry)

        self.prx.matrix_transform(rotate_matrix)
        self.pry.matrix_transform(rotate_matrix)
        self.sweep = Angle.degrees(delta).as_radians

    # def as_quad_curves(self):
    #     sweep_limit = tau / 12
    #     arc_required = int(ceil(abs(self.sweep) / sweep_limit))
    #     if arc_required == 0:
    #         return
    #     slice = self.sweep / float(arc_required)
    #
    #     current_t = 0
    #
    #     p_start = self.start
    #     for i in range(0, arc_required):
    #         end_t = current_t + slice
    #         p_end = self.point_at_t(end_t)
    #         q = Point(p_start[0] + tan((p_end[0] - p_start[0]) / 2.0))
    #         yield QuadraticBezier(p_start, q, p_end)
    #         p_start = p_end
    #         current_t = end_t

    def as_cubic_curves(self):
        sweep_limit = tau / 12
        arc_required = int(ceil(abs(self.sweep) / sweep_limit))
        if arc_required == 0:
            return
        slice = self.sweep / float(arc_required)

        theta = self.get_rotation()
        rx = self.rx
        ry = self.ry
        p_start = self.start
        current_angle = self.get_start_t()
        x0 = self.center[0]
        y0 = self.center[1]
        cos_theta = cos(theta)
        sin_theta = sin(theta)

        for i in range(0, arc_required):
            next_angle = current_angle + slice

            alpha = sin(slice) * (sqrt(4 + 3 * pow(tan((slice) / 2.0), 2)) - 1) / 3.0

            cos_start_angle = cos(current_angle)
            sin_start_angle = sin(current_angle)

            ePrimen1x = -rx * cos_theta * sin_start_angle - ry * sin_theta * cos_start_angle
            ePrimen1y = -rx * sin_theta * sin_start_angle + ry * cos_theta * cos_start_angle

            cos_end_angle = cos(next_angle)
            sin_end_angle = sin(next_angle)

            p2En2x = x0 + rx * cos_end_angle * cos_theta - ry * sin_end_angle * sin_theta
            p2En2y = y0 + rx * cos_end_angle * sin_theta + ry * sin_end_angle * cos_theta
            p_end = (p2En2x, p2En2y)
            if i == arc_required - 1:
                p_end = self.end

            ePrimen2x = -rx * cos_theta * sin_end_angle - ry * sin_theta * cos_end_angle
            ePrimen2y = -rx * sin_theta * sin_end_angle + ry * cos_theta * cos_end_angle

            p_c1 = (p_start[0] + alpha * ePrimen1x, p_start[1] + alpha * ePrimen1y)
            p_c2 = (p_end[0] - alpha * ePrimen2x, p_end[1] - alpha * ePrimen2y)

            yield CubicBezier(p_start, p_c1, p_c2, p_end)
            p_start = Point(p_end)
            current_angle = next_angle

    def is_circular(self):
        a = self.rx
        b = self.ry
        return a == b

    @property
    def radius(self):
        """Legacy complex radius property

        Point will work like a complex for legacy reasons.
        """
        return Point(self.rx, self.ry)

    @property
    def rx(self):
        return Point.distance(self.center, self.prx)

    @property
    def ry(self):
        return Point.distance(self.center, self.pry)

    def get_rotation(self):
        return Point.angle(self.center, self.prx)

    def get_start_angle(self):
        """
        :return: Angle from the center point to start point.
        """
        return self.angle_at_point(self.start)

    def get_end_angle(self):
        """
        :return: Angle from the center point to end point.
        """
        return self.angle_at_point(self.end)

    def get_start_t(self):
        """
        start t value in the ellipse.

        :return: t parameter of start point.
        """
        return self.t_at_point(self.point_at_angle(self.get_start_angle()))

    def get_end_t(self):
        """
        end t value in the ellipse.

        :return: t parameter of start point.
        """
        return self.t_at_point(self.point_at_angle(self.get_end_angle()))

    def point_at_angle(self, angle):
        """
        find the point on the ellipse from the center at the given angle.
        Note: For non-circular arcs this is different than point(t).

        :param angle: angle from center to find point
        :return: point found
        """
        angle -= self.get_rotation()
        a = self.rx
        b = self.ry
        if a == b:
            return self.point_at_t(angle)
        if abs(angle) > tau / 4:
            return self.point_at_t(atan2(a * tan(angle), b) + tau / 2)
        else:
            return self.point_at_t(atan2(a * tan(angle), b))

    def angle_at_point(self, p):
        """
        find the angle to the point.

        :param p: point
        :return: angle to given point.
        """
        return self.center.angle_to(p)

    def t_at_point(self, p):
        """
        find the t parameter to at the point.

        :param p: point
        :return: t parameter to the given point.
        """
        angle = self.angle_at_point(p)
        angle -= self.get_rotation()
        a = self.rx
        b = self.ry
        if abs(angle) > tau / 4:
            return atan2(a * tan(angle), b) + tau / 2
        else:
            return atan2(a * tan(angle), b)

    def point_at_t(self, t):
        """
        find the point that corresponds to given value t.
        Where t=0 is the first point and t=tau is the final point.

        In the case of a circle: t = angle.

        :param t:
        :return:
        """
        rotation = self.get_rotation()
        a = self.rx
        b = self.ry
        cx = self.center[0]
        cy = self.center[1]
        cosTheta = cos(rotation)
        sinTheta = sin(rotation)
        cosT = cos(t)
        sinT = sin(t)
        px = cx + a * cosT * cosTheta - b * sinT * sinTheta
        py = cy + a * cosT * sinTheta + b * sinT * cosTheta
        return Point(px, py)

    def get_ellipse(self):
        return Ellipse(self.center, self.rx, self.ry, self.get_rotation())

    def bbox(self):
        """Returns the bounding box of the arc."""
        # TODO: truncated the bounding box to the arc rather than the entire ellipse.
        theta = Point.angle(self.center, self.prx)
        a = Point.distance(self.center, self.prx)
        b = Point.distance(self.center, self.pry)
        cos_theta = cos(theta)
        sin_theta = sin(theta)
        xmax = sqrt(a * a * cos_theta * cos_theta + b * b * sin_theta * sin_theta)
        xmin = -xmax
        ymax = sqrt(a * a * sin_theta * sin_theta + b * b * cos_theta * cos_theta)
        ymin = -xmax
        return xmin + self.center[0], ymin + self.center[1], xmax + self.center[0], ymax + self.center[1]

    def d(self, current_point=None, smooth=False):
        if current_point is None:
            return 'A %G,%G %G %d,%d %s' % (
                self.rx,
                self.ry,
                self.get_rotation().as_degrees,
                int(abs(self.sweep) > (tau / 2.0)),
                int(self.sweep >= 0),
                self.end)
        else:
            return 'a %G,%G %G %d,%d %s' % (
                self.rx,
                self.ry,
                self.get_rotation().as_degrees,
                int(abs(self.sweep) > (tau / 2.0)),
                int(self.sweep >= 0),
                self.end - current_point)

    def plot(self):
        # TODO: Should actually plot the arc according to the pixel-perfect standard. In this case we would plot a
        # Bernstein weighted bezier curve.
        for curve in self.as_cubic_curves():
            for value in curve.plot():
                yield value


class Path(Shape, MutableSequence):
    """
    A Path is a Mutable sequence of path segments

    It is a generalized shape which can map out all the other shapes.

    Each PathSegment object maps a particular command. Each one exists only once in each path and every point contained
    within the object is also unique. We attempt to internally maintain some validity. Each end point should link
    to the following segments start point. And each close point should connect from the preceding segments endpoint to
    the last Move command.

    These are soft checks made only at the time of addition and some manipulations. Modifying the points of the segments
    can and will cause path invalidity. Some SVG invalid operations are permitted such as arcs longer than tau radians
    or beginning sequences without a move. The expectation is that these will eventually be used as part of a valid path
    so these fragment paths are permitted. In some cases these invalid paths will still have consistent path_d values,
    in other cases, there will be no valid methods to reproduce these.
    """

    def __init__(self, *args, **kwargs):
        Shape.__init__(self, *args, **kwargs)
        self._length = None
        self._lengths = None
        if len(args) != 1:
            self._segments = list(args)
        else:
            p = args[0]
            if isinstance(p, dict):
                self._segments = list()
                if SVG_ATTR_DATA in p:
                    self.parse(p[SVG_ATTR_DATA])
            elif isinstance(p, Subpath):
                self._segments = list(p.segments(transformed=False))
                Shape.__init__(self,p._path)
            elif isinstance(args[0], Shape):
                self._segments = list(p.segments(transformed=False))
            elif isinstance(args[0], str):
                self._segments = list()
                self.parse(args[0])
            elif isinstance(args[0], tuple):
                self._segments = list(args[0])
                self.validate_connections()
            elif isinstance(args[0], list):
                self._segments = args[0]
                # We have no guarantee of the validity of the source data
                self.validate_connections()
            else:
                self._segments = list(args)

    def __copy__(self):
        return Path(*map(copy, self._segments),
                    transform=Matrix(self.transform), stroke=Color(self.stroke), fill=Color(self.fill),
                    apply=self.apply, id=self.id)

    def __getitem__(self, index):
        return self._segments[index]

    def _validate_subpath(self, index):
        """ensure the subpath containing this index is valid."""
        for j in range(index, len(self._segments)):
            close_search = self._segments[j]
            if isinstance(close_search, Move):
                return  # Not a closed path, subpath is valid.
            if isinstance(close_search, Close):
                for k in range(index, -1, -1):
                    move_search = self._segments[k]
                    if isinstance(move_search, Move):
                        self._segments[j].end = Point(move_search.end)
                        return
                self._segments[j].end = Point(self._segments[0].end)
                return

    def _validate_move(self, index):
        """ensure the next closed point from this index points to a valid location."""
        for i in range(index + 1, len(self._segments)):
            segment = self._segments[i]
            if isinstance(segment, Move):
                return  # Not a closed path, the move is valid.
            if isinstance(segment, Close):
                segment.end = Point(self._segments[index].end)
                return

    def _validate_close(self, index):
        """ensure the close element at this position correctly links to the previous move"""
        for i in range(index, -1, -1):
            segment = self._segments[i]
            if isinstance(segment, Move):
                self._segments[index].end = Point(segment.end)
                return
        self._segments[index].end = Point(self._segments[0].end)
        # If move is never found, just the end point of the first element.

    def _validate_connection(self, index):
        """
        Validates the connection at the index.
        Connection 0 is the connection between getitem(0) and getitem(1)
        """
        if index < 0 or index + 1 >= len(self._segments):
            return  # This connection doesn't exist.
        first = self._segments[index]
        second = self._segments[index + 1]
        if first.end is not None and second.start is None:
            second.start = Point(first.end)
        elif first.end is None and second.start is not None:
            first.end = Point(second.start)
        elif first.end != second.start:
            second.start = Point(first.end)

    def __setitem__(self, index, new_element):
        if isinstance(new_element, str):
            new_element = Path(new_element)
            if len(new_element) == 0:
                return
            new_element = new_element[0]
        self._segments[index] = new_element
        self._length = None
        self._validate_connection(index - 1)
        self._validate_connection(index)
        if isinstance(new_element, Move):
            self._validate_move(index)
        if isinstance(new_element, Close):
            self._validate_close(index)

    def __delitem__(self, index):
        original_element = self._segments[index]
        del self._segments[index]
        self._length = None
        self._validate_connection(index - 1)
        if isinstance(original_element, (Close, Move)):
            self._validate_subpath(index)

    def __iadd__(self, other):
        if isinstance(other, str):
            self.parse(other)
        elif isinstance(other, (Path, Subpath)):
            self.extend(map(copy, list(other)))
        elif isinstance(other, Shape):
            self.parse(other.d())
        elif isinstance(other, PathSegment):
            self.append(other)
        else:
            return NotImplemented
        return self

    def __add__(self, other):
        n = copy(self)
        n += other
        return n

    def __radd__(self, other):
        if isinstance(other, str):
            path = Path(other)
            path.extend(map(copy, self._segments))
            return path
        elif isinstance(other, PathSegment):
            path = copy(self)
            path.insert(0, other)
            return path
        else:
            return NotImplemented

    def __len__(self):
        return len(self._segments)

    def __str__(self):
        return self.d()

    def __repr__(self):
        values = []
        if len(self) > 0:
            values.append(', '.join(repr(x) for x in self._segments))
        self._repr_shape(values)
        params = ", ".join(values)
        name = self._name()
        return "%s(%s)" % (name, params)

    def __eq__(self, other):
        if isinstance(other, str):
            return self.__eq__(Path(other))
        if not isinstance(other, Path):
            return NotImplemented
        if len(self) != len(other):
            return False
        p = abs(self)
        q = abs(other)
        for s, o in zip(q._segments, p._segments):
            if not s == o:
                return False
        return True

    def __ne__(self, other):
        if not isinstance(other, (Path, str)):
            return NotImplemented
        return not self == other

    def parse(self, pathdef):
        """Parses the SVG path."""
        tokens = SVGPathTokens()
        tokens.svg_parse(self, pathdef)

    def validate_connections(self):
        """
        Force validate all connections.

        This will scan path connections and link any adjacent elements together by replacing any None points or causing
        the start position of the next element to equal the end position of the previous. This should only be needed
        when combining paths and elements together. Close elements are always connected to the last Move element or to
        the end position of the first element in the list. The start element of the first segment may or may not be
        None.
        """
        zpoint = None
        last_segment = None
        for segment in self._segments:
            if zpoint is None or isinstance(segment, Move):
                zpoint = segment.end
            if last_segment is not None:
                if segment.start is None and last_segment.end is not None:
                    segment.start = Point(last_segment.end)
                elif last_segment.end is None and segment.start is not None:
                    last_segment.end = Point(segment.start)
                elif last_segment.end != segment.start:
                    segment.start = Point(last_segment.end)
            if isinstance(segment, Close) and zpoint is not None and segment.end != zpoint:
                segment.end = Point(zpoint)
            last_segment = segment

    @property
    def first_point(self):
        """First point along the Path. This is the start point of the first segment unless it starts
        with a Move command with a None start in which case first point is that Move's destination."""
        if len(self._segments) == 0:
            return None
        if self._segments[0].start is not None:
            return Point(self._segments[0].start)
        return Point(self._segments[0].end)

    @property
    def current_point(self):
        if len(self._segments) == 0:
            return None
        return Point(self._segments[-1].end)

    @property
    def z_point(self):
        """
        Z doesn't necessarily mean the first_point, it's the destination of the last Move.
        This behavior of Z is defined in svg spec:
        http://www.w3.org/TR/SVG/paths.html#PathDataClosePathCommand
        """
        end_pos = None
        for segment in reversed(self._segments):
            if isinstance(segment, Move):
                end_pos = segment.end
                break
        if end_pos is None:
            try:
                end_pos = self._segments[0].end
            except IndexError:
                pass  # entire path is "z".
        return end_pos

    @property
    def smooth_point(self):
        """Returns the smoothing control point for the smooth commands.
        With regards to the SVG standard if the last command was a curve the smooth
        control point is the reflection of the previous control point.

        If the last command was not a curve, the smooth_point is coincident with the current.
        https://www.w3.org/TR/SVG/paths.html#PathDataCubicBezierCommands
        """

        if len(self._segments) == 0:
            return None
        start_pos = self.current_point
        last_segment = self._segments[-1]
        if isinstance(last_segment, QuadraticBezier):
            previous_control = last_segment.control
            return previous_control.reflected_across(start_pos)
        elif isinstance(last_segment, CubicBezier):
            previous_control = last_segment.control2
            return previous_control.reflected_across(start_pos)
        return start_pos

    def start(self):
        pass

    def end(self):
        pass

    def move(self, *points):
        end_pos = points[0]
        start_pos = self.current_point
        self.append(Move(start_pos, end_pos))
        if len(points) > 1:
            self.line(*points[1:])

    def line(self, *points):
        start_pos = self.current_point
        end_pos = points[0]
        if end_pos == 'z':
            self.append(Line(start_pos, self.z_point))
            self.closed()
            return
        self.append(Line(start_pos, end_pos))
        if len(points) > 1:
            self.line(*points[1:])

    def absolute_v(self, *y_points):
        y_pos = y_points[0]
        start_pos = self.current_point
        self.append(Line(start_pos, Point(start_pos[0], y_pos)))
        if len(y_points) > 1:
            self.absolute_v(*y_points[1:])

    def relative_v(self, *dys):
        dy = dys[0]
        start_pos = self.current_point
        self.append(Line(start_pos, Point(start_pos[0], start_pos[1] + dy)))
        if len(dys) > 1:
            self.relative_v(*dys[1:])

    def absolute_h(self, *x_points):
        x_pos = x_points[0]
        start_pos = self.current_point
        self.append(Line(start_pos, Point(x_pos, start_pos[1])))
        if len(x_points) > 1:
            self.absolute_h(*x_points[1:])

    def relative_h(self, *dxs):
        dx = dxs[0]
        start_pos = self.current_point
        self.append(Line(start_pos, Point(start_pos[0] + dx, start_pos[1])))
        if len(dxs) > 1:
            self.relative_h(*dxs[1:])

    def smooth_quad(self, *points):
        """Smooth curve. First control point is the "reflection" of
           the second control point in the previous path."""
        start_pos = self.current_point
        control1 = self.smooth_point
        end_pos = points[0]
        if end_pos == 'z':
            self.append(QuadraticBezier(start_pos, control1, self.z_point))
            self.closed()
            return
        self.append(QuadraticBezier(start_pos, control1, end_pos))
        if len(points) > 1:
            self.smooth_quad(*points[1:])

    def quad(self, *points):
        start_pos = self.current_point
        control = points[0]
        if control == 'z':
            self.append(QuadraticBezier(start_pos, self.z_point, self.z_point))
            self.closed()
            return
        end_pos = points[1]
        if end_pos == 'z':
            self.append(QuadraticBezier(start_pos, control, self.z_point))
            self.closed()
            return
        self.append(QuadraticBezier(start_pos, control, end_pos))
        if len(points) > 2:
            self.quad(*points[2:])

    def smooth_cubic(self, *points):
        """Smooth curve. First control point is the "reflection" of
        the second control point in the previous path."""
        start_pos = self.current_point
        control1 = self.smooth_point
        control2 = points[0]
        if control2 == 'z':
            self.append(CubicBezier(start_pos, control1, self.z_point, self.z_point))
            self.closed()
            return
        end_pos = points[1]
        if end_pos == 'z':
            self.append(CubicBezier(start_pos, control1, control2, self.z_point))
            self.closed()
            return
        self.append(CubicBezier(start_pos, control1, control2, end_pos))
        if len(points) > 2:
            self.smooth_cubic(*points[2:])

    def cubic(self, *points):
        start_pos = self.current_point
        control1 = points[0]
        if control1 == 'z':
            self.append(CubicBezier(start_pos, self.z_point, self.z_point, self.z_point))
            self.closed()
            return
        control2 = points[1]
        if control2 == 'z':
            self.append(CubicBezier(start_pos, control1, self.z_point, self.z_point))
            self.closed()
            return
        end_pos = points[2]
        if end_pos == 'z':
            self.append(CubicBezier(start_pos, control1, control2, self.z_point))
            self.closed()
            return
        self.append(CubicBezier(start_pos, control1, control2, end_pos))
        if len(points) > 3:
            self.cubic(*points[3:])

    def arc(self, *arc_args):
        start_pos = self.current_point
        rx = arc_args[0]
        ry = arc_args[1]
        rotation = arc_args[2]
        arc = arc_args[3]
        sweep = arc_args[4]
        end_pos = arc_args[5]
        if end_pos == 'z':
            self.append(Arc(start_pos, rx, ry, rotation, arc, sweep, self.z_point))
            self.closed()
            return
        self.append(Arc(start_pos, rx, ry, rotation, arc, sweep, end_pos))
        if len(arc_args) > 6:
            self.arc(*arc_args[6:])

    def closed(self):
        start_pos = self.current_point
        end_pos = self.z_point
        self.append(Close(start_pos, end_pos))

    def _calc_lengths(self, error=ERROR, min_depth=MIN_DEPTH):
        if self._length is not None:
            return
        lengths = [each.length(error=error, min_depth=min_depth) for each in self._segments]
        self._length = sum(lengths)
        self._lengths = [each / self._length for each in lengths]

    def point(self, position, error=ERROR):
        if len(self._segments) == 0:
            return None
        # Shortcuts
        if position <= 0.0:
            return self._segments[0].point(position)
        if position >= 1.0:
            return self._segments[-1].point(position)

        self._calc_lengths(error=error)
        # Find which segment the point we search for is located on:
        segment_start = 0
        segment_pos = 0
        segment = self._segments[0]
        for index, segment in enumerate(self._segments):
            segment_end = segment_start + self._lengths[index]
            if segment_end >= position:
                # This is the segment! How far in on the segment is the point?
                segment_pos = (position - segment_start) / (segment_end - segment_start)
                break
            segment_start = segment_end
        return segment.point(segment_pos)

    def length(self, error=ERROR, min_depth=MIN_DEPTH):
        self._calc_lengths(error, min_depth)
        return self._length

    def plot(self):
        for segment in self._segments:
            for e in segment.plot():
                yield e

    def append(self, value):
        if isinstance(value, str):
            value = Path(value)
            if len(value) == 0:
                return
            if len(value) > 1:
                self.extend(value)
                return
            value = value[0]
        self._length = None
        index = len(self._segments) - 1
        self._segments.append(value)
        self._validate_connection(index)
        if isinstance(value, Close):
            self._validate_close(index + 1)

    def insert(self, index, value):
        if isinstance(value, str):
            value = Path(value)
            if len(value) == 0:
                return
            value = value[0]
        self._length = None
        self._segments.insert(index, value)
        self._validate_connection(index - 1)
        self._validate_connection(index)
        if isinstance(value, Move):
            self._validate_move(index)
        if isinstance(value, Close):
            self._validate_close(index)

    def extend(self, iterable):
        if isinstance(iterable, str):
            iterable = Path(iterable)
        self._length = None
        index = len(self._segments) - 1
        self._segments.extend(iterable)
        self._validate_connection(index)
        self._validate_subpath(index)

    def reverse(self):
        if len(self._segments) == 0:  # M 1,0 L 22,7 Q 17,17 91,2
            return
        prepoint = self._segments[0].start
        self._segments[0].start = None
        p = Path()
        subpaths = list(self.as_subpaths())
        for subpath in subpaths:
            subpath.reverse()
        for subpath in reversed(subpaths):
            p += subpath
        self._segments = p._segments
        self._segments[0].start = prepoint
        return self

    def subpath(self, index):
        subpaths = list(self.as_subpaths())
        return subpaths[index]

    def count_subpaths(self):
        subpaths = list(self.as_subpaths())
        return len(subpaths)

    def as_subpaths(self):
        last = 0
        for current, seg in enumerate(self):
            if current != last and isinstance(seg, Move):
                yield Subpath(self, last, current - 1)
                last = current
        yield Subpath(self, last, len(self) - 1)

    def as_points(self):
        """Returns the list of defining points within path"""
        for seg in self:
            for p in seg:
                if not isinstance(p, Point):
                    yield Point(p)
                else:
                    yield p

    def reify(self):
        """
        Realizes the transform to the shape properties.

        Path objects reify perfectly.
        """
        if isinstance(self.transform, Matrix):
            for e in self._segments:
                e *= self.transform
        self.transform.reset()
        return self

    @staticmethod
    def svg_d(segments, relative=False, transformed=True):
        if len(segments) == 0:
            return ''
        if relative:
            return Path.svg_d_relative(segments, transformed=transformed)
        else:
            return Path.svg_d_absolute(segments, transformed=transformed)

    @staticmethod
    def svg_d_relative(segments, transformed=True):
        parts = []
        previous_segment = None
        p = Point(0)
        for segment in segments:
            if isinstance(segment, (Move, Line, Arc, Close)):
                parts.append(segment.d(p))
            elif isinstance(segment, (CubicBezier, QuadraticBezier)):
                parts.append(segment.d(p, smooth=segment.is_smooth_from(previous_segment)))
            previous_segment = segment
            p = previous_segment.end
        return ' '.join(parts)

    @staticmethod
    def svg_d_absolute(segments, transformed=True):
        parts = []
        previous_segment = None
        for segment in segments:
            if isinstance(segment, (Move, Line, Arc, Close)):
                parts.append(segment.d())
            elif isinstance(segment, (CubicBezier, QuadraticBezier)):
                parts.append(segment.d(smooth=segment.is_smooth_from(previous_segment)))
            previous_segment = segment
        return ' '.join(parts)

    def d(self, relative=False, transformed=True):
        if transformed:
            p = self.__copy__()
            p.reify()
            return Path.svg_d(p._segments, relative)
        else:
            return Path.svg_d(self._segments, relative)

    def segments(self, transformed=True):
        if transformed:
            return [s * self.transform for s in self._segments]
        return self._segments


class Rect(Shape):
    """
    SVG Rect shapes are defined in SVG2 10.2
    https://www.w3.org/TR/SVG2/shapes.html#RectElement

    These have geometric properties x, y, width, height, rx, ry
    Geometric properties can be Length values.

    Rect(x, y, width, height)
    Rect(x, y, width, height, rx, ry)
    Rect(x, y, width, height, rx, ry, matrix)
    Rect(x, y, width, height, rx, ry, matrix, stroke, fill)

    Rect(dict): dictionary values read from svg.

    """

    def __init__(self, *args, **kwargs):
        Shape.__init__(self, *args, **kwargs)
        arg_length = len(args)

        if arg_length == 1:
            if isinstance(args[0], dict):
                values = args[0]
                self.x = Length(values.get(SVG_ATTR_X, 0)).value()
                self.y = Length(values.get(SVG_ATTR_Y, 0)).value()
                self.width = Length(values.get(SVG_ATTR_WIDTH, 1)).value()
                self.height = Length(values.get(SVG_ATTR_HEIGHT, 1)).value()
                self.rx = Length(values.get(SVG_ATTR_RADIUS_X, None)).value()
                self.ry = Length(values.get(SVG_ATTR_RADIUS_Y, None)).value()
                self._validate_rect()
                return
            elif isinstance(args[0], Rect):
                s = args[0]
                self.x = s.x
                self.y = s.y
                self.width = s.width
                self.height = s.height
                self.rx = s.rx
                self.ry = s.ry
                self._validate_rect()
                return
        if arg_length >= 1:
            self.x = Length(args[0]).value()
        elif 'x' in kwargs:
            self.x = Length(kwargs['x']).value()
        else:
            self.x = 0.0

        if arg_length >= 2:
            self.y = Length(args[1]).value()
        elif 'y' in kwargs:
            self.y = Length(kwargs['y']).value()
        else:
            self.y = 0.0

        if arg_length >= 3:
            self.width = Length(args[2]).value()
        elif 'width' in kwargs:
            self.width = Length(kwargs['width']).value()
        else:
            self.width = 1.0

        if arg_length >= 4:
            self.height = Length(args[3]).value()
        elif 'height' in kwargs:
            self.height = Length(kwargs['height']).value()
        else:
            self.height = 1.0

        if arg_length >= 5:
            self.rx = Length(args[4]).value()
        elif 'rx' in kwargs:
            self.rx = Length(kwargs['rx']).value()
        else:
            self.rx = 0.0

        if arg_length >= 6:
            self.ry = Length(args[5]).value()
        elif 'ry' in kwargs:
            self.ry = Length(kwargs['ry']).value()
        else:
            self.ry = 0.0
        self._init_shape(*args[6:])
        self._validate_rect()

    def _validate_rect(self):
        """None is 'auto' for values."""
        rx = self.rx
        ry = self.ry
        if rx is None and ry is None:
            rx = ry = 0
        if rx is not None and ry is None:
            rx = Length(rx).value(relative_length=self.width)
            ry = rx
        elif ry is not None and rx is None:
            ry = Length(ry).value(relative_length=self.height)
            rx = ry
        elif rx is not None and ry is not None:
            rx = Length(rx).value(relative_length=self.width)
            ry = Length(ry).value(relative_length=self.height)
        if rx == 0 or ry == 0:
            rx = ry = 0
        else:
            rx = min(rx, self.width / 2.0)
            ry = min(ry, self.height / 2.0)
        self.rx = rx
        self.ry = ry

    def __repr__(self):
        values = []
        if self.x != 0:
            values.append('x=%s' % Length.str(self.x))
        if self.y != 0:
            values.append('y=%s' % Length.str(self.y))
        if self.width != 0:
            values.append('width=%s' % Length.str(self.width))
        if self.height != 0:
            values.append('height=%s' % Length.str(self.height))
        if self.rx != 0:
            values.append('rx=%s' % Length.str(self.rx))
        if self.ry != 0:
            values.append('ry=%s' % Length.str(self.ry))
        self._repr_shape(values)
        params = ", ".join(values)
        return "Rect(%s)" % params

    def __copy__(self):
        return Rect(self.x, self.y, self.width, self.height, self.rx, self.ry,
                    transform=Matrix(self.transform), stroke=Color(self.stroke), fill=Color(self.fill),
                    apply=self.apply, id=self.id)

    @property
    def implicit_position(self):
        if not self.apply:
            return Point(self.x, self.y)
        point = Point(self.x, self.y)
        point *= self.transform
        return point

    @property
    def implicit_x(self):
        if not self.apply:
            return self.x
        return self.implicit_position[0]

    @property
    def implicit_y(self):
        if not self.apply:
            return self.y
        return self.implicit_position[1]

    @property
    def implicit_width(self):
        if not self.apply:
            return self.width
        p = Point(self.width, 0)
        p *= self.transform
        origin = Point(0, 0)
        origin *= self.transform
        return origin.distance_to(p)

    @property
    def implicit_height(self):
        if not self.apply:
            return self.height
        p = Point(0, self.height)
        p *= self.transform
        origin = Point(0, 0)
        origin *= self.transform
        return origin.distance_to(p)

    @property
    def implicit_rx(self):
        if not self.apply:
            return self.rx
        p = Point(self.rx, 0)
        p *= self.transform
        origin = Point(0, 0)
        origin *= self.transform
        return origin.distance_to(p)

    @property
    def implicit_ry(self):
        if not self.apply:
            return self.ry
        p = Point(0, self.ry)
        p *= self.transform
        origin = Point(0, 0)
        origin *= self.transform
        return origin.distance_to(p)

    def segments(self, transformed=True):
        """
        Rect decomposition is given in SVG 2.0 10.2

        Rect:
        * perform an absolute moveto operation to location (x,y);
        * perform an absolute horizontal lineto with parameter x+width;
        * perform an absolute vertical lineto parameter y+height;
        * perform an absolute horizontal lineto parameter x;
        * ( close the path)

        Rounded Rect:
        rx and ry are used as the equivalent parameters to the elliptical arc command,
        the x-axis-rotation and large-arc-flag are set to zero, the sweep-flag is set to one

        * perform an absolute moveto operation to location (x+rx,y);
        * perform an absolute horizontal lineto with parameter x+width-rx;
        * perform an absolute elliptical arc operation to coordinate (x+width,y+ry)
        * perform an absolute vertical lineto parameter y+height-ry;
        * perform an absolute elliptical arc operation to coordinate (x+width-rx,y+height)
        * perform an absolute horizontal lineto parameter x+rx;
        * perform an absolute elliptical arc operation to coordinate (x,y+height-ry)
        * perform an absolute vertical lineto parameter y+ry
        * perform an absolute elliptical arc operation with a segment-completing close path operation

        :param transformed: provide the reified version.
        :return: path_d of shape.
        """
        x = self.x
        y = self.y
        width = self.width
        height = self.height
        if width == 0 or height == 0:
            return ''  # a computed value of zero for either dimension disables rendering.
        rx = self.rx
        ry = self.ry
        if rx == ry == 0:
            segments = (Move(None, (x, y)),
                        Line((x, y), (x + width, y)),
                        Line((x + width, y), (x + width, y + height)),
                        Line((x + width, y + height), (x, y + height)),
                        Close((x, y + height), (x, y)))
        else:
            segments = (Move(None, (x + rx, y)),
                        Line((x + rx, y), (x + width - rx, y)),
                        Arc((x + width - rx, y), (x + width, y + ry), rx=rx, ry=ry),
                        Line((x + width, y + ry), (x + width, y + height - ry)),
                        Arc((x + width, y + height - ry), (x + width - rx, y + height), rx=rx, ry=ry),
                        Line((x + width - rx, y + height), (x + rx, y + height)),
                        Arc((x + rx, y + height), (x, y + height - ry), rx=rx, ry=ry),
                        Line((x, y + height - ry), (x, y + ry)),
                        Arc((x, y + ry), (x + rx, y), rx=rx, ry=ry),
                        Close((x + rx, y), (x + rx, y)))
        if not transformed or self.transform.is_identity():
            return segments
        else:
            return [s * self.transform for s in segments]

    def reify(self):
        """
        Realizes the transform to the shape properties.

        If the realized shape can be properly represented as a rectangle with an identity matrix
        it will be, otherwise the properties will approximate the implied values.

        Skewed and Rotated rectangles cannot be reified.
        """
        scale_x = self.transform.value_scale_x()
        scale_y = self.transform.value_scale_y()
        translate_x = self.transform.value_trans_x()
        translate_y = self.transform.value_trans_y()
        if self.transform.value_skew_x() == 0 and self.transform.value_skew_y() == 0 \
                and scale_x != 0 and scale_y != 0:
            self.x *= scale_x
            self.y *= scale_y
            self.x += translate_x
            self.y += translate_y
            self.transform *= Matrix.translate(-translate_x, -translate_y)
            self.rx = scale_x * self.rx
            self.ry = scale_y * self.ry
            self.width = scale_x * self.width
            self.height = scale_y * self.height
            self.transform *= Matrix.scale(1.0 / scale_x, 1.0 / scale_y)
        return self

    def render(self, width=None, height=None, relative_length=None, **kwargs):
        if width is None and relative_length is not None:
            width = relative_length
        if height is None and relative_length is not None:
            height = relative_length
        Shape.render(self, width=width, height=height, relative_length=relative_length, **kwargs)
        if isinstance(self.x, Length):
            self.x = self.x.value(relative_length=width, **kwargs)
        if isinstance(self.y, Length):
            self.y = self.y.value(relative_length=height, **kwargs)
        if isinstance(self.width, Length):
            self.width = self.width.value(relative_length=width, **kwargs)
        if isinstance(self.height, Length):
            self.height = self.height.value(relative_length=height, **kwargs)
        if isinstance(self.rx, Length):
            self.rx = self.rx.value(relative_length=width, **kwargs)
        if isinstance(self.ry, Length):
            self.ry = self.ry.value(relative_length=height, **kwargs)
        return self


class _RoundShape(Shape):

    def __init__(self, *args, **kwargs):
        Shape.__init__(self, *args, **kwargs)
        arg_length = len(args)

        if arg_length == 1:
            if isinstance(args[0], dict):
                ellipse = args[0]
                cx = Length(ellipse.get(SVG_ATTR_CENTER_X, None)).value()
                cy = Length(ellipse.get(SVG_ATTR_CENTER_Y, None)).value()
                rx = Length(ellipse.get(SVG_ATTR_RADIUS_X, None)).value()
                ry = Length(ellipse.get(SVG_ATTR_RADIUS_Y, None)).value()
                r = Length(ellipse.get(SVG_ATTR_RADIUS, None)).value()
                if r is not None:
                    self.rx = self.ry = r
                else:
                    if rx is None:
                        self.rx = 1
                    else:
                        self.rx = rx
                    if ry is None:
                        self.ry = 1
                    else:
                        self.ry = ry
                if cx is None:
                    cx = 0
                if cy is None:
                    cy = 0
                self.cx = cx
                self.cy = cy
                return
            elif isinstance(args[0], _RoundShape):
                s = args[0]
                self.cx = s.cx
                self.cy = s.cy
                self.rx = s.rx
                self.ry = s.ry
                return
        if 'center' in kwargs:
            center = Point(kwargs['center'])
            cx = center[0]
            cy = center[1]
        else:
            cx = 0
            cy = 0
        if arg_length >= 1:
            self.cx = Length(args[0]).value()
        elif 'cx' in kwargs:
            self.cx = Length(kwargs['cx']).value()
        else:
            self.cx = cx
        if arg_length >= 2:
            self.cy = Length(args[1]).value()
        elif 'cx' in kwargs:
            self.cy = Length(kwargs['cy']).value()
        else:
            self.cy = cy
        if arg_length >= 3:
            self.rx = Length(args[2]).value()
        elif 'rx' in kwargs:
            self.rx = Length(kwargs['rx']).value()
        elif 'r' in kwargs:
            self.rx = Length(kwargs['r']).value()
        else:
            self.rx = 1.0
        if arg_length >= 4:
            self.ry = Length(args[3]).value()
        elif 'ry' in kwargs:
            self.ry = Length(kwargs['ry']).value()
        elif 'r' in kwargs:
            self.ry = Length(kwargs['r']).value()
        else:
            self.ry = self.rx
        self._init_shape(*args[4:])

    def __repr__(self):
        values = []
        if self.cx is not None:
            values.append('cx=%s' % Length.str(self.cx))
        if self.cy is not None:
            values.append('cy=%s' % Length.str(self.cy))
        if self.rx == self.ry:
            values.append('r=%s' % Length.str(self.rx))
        else:
            if self.rx != 0:
                values.append('rx=%s' % Length.str(self.rx))
            if self.ry != 0:
                values.append('ry=%s' % Length.str(self.ry))
        self._repr_shape(values)
        params = ", ".join(values)
        name = self._name()
        return "%s(%s)" % (name, params)

    @property
    def implicit_rx(self):
        if not self.apply:
            return self.rx
        prx = Point(self.rx, 0)
        prx *= self.transform
        origin = Point(0, 0)
        origin *= self.transform
        return origin.distance_to(prx)

    @property
    def implicit_ry(self):
        if not self.apply:
            return self.ry
        pry = Point(0, self.ry)
        pry *= self.transform
        origin = Point(0, 0)
        origin *= self.transform
        return origin.distance_to(pry)

    implicit_r = implicit_rx

    @property
    def implicit_center(self):
        center = Point(self.cx, self.cy)
        if not self.apply:
            return center
        center *= self.transform
        return center

    def segments(self, transformed=True):
        """
        SVG path decomposition is given in SVG 2.0 10.3, 10.4.

        A move-to command to the point cx+rx,cy;
        arc to cx,cy+ry;
        arc to cx-rx,cy;
        arc to cx,cy-ry;
        arc with a segment-completing close path operation.

        Converts the parameters from an ellipse or a circle to a string for a
        Path object d-attribute"""
        original = self.apply
        self.apply = transformed
        path = Path()
        steps = 4
        step_size = tau / steps
        t_start = 0
        t_end = step_size
        path.move((self.point_at_t(0)))
        for i in range(steps):
            path += Arc(
                self.point_at_t(t_start),
                self.point_at_t(t_end),
                self.implicit_center,
                rx=self.implicit_rx, ry=self.implicit_ry, rotation=self.rotation, sweep=step_size)
            t_start = t_end
            t_end += step_size
        path.closed()
        self.apply = original
        return path.segments(transformed)

    def reify(self):
        """
        Realizes the transform to the shape properties.

        Skewed and Rotated roundshapes cannot be reified.
        """
        scale_x = self.transform.value_scale_x()
        scale_y = self.transform.value_scale_y()
        translate_x = self.transform.value_trans_x()
        translate_y = self.transform.value_trans_y()
        if self.transform.value_skew_x() == 0 and self.transform.value_skew_y() == 0 \
                and scale_x != 0 and scale_y != 0:
            self.cx *= scale_x
            self.cy *= scale_y
            self.cx += translate_x
            self.cy += translate_y
            self.transform *= Matrix.translate(-translate_x, -translate_y)
            self.rx = scale_x * self.rx
            self.ry = scale_y * self.ry
            self.transform *= Matrix.scale(1.0 / scale_x, 1.0 / scale_y)
        return self

    def render(self, width=None, height=None, relative_length=None, **kwargs):
        if width is None and relative_length is not None:
            width = relative_length
        if height is None and relative_length is not None:
            height = relative_length
        Shape.render(self, width=width, height=height, relative_length=relative_length, **kwargs)
        if isinstance(self.cx, Length):
            self.cx = self.cx.value(relative_length=width, **kwargs)
        if isinstance(self.cy, Length):
            self.cy = self.cy.value(relative_length=height, **kwargs)
        if isinstance(self.rx, Length):
            self.rx = self.rx.value(relative_length=width, **kwargs)
        if isinstance(self.ry, Length):
            self.ry = self.ry.value(relative_length=height, **kwargs)
        return self

    def unit_matrix(self):
        """
        return the unit matrix which could would transform the unit circle into this ellipse.

        One of the valid parameterizations for ellipses is that they are all affine transforms of the unit circle.
        This provides exactly such a matrix.

        :return: matrix
        """
        m = Matrix()
        m.post_scale(self.implicit_rx, self.implicit_ry)
        m.post_rotate(self.rotation)
        center = self.implicit_center
        m.post_translate(center[0], center[1])
        return m

    def arc_t(self, t0, t1):
        """
        return the arc found between the given values of t on the ellipse.

        :param t0: t start
        :param t1: t end
        :return: arc
        """
        return Arc(self.point_at_t(t0),
                   self.point_at_t(t1),
                   self.implicit_center,
                   rx=self.implicit_rx, ry=self.implicit_ry, rotation=self.rotation, sweep=t1 - t0)

    def arc_angle(self, a0, a1):
        """
        return the arc found between the given angles on the ellipse.

        :param a0: start angle
        :param a1: end angle
        :return: arc
        """
        return Arc(self.point_at_angle(a0),
                   self.point_at_angle(a1),
                   self.implicit_center,
                   rx=self.implicit_rx, ry=self.implicit_ry,
                   rotation=self.rotation, ccw=a0 > a1)

    def point_at_angle(self, angle):
        """
        find the point on the ellipse from the center at the given angle.
        Note: For non-circular arcs this is different than point(t).

        :param angle: angle from center to find point
        :return: point found
        """
        a = self.implicit_rx
        b = self.implicit_ry
        if a == b:
            return self.point_at_t(angle)
        angle -= self.rotation
        if abs(angle) > tau / 4:
            t = atan2(a * tan(angle), b) + tau / 2
        else:
            t = atan2(a * tan(angle), b)
        return self.point_at_t(t)

    def angle_at_point(self, p):
        """
        find the angle to the point.

        :param p: point
        :return: angle to given point.
        """
        if self.apply and not self.transform.is_identity():
            return self.implicit_center.angle_to(p)
        else:
            center = Point(self.cx, self.cy)
            return center.angle_to(p)

    def t_at_point(self, p):
        """
        find the t parameter to at the point.

        :param p: point
        :return: t parameter to the given point.
        """
        angle = self.angle_at_point(p)
        angle -= self.rotation
        a = self.implicit_rx
        b = self.implicit_ry
        if abs(angle) > tau / 4:
            return atan2(a * tan(angle), b) + tau / 2
        else:
            return atan2(a * tan(angle), b)

    def point_at_t(self, t):
        """
        find the point that corresponds to given value t.
        Where t=0 is the first point and t=tau is the final point.

        In the case of a circle: t = angle.

        :param t:
        :return:
        """
        rotation = self.rotation
        a = self.implicit_rx
        b = self.implicit_ry
        center = self.implicit_center
        cx = center[0]
        cy = center[1]
        cosTheta = cos(rotation)
        sinTheta = sin(rotation)
        cosT = cos(t)
        sinT = sin(t)
        px = cx + a * cosT * cosTheta - b * sinT * sinTheta
        py = cy + a * cosT * sinTheta + b * sinT * cosTheta
        return Point(px, py)

    def point(self, position):
        """
        find the point that corresponds to given value [0,1].
        Where t=0 is the first point and t=1 is the final point.

        :param position:
        :return: point at t
        """
        return self.point_at_t(tau * position)


class Ellipse(_RoundShape):
    """
    SVG Ellipse shapes are defined in SVG2 10.4
    https://www.w3.org/TR/SVG2/shapes.html#EllipseElement

    These have geometric properties cx, cy, rx, ry
    """

    def __init__(self, *args, **kwargs):
        _RoundShape.__init__(self, *args, **kwargs)

    def __copy__(self):
        return Ellipse(self.cx, self.cy, self.rx, self.ry,
                       transform=Matrix(self.transform), stroke=Color(self.stroke), fill=Color(self.fill),
                       apply=self.apply, id=self.id)

    def _name(self):
        return self.__class__.__name__


class Circle(_RoundShape):
    """
    SVG Circle shapes are defined in SVG2 10.3
    https://www.w3.org/TR/SVG2/shapes.html#CircleElement

    These have geometric properties cx, cy, r
    """

    def __init__(self, *args, **kwargs):
        _RoundShape.__init__(self, *args, **kwargs)

    def __copy__(self):
        return Circle(self.cx, self.cy, self.rx, self.ry,
                      transform=Matrix(self.transform), stroke=Color(self.stroke), fill=Color(self.fill),
                      apply=self.apply, id=self.id)

    def _name(self):
        return self.__class__.__name__


class SimpleLine(Shape):
    """
    SVG Line shapes are defined in SVG2 10.5
    https://www.w3.org/TR/SVG2/shapes.html#LineElement

    These have geometric properties x1, y1, x2, y2

    These are called Line in SVG but that name is already used for Line(PathSegment)
    """

    def __init__(self, *args, **kwargs):
        Shape.__init__(self, *args, **kwargs)
        arg_length = len(args)
        if arg_length == 1:
            if isinstance(args[0], dict):
                values = args[0]
                self.x1 = Length(values.get(SVG_ATTR_X1, 0)).value()
                self.y1 = Length(values.get(SVG_ATTR_Y1, 0)).value()
                self.x2 = Length(values.get(SVG_ATTR_X2, 0)).value()
                self.y2 = Length(values.get(SVG_ATTR_Y2, 0)).value()
            elif isinstance(args[0], SimpleLine):
                s = args[0]
                self.x1 = s.x1
                self.y1 = s.y1
                self.x2 = s.x2
                self.y2 = s.y2
            return
        if arg_length >= 1:
            self.x1 = Length(args[0]).value()
        elif SVG_ATTR_X1 in kwargs:
            self.x1 = Length(kwargs[SVG_ATTR_X1]).value()
        else:
            self.x1 = 0.0

        if arg_length >= 2:
            self.y1 = Length(args[1]).value()
        elif SVG_ATTR_Y1 in kwargs:
            self.y1 = Length(kwargs[SVG_ATTR_Y1]).value()
        else:
            self.y1 = 0.0

        if arg_length >= 3:
            self.x2 = Length(args[2]).value()
        elif SVG_ATTR_X2 in kwargs:
            self.x2 = Length(kwargs[SVG_ATTR_X2]).value()
        else:
            self.x2 = 0.0

        if arg_length >= 4:
            self.y2 = Length(args[3]).value()
        elif SVG_ATTR_Y2 in kwargs:
            self.y2 = Length(kwargs[SVG_ATTR_Y2]).value()
        else:
            self.y2 = 0.0

        self._init_shape(*args[4:])

    def __repr__(self):
        values = []
        if self.x1 is not None:
            values.append('x1=%s' % repr(self.x1))
        if self.y1 is not None:
            values.append('y1=%s' % repr(self.y1))
        if self.x2 is not None:
            values.append('x2=%s' % repr(self.x2))
        if self.y2 is not None:
            values.append('y2=%s' % repr(self.y2))
        self._repr_shape(values)
        params = ", ".join(values)
        return "SimpleLine(%s)" % params

    def __copy__(self):
        return SimpleLine(self.x1, self.y1, self.x2, self.y2,
                          transform=Matrix(self.transform), stroke=Color(self.stroke), fill=Color(self.fill),
                          apply=self.apply, id=self.id)

    @property
    def implicit_x1(self):
        point = Point(self.x1, self.y1)
        point *= self.transform
        return point[0]

    @property
    def implicit_y1(self):
        point = Point(self.x1, self.y1)
        point *= self.transform
        return point[1]

    @property
    def implicit_x2(self):
        point = Point(self.x2, self.y2)
        point *= self.transform
        return point[0]

    @property
    def implicit_y2(self):
        point = Point(self.x2, self.y2)
        point *= self.transform
        return point[1]

    def segments(self, transformed=True):
        """
        SVG path decomposition is given in SVG 2.0 10.5.

        perform an absolute moveto operation to absolute location (x1,y1)
        perform an absolute lineto operation to absolute location (x2,y2)

        :returns Path_d path for line.
        """

        start = Point(self.x1, self.y1)
        end = Point(self.x2, self.y2)
        if transformed:
            start *= self.transform
            end *= self.transform
        return (Move(None, start), Line(start, end))

    def reify(self):
        """
        Realizes the transform to the shape properties.

        SimpleLines are perfectly reified.
        """
        matrix = self.transform
        p = Point(self.x1, self.y1)
        p *= matrix
        self.x1 = p[0]
        self.y1 = p[1]

        p = Point(self.x2, self.y2)
        p *= matrix
        self.x2 = p[0]
        self.y2 = p[1]

        matrix.reset()
        return self

    def render(self, width=None, height=None, relative_length=None, **kwargs):
        if width is None and relative_length is not None:
            width = relative_length
        if height is None and relative_length is not None:
            height = relative_length
        Shape.render(self, width=width, height=height, relative_length=relative_length, **kwargs)
        if isinstance(self.x1, Length):
            self.x1 = self.x1.value(relative_length=width, **kwargs)
        if isinstance(self.y1, Length):
            self.y1 = self.y1.value(relative_length=height, **kwargs)
        if isinstance(self.x2, Length):
            self.x2 = self.x2.value(relative_length=width, **kwargs)
        if isinstance(self.y2, Length):
            self.y2 = self.y2.value(relative_length=height, **kwargs)
        return self


class _Polyshape(Shape):
    """Base form of Polygon and Polyline since the objects are nearly the same."""

    def __init__(self, *args, **kwargs):
        Shape.__init__(self, *args, **kwargs)
        arg_length = len(args)
        if arg_length == 0:
            self._init_points(kwargs)
        else:
            if isinstance(args[0], dict):
                self._init_points(args[0])
            elif isinstance(args[0], Polyline):
                s = args[0]
                self._init_points(s.points)
            elif isinstance(args[0], (float, int, list, tuple, Point, str, complex)):
                self._init_points(args)
            else:
                self.points = list()

    def _init_points(self, points):
        if points is None:
            self.points = list()
            return
        if isinstance(points, (dict)):
            if SVG_ATTR_POINTS in points:
                points = points[SVG_ATTR_POINTS]
            else:
                self.points = list()
                return
        try:
            if len(points) == 1:
                points = points[0]
        except TypeError:
            pass
        if isinstance(points, (str)):
            findall = REGEX_COORD_PAIR.findall(points)
            self.points = [Point(float(j), float(k)) for j, k in findall]
        elif isinstance(points, (list, tuple)):
            if len(points) == 0:
                self.points = list()
            else:
                first_point = points[0]
                if isinstance(first_point, (float, int)):
                    self.points = list(map(Point, zip(*[iter(points)] * 2)))
                elif isinstance(first_point, (list, tuple, complex, str, Point)):
                    self.points = list(map(Point, points))
        else:
            self.points = list()

    def __repr__(self):
        values = []
        if self.points is not None:
            s = ", ".join(map(str, self.points))
            values.append('points=(%s)' % repr(s))
        self._repr_shape(values)
        params = ", ".join(values)
        name = self._name()
        return "%s(%s)" % (name, params)

    def __len__(self):
        return len(self.points)

    def __getitem__(self, item):
        return self.points[item]

    def segments(self, transformed=True):
        """
        Polyline and Polygon decomposition is given in SVG2. 10.6 and 10.7

        * perform an absolute moveto operation to the first coordinate pair in the list of points
        * for each subsequent coordinate pair, perform an absolute lineto operation to that coordinate pair.
        * (Polygon-only) perform a closepath command

        Note:  For a polygon/polyline made from n points, the resulting path will
        be composed of n lines (even if some of these lines have length zero).
        """
        if self.transform.is_identity() or not transformed:
            points = self.points
        else:
            points = list(map(self.transform.point_in_matrix_space, self.points))
        if len(points) == 0:
            return []
        segments = [Move(None, points[0])]
        last = points[0]
        for i in range(1, len(points)):
            current = points[i]
            segments.append(Line(last, current))
            last = current
        if isinstance(self, Polygon):
            segments.append(Close(last, points[0]))
        return segments

    def reify(self):
        """
        Realizes the transform to the shape properties.

        Polyshapes are perfectly reified.
        """
        matrix = self.transform
        for p in self:
            p *= matrix
        matrix.reset()
        return self


class Polyline(_Polyshape):
    """
    SVG Polyline shapes are defined in SVG2 10.6
    https://www.w3.org/TR/SVG2/shapes.html#PolylineElement

    These have geometric properties points
    """

    def __init__(self, *args, **kwargs):
        _Polyshape.__init__(self, *args, **kwargs)

    def __copy__(self):
        return Polyline(*self.points,
                        transform=Matrix(self.transform), stroke=Color(self.stroke), fill=Color(self.fill),
                        apply=self.apply, id=self.id)

    def _name(self):
        return self.__class__.__name__


class Polygon(_Polyshape):
    """
    SVG Polygon shapes are defined in SVG2 10.7
    https://www.w3.org/TR/SVG2/shapes.html#PolygonElement

    These have geometric properties points
    """

    def __init__(self, *args, **kwargs):
        _Polyshape.__init__(self, *args, **kwargs)

    def __copy__(self):
        return Polygon(*self.points,
                       transform=Matrix(self.transform), stroke=Color(self.stroke), fill=Color(self.fill),
                       apply=self.apply, id=self.id)

    def _name(self):
        return self.__class__.__name__


class Subpath:
    """
    Subpath is a Path-backed window implementation. It does not store a list of segments but rather
    stores a Path, start position, end position. When a function is called on a subpath, the result of
    those events is performed on the backing Path. When the backing Path is modified the behavior is
     undefined."""

    def __init__(self, path, start, end):
        self._path = path
        self._start = start
        self._end = end

    def __copy__(self):
        p = Path()
        for seg in self._path:
            p.append(copy(seg))
        return p

    def __getitem__(self, index):
        return self._path[self.index_to_path_index(index)]

    def __setitem__(self, index, value):
        self._path[self.index_to_path_index(index)] = value

    def __delitem__(self, index):
        del self._path[self.index_to_path_index(index)]
        self._end -= 1

    def __iadd__(self, other):
        if isinstance(other, str):
            p = Path(other)
            self._path[self._end:self._end] = p
        elif isinstance(other, Path):
            p = copy(other)
            self._path[self._end:self._end] = p
        elif isinstance(other, PathSegment):
            self._path.insert(self._end, other)
        else:
            return NotImplemented
        return self

    def __add__(self, other):
        n = copy(self)
        n += other
        return n

    def __radd__(self, other):
        if isinstance(other, str):
            path = Path(other)
            path.extend(map(copy, self._path))
            return path
        elif isinstance(other, PathSegment):
            path = Path(self)
            path.insert(0, other)
            return path
        else:
            return NotImplemented

    def __imul__(self, other):
        if isinstance(other, str):
            other = Matrix(other)
        if isinstance(other, Matrix):
            for e in self:
                e *= other
        return self

    def __mul__(self, other):
        if isinstance(other, (Matrix, str)):
            n = copy(self)
            n *= other
            return n

    __rmul__ = __mul__

    def __iter__(self):
        class Iterator:
            def __init__(self, subpath):
                self.n = subpath._start - 1
                self.subpath = subpath

            def __next__(self):
                self.n += 1
                try:
                    if self.n > self.subpath._end:
                        raise StopIteration
                    return self.subpath._path[self.n]
                except IndexError:
                    raise StopIteration

            next = __next__

        return Iterator(self)

    def __len__(self):
        return self._end - self._start + 1

    def __str__(self):
        return self.d()

    def __repr__(self):
        return 'Path(%s)' % (', '.join(repr(x) for x in self))

    def __eq__(self, other):
        if isinstance(other, str):
            return self.__eq__(Path(other))
        if not isinstance(other, (Path, Subpath)):
            return NotImplemented
        if len(self) != len(other):
            return False
        for s, o in zip(self, other):
            if not s == o:
                return False
        return True

    def __ne__(self, other):
        if not isinstance(other, (Path, Subpath, str)):
            return NotImplemented
        return not self == other

    def segments(self, transformed=True):
        path = self._path
        if transformed:
            return [s * path.transform for s in path._segments[self._start:self._end + 1]]
        return path._segments[self._start:self._end + 1]

    def index_to_path_index(self, index):
        if index < 0:
            return self._end + index + 1
        else:
            return self._start + index

    def bbox(self):
        """returns a bounding box for the input Path"""
        segments = self._path._segments[self._start:self._end + 1]
        bbs = [seg.bbox() for seg in segments if not isinstance(Close, Move)]
        try:
            xmins, ymins, xmaxs, ymaxs = list(zip(*bbs))
        except ValueError:
            return None  # No bounding box items existed. So no bounding box.
        xmin = min(xmins)
        xmax = max(xmaxs)
        ymin = min(ymins)
        ymax = max(ymaxs)
        return xmin, ymin, xmax, ymax

    def d(self, relative=False):
        segments = self._path._segments[self._start:self._end + 1]
        return Path.svg_d(segments, relative)

    def _reverse_segments(self, start, end):
        """Reverses segments between the given indexes in the subpath space."""
        segments = self._path._segments  # must avoid path validation.
        start = self.index_to_path_index(start)
        end = self.index_to_path_index(end)
        while start <= end:
            start_segment = segments[start]
            end_segment = segments[end]
            start_segment.reverse()
            if start_segment is not end_segment:
                end_segment.reverse()
                segments[start] = end_segment
                segments[end] = start_segment
            start += 1
            end -= 1
        start = self.index_to_path_index(start)
        end = self.index_to_path_index(end)
        self._path._validate_connection(start - 1)
        self._path._validate_connection(end)

    def reverse(self):
        size = len(self)
        if size == 0:
            return
        start = 0
        end = size - 1
        if isinstance(self[-1], Close):
            end -= 1
        if isinstance(self[0], Move):  # Move remains in place but references next element.
            start += 1
        self._reverse_segments(start, end)
        if size > 1:
            if isinstance(self[0], Move):
                self[0].end = Point(self[1].start)
        last = self[-1]
        if isinstance(last, Close):
            last.reverse()
            if last.start != self[-2].end:
                last.start = Point(self[-2].end)
            if last.end != self[0].end:
                last.end = Point(self[0].end)
        return self


class SVGText(GraphicObject, Transformable):
    """
    SVG Text are defined in SVG 2.0 Chapter 11

    No methods are implemented to perform a text to path conversion.
    However, if such a method exists the assumption is that the results will be
    placed in the path attribute, and functions like bbox() will check if such
    a value exists.
    """

    def __init__(self, *args, **kwargs):
        Transformable.__init__(self, *args, **kwargs)
        GraphicObject.__init__(self, *args, **kwargs)
        self.text = ''
        self.x = 0
        self.y = 0
        self.dx = 0
        self.dy = 0
        self.font = 0
        if len(args) == 1:
            if isinstance(args[0], dict):
                values = args[0]
                self.text = values.get(SVG_TAG_TEXT, self.text)
                self.font = values.get(SVG_ATTR_FONT, self.font)
                self.x = Length(values.get(SVG_ATTR_X, self.x)).value()
                self.y = Length(values.get(SVG_ATTR_Y, self.y)).value()
                self.dx = Length(values.get(SVG_ATTR_DX, self.dx)).value()
                self.dy = Length(values.get(SVG_ATTR_DY, self.dy)).value()
            elif isinstance(args[0], SVGText):
                s = args[0]
                self.text = s.text
                self.x = s.x
                self.y = s.y
                self.dx = s.dx
                self.dy = s.dy
                self.font = s.font
                return
        values = kwargs
        self.text = values.get(SVG_TAG_TEXT, self.text)
        self.font = values.get(SVG_ATTR_FONT, self.font)
        self.x = Length(values.get(SVG_ATTR_X, self.x)).value()
        self.y = Length(values.get(SVG_ATTR_Y, self.y)).value()
        self.dx = Length(values.get(SVG_ATTR_DX, self.dx)).value()
        self.dy = Length(values.get(SVG_ATTR_DY, self.dy)).value()
        self.path = None

    def _set_values_by_dict(self, values):
        if SVG_TAG_TEXT in values:
            self.text = values[SVG_TAG_TEXT]
        else:
            self.text = ''
        if SVG_ATTR_FONT in values:
            self.font = values[SVG_ATTR_FONT]
        else:
            self.font = None
        if SVG_ATTR_X in values:
            self.x = Length(values[SVG_ATTR_X]).value()
        else:
            self.x = 0
        if SVG_ATTR_Y in values:
            self.y = Length(values[SVG_ATTR_Y]).value()
        else:
            self.y = 0
        if SVG_ATTR_DX in values:
            self.dx = Length(values[SVG_ATTR_DX]).value()
        else:
            self.dx = None
        if SVG_ATTR_DY in values:
            self.dy = Length(values[SVG_ATTR_DY]).value()
        else:
            self.dy = None

    def render(self, width=None, height=None, relative_length=None, **kwargs):
        if width is None and relative_length is not None:
            width = relative_length
        if height is None and relative_length is not None:
            height = relative_length
        self.transform.render(width=width, height=height, relative_length=relative_length, **kwargs)
        if isinstance(self.x, Length):
            self.x = self.x.value(relative_length=width, **kwargs)
        if isinstance(self.y, Length):
            self.y = self.y.value(relative_length=height, **kwargs)
        if isinstance(self.dx, Length):
            self.dx = self.dx.value(relative_length=width, **kwargs)
        if isinstance(self.dy, Length):
            self.dy = self.dy.value(relative_length=height, **kwargs)
        return self

    def bbox(self, transformed=True):
        """
        Get the bounding box for the given text object.
        """
        if self.path is not None:
            return (self.path * self.transform).bbox(transformed=True)
        return self.x, self.y, self.x, self.y


class SVGDesc:
    """
    SVG Desc are just desc data.

    This is a stub element.
    """

    def __init__(self, values, desc=None):
        if isinstance(values, dict):
            self.desc = desc
        else:
            self.desc = values


class SVGImage(GraphicObject, Transformable):
    """
    SVG Images are defined in SVG 2.0 12.3

    This class is called SVG Image rather than image as a guard against many Image objects
    which are quite useful and would be ideal for reading the linked or contained data.

    """

    def __init__(self, *args, **kwargs):
        Transformable.__init__(self, *args, **kwargs)
        GraphicObject.__init__(self, *args, **kwargs)
        self.url = None
        if len(args) == 1:
            if isinstance(args[0], dict):
                values = args[0]
            if isinstance(values, dict):
                if XLINK_HREF in values:
                    self.url = values[XLINK_HREF]
                elif SVG_HREF in values:
                    self.url = values[SVG_HREF]
                else:
                    self.url = None
            self.viewbox = Viewbox(values)
            self.data = None
        if self.url is not None:
            if self.url.startswith("data:image/"):
                # Data URL
                from base64 import b64decode
                if self.url.startswith("data:image/png;base64,"):
                    self.data = b64decode(self.url[22:])
                elif self.url.startswith("data:image/jpg;base64,"):
                    self.data = b64decode(self.url[22:])
                elif self.url.startswith("data:image/jpeg;base64,"):
                    self.data = b64decode(self.url[23:])
                elif self.url.startswith("data:image/svg+xml;base64,"):
                    self.data = b64decode(self.url[26:])
        if 'image' in kwargs:
            self.image = kwargs['image']
            self.image_width, self.image_height = self.image.size
        else:
            self.image = None
            self.image_width = None
            self.image_height = None
        if SVG_ATTR_WIDTH in kwargs:
            self.viewbox.physical_width = Length(kwargs[SVG_ATTR_WIDTH]).value()
        if SVG_ATTR_HEIGHT in kwargs:
            self.viewbox.physical_height = Length(kwargs[SVG_ATTR_HEIGHT]).value()

    def load(self, directory=None):
        try:
            from PIL import Image
            if self.data is not None:
                self.load_data()
            elif self.url is not None:
                self.load_file(directory)
            self.set_values_by_image()
        except ImportError:
            pass

    def load_data(self):
        try:
            # This code will not activate without PIL/Pillow installed.
            from PIL import Image
            if self.data is not None:
                from io import BytesIO
                self.image = Image.open(BytesIO(self.data))
            else:
                return
        except ImportError:
            # PIL/Pillow not found, decoding data is most we can do.
            pass

    def load_file(self, directory):
        try:
            # This code will not activate without PIL/Pillow installed.
            from PIL import Image
            if self.url is not None:
                try:
                    self.image = Image.open(self.url)
                except IOError:
                    try:
                        if directory is not None:
                            from os.path import join
                            relpath = join(directory, self.url)
                            self.image = Image.open(relpath)
                    except IOError:
                        return
        except ImportError:
            # PIL/Pillow not found, decoding data is most we can do.
            pass

    def set_values_by_image(self):
        if self.image is not None:
            self.image_width = self.image.width
            self.image_height = self.image.height
        else:
            return
        viewbox = "0 0 %d %d" % (self.image_width, self.image_height)
        self.viewbox.set_viewbox(viewbox)
        self.viewbox.render(width=self.image_width, height=self.image_height)
        viewbox_transform = self.viewbox.transform()
        self.transform = Matrix(viewbox_transform) * self.transform

    def bbox(self, transformed=True):
        """
        Get the bounding box for the given image object
        """
        if self.image_width is None or self.image_height is None:
            p = Point(0, 0)
            p *= self.transform
            return p[0], p[1], p[0], p[1]
        width = self.image_width
        height = self.image_height
        if transformed:
            p = (Point(0, 0) * self.transform,
                 Point(width, 0) * self.transform,
                 Point(width, height) * self.transform,
                 Point(0, height) * self.transform)
        else:
            p = (Point(0, 0),
                 Point(width, 0),
                 Point(width, height),
                 Point(0, height))
        x_vals = list(s[0] for s in p)
        y_vals = list(s[1] for s in p)
        min_x = min(x_vals)
        min_y = min(y_vals)
        max_x = max(x_vals)
        max_y = max(y_vals)
        return min_x, min_y, max_x, max_y


class Viewbox:

    def __init__(self, *args, **kwargs):
        """
        Viewbox(nodes)

        If the viewbox is not availible or in the nodes data it doesn't need to be expressly defined.

        Viewbox control the scaling between the element size and viewbox.

        The given width and height are merely to intepret the meaning of percent values of lengths. Usually this is
        the size of the physical space being occupied. And the PPI is used to interpret the meaning of physical units
        if the pixel_per_inch conversion isn't 96.

        :param args: nodes, must contain node values.
        :param kwargs: ppi, width, height, viewbox
        """
        if len(args) == 1:
            values = args[0]
        else:
            return

        if SVG_ATTR_VIEWBOX in kwargs:
            self.viewbox = kwargs[SVG_ATTR_VIEWBOX]
        elif SVG_ATTR_VIEWBOX in values:
            self.viewbox = values[SVG_ATTR_VIEWBOX]
        else:
            self.viewbox = None

        if SVG_ATTR_WIDTH in kwargs:
            self.physical_width = Length(kwargs[SVG_ATTR_WIDTH]).value()
        else:
            self.physical_width = None

        if SVG_ATTR_HEIGHT in kwargs:
            self.physical_height = Length(kwargs[SVG_ATTR_HEIGHT]).value()
        else:
            self.physical_height = None

        if SVG_ATTR_WIDTH in values:
            self.element_width = Length(values[SVG_ATTR_WIDTH]).value(relative_length=self.physical_width)
        else:
            self.element_width = self.physical_width

        if SVG_ATTR_HEIGHT in values:
            self.element_height = Length(values[SVG_ATTR_HEIGHT]).value(relative_length=self.physical_height)
        else:
            self.element_height = self.physical_height

        if SVG_ATTR_X in values:
            self.element_x = Length(values[SVG_ATTR_X]).value(relative_length=self.physical_width)
        else:
            self.element_x = 0

        if SVG_ATTR_Y in values:
            self.element_y = Length(values[SVG_ATTR_Y]).value(relative_length=self.physical_height)
        else:
            self.element_y = 0
        self.set_viewbox(self.viewbox)
        if SVG_ATTR_PRESERVEASPECTRATIO in values:
            self.preserve_aspect_ratio = values[SVG_ATTR_PRESERVEASPECTRATIO]
        else:
            self.preserve_aspect_ratio = None

    def __str__(self):
        return '%s %s %s %s -> %s %s %s %s' % (
            Length.str(self.element_x),
            Length.str(self.element_y),
            Length.str(self.element_width),
            Length.str(self.element_height),
            Length.str(self.viewbox_x),
            Length.str(self.viewbox_y),
            Length.str(self.viewbox_width),
            Length.str(self.viewbox_height),
        )

    def set_viewbox(self, viewbox):
        if viewbox is not None and isinstance(viewbox, str):
            dims = list(REGEX_FLOAT.findall(viewbox))
            self.viewbox_x = float(dims[0])
            self.viewbox_y = float(dims[1])
            self.viewbox_width = float(dims[2])
            self.viewbox_height = float(dims[3])
        else:
            self.viewbox_x = None
            self.viewbox_y = None
            self.viewbox_width = None
            self.viewbox_height = None

    def render(self, width=None, height=None, relative_length=None, **kwargs):
        if width is None and relative_length is not None:
            width = relative_length
        if height is None and relative_length is not None:
            height = relative_length
        if isinstance(self.physical_width, Length):
            self.physical_width = self.physical_width.value(relative_length=width, **kwargs)
        if isinstance(self.physical_height, Length):
            self.physical_height = self.physical_height.value(relative_length=height, **kwargs)
        if self.physical_width is not None:
            width = self.physical_width
        if self.physical_height is not None:
            height = self.physical_height
        if isinstance(self.element_x, Length):
            self.element_x = self.element_x.value(relative_length=width, **kwargs)
        if isinstance(self.element_y, Length):
            self.element_y = self.element_y.value(relative_length=height, **kwargs)
        if isinstance(self.element_width, Length):
            self.element_width = self.element_width.value(relative_length=width, **kwargs)
        if isinstance(self.element_height, Length):
            self.element_height = self.element_height.value(relative_length=height, **kwargs)
        return self

    def transform(self):
        return Viewbox.viewbox_transform(
            self.element_x, self.element_y, self.element_width, self.element_height,
            self.viewbox_x, self.viewbox_y, self.viewbox_width, self.viewbox_height,
            self.preserve_aspect_ratio)

    @staticmethod
    def viewbox_transform(e_x, e_y, e_width, e_height, vb_x, vb_y, vb_width, vb_height, aspect):
        """
        SVG 1.1 7.2, SVG 2.0 8.2 equivalent transform of an SVG viewport.
        With regards to https://github.com/w3c/svgwg/issues/215 use 8.2 version.

        It creates transform commands equal to that viewport expected.

        :param svg_node: dict containing the relevant svg entries.
        :return: string of the SVG transform commands to account for the viewbox.
        """

        # Let e-x, e-y, e-width, e-height be the position and size of the element respectively.

        # Let vb-x, vb-y, vb-width, vb-height be the min-x, min-y,
        # width and height values of the viewBox attribute respectively.

        # Let align be the align value of preserveAspectRatio, or 'xMidYMid' if preserveAspectRatio is not defined.
        # Let meetOrSlice be the meetOrSlice value of preserveAspectRatio, or 'meet' if preserveAspectRatio is not defined
        # or if meetOrSlice is missing from this value.
        if e_x is None or e_y is None or e_width is None or e_height is None or \
                vb_x is None or vb_y is None or vb_width is None or vb_height is None:
            return ''
        if aspect is not None:
            aspect_slice = aspect.split(' ')
            try:
                align = aspect_slice[0]
            except IndexError:
                align = 'xMidyMid'
            try:
                meet_or_slice = aspect_slice[1]
            except IndexError:
                meet_or_slice = 'meet'
        else:
            align = 'xMidyMid'
            meet_or_slice = 'meet'
        # Initialize scale-x to e-width/vb-width.
        scale_x = e_width / vb_width
        # Initialize scale-y to e-height/vb-height.
        scale_y = e_height / vb_height

        # If align is not 'none' and meetOrSlice is 'meet', set the larger of scale-x and scale-y to the smaller.
        if align != SVG_VALUE_NONE and meet_or_slice == 'meet':
            scale_x = scale_y = min(scale_x, scale_y)
        # Otherwise, if align is not 'none' and meetOrSlice is 'slice', set the smaller of scale-x and scale-y to the larger
        elif align != SVG_VALUE_NONE and meet_or_slice == 'slice':
            scale_x = scale_y = max(scale_x, scale_y)
        # Initialize translate-x to e-x - (vb-x * scale-x).
        translate_x = e_x - (vb_x * scale_x)
        # Initialize translate-y to e-y - (vb-y * scale-y)
        translate_y = e_y - (vb_y * scale_y)
        # If align contains 'xMid', add (e-width - vb-width * scale-x) / 2 to translate-x.
        align = align.lower()
        if 'xmid' in align:
            translate_x += (e_width - vb_width * scale_x) / 2.0
        # If align contains 'xMax', add (e-width - vb-width * scale-x) to translate-x.
        if 'xmax' in align:
            translate_x += e_width - vb_width * scale_x
        # If align contains 'yMid', add (e-height - vb-height * scale-y) / 2 to translate-y.
        if 'ymid' in align:
            translate_y += (e_height - vb_height * scale_y) / 2.0
        # If align contains 'yMax', add (e-height - vb-height * scale-y) to translate-y.
        if 'ymax' in align:
            translate_y += (e_height - vb_height * scale_y)
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
                return "translate(%s, %s)" % (Length.str(translate_x), Length.str(translate_y))
            else:
                return "translate(%s, %s) scale(%s, %s)" % \
                       (Length.str(translate_x), Length.str(translate_y),
                        Length.str(scale_x), Length.str(scale_y))


class SVG:
    """
    SVG Document parsing.
    This currently only supports nodes which are dictionary objects with svg attributes.
    These can then be converted into various elements through the various parsing methods.
    """

    def __init__(self, f):
        self.f = f

    def elements(self, reify=True, ppi=DEFAULT_PPI, width=1, height=1, color="black", transform=None):
        """
        Parses the SVG file.
        Style elements are split into their proper values.

        def elements are not processed.
        use elements are not processed.
        switch elements are not processed.
        title elements are not processed.
        metadata elements are not processed.
        foreignObject elements are not processed.
        """

        f = self.f
        stack = []
        values = {SVG_ATTR_COLOR: color, SVG_ATTR_FILL: color,
                  SVG_ATTR_STROKE: color}
        for event, elem in iterparse(f, events=('start', 'end')):
            if event == 'start':
                stack.append(values)
                current_values = values
                values = {}
                values.update(current_values)  # copy of dictionary

                # Non-propagating values.
                if SVG_ATTR_PRESERVEASPECTRATIO in values:
                    del values[SVG_ATTR_PRESERVEASPECTRATIO]
                if SVG_ATTR_VIEWBOX in values:
                    del values[SVG_ATTR_VIEWBOX]
                if SVG_ATTR_ID in values:
                    del values[SVG_ATTR_ID]

                attributes = elem.attrib
                if SVG_ATTR_STYLE in attributes:
                    for equate in attributes[SVG_ATTR_STYLE].split(";"):
                        equal_item = equate.split(":")
                        if len(equal_item) == 2:
                            attributes[equal_item[0]] = equal_item[1]
                if SVG_ATTR_FILL in attributes and attributes[SVG_ATTR_FILL] == SVG_VALUE_CURRENT_COLOR:
                    if SVG_ATTR_COLOR in attributes:
                        attributes[SVG_ATTR_FILL] = attributes[SVG_ATTR_COLOR]
                    else:
                        attributes[SVG_ATTR_FILL] = values[SVG_ATTR_COLOR]
                if SVG_ATTR_STROKE in attributes and attributes[SVG_ATTR_STROKE] == SVG_VALUE_CURRENT_COLOR:
                    if SVG_ATTR_COLOR in attributes:
                        attributes[SVG_ATTR_STROKE] = attributes[SVG_ATTR_COLOR]
                    else:
                        attributes[SVG_ATTR_STROKE] = values[SVG_ATTR_COLOR]
                if SVG_ATTR_TRANSFORM in attributes:
                    new_transform = attributes[SVG_ATTR_TRANSFORM]
                    if SVG_ATTR_TRANSFORM in values:
                        current_transform = values[SVG_ATTR_TRANSFORM]
                        attributes[SVG_ATTR_TRANSFORM] = current_transform + " " + new_transform
                    else:
                        attributes[SVG_ATTR_TRANSFORM] = new_transform
                values.update(attributes)
                tag = elem.tag
                if tag.startswith('{'):
                    tag = tag[28:]  # Removing namespace. http://www.w3.org/2000/svg:

                if SVG_NAME_TAG == tag:
                    if SVG_ATTR_VIEWBOX not in values:
                        values[SVG_ATTR_VIEWBOX] = "0 0 100 100"
                    viewbox = Viewbox(values)
                    viewbox.render(ppi=ppi, width=width, height=height)
                    yield viewbox
                    if transform is not None:
                        new_transform = transform + ' ' + viewbox.transform()
                        transform = None
                    else:
                        new_transform = viewbox.transform()
                    width = viewbox.viewbox_width
                    height = viewbox.viewbox_height
                    values[SVG_VIEWBOX_TRANSFORM] = new_transform
                    if SVG_ATTR_TRANSFORM in attributes:
                        # transform on SVG element applied as if svg had parent with transform.
                        values[SVG_ATTR_TRANSFORM] += " " + new_transform
                    else:
                        values[SVG_ATTR_TRANSFORM] = new_transform
                    continue
                elif SVG_TAG_GROUP == tag:
                    continue  # Groups are ignored.
                elif SVG_TAG_PATH == tag:
                    s = Path(values)
                    s.render(ppi=ppi, width=width, height=height)
                    if reify:
                        s.reify()
                    yield s
                elif SVG_TAG_CIRCLE == tag:
                    s = Circle(values)
                    s.render(ppi=ppi, width=width, height=height)
                    if reify:
                        s.reify()
                    yield s
                elif SVG_TAG_ELLIPSE == tag:
                    s = Ellipse(values)
                    s.render(ppi=ppi, width=width, height=height)
                    if reify:
                        s.reify()
                    yield s
                elif SVG_TAG_LINE == tag:
                    s = SimpleLine(values)
                    s.render(ppi=ppi, width=width, height=height)
                    if reify:
                        s.reify()
                    yield s
                elif SVG_TAG_POLYLINE == tag:
                    s = Polyline(values)
                    s.render(ppi=ppi, width=width, height=height)
                    if reify:
                        s.reify()
                    yield s
                elif SVG_TAG_POLYGON == tag:
                    s = Polygon(values)
                    s.render(ppi=ppi, width=width, height=height)
                    if reify:
                        s.reify()
                    yield s
                elif SVG_TAG_RECT == tag:
                    s = Rect(values)
                    s.render(ppi=ppi, width=width, height=height)
                    if reify:
                        s.reify()
                    yield s
                elif SVG_TAG_IMAGE == tag:
                    s = SVGImage(values)
                    s.render(ppi=ppi, width=width, height=height)
                    if reify:
                        s.reify()
                    yield s
                else:
                    continue
            else:  # End event.
                # The iterparse spec makes it clear that internal text data is undefined except at the end.
                tag = elem.tag
                if tag.startswith('{'):
                    tag = tag[28:]  # Removing namespace. http://www.w3.org/2000/svg:
                if SVG_TAG_TEXT == tag:
                    s = SVGText(values, text=elem.text)
                    s.render(ppi=ppi, width=width, height=height)
                    if reify:
                        s.reify()
                    yield s
                elif SVG_TAG_DESC == tag:
                    yield SVGDesc(values, desc=elem.text)
                values = stack.pop()
