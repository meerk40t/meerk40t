from __future__ import division

from collections import MutableSequence
from copy import copy
from math import cos, sin, acos, atan2, floor, tan, sqrt, ceil, radians, pi

try:
    from math import tau
except ImportError:
    tau = pi * 2


# This file contains classes for the different types of SVG path segments as well as a Path
# object that contains a sequence of path segments. Matrix and Point classes.

class Point:
    """Point is a general subscriptable point class with .x and .y as well as [0] and [1]
    For compatibility it accepts complex numbers as x + yj"""

    def __init__(self, x, y=None):
        if y is None:
            if isinstance(x, complex):
                y = x.imag
                x = x.real
            else:
                y = x[1]
                x = x[0]
        self.x = x
        self.y = y

    def __eq__(self, other):
        if isinstance(other, (Point, list, tuple)):
            return self[0] == other[0] and self[1] == other[1]
        elif isinstance(other, complex):
            return self[0] == other.real and self[1] == other.imag
        return NotImplemented

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
        return "Point(%f,%f)" % (self.x, self.y)

    def __copy__(self):
        return Point(self.x, self.y)

    def __str__(self):
        return "(%f,%f)" % (self.x, self.y)

    def __mul__(self, other):
        if isinstance(other, Matrix):
            n = copy(self)
            n *= other
            return n

    __rmul__ = __mul__

    def __imul__(self, other):
        if isinstance(other, Matrix):
            v = other.point_in_matrix_space(self)
            self[0] = v[0]
            self[1] = v[1]
        return self

    def __add__(self, other):
        if isinstance(other, (Point, tuple, list)):
            x = self[0] + other[0]
            y = self[1] + other[1]
            return Point(x, y)

    __radd__ = __add__

    def __iadd__(self, other):
        if isinstance(other, (Point, tuple, list)):
            self[0] += other[0]
            self[1] += other[1]

    def __rsub__(self, other):
        if isinstance(other, (Point, tuple, list)):
            x = other[0] - self[0]
            y = other[1] - self[1]
            return Point(x, y)

    def __sub__(self, other):
        if isinstance(other, (Point, tuple, list)):
            x = self[0] - other[0]
            y = self[1] - other[1]
            return Point(x, y)

    def __isub__(self, other):
        if isinstance(other, (Point, tuple, list)):
            self[0] -= other[0]
            self[1] -= other[1]

    def distance_to(self, p2):
        return Point.distance(self, p2)

    def angle_to(self, p2):
        return Point.angle(self, p2)

    def polar_to(self, angle, distance):
        return Point.polar(self, angle, distance)

    @staticmethod
    def distance(p1, p2):
        dx = p1[0] - p2[0]
        dx *= dx
        dy = p1[1] - p2[1]
        dy *= dy
        return sqrt(dx + dy)

    @staticmethod
    def polar(p1, angle, r):
        dx = cos(angle) * r
        dy = sin(angle) * r
        return Point(p1[0] + dx, p1[1] + dy)

    @staticmethod
    def angle(p1, p2):
        return atan2(p2[1] - p1[1], p2[0] - p1[0])


