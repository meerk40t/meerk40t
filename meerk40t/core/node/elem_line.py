from copy import copy

from meerk40t.core.node.mixins import Stroked
from meerk40t.core.node.node import Fillrule, Linecap, Linejoin, Node
from meerk40t.svgelements import (
    Point,
    Color,
    Matrix,
)
from meerk40t.tools.geomstr import Geomstr


class LineNode(Node, Stroked):
    """
    LineNode is the bootstrapped node type for the 'elem line' type.
    """

    def __init__(self, **kwargs):
        self.x1 = None
        self.y1 = None
        self.x2 = None
        self.y2 = None

        self.matrix = None
        self.fill = None
        self.stroke = Color("black")
        self.stroke_width = 1000.0
        self.stroke_scale = False
        self.linecap = Linecap.CAP_BUTT
        self.linejoin = Linejoin.JOIN_MITER
        self.fillrule = Fillrule.FILLRULE_EVENODD

        self._stroke_zero = None

        super().__init__(type="elem line", **kwargs)

        if self.matrix is None:
            self.matrix = Matrix()

        if self._stroke_zero is None:
            # This defines the stroke-width zero point scale
            self.stroke_width_zero()

        self._formatter = "{element_type} {id} {stroke}"
        self.set_dirty_bounds()

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.type}', {str(self._parent)})"

    def __copy__(self):
        nd = self.node_dict
        nd["matrix"] = copy(self.matrix)
        nd["fill"] = copy(self.fill)
        nd["stroke"] = copy(self.stroke)
        return LineNode(**nd)

    def scaled(self, sx, sy, ox, oy):
        """
        This is a special case of the modified call, we are scaling
        the node without fundamentally altering its properties
        """

        def apply_it(box):
            x0, y0, x1, y1 = box
            if sx != 1.0:
                d1 = x0 - ox
                d2 = x1 - ox
                x0 = ox + sx * d1
                x1 = ox + sx * d2
            if sy != 1.0:
                d1 = y0 - oy
                d2 = y1 - oy
                y0 = oy + sy * d1
                y1 = oy + sy * d2
            return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))

        if self._bounds_dirty or self._bounds is None:
            # A pity but we need proper data
            self.modified()
            return

        self._bounds = apply_it(self._bounds)
        delta = float(self.implied_stroke_width) / 2.0
        self._paint_bounds = (
            self._bounds[0] - delta,
            self._bounds[1] - delta,
            self._bounds[2] + delta,
            self._bounds[3] + delta,
        )
        self._points_dirty = True
        self.notify_scaled(self, sx=sx, sy=sy, ox=ox, oy=oy)

    def bbox(self, transformed=True, with_stroke=False):
        path = self.as_path()
        if transformed:
            bounds = path.bbox(mx=self.matrix)
        else:
            bounds = path.bbox()
        xmin, ymin, xmax, ymax = bounds
        if with_stroke:
            delta = float(self.implied_stroke_width) / 2.0
            return (
                xmin - delta,
                ymin - delta,
                xmax + delta,
                ymax + delta,
            )
        return xmin, ymin, xmax, ymax

    def preprocess(self, context, matrix, plan):
        self.stroke_scaled = False
        self.stroke_scaled = True
        self.matrix *= matrix
        self.stroke_scaled = False
        self.set_dirty_bounds()

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Line"
        default_map.update(self.__dict__)
        return default_map

    def drop(self, drag_node, modify=True):
        # Dragging element into element.
        if drag_node.type.startswith("elem"):
            if modify:
                self.insert_sibling(drag_node)
            return True
        return False

    def revalidate_points(self):
        bounds = self.bounds
        if bounds is None:
            return
        self._points = []
        cx = (bounds[0] + bounds[2]) / 2
        cy = (bounds[1] + bounds[3]) / 2
        # self._points.append([bounds[0], bounds[1], "bounds top_left"])
        # self._points.append([bounds[2], bounds[1], "bounds top_right"])
        # self._points.append([bounds[0], bounds[3], "bounds bottom_left"])
        # self._points.append([bounds[2], bounds[3], "bounds bottom_right"])
        # self._points.append([cx, cy, "bounds center_center"])
        # self._points.append([cx, bounds[1], "bounds top_center"])
        # self._points.append([cx, bounds[3], "bounds bottom_center"])
        # self._points.append([bounds[0], cy, "bounds center_left"])
        # self._points.append([bounds[2], cy, "bounds center_right"])
        p1 = Point(self.x2, self.y2)
        p2 = Point(self.x2, self.y2)
        p3 = Point(self.x2 + self.x2, self.y2 + self.y2)
        if not self.matrix.is_identity():
            p1 = self.matrix.point_in_matrix_space(p1)
            p2 = self.matrix.point_in_matrix_space(p2)
            p3 = self.matrix.point_in_matrix_space(p3)

        self._points.append([p1.x, p1.y, "endpoint"])
        self._points.append([p2.x, p2.y, "endpoint"])
        self._points.append([p3.x, p3.y, "midpoint"])

    def update_point(self, index, point):
        return False

    def add_point(self, point, index=None):
        return False

    def as_path(self):
        path = Geomstr()
        path.line(complex(self.x1, self.y1), complex(self.x2, self.y2))
        return path
