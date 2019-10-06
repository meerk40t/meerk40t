from __future__ import division

from collections import MutableSequence
from copy import copy
from math import *

try:
    from math import tau
except ImportError:
    tau = pi * 2

"""
This file is derived from regebro's svg.path project ( https://github.com/regebro/svg.path )
some of the math is from mathandy's svgpathtools project ( https://github.com/mathandy/svgpathtools ).
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


def segment_length(curve, start, end, start_point, end_point, error, min_depth, depth):
    """Recursively approximates the length by straight lines"""
    mid = (start + end) / 2
    mid_point = curve.point(mid)
    length = abs(end_point - start_point)
    first_half = abs(mid_point - start_point)
    second_half = abs(end_point - mid_point)

    length2 = first_half + second_half
    if (length2 - length > error) or (depth < min_depth):
        # Calculate the length of each segment:
        depth += 1
        return (segment_length(curve, start, mid, start_point, mid_point,
                               error, min_depth, depth) +
                segment_length(curve, mid, end, mid_point, end_point,
                               error, min_depth, depth))
    # This is accurate enough.
    return length2


class Point:
    """Point is a general subscriptable point class with .x and .y as well as [0] and [1]

    For compatibility with regbro svg.path we accept complex numbers as x + yj,
    and provide .real and .imag as properties. As well as float and integer values as (v,0) elements.

    With regard to SGV 7.15.1 defining SVGPoint this class provides for matrix transformations.
    """

    def __init__(self, x, y=None):
        if y is None:
            try:
                y = x[1]
                x = x[0]
            except TypeError:  # not subscriptable, must be a legacy complex
                if isinstance(x, complex):
                    y = x.imag
                    x = x.real
                else:
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
        if isinstance(other, (Point, list, tuple)):
            b0 = other[0]
            b1 = other[1]
        elif isinstance(other, complex):
            b0 = other.real
            b1 = other.imag
        else:
            return NotImplemented
        c0 = abs(a0 - b0) <= ERROR
        c1 = abs(a1 - b1) <= ERROR
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
        return "Point(%.12f,%.12f)" % (self.x, self.y)

    def __copy__(self):
        return Point(self.x, self.y)

    def __str__(self):
        return "(%g,%g)" % (self.x, self.y)

    def __imul__(self, other):
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
        if isinstance(other, (Matrix, int, float)):
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
        self *= matrix

    def move_towards(self, p2, amount=1):
        self.x = amount * (p2[0] - self[0]) + self[0]
        self.y = amount * (p2[1] - self[1]) + self[1]

    def distance_to(self, p2):
        return Point.distance(self, p2)

    def angle_to(self, p2):
        return Point.angle(self, p2)

    def polar_to(self, angle, distance):
        return Point.polar(self, angle, distance)

    def reflected_across(self, p):
        m = p + p
        m -= self
        return m

    @staticmethod
    def orientation(p, q, r):
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
    """CSS Angle defines as used in SVG"""

    def __repr__(self):
        return "Angle(%.12f)" % self

    def __eq__(self, other):
        # Python 2
        c1 = abs(self - other) <= 1e-11
        return c1

    @classmethod
    def parse(cls, angle_string):
        if not isinstance(angle_string, str):
            return
        angle_string = angle_string.lower()
        if angle_string.endswith('deg'):
            return Angle.degrees(float(angle_string[:-3]))
        if angle_string.endswith('rad'):
            return Angle.radians(float(angle_string[:-3]))
        if angle_string.endswith('grad'):
            return Angle.gradians(float(angle_string[:-4]))
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
        v = self * 360.0 / tau
        while v < 0:
            v += 360.0
        return v

    @property
    def as_gradians(self):
        return self * 400.0 / tau

    @property
    def as_turns(self):
        return self / tau


class Matrix:
    """"
    Provides svg matrix interfacing.

    SVG 7.15.3 defines the matrix form as:
    [a c  e]
    [b d  f]
    """

    def __init__(self, *components):
        if len(components) == 0:
            self.a = 1.0
            self.b = 0.0
            self.c = 0.0
            self.d = 1.0
            self.e = 0.0
            self.f = 0.0
        elif len(components) == 1:
            m = components[0]
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

    def __ne__(self, other):
        return other is None or \
               not isinstance(other, Matrix) or \
               self.a != other.a or self.b != other.b or \
               self.c != other.c or self.d != other.d or \
               self.e != other.e or self.f != other.f

    def __eq__(self, other):
        return not self.__ne__(other)

    def __len__(self):
        return 6

    def __matmul__(self, other):
        m = copy(self)
        m.__imatmul__(other)
        return m

    def __rmatmul__(self, other):
        m = copy(other)
        m.__imatmul__(self)
        return m

    def __imatmul__(self, other):
        self.a, self.b, self.c, self.d, self.e, self.f = Matrix.matrix_multiply(self, other)
        return self

    def __getitem__(self, item):
        if item == 0:
            return self.a
        elif item == 1:
            return self.b
        elif item == 2:
            return self.c
        elif item == 3:
            return self.d
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
        return "Matrix(%3f, %3f, %3f, %3f, %3f, %3f)" % \
               (self.a, self.b, self.c, self.d, self.e, self.f)

    def __copy__(self):
        return Matrix(self.a, self.b, self.c, self.d, self.e, self.f)

    def __str__(self):
        """
        Many of SVG's graphics operations utilize 2x3 matrices of the form:

        :returns string representation of matrix.
        """
        return "[%3f, %3f,\n %3f, %3f,   %3f, %3f]" % \
               (self.a, self.c, self.b, self.d, self.e, self.f)

    def value_trans_x(self):
        return self.e

    def value_trans_y(self):
        return self.f

    def value_scale_x(self):
        return self.a

    def value_scale_y(self):
        return self.d

    def value_skew_x(self):
        return self.b

    def value_skew_y(self):
        return self.c

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
        [a c e]
        [b d f]
        """
        m48s75 = self.d * 1 - self.f * 0
        m38s56 = 0 * self.e - self.c * 1
        m37s46 = self.c * self.f - self.d * self.e
        det = self.a * m48s75 + self.c * m38s56 + 0 * m37s46
        inverse_det = 1.0 / float(det)

        self.a = m48s75 * inverse_det
        self.b = (0 * self.f - self.c * 1) * inverse_det
        # self.g = (self.c * self.h - self.g * self.d) * inverse_det
        self.c = m38s56 * inverse_det
        self.d = (self.a * 1 - 0 * self.e) * inverse_det
        # self.h = (self.c * self.g - self.a * self.h) * inverse_det
        self.e = m37s46 * inverse_det
        self.f = (0 * self.c - self.a * self.f) * inverse_det
        # self.i = (self.a * self.d - self.c * self.c) * inverse_det

    def post_cat(self, *components):
        mx = Matrix(*components)
        self.__imatmul__(mx)

    def post_scale(self, sx=1, sy=None, x=0, y=0):
        if sy is None:
            sy = sx
        if x is None:
            x = 0
        if y is None:
            y = 0
        if x == 0 and y == 0:
            self.post_cat(Matrix.scale(sx, sy))
        else:
            self.post_translate(-x, -y)
            self.post_scale(sx, sy)
            self.post_translate(x, y)

    def post_translate(self, tx, ty):
        self.post_cat(Matrix.translate(tx, ty))

    def post_rotate(self, angle, x=0, y=0):
        if x is None:
            x = 0
        if y is None:
            y = 0
        if x == 0 and y == 0:
            self.post_cat(Matrix.rotate(angle))  # self %= self.get_rotate(theta)
        else:
            matrix = Matrix()
            matrix.post_translate(-x, -y)
            matrix.post_cat(Matrix.rotate(angle))
            matrix.post_translate(x, y)
            self.post_cat(matrix)

    def post_skew_x(self, angle, x=0, y=0):
        if x is None:
            x = 0
        if y is None:
            y = 0
        if x == 0 and y == 0:
            self.post_cat(Matrix.skew_x(angle))
        else:
            self.post_translate(-x, -y)
            self.post_skew_x(angle)
            self.post_translate(x, y)

    def post_skew_y(self, angle, x=0, y=0):
        if x is None:
            x = 0
        if y is None:
            y = 0
        if x == 0 and y == 0:
            self.post_cat(Matrix.skew_y(angle))
        else:
            self.post_translate(-x, -y)
            self.post_skew_y(angle)
            self.post_translate(x, y)

    def pre_cat(self, *components):
        mx = Matrix(*components)
        self.a, self.b, self.c, self.d, self.e, self.f = Matrix.matrix_multiply(mx, self)

    def pre_skew_x(self, radians, x=0, y=0):
        if x is None:
            x = 0
        if y is None:
            y = 0
        if x == 0 and y == 0:
            self.pre_cat(Matrix.skew_x(radians))
        else:
            self.pre_translate(x, y)
            self.pre_skew_x(radians)
            self.pre_translate(-x, -y)

    def pre_skew_y(self, radians, x=0, y=0):
        if x is None:
            x = 0
        if y is None:
            y = 0
        if x == 0 and y == 0:
            self.pre_cat(Matrix.skew_y(radians))
        else:
            self.pre_translate(x, y)
            self.pre_skew_y(radians)
            self.pre_translate(-x, -y)

    def pre_scale(self, sx=1, sy=None, x=0, y=0):
        if sy is None:
            sy = sx
        if x is None:
            x = 0
        if y is None:
            y = 0
        if x == 0 and y == 0:
            self.pre_cat(Matrix.scale(sx, sy))
        else:
            self.pre_translate(x, y)
            self.pre_scale(sx, sy)
            self.pre_translate(-x, -y)

    def pre_translate(self, tx, ty):
        self.pre_cat(Matrix.translate(tx, ty))

    def pre_rotate(self, angle, x=0, y=0):
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
    def scale(cls, sx, sy=None):
        if sy is None:
            sy = sx
        return cls(sx, 0,
                   0, sy, 0, 0)

    @classmethod
    def translate(cls, tx, ty):
        """SVG Matrix:
                [a c e]
                [b d f]
                """
        return cls(1, 0,
                   0, 1, tx, ty)

    @classmethod
    def rotate(cls, angle):
        ct = cos(angle)
        st = sin(angle)
        return cls(ct, st,
                   -st, ct, 0, 0)

    @classmethod
    def skew_x(cls, angle):
        tt = tan(angle)
        return cls(1, 0,
                   tt, 1, 0, 0)

    @classmethod
    def skew_y(cls, angle):
        tt = tan(angle)
        return cls(1, tt,
                   0, 1, 0, 0)

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

        return r0[0], r1[0], r0[1], r1[1], r0[2], r1[2]