class Matrix:
    def __init__(self, m=None):
        if m is None:
            self.m = self.get_identity()
        else:
            self.m = m

    def __ne__(self, other):
        return not self.__eq__(other)

    def __eq__(self, other):
        return self.m == other.m

    def __matmul__(self, other):
        return Matrix(Matrix.matrix_multiply(self.m, other.m))

    def __rmatmul__(self, other):
        return Matrix(Matrix.matrix_multiply(self.m, other.m))

    def __imatmul__(self, other):
        self.m = Matrix.matrix_multiply(self.m, other.m)

    def __getitem__(self, item):
        return self.m[item]

    def __repr__(self):
        return "Matrix([%3f, %3f, %3f, %3f, %3f, %3f, %3f, %3f, %3f])" % self.m

    def __copy__(self):
        return Matrix(self.m)

    def __str__(self):
        return "[%3f, %3f, %3f,\n %3f, %3f, %3f,\n %3f, %3f, %3f]" % self.m

    def get_matrix(self):
        return self.m

    def value_trans_x(self):
        return self[6]

    def value_trans_y(self):
        return self[7]

    def value_scale_x(self):
        return self[0]

    def value_scale_y(self):
        return self[4]

    def value_skew_x(self):
        return self[1]

    def value_skew_y(self):
        return self[3]

    def reset(self):
        self.m = self.get_identity()

    def inverse(self):
        m = self.m
        m48s75 = m[4] * m[8] - m[7] * m[5]
        m38s56 = m[5] * m[6] - m[3] * m[8]
        m37s46 = m[3] * m[7] - m[4] * m[6]
        det = m[0] * m48s75 + m[1] * m38s56 + m[2] * m37s46
        inverse_det = 1.0 / float(det)
        self.m = [
            m48s75 * inverse_det,
            (m[2] * m[7] - m[1] * m[8]) * inverse_det,
            (m[1] * m[5] - m[2] * m[4]) * inverse_det,
            m38s56 * inverse_det,
            (m[0] * m[8] - m[2] * m[6]) * inverse_det,
            (m[3] * m[2] - m[0] * m[5]) * inverse_det,
            m37s46 * inverse_det,
            (m[6] * m[1] - m[0] * m[7]) * inverse_det,
            (m[0] * m[4] - m[3] * m[1]) * inverse_det,
        ]

    def post_scale(self, sx=1, sy=None, x=0, y=0):
        if sy is None:
            sy = sx
        if x is None:
            x = 0
        if y is None:
            y = 0
        if x == 0 and y == 0:
            self.m = self.matrix_multiply(self.m, self.get_scale(sx, sy))
        else:
            self.post_translate(x, y)
            self.post_scale(sx, sy)
            self.post_translate(-x, -y)

    def post_translate(self, tx, ty):
        self.m = self.matrix_multiply(self.m, self.get_translate(tx, ty))

    def post_rotate(self, theta, x=0, y=0):
        if x is None:
            x = 0
        if y is None:
            y = 0
        if x == 0 and y == 0:
            self.m = self.matrix_multiply(self.m, self.get_rotate(theta))
        else:
            self.post_translate(x, y)
            self.post_rotate(theta)
            self.post_translate(-x, -y)

    def post_cat(self, matrix_list):
        for mx in matrix_list:
            self.m = self.matrix_multiply(self.m, mx)

    def pre_scale(self, sx=1, sy=None):
        if sy is None:
            sy = sx
        self.m = self.matrix_multiply(self.get_scale(sx, sy), self.m)

    def pre_translate(self, tx, ty):
        self.m = self.matrix_multiply(self.get_translate(tx, ty), self.m)

    def pre_rotate(self, theta):
        self.m = self.matrix_multiply(self.get_rotate(theta), self.m)

    def pre_cat(self, matrix_list):
        for mx in matrix_list:
            self.m = self.matrix_multiply(mx, self.m)

    def point_in_inverse_space(self, v0, v1=None):
        inverse = Matrix(self)
        inverse.inverse()
        return inverse.point_in_matrix_space(v0, v1)

    def point_in_matrix_space(self, v0, v1=None):
        m = self.m
        if v1 is None:
            try:
                return [
                    v0[0] * m[0] + v0[1] * m[3] + 1 * m[6],
                    v0[0] * m[1] + v0[1] * m[4] + 1 * m[7],
                    v0[2]
                ]
            except IndexError:
                return [
                    v0[0] * m[0] + v0[1] * m[3] + 1 * m[6],
                    v0[0] * m[1] + v0[1] * m[4] + 1 * m[7]
                    # Must not have had a 3rd element.
                ]
        return [
            v0 * m[0] + v1 * m[3] + 1 * m[6],
            v0 * m[1] + v1 * m[4] + 1 * m[7]
        ]

    def apply(self, v):
        m = self.m
        nx = v[0] * m[0] + v[1] * m[3] + 1 * m[6]
        ny = v[0] * m[1] + v[1] * m[4] + 1 * m[7]
        v[0] = nx
        v[1] = ny

    @classmethod
    def scale(cls, sx, sy=None):
        cls().post_scale(sx, sy)
        return cls

    @classmethod
    def translate(cls, tx, ty):
        cls().post_translate(tx, ty)
        return cls

    @classmethod
    def rotate(cls, angle):
        cls().post_rotate(angle)
        return cls

    @staticmethod
    def get_identity():
        return \
            1, 0, 0, \
            0, 1, 0, \
            0, 0, 1  # identity

    @staticmethod
    def get_scale(sx, sy=None):
        if sy is None:
            sy = sx
        return \
            sx, 0, 0, \
            0, sy, 0, \
            0, 0, 1

    @staticmethod
    def get_translate(tx, ty):
        return \
            1, 0, 0, \
            0, 1, 0, \
            tx, ty, 1

    @staticmethod
    def get_rotate(theta):
        theta *= tau / 360
        ct = cos(theta)
        st = sin(theta)
        return \
            ct, st, 0, \
            -st, ct, 0, \
            0, 0, 1

    @staticmethod
    def matrix_multiply(m0, m1):
        return [
            m1[0] * m0[0] + m1[1] * m0[3] + m1[2] * m0[6],
            m1[0] * m0[1] + m1[1] * m0[4] + m1[2] * m0[7],
            m1[0] * m0[2] + m1[1] * m0[5] + m1[2] * m0[8],
            m1[3] * m0[0] + m1[4] * m0[3] + m1[5] * m0[6],
            m1[3] * m0[1] + m1[4] * m0[4] + m1[5] * m0[7],
            m1[3] * m0[2] + m1[4] * m0[5] + m1[5] * m0[8],
            m1[6] * m0[0] + m1[7] * m0[3] + m1[8] * m0[6],
            m1[6] * m0[1] + m1[7] * m0[4] + m1[8] * m0[7],
            m1[6] * m0[2] + m1[7] * m0[5] + m1[8] * m0[8]]


