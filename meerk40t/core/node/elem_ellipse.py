import math
from copy import copy
from math import cos, sin

from meerk40t.core.node.mixins import Stroked
from meerk40t.core.node.node import Fillrule, Node
from meerk40t.svgelements import (
    SVG_ATTR_VECTOR_EFFECT,
    SVG_VALUE_NON_SCALING_STROKE,
    Ellipse,
    Matrix,
    Point,
)
from meerk40t.tools.geomstr import Geomstr


class EllipseNode(Node, Stroked):
    """
    EllipseNode is the bootstrapped node type for the 'elem ellipse' type.
    """

    def __init__(self, **kwargs):
        shape = kwargs.get("shape")
        if shape is not None:
            if "cx" not in kwargs:
                kwargs["cx"] = shape.cx
            if "cy" not in kwargs:
                kwargs["cy"] = shape.cy
            if "rx" not in kwargs:
                kwargs["rx"] = shape.rx
            if "ry" not in kwargs:
                kwargs["ry"] = shape.ry
            if "stroke" not in kwargs:
                kwargs["stroke"] = shape.stroke
            if "stroke_width" not in kwargs:
                kwargs["stroke_width"] = shape.implicit_stroke_width
            if "fill" not in kwargs:
                kwargs["fill"] = shape.fill
            if "matrix" not in kwargs:
                kwargs["matrix"] = shape.transform
            if "stroke_scale" not in kwargs:
                kwargs["stroke_scale"] = (
                    shape.values.get(SVG_ATTR_VECTOR_EFFECT)
                    != SVG_VALUE_NON_SCALING_STROKE
                )
        self.cx = 0
        self.cy = 0
        self.rx = 0
        self.ry = 0
        self.matrix = None
        self.fill = None
        self.stroke = None
        self.stroke_width = 1000.0
        self.stroke_scale = False
        self._stroke_zero = None
        self.fillrule = Fillrule.FILLRULE_EVENODD

        super().__init__(type="elem ellipse", **kwargs)
        self.__formatter = "{element_type} {id} {stroke}"
        if self.cx is None:
            self.cx = 0
        if self.cy is None:
            self.cy = 0
        if self.rx is None:
            self.rx = 0
        if self.ry is None:
            self.ry = 0
        if self.matrix is None:
            self.matrix = Matrix()

        if self._stroke_zero is None:
            # This defines the stroke-width zero point scale
            self.stroke_width_zero()

        self.set_dirty_bounds()

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.type}', {str(self._parent)})"

    def __copy__(self):
        nd = self.node_dict
        nd["matrix"] = copy(self.matrix)
        nd["stroke"] = copy(self.stroke)
        nd["fill"] = copy(self.fill)
        return EllipseNode(**nd)

    @property
    def shape(self):
        return Ellipse(
            cx=self.cx,
            cy=self.cy,
            rx=self.rx,
            ry=self.ry,
            transform=self.matrix,
            stroke=self.stroke,
            fill=self.fill,
            stroke_width=self.stroke_width,
        )

    def point_at_t(self, t):
        """
        find the point that corresponds to given value t.
        Where t=0 is the first point and t=tau is the final point.

        In the case of a circle: t = angle.

        :param t:
        :return:
        """
        return complex(self.cx + self.rx * cos(t), self.cy + self.ry * sin(t))

    def as_geometry(self):
        path = Geomstr.ellipse(self.rx, self.ry, self.cx, self.cy, 0, 12)
        path.transform(self.matrix)
        return path

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
            return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)

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
        self.notify_scaled(self, sx=sx, sy=sy, ox=ox, oy=oy)

    def bbox(self, transformed=True, with_stroke=False):
        # self._sync_svg()
        # bounds = self.shape.bbox(transformed=transformed, with_stroke=False)
        # if bounds is None:
        #     # degenerate paths can have no bounds.
        #     return None
        geometry = self.as_geometry()
        if transformed:
            bounds = geometry.bbox(mx=self.matrix)
        else:
            bounds = geometry.bbox()
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
        default_map["element_type"] = "Ellipse"
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
        npoints = [
            Point(self.cx - self.rx, self.cy),
            Point(self.cx, self.cy - self.ry),
            Point(self.cx + self.rx, self.cy),
            Point(self.cx, self.cy + self.ry),
        ]
        p1 = Point(self.cx, self.cy)
        if not self.matrix.is_identity():
            points = list(map(self.matrix.point_in_matrix_space, npoints))
            p1 = self.matrix.point_in_matrix_space(p1)
        else:
            points = npoints
        for pt in points:
            self._points.append([pt.x, pt.y, "point"])
        self._points.append([p1.x, p1.y, "bounds center_center"])

    def update_point(self, index, point):
        return False

    def add_point(self, point, index=None):
        return False

    def as_path(self):
        geometry = self.as_geometry()
        path = geometry.as_path()
        path.stroke = self.stroke
        path.fill = self.fill
        path.stroke_width = self.stroke_width
        path.values[SVG_ATTR_VECTOR_EFFECT] = (
            SVG_VALUE_NON_SCALING_STROKE if not self.stroke_scale else ""
        )
        return path
