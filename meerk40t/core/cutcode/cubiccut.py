from ...svgelements import Point
from ...tools.zinglplotter import ZinglPlotter
from .cutobject import CutObject


class CubicCut(CutObject):
    def __init__(
        self,
        start_point,
        control1,
        control2,
        end_point,
        settings=None,
        passes=1,
        parent=None,
    ):
        CutObject.__init__(
            self,
            start_point,
            end_point,
            settings=settings,
            passes=passes,
            parent=parent,
        )
        self.raster_step = 0
        self._control1 = control1
        self._control2 = control2

    def __repr__(self):
        return f'CubicCut({repr(self.start)}, {repr(self.c1())},  {repr(self.c2())}, {repr(self.end)}, settings="{self.settings}", passes={self.implicit_passes})'

    def __str__(self):
        return f"CubicCut({repr(self.start)}, {repr(self.c1())},  {repr(self.c2())}, {repr(self.end)}, passes={self.implicit_passes})"

    def c1(self):
        return self._control1 if self.normal else self._control2

    def c2(self):
        return self._control2 if self.normal else self._control1

    def length(self):
        return (
            Point.distance(self.start, self.c1())
            + Point.distance(self.c1(), self.c2())
            + Point.distance(self.c2(), self.end)
        )

    def generator(self):
        start = self.start
        c1 = self.c1()
        c2 = self.c2()
        end = self.end
        return ZinglPlotter.plot_cubic_bezier(
            start[0],
            start[1],
            c1[0],
            c1[1],
            c2[0],
            c2[1],
            end[0],
            end[1],
        )

    def point(self, t):
        x0, y0 = self.start
        x1, y1 = self.c1()
        x2, y2 = self.c2()
        x3, y3 = self.end
        e = 1 - t
        x = e * e * e * x0 + 3 * e * e * t * x1 + 3 * e * t * t * x2 + t * t * t * x3
        y = e * e * e * y0 + 3 * e * e * t * y1 + 3 * e * t * t * y2 + t * t * t * y3
        return x, y