class Segment:
    def __init__(self):
        self.start = None
        self.end = None

    def __mul__(self, other):
        if isinstance(other, Matrix):
            n = copy(self)
            n *= other
            return n

    __rmul__ = __mul__

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


class Move(Segment):
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
        Segment.__init__(self)
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
        if isinstance(other, Matrix):
            if self.start is not None:
                self.start *= other
            if self.end is not None:
                self.end *= other
        return self

    def __copy__(self):
        return Move(self.start, self.end)

    def __repr__(self):
        if self.start is None:
            return 'Move(end=%s)' % repr(self.end)
        else:
            return 'Move(start=%s, end=%s)' % (repr(self.start), repr(self.end))

    def __eq__(self, other):
        if not isinstance(other, Move):
            return NotImplemented
        return self.start == other.start

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

    def point(self, pos):
        return self.start

    def length(self, error=ERROR, min_depth=MIN_DEPTH):
        return 0

    def plot(self):
        if self.start is not None:
            for x, y in Line.plot_line(self.start[0], self.start[1], self.end[0], self.end[1]):
                yield x, y, 0

    def reverse(self):
        if self.start is not None:
            return Move(self.end, self.start)
        else:
            if self.start is not None:
                return Move(self.start, self.end)

    def bbox(self):
        """returns the bounding box for the segment in the form
        (xmin, ymin, ymax, ymax)."""
        if self.start is not None:
            return self.start[0], self.start[1], self.end[0], self.end[1]
        else:
            return self.end[0], self.end[1], self.end[0], self.end[1]


