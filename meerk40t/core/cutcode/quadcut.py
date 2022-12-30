from ...svgelements import Point
from ...tools.zinglplotter import ZinglPlotter
from .cutobject import CutObject


class QuadCut(CutObject):
    def __init__(
        self,
        start_point,
        control_point,
        end_point,
        settings=None,
        passes=1,
        parent=None,
        color=None,
    ):
        CutObject.__init__(
            self,
            start_point,
            end_point,
            settings=settings,
            passes=passes,
            parent=parent,
            color=color,
        )
        self.raster_step = 0
        self._control = control_point

    def __repr__(self):
        return f'QuadCut({repr(self.start)}, {repr(self.c())}, {repr(self.end)}, settings="{self.settings}", passes={self.passes})'

    def __str__(self):
        return f"QuadCut({repr(self.start)}, {repr(self.c())}, {repr(self.end)}, passes={self.passes})"

    def c(self):
        return self._control

    def length(self):
        return Point.distance(self.start, self.c()) + Point.distance(self.c(), self.end)

    def generator(self):
        # pylint: disable=unsubscriptable-object
        start = self.start
        c = self.c()
        end = self.end
        return ZinglPlotter.plot_quad_bezier(
            start[0],
            start[1],
            c[0],
            c[1],
            end[0],
            end[1],
        )

    def point(self, t):
        x0, y0 = self.start
        x1, y1 = self.c()
        x2, y2 = self.end
        e = 1 - t
        x = e * e * x0 + 2 * e * t * x1 + t * t * x2
        y = e * e * y0 + 2 * e * t * y1 + t * t * y2
        return x, y
