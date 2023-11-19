import numpy as np
from copy import copy


class PMatrix:
    def __init__(self, a=1.0, b=0.0, c=0.0, d=0.0, e=1.0, f=0, g=0.0, h=0.0, i=1.0):
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

    @classmethod
    def map(cls, p1, p2, p3, p4, r1, r2, r3, r4):
        p = PMatrix.perspective(p1, p2, p3, p4)
        r = PMatrix.perspective(r1, r2, r3, r4)
        mx = np.dot(np.linalg.inv(p.mx), r.mx)
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

        m = cls()
        m.mx[0, 0] = a
        m.mx[0, 1] = d
        m.mx[0, 2] = g

        m.mx[1, 0] = b
        m.mx[1, 1] = e
        m.mx[1, 2] = h

        m.mx[2, 0] = c
        m.mx[2, 1] = f
        m.mx[2, 2] = i
        return m