class Close(Segment):
    """Represents close commands. If this exists at the end of the shape then the shape is closed.
    the methodology of a single flag close fails in a couple ways. You can have multi-part shapes
    which can close or not close several times.
    """

    def __init__(self, start=None, end=None):
        Segment.__init__(self)
        if end is None:
            if start is None:
                self.start = None
                self.end = None
            self.start = Point(start)
            self.end = Point(start)
        else:
            self.start = Point(start)
            self.end = Point(end)

    def __imul__(self, other):
        if isinstance(other, Matrix):
            if self.start is not None:
                self.start *= other
            if self.end is not None:
                self.end *= other
        return self

    def __copy__(self):
        return Close(self.start, self.end)

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

    def __eq__(self, other):
        if not isinstance(other, Close):
            return NotImplemented
        return self.start == other.start

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

    def reverse(self):
        return Close(self.end, self.start)

    def bbox(self):
        """returns the bounding box for the segment in the form
        (xmin, ymin, ymax, ymax)."""
        if self.start is None and self.end is None:
            return None
        return self.start[0], self.start[1], self.end[0], self.end[1]


class Line(Segment):
    def __init__(self, start, end):
        Segment.__init__(self)
        self.start = Point(start)
        self.end = Point(end)

    def __repr__(self):
        return 'Line(start=%s, end=%s)' % (repr(self.start), repr(self.end))

    def __eq__(self, other):
        if not isinstance(other, Line):
            return NotImplemented
        return self.start == other.start and self.end == other.end

    def __ne__(self, other):
        if not isinstance(other, Line):
            return NotImplemented
        return not self == other

    def __imul__(self, other):
        if isinstance(other, Matrix):
            self.start *= other
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

    def point(self, pos):
        return Point.towards(self.start, self.end, pos)

    def length(self, error=None, min_depth=None):
        return Point.distance(self.end, self.start)

    def reverse(self):
        return Line(self.end, self.start)

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

    def bbox(self):
        """returns the bounding box for the segment.
        xmin, ymin, xmax, ymax
        """
        xmin = min(self.start[0], self.end[0])
        xmax = max(self.start[0], self.end[0])
        ymin = min(self.start[1], self.end[1])
        ymax = max(self.start[1], self.end[1])
        return xmin, ymin, xmax, ymax

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


