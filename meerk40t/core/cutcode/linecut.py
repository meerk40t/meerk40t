from zinglplotter import plot_line

from .cutobject import CutObject


class LineCut(CutObject):
    def __init__(
        self, start_point, end_point, settings=None, passes=1, parent=None, color=None
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

    def __repr__(self):
        return f'LineCut({repr(self.start)}, {repr(self.end)}, settings="{self.settings}", passes={self.passes})'

    def generator(self):
        # pylint: disable=unsubscriptable-object
        start = self.start
        end = self.end
        return plot_line(start[0], start[1], end[0], end[1])

    def point(self, t):
        x0, y0 = self.start
        x1, y1 = self.end
        x = x1 * t + x0
        y = y1 * t + y0
        return x, y