class Move(object):
    """Represents move commands. Does nothing, but is there to handle
    paths that consist of only move commands, which is valid, but pointless.
    Also serve as a bridge to make discontinuous paths into continuous paths
    with non-drawn sections.
    """

    def __init__(self, start, end=None):
        if end is None:
            self.start = Point(start)
            self.end = Point(start)
        else:
            self.start = Point(start)
            self.end = Point(end)

    def __imul__(self, other):
        if isinstance(other, Matrix):
            self.start *= other
            self.end *= other
        return self

    def __mul__(self, other):
        if isinstance(other, Matrix):
            n = copy(self)
            n *= other
            return n

    __rmul__ = __mul__

    def __copy__(self):
        return Move(self.start, self.end)

    def __repr__(self):
        return 'Move(start=%s, end=%s)' % (self.start, self.end)

    def __eq__(self, other):
        if not isinstance(other, Move):
            return NotImplemented
        return self.start == other.start

    def __ne__(self, other):
        if not isinstance(other, Move):
            return NotImplemented
        return not self == other

    def __len__(self):
        return 1

    def __getitem__(self, item):
        if item == 0:
            return self.start
        else:
            raise IndexError

    def plot(self):
        for x, y in Line.plot_line(self.start[0], self.start[1], self.end[0], self.end[1]):
            yield x, y, 0

    def reverse(self):
        return Move(self.end, self.start)

    def bbox(self):
        """returns the bounding box for the segment in the form
        (xmin, ymin, ymax, ymax)."""
        return self.start[0], self.start[1], self.end[0], self.end[1]


class Line(object):
    def __init__(self, start, end):
        self.start = Point(start)
        self.end = Point(end)

    def __repr__(self):
        return 'Line(start=%s, end=%s)' % (self.start, self.end)

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

    def __mul__(self, other):
        if isinstance(other, Matrix):
            n = copy(self)
            n *= other
            return n

    __rmul__ = __mul__

    def __len__(self):
        return 2

    def __getitem__(self, item):
        if item == 0:
            return self.start
        elif item == 1:
            return self.end
        else:
            raise IndexError

    def reverse(self):
        return Line(self.end, self.start)

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


class QuadraticBezier(object):
    def __init__(self, start, control, end):
        self.start = Point(start)
        self.control = Point(control)
        self.end = Point(end)

    def __repr__(self):
        return 'QuadraticBezier(start=%s, control=%s, end=%s)' % (
            self.start, self.control, self.end)

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

    def __mul__(self, other):
        if isinstance(other, Matrix):
            n = copy(self)
            n *= other
            return n

    __rmul__ = __mul__

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