class QuadraticBezier(Segment):
    def __init__(self, start, control, end):
        Segment.__init__(self)
        self.start = Point(start)
        self.control = Point(control)
        self.end = Point(end)

    def __repr__(self):
        return 'QuadraticBezier(start=%s, control=%s, end=%s)' % (
            repr(self.start), repr(self.control), repr(self.end))

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
        if isinstance(other, Matrix):
            self.start *= other
            self.control *= other
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

    def point(self, t):
        """Calculate the x,y position at a certain position of the path"""
        x0, y0 = self.start
        x1, y1 = self.control
        x2, y2 = self.end
        x = (1 - t) * (1 - t) * x0 + 2 * (1 - t) * t * x1 + t * t * x2
        y = (1 - t) * (1 - t) * y0 + 2 * (1 - t) * t * y1 + t * t * y2
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

    def reverse(self):
        return QuadraticBezier(self.end, self.control, self.start)

    def is_smooth_from(self, previous):
        """Checks if this segment would be a smooth segment following the previous"""
        if isinstance(previous, QuadraticBezier):
            return (self.start == previous.end and
                    (self.control - self.start) == (previous.end - previous.control))
        else:
            return self.control == self.start

    def plot(self):
        for x, y in QuadraticBezier.plot_quad_bezier(self.start[0], self.start[1],
                                                     self.control[0], self.control[1],
                                                     self.end[0], self.end[1]):
            yield x, y, 1

    def bbox(self):
        """returns the bounding box for the segment"""
        xmin = min(self.start[0], self.control[0], self.end[0])
        ymin = min(self.start[1], self.control[1], self.end[1])
        xmax = max(self.start[0], self.control[0], self.end[0])
        ymax = max(self.start[1], self.control[1], self.end[1])
        return xmin, ymin, xmax, ymax

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


