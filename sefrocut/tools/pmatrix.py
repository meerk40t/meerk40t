from copy import copy

import numpy as np
import numpy.linalg


class PMatrix:
    """
    PMatrix is a perspective matrix class. Primarily this is needed to perform Transform3x3 for geomstr classes.
    Unlike svgelements. Matrix used elsewhere this is a numpy based class and uses native @ commands for concat.
    """

    def __init__(self, a=1.0, b=0.0, c=0.0, d=0.0, e=1.0, f=0.0, g=0.0, h=0.0, i=1.0):
        if isinstance(a, PMatrix):
            self.mx = copy(a.mx)
            return
        if isinstance(a, np.ndarray):
            self.mx = a
            return
        self.mx = np.array([[a, b, c], [d, e, f], [g, h, i]])

    def __invert__(self):
        self.mx = np.linalg.inv(self.mx)
        return self

    def __str__(self):
        return f"PMatrix([{self.a}, {self.b}, {self.c}\n{self.d}, {self.e}, {self.f}\n{self.g}, {self.h}, {self.i}\n)"

    def __repr__(self):
        return f"PMatrix({self.a}, {self.b}, {self.c}, {self.d}, {self.e}, {self.f}, {self.g}, {self.h}, {self.i})"

    def __eq__(self, other):
        if other is None:
            return False
        try:
            if abs(self.a - other.a) > 1e-12:
                return False
            if abs(self.b - other.b) > 1e-12:
                return False
            if abs(self.c - other.c) > 1e-12:
                return False
            if abs(self.d - other.d) > 1e-12:
                return False
            if abs(self.e - other.e) > 1e-12:
                return False
            if abs(self.f - other.f) > 1e-12:
                return False
        except AttributeError:
            return False
        try:
            if abs(self.g - other.g) > 1e-12:
                return False
            if abs(self.h - other.h) > 1e-12:
                return False
            if abs(self.i - other.i) > 1e-12:
                return False
        except AttributeError:
            pass
        return True

    def __rmatmul__(self, other):
        return PMatrix(self.mx.__rmatmul__(other.mx))

    def __matmul__(self, other):
        return PMatrix(self.mx.__matmul__(other.mx))

    def __imatmul__(self, other):
        self.mx.__imatmul__(other)

    @classmethod
    def scale(cls, sx=1.0, sy=None, rx=0, ry=0):
        if sy is None:
            sy = sx
        r = cls(sx, 0, 0, 0, sy, 0)
        if rx != 0 or ry != 0:
            m0 = cls.translate(-rx, -ry)
            m1 = cls.translate(rx, ry)
            r = m1.mx @ r.mx @ m0.mx
        return cls(r)

    @classmethod
    def scale_x(cls, sx=1.0):
        return cls.scale(sx, 1.0)

    @classmethod
    def scale_y(cls, sy=1.0):
        return cls.scale(1.0, sy)

    @classmethod
    def translate(cls, tx=0.0, ty=0.0):
        return cls(1.0, 0.0, tx, 0.0, 1.0, ty)

    @classmethod
    def rotate(cls, angle=0.0, rx=0, ry=0):
        cos_theta = np.cos(float(angle))
        sin_theta = np.sin(float(angle))

        r = cls(cos_theta, -sin_theta, 0, sin_theta, cos_theta, 0, 0, 0, 1)
        if rx != 0 or ry != 0:
            m0 = cls.translate(-rx, -ry)
            m1 = cls.translate(rx, ry)
            r = m1.mx @ r.mx @ m0.mx
        return cls(r)

    @classmethod
    def map(cls, p1, p2, p3, p4, r1, r2, r3, r4):
        """
        Provides a matrix which maps points p1, p2, p3, p4 to points r1, r2, r3 r4 respectively.
        @param p1:
        @param p2:
        @param p3:
        @param p4:
        @param r1:
        @param r2:
        @param r3:
        @param r4:
        @return:
        """
        p = PMatrix.perspective(p1, p2, p3, p4)
        r = PMatrix.perspective(r1, r2, r3, r4)
        try:
            mx = r.mx @ np.linalg.inv(p.mx)
        except numpy.linalg.LinAlgError:
            return cls()
        return cls(mx)

    @classmethod
    def perspective(cls, p1, p2, p3, p4):
        """
        Create a matrix which transforms these four ordered points to the clockwise points of the unit-square.

        If G and H are very close to 0, this is an affine transformation. If they are not, then the perspective
        transform requires g and h,

        @param p1:
        @param p2:
        @param p3:
        @param p4:
        @return:
        """
        if isinstance(p1, complex):
            p1 = p1.real, p1.imag
        if isinstance(p2, complex):
            p2 = p2.real, p2.imag
        if isinstance(p3, complex):
            p3 = p3.real, p3.imag
        if isinstance(p4, complex):
            p4 = p4.real, p4.imag
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4

        i = 1
        try:
            j = (y1 - y2 + y3 - y4) / (y2 - y3)
            k = (x1 - x2 + x3 - x4) / (x4 - x3)
            m = (y4 - y3) / (y2 - y3)
            n = (x2 - x3) / (x4 - x3)

            h = i * (j - k * m) / (1 - m * n)
            g = i * (k - j * n) / (1 - m * n)
        except ZeroDivisionError:
            h = 0.0
            g = 0.0

        c = x1 * i
        f = y1 * i
        a = x4 * (g + i) - x1 * i
        b = x2 * (h + i) - x1 * i
        d = y4 * (g + i) - y1 * i
        e = y2 * (h + i) - y1 * i

        return cls(a, b, c, d, e, f, g, h, i)

    @property
    def a(self):
        return self.mx[0, 0]

    @property
    def b(self):
        return self.mx[0, 1]

    @property
    def c(self):
        return self.mx[0, 2]

    @property
    def d(self):
        return self.mx[1, 0]

    @property
    def e(self):
        return self.mx[1, 1]

    @property
    def f(self):
        return self.mx[1, 2]

    @property
    def g(self):
        return self.mx[2, 0]

    @property
    def h(self):
        return self.mx[2, 1]

    @property
    def i(self):
        return self.mx[2, 2]

    def point_in_matrix(self, x, y):
        if isinstance(x, float):
            count = 1
            pts = np.vstack((x, y, np.ones(count)))
            result = np.dot(self.mx, pts)
            return (result[0] / result[2] + 1j * result[1] / result[2])[0]
        count = len(x)
        pts = np.vstack((x, y, np.ones(count)))
        result = np.dot(self.mx, pts)
        return result[0] / result[2] + 1j * result[1] / result[2]

    def is_identity(self):
        return (
            self.a == 1
            and self.b == 0
            and self.c == 0
            and self.d == 0
            and self.e == 1
            and self.f == 0
            and self.g == 0
            and self.h == 0
            and self.i == 1
        )