class CubicBezier(object):
    def __init__(self, start, control1, control2, end):
        self.start = Point(start)
        self.control1 = Point(control1)
        self.control2 = Point(control2)
        self.end = Point(end)

    def __repr__(self):
        return 'CubicBezier(start=%s, control1=%s, control2=%s, end=%s)' % (
            self.start, self.control1, self.control2, self.end)

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

    def __mul__(self, other):
        if isinstance(other, Matrix):
            n = copy(self)
            n *= other
            return n

    __rmul__ = __mul__

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


class Arc(object):
    def __init__(self, *args, **kwargs):
        """Arc objects can take different parameters to create arcs.
        Since we are often taking in SVG parameters.
        The main is SVG parameterization which is start, rx, ry, rotation, arc_flag, sweep_flag, end.
        So that we can do matrix transitions, the native parameterization is start, end, center, prx, pry, sweep
        'start, end, center, prx, pry' are points and sweep amount is a value in tau radians.
        prx is the point at angle 0 of the non-rotated ellipse.
        pry is the point at angle tau/4 of the non-rotated ellipse.
        The theta-rotation can be defined as the angle from center to prx
        If points are modified by an affine transformation, the arc is thusly transformed.
        The sweep angle can be a value greater than tau and less than -tau.

        prx->center->pry should form a right triangle.
        angle(center,end) - angle(center, start) should equal sweep or a angle mod thereof
        start and end should fall on the ellipse defined by prx, pry and center.
        """
        self.start = None
        self.end = None
        self.center = None
        self.prx = None
        self.pry = None
        self.sweep = None
        if len(args) == 7:
            # This is an svg parameterized call.
            # A rx ry x-axis-rotation large-arc-flag sweep-flag x y
            self.svg_parameterize(args[0], args[1], args[2], args[3], args[4], args[5], args[6])
            return
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
                self.prx = [self.center[0] + radius_s, self.center[1]]
                self.pry = [self.center[0], self.center[1] + radius_s]
            if self.end is not None and (self.prx is None or self.pry is None):
                radius_e = Point.distance(self.center, self.end)
                self.prx = [self.center[0] + radius_e, self.center[1]]
                self.pry = [self.center[0], self.center[1] + radius_e]
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
            self.start, self.end, self.center, self.prx, self.pry, self.sweep)

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
        return self

    def __mul__(self, other):
        if isinstance(other, Matrix):
            n = copy(self)
            n *= other
            return n

    __rmul__ = __mul__

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

    def reverse(self):
        return Arc(self.end, self.start, self.center, self.prx, self.pry, -self.sweep)

    def svg_parameterize(self, start, rx, ry, rotation_degrees, large_arc_flag, sweep_flag, end):
        rotation_radians = radians(rotation_degrees)
        large_arc_flag = bool(large_arc_flag)
        sweep_flag = bool(sweep_flag)
        # Conversion from endpoint to center parameterization
        # http://www.w3.org/TR/SVG/implnote.html#ArcImplementationNotes
        cosr = cos(rotation_radians)
        sinr = sin(rotation_radians)
        dx = (start[0] - end[0]) / 2.0
        dy = (start[1] - end[1]) / 2.0
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

        try:
            c = sqrt(abs((rx_sq * ry_sq - t1 - t2) / (t1 + t2)))
        except ZeroDivisionError:
            c = 0

        if large_arc_flag == sweep_flag:
            c = -c
        cxprim = c * rx * y1prim / ry
        cyprim = -c * ry * x1prim / rx

        center = [(cosr * cxprim - sinr * cyprim) + ((start[0] + end[0]) / 2),
                  (sinr * cxprim + cosr * cyprim) + ((start[1] + end[1]) / 2)]

        ux = (x1prim - cxprim) / rx
        uy = (y1prim - cyprim) / ry
        vx = (-x1prim - cxprim) / rx
        vy = (-y1prim - cyprim) / ry
        n = sqrt(ux * ux + uy * uy)
        p = ux
        theta_radians = acos(p / n)
        if uy < 0:
            theta_radians = -theta_radians
        theta_radians = theta_radians % tau

        n = sqrt((ux * ux + uy * uy) * (vx * vx + vy * vy))
        p = ux * vx + uy * vy
        d = p / n
        # In certain cases the above calculation can through inaccuracies
        # become just slightly out of range, f ex -1.0000000000000002.
        if d > 1.0:
            d = 1.0
        elif d < -1.0:
            d = -1.0
        delta_radians = acos(d)
        if (ux * vy - uy * vx) < 0:
            delta_radians = -delta_radians
        self.sweep = delta_radians % tau
        if not sweep_flag:
            self.sweep -= tau
        self.start = start
        self.prx = Point.polar(center, rotation_radians, rx)
        self.pry = Point.polar(center, rotation_radians + tau / 4.0, ry)
        self.center = center
        self.end = end

    def as_cubic_curves(self):
        sweep_limit = tau / 12
        arc_required = ceil(abs(self.sweep) / sweep_limit)
        slice = self.sweep / float(arc_required)

        start_angle = self.get_start_angle()
        theta = self.get_rotation()
        rx = self.get_radius_x()
        ry = self.get_radius_y()
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
        a = self.get_radius_x()
        b = self.get_radius_y()
        return a == b

    def get_radius(self):
        return self.get_radius_x()

    def get_radius_x(self):
        return Point.distance(self.center, self.prx)

    def get_radius_y(self):
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

    def __init__(self, *segments, **kw):
        self._segments = list(segments)
        self._length = None
        self._lengths = None
        self.closed = False
        if 'closed' in kw:
            self.closed = kw['closed']

    def __copy__(self):
        p = Path(closed=self.closed)
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
        return 'Path(%s, closed=%s)' % (
            ', '.join(repr(x) for x in self._segments), self.closed)

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

    def plot(self):
        for segment in self._segments:
            print(segment)
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

    def _is_closable(self):
        """Returns true if the end is on the start of a segment"""
        end = self[-1].end
        for segment in self:
            if segment.start == end:
                return True
        return False

    @property
    def closed(self):
        """Checks that the path is closed"""
        return self._closed and self._is_closable()

    @closed.setter
    def closed(self, value):
        value = bool(value)
        if value and not self._is_closable():
            raise ValueError("End does not coincide with a segment start.")
        self._closed = value

    def bbox(self):
        """returns a bounding box for the input Path"""
        bbs = [seg.bbox() for seg in self._segments]
        xmins, ymins, xmaxs, ymaxs = list(zip(*bbs))
        xmin = min(xmins)
        xmax = max(xmaxs)
        ymin = min(ymins)
        ymax = max(ymaxs)
        return xmin, ymin, xmax, ymax

    def d(self):
        if self.closed:
            segments = self[:-1]
        else:
            segments = self[:]

        current_pos = None
        parts = []
        previous_segment = None
        end = self[-1].end

        for segment in segments:
            start = segment.start
            # If the start of this segment does not coincide with the end of
            # the last segment or if this segment is actually the close point
            # of a closed path, then we should start a new subpath here.
            if isinstance(segment, Move) or (current_pos != start) or (
                    start == end and not isinstance(previous_segment, Move)):
                parts.append('M {0:G},{1:G}'.format(start[0], start[1]))

            if isinstance(segment, Line):
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
                    segment.get_radius_x(), segment.get_radius_y(), segment.get_rotation(),
                    int(segment.arc), int(segment.sweep),
                    segment.end[0], segment.end[1])
                )
            current_pos = segment.end
            previous_segment = segment

        if self.closed:
            parts.append('Z')

        return ' '.join(parts)


class ObjectParser:
    def __init__(self):
        self.path = Path()

    def start(self):
        pass

    def end(self):
        pass

    def move(self, start_pos, end_pos):
        self.path.append(Move(start_pos, end_pos))

    def line(self, start_pos, end_pos):
        self.path.append(Line(start_pos, end_pos))

    def quad(self, start_pos, control, end_pos):
        self.path.append(QuadraticBezier(start_pos, control, end_pos))

    def cubic(self, start_pos, control1, control2, end_pos):
        self.path.append(CubicBezier(start_pos, control1, control2, end_pos))

    def arc(self, start_pos, rx, ry, rotation, arc, sweep, end_pos):
        self.path.append(Arc(start_pos, rx, ry, rotation, arc, sweep, end_pos))

    def closed(self):
        pass