class CubicBezier(Segment):
    def __init__(self, start, control1, control2, end):
        Segment.__init__(self)
        self.start = Point(start)
        self.control1 = Point(control1)
        self.control2 = Point(control2)
        self.end = Point(end)

    def __repr__(self):
        return 'CubicBezier(start=%s, control1=%s, control2=%s, end=%s)' % (
            repr(self.start), repr(self.control1), repr(self.control2), repr(self.end))

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
        if isinstance(other, Matrix):
            self.start *= other
            self.control1 *= other
            self.control2 *= other
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

    def point(self, t):
        """Calculate the x,y position at a certain position of the path"""
        x0, y0 = self.start
        x1, y1 = self.control1
        x2, y2 = self.control2
        x3, y3 = self.end
        x = (1 - t) * (1 - t) * (1 - t) * x0 + 3 * (1 - t) * (1 - t) * t * x1 + 3 * (
                1 - t) * t * t * x2 + t * t * t * x3
        y = (1 - t) * (1 - t) * (1 - t) * y0 + 3 * (1 - t) * (1 - t) * t * y1 + 3 * (
                1 - t) * t * t * y2 + t * t * t * y3
        return Point(x, y)

    def length(self, error=ERROR, min_depth=MIN_DEPTH):
        """Calculate the length of the path up to a certain position"""
        start_point = self.point(0)
        end_point = self.point(1)
        return segment_length(self, 0, 1, start_point, end_point, error, min_depth, 0)

    def reverse(self):
        return CubicBezier(self.end, self.control2, self.control1, self.start)

    def is_smooth_from(self, previous):
        """Checks if this segment would be a smooth segment following the previous"""
        if isinstance(previous, CubicBezier):
            return (self.start == previous.end and
                    (self.control1 - self.start) == (previous.end - previous.control2))
        else:
            return self.control1 == self.start

    def bbox(self):
        """returns the bounding box for the segment"""
        xmin = min(self.start[0], self.control1[0], self.control2[0], self.end[0])
        ymin = min(self.start[1], self.control1[1], self.control2[1], self.end[1])
        xmax = max(self.start[0], self.control1[0], self.control2[0], self.end[0])
        ymax = max(self.start[1], self.control1[1], self.control2[1], self.end[1])
        return xmin, ymin, xmax, ymax

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


class Arc(Segment):
    def __init__(self, *args, **kwargs):
        """Arc objects can take different parameters to create arcs.
        Since we expect taking in SVG parameters. We accept SVG parameterization which is:
        start, rx, ry, rotation, arc_flag, sweep_flag, end.

        To do matrix transitions, the native parameterization is start, end, center, prx, pry, sweep

        'start, end, center, prx, pry' are points and sweep amount is a value in tau radians.
        If points are modified by an affine transformation, the arc is transformed.
        There is a special case for when the scale factor inverts, it inverts the sweep.

        prx is the point at angle 0 of the non-rotated ellipse.
        pry is the point at angle tau/4 of the non-rotated ellipse.
        The theta-rotation can be defined as the angle from center to prx

        The sweep angle can be a value greater than tau and less than -tau.
        However if this is the case conversion back to Path.d() is expected to fail.

        prx -> center -> pry should form a right triangle.
        angle(center,end) - angle(center, start) should equal sweep or mod thereof.

        start and end should fall on the ellipse defined by prx, pry and center.
        """
        Segment.__init__(self)
        self.start = None
        self.end = None
        self.center = None
        self.prx = None
        self.pry = None
        self.sweep = None
        if len(args) == 6 and isinstance(args[1], complex):
            self.svg_complex_parameterize(*args)
            return
        elif len(kwargs) == 6 and 'rotation' in kwargs:
            self.svg_complex_parameterize(**kwargs)
            return
        elif len(args) == 7:
            # This is an svg parameterized call.
            # A: rx ry x-axis-rotation large-arc-flag sweep-flag x y
            self.svg_parameterize(args[0], args[1], args[2], args[3], args[4], args[5], args[6])
            return
        # TODO: account for L, T, R, B, startAngle, endAngle, theta parameters.
        # cx = (left + right) / 2
        # cy = (top + bottom) / 2
        #
        # rx = (right - left) / 2
        # cy = (bottom - top) / 2
        # startAngle, endAngle, theta
        len_args = len(args)
        if len_args > 0:
            self.start = Point(args[0])
        if len_args > 1:
            self.end = Point(args[1])
        if len_args > 2:
            self.center = Point(args[2])
        if len_args > 3:
            self.prx = Point(args[3])
        if len_args > 4:
            self.pry = Point(args[4])
        if len_args > 5:
            self.sweep = args[5]
            return  # The args gave us everything.
        if 'start' in kwargs:
            self.start = kwargs['start']
        if 'end' in kwargs:
            self.end = kwargs['end']
        if 'center' in kwargs:
            self.center = kwargs['center']
        if 'prx' in kwargs:
            self.prx = kwargs['prx']
        if 'pry' in kwargs:
            self.pry = kwargs['pry']
        if 'sweep' in kwargs:
            self.sweep = kwargs['sweep']
        if self.center is not None:
            if 'r' in kwargs:
                r = kwargs['r']
                if self.prx is None:
                    self.prx = [self.center[0] + r, self.center[1]]
                if self.pry is None:
                    self.pry = [self.center[0], self.center[1] + r]
            if 'rx' in kwargs:
                rx = kwargs['rx']
                if self.prx is None:
                    if 'rotation' in kwargs:
                        theta = kwargs['rotation']
                        self.prx = Point.polar(self.center, theta, rx)
                    else:
                        self.prx = [self.center[0] + rx, self.center[1]]
            if 'ry' in kwargs:
                ry = kwargs['ry']
                if self.pry is None:
                    if 'rotation' in kwargs:
                        theta = kwargs['rotation']
                        theta += tau / 4.0
                        self.pry = Point.polar(self.center, theta, ry)
                    else:
                        self.pry = [self.center[0], self.center[1] + ry]
            if self.start is not None and (self.prx is None or self.pry is None):
                radius_s = Point.distance(self.center, self.start)
                self.prx = Point(self.center[0] + radius_s, self.center[1])
                self.pry = Point(self.center[0], self.center[1] + radius_s)
            if self.end is not None and (self.prx is None or self.pry is None):
                radius_e = Point.distance(self.center, self.end)
                self.prx = Point(self.center[0] + radius_e, self.center[1])
                self.pry = Point(self.center[0], self.center[1] + radius_e)
            if self.sweep is None and self.start is not None and self.end is not None:
                start_angle = Point.angle(self.center, self.start)
                end_angle = Point.angle(self.center, self.end)
                self.sweep = end_angle - start_angle
            if self.sweep is not None and self.start is not None and self.end is None:
                start_angle = Point.angle(self.center, self.start)
                end_angle = start_angle + self.sweep
                r = Point.distance(self.center, self.start)
                self.end = Point.polar(self.center, end_angle, r)
            if self.sweep is not None and self.start is None and self.end is not None:
                end_angle = Point.angle(self.center, self.end)
                start_angle = end_angle - self.sweep
                r = Point.distance(self.center, self.end)
                self.start = Point.polar(self.center, start_angle, r)
        else:  # center is None
            pass

    def __repr__(self):
        return 'Arc(%s, %s, %s, %s, %s, %s)' % (
            repr(self.start), repr(self.end), repr(self.center), repr(self.prx), repr(self.pry), self.sweep)

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

    def __copy__(self):
        return Arc(self.start, self.end, self.center, self.prx, self.pry, self.sweep)

    def __imul__(self, other):
        if isinstance(other, Matrix):
            self.start *= other
            self.center *= other
            self.end *= other
            self.prx *= other
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
        return self.get_start_angle().as_positive_degrees

    @property
    def delta(self):
        """legacy property"""
        return Angle.radians(self.sweep).as_degrees

    def point_at_angle(self, t):
        rotation = self.get_rotation()
        cos_theta_rotation = cos(rotation)
        sin_theta_rotation = sin(rotation)
        cos_angle = cos(t)
        sin_angle = sin(t)
        rx = self.rx
        ry = self.ry
        x = (cos_theta_rotation * cos_angle * rx - sin_theta_rotation * sin_angle * ry + self.center[0])
        y = (sin_theta_rotation * cos_angle * rx + cos_theta_rotation * sin_angle * ry + self.center[1])
        return Point(x, y)

    def point(self, t):
        if self.start == self.end and self.sweep == 0:
            # This is equivalent of omitting the segment
            return self.start
        angle = self.get_start_angle() - self.get_rotation() + self.sweep * t
        return self.point_at_angle(angle)

    def length(self, error=ERROR, min_depth=MIN_DEPTH):
        """The length of an elliptical arc segment requires numerical
        integration, and in that case it's simpler to just do a geometric
        approximation, as for cubic bezier curves.
        """
        if self.start == self.end and self.sweep == 0:
            # This is equivalent of omitting the segment
            return 0
        start_point = self.point(0)
        end_point = self.point(1)
        return segment_length(self, 0, 1, start_point, end_point, error, min_depth, 0)

    def reverse(self):
        return Arc(self.end, self.start, self.center, self.prx, self.pry, -self.sweep)

    def svg_complex_parameterize(self, start, radius, rotation, arc, sweep, end):
        """Parameterization with complex radius and having rotation factors."""
        self.svg_parameterize(Point(start), radius.real, radius.imag, rotation, bool(arc), bool(sweep), Point(end))

    def svg_parameterize(self, start, rx, ry, rotation, large_arc_flag, sweep_flag, end):
        """Conversion from svg parameterization, our chosen native native form.
        http://www.w3.org/TR/SVG/implnote.html#ArcImplementationNotes """

        start = Point(start)
        self.start = start
        end = Point(end)
        self.end = end
        if start == end:
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

    def as_quad_curves(self):
        sweep_limit = tau / 12
        arc_required = int(ceil(abs(self.sweep) / sweep_limit))
        if arc_required == 0:
            return
        slice = self.sweep / float(arc_required)

        start_angle = self.get_start_angle()
        theta = self.get_rotation()
        p_start = self.start

        current_angle = start_angle - theta

        for i in range(0, arc_required):
            next_angle = current_angle + slice
            q = Point(p_start[0] + tan((p_end[0] - p_start[0]) / 2.0))
            yield QuadraticBezier(p_start, q, p_end)
            p_start = Point(p_end)
            current_angle = next_angle

    def as_cubic_curves(self):
        sweep_limit = tau / 12
        arc_required = int(ceil(abs(self.sweep) / sweep_limit))
        if arc_required == 0:
            return
        slice = self.sweep / float(arc_required)

        start_angle = self.get_start_angle()
        theta = self.get_rotation()
        rx = self.rx
        ry = self.ry
        p_start = self.start
        current_angle = start_angle - theta
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
        return Point.angle(self.center, self.start)

    def get_end_angle(self):
        return Point.angle(self.center, self.end)

    def bbox_rotated(self):
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

    def bbox(self):
        """returns the bounding box for the segment"""
        # TODO: The bbox rotated command should be integrated into here. It's not enough to min and max the start, end,
        #  and center, but rather needs to find the min and max of the path along the arc.
        xmin = min(self.start[0], self.center[0], self.end[0])
        ymin = min(self.start[1], self.center[1], self.end[1])
        xmax = max(self.start[0], self.center[0], self.end[0])
        ymax = max(self.start[1], self.center[1], self.end[1])
        return xmin, ymin, xmax, ymax

    def plot(self):
        # TODO: This needs to work correctly. Should actually plot the arc according to the pixel-perfect standard.
        for curve in self.as_cubic_curves():
            for value in curve.plot():
                yield value

    @staticmethod
    def plot_arc(arc):
        theta = Point.angle(arc.center, arc.prx)
        a = Point.distance(arc.center, arc.prx)
        b = Point.distance(arc.center, arc.pry)
        cos_theta = cos(theta)
        sin_theta = sin(theta)
        xmax = sqrt(a * a * cos_theta * cos_theta + b * b * sin_theta * sin_theta)
        ymax = sqrt(a * a * sin_theta * sin_theta + b * b * cos_theta * cos_theta)
        angle_xmax = Point.distance(arc.center, [xmax, ymax])
        # TODO: need to plug this back into the arc to solve for the position of xmax,
        #  y-unknown on the ellipse.

        yield arc.start[0], arc.start[1]
        # TODO: Actually write this, divide into proper segments
        yield arc.end[0], arc.end[1]

    @staticmethod
    def plot_arc_seg(xm, ym, ar, br=None, theta=0):
        if br is None:
            br = ar
        x = -ar
        y = 0
        e2 = br * br
        err = x * (2 * e2 + x) + e2
        sx = 1
        sy = 1
        while True:
            yield xm + x, ym + y
            e2 = 2 * err
            if e2 >= (x * 2 + 1) * br * br:
                x = x + sx
                err += (x * 2 + 1) * br * br
            if e2 <= (y * 2 + 1) * ar * ar:
                y = y + sy
                err += (y * 2 + 1) * ar * ar
            if x <= 0:
                break


class Path(MutableSequence):
    """A Path is a sequence of path segments"""

    def __init__(self, *segments):
        self._segments = list(segments)
        self._length = None
        self._lengths = None

    def __copy__(self):
        p = Path()
        for seg in self._segments:
            p.append(copy(seg))
        return p

    def __getitem__(self, index):
        return self._segments[index]

    def __setitem__(self, index, value):
        self._segments[index] = value
        self._length = None

    def __delitem__(self, index):
        del self._segments[index]
        self._length = None

    def __imul__(self, other):
        if isinstance(other, Matrix):
            for e in self._segments:
                e *= other
        return self

    def __mul__(self, other):
        if isinstance(other, Matrix):
            n = copy(self)
            n *= other
            return n

    __rmul__ = __mul__

    def __reversed__(self):
        for segment in reversed(self._segments):
            yield segment.reverse()

    def __len__(self):
        return len(self._segments)

    def __repr__(self):
        return 'Path(%s)' % (', '.join(repr(x) for x in self._segments))

    def __eq__(self, other):
        if not isinstance(other, Path):
            return NotImplemented
        if len(self) != len(other):
            return False
        for s, o in zip(self._segments, other._segments):
            if not s == o:
                return False
        return True

    def __ne__(self, other):
        if not isinstance(other, Path):
            return NotImplemented
        return not self == other

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
            end_pos = self._segments[0].start
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
        if len(self._segments) > 0:
            if isinstance(self._segments[-1], Move):
                # If there was just a move command update that.
                self._segments[-1].end = Point(end_pos)
                return
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

    def point(self, pos, error=ERROR):
        # Shortcuts
        if pos == 0.0:
            return self._segments[0].point(pos)
        if pos == 1.0:
            return self._segments[-1].point(pos)

        self._calc_lengths(error=error)
        # Find which segment the point we search for is located on:
        segment_start = 0
        for index, segment in enumerate(self._segments):
            segment_end = segment_start + self._lengths[index]
            if segment_end >= pos:
                # This is the segment! How far in on the segment is the point?
                segment_pos = (pos - segment_start) / (segment_end - segment_start)
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

    def insert(self, index, value):
        self._segments.insert(index, value)
        self._length = None

    def reverse(self):
        reversed_segments = self._segments[::-1]
        for i in range(0, len(reversed_segments)):
            reversed_segments[i] = reversed_segments[i].reverse()
        path = Path()
        path._segments = reversed_segments
        return path

    def as_subpaths(self):
        last = 0
        subpath = Path()
        for current, seg in enumerate(self):
            if current != last and isinstance(seg, Move):
                subpath._segments = self[last:current]
                yield subpath
                last = current
        subpath._segments = self[last:]
        yield subpath

    def as_points(self):
        """Returns the list of defining points within path"""
        for seg in self:
            for p in seg:
                if not isinstance(p, Point):
                    yield Point(p)
                else:
                    yield p

    def bbox(self):
        """returns a bounding box for the input Path"""
        bbs = [seg.bbox() for seg in self._segments if not isinstance(Close, Move)]
        try:
            xmins, ymins, xmaxs, ymaxs = list(zip(*bbs))
        except ValueError:
            return None  # No bounding box items existed. So no bounding box.
        xmin = min(xmins)
        xmax = max(xmaxs)
        ymin = min(ymins)
        ymax = max(ymaxs)
        return xmin, ymin, xmax, ymax

    def d(self):
        parts = []
        previous_segment = None
        if len(self) == 0:
            return ''
        for segment in self:
            if isinstance(segment, Move):
                parts.append('M {0:G},{1:G}'.format(segment.end[0], segment.end[1]))
            elif isinstance(segment, Line):
                parts.append('L {0:G},{1:G}'.format(
                    segment.end[0], segment.end[1])
                )
            elif isinstance(segment, CubicBezier):
                if segment.is_smooth_from(previous_segment):
                    parts.append('S {0:G},{1:G} {2:G},{3:G}'.format(
                        segment.control2[0], segment.control2[1],
                        segment.end[0], segment.end[1])
                    )
                else:
                    parts.append('C {0:G},{1:G} {2:G},{3:G} {4:G},{5:G}'.format(
                        segment.control1[0], segment.control1[1],
                        segment.control2[0], segment.control2[1],
                        segment.end[0], segment.end[1])
                    )
            elif isinstance(segment, QuadraticBezier):
                if segment.is_smooth_from(previous_segment):
                    parts.append('T {0:G},{1:G}'.format(
                        segment.end[0], segment.end[1])
                    )
                else:
                    parts.append('Q {0:G},{1:G} {2:G},{3:G}'.format(
                        segment.control[0], segment.control[1],
                        segment.end[0], segment.end[1])
                    )

            elif isinstance(segment, Arc):
                parts.append('A {0:G},{1:G} {2:G} {3:d},{4:d} {5:G},{6:G}'.format(
                    segment.rx, segment.ry, segment.get_rotation().as_degrees,
                    int(abs(segment.sweep) > (tau / 2.0)), int(segment.sweep >= 0),
                    segment.end[0], segment.end[1])
                )
            elif isinstance(segment, Close):
                parts.append('Z')
            previous_segment = segment
        return ' '.join(parts)
