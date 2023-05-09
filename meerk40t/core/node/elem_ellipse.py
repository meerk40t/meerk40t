from copy import copy
from math import tau, cos, sin, sqrt

from meerk40t.core.node.node import Fillrule, Node
from meerk40t.svgelements import (
    Point, Matrix, Color,
)
from meerk40t.tools.geomstr import Geomstr


class EllipseNode(Node):
    """
    EllipseNode is the bootstrapped node type for the 'elem ellipse' type.
    """

    def __init__(self, **kwargs):
        self.cx = None
        self.cy = None
        self.rx = None
        self.ry = None

        self.matrix = None
        self.fill = None
        self.stroke = Color("black")
        self.stroke_width = 1000.0
        self.stroke_scale = False
        self.fillrule = Fillrule.FILLRULE_EVENODD

        self._stroke_zero = None

        super().__init__(type="elem ellipse", **kwargs)
        if self.matrix is None:
            self.matrix = Matrix()

        if self._stroke_zero is None:
            # This defines the stroke-width zero point scale
            self.stroke_width_zero()

        self.__formatter = "{element_type} {id} {stroke}"
        self.set_dirty_bounds()

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.type}', {str(self._parent)})"

    def __copy__(self):
        nd = self.node_dict
        nd["cx"] = copy(self.cx)
        nd["cy"] = copy(self.cy)
        nd["rx"] = copy(self.rx)
        nd["ry"] = copy(self.ry)
        nd["matrix"] = copy(self.matrix)
        nd["fill"] = copy(self.fill)
        nd["stroke"] = copy(self.stroke)
        nd["stroke_width"] = copy(self.stroke_width)
        return EllipseNode(**nd)

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
        self.notify_scaled(self, sx=sx, sy=sy, ox=ox, oy=oy)

    def point_at_t(self, t):
        """
        find the point that corresponds to given value t.
        Where t=0 is the first point and t=tau is the final point.

        In the case of a circle: t = angle.

        :param t:
        :return:
        """
        return complex(self.cx + self.rx * cos(t), self.cy + self.ry * sin(t))

    @property
    def path(self):
        path = Geomstr()
        steps = 4
        step_size = tau / steps
        if self.matrix.determinant < 0:
            step_size = -step_size

        t_start = 0
        t_end = step_size
        for i in range(steps):
            path.arc(self.point_at_t(t_start), self.point_at_t((t_start + t_end) / 2), self.point_at_t(t_end))
            t_start = t_end
            t_end += step_size
        return path

    def bbox(self, transformed=True, with_stroke=False):
        path = self.path
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

    @property
    def stroke_scaled(self):
        return self.stroke_scale

    @stroke_scaled.setter
    def stroke_scaled(self, v):
        """
        Setting stroke_scale directly will not resize the stroke-width based on current scaling. This function allows
        the toggling of the stroke-scaling without the current stroke_width being affected.

        @param v:
        @return:
        """
        if bool(v) == bool(self.stroke_scale):
            # Unchanged.
            return
        if not v:
            self.stroke_width *= self.stroke_factor
        self.stroke_width_zero()
        self.stroke_scale = v

    @property
    def implied_stroke_width(self):
        """
        The implied stroke width is stroke_width if not scaled or the scaled stroke_width if scaled.

        @return:
        """
        if self.stroke_scale:
            factor = self.stroke_factor
        else:
            factor = 1
        if hasattr(self, "stroke"):
            # print (f"Have stroke {self.stroke}, {type(self.stroke).__name__}")
            if self.stroke is None or self.stroke.argb is None:
                # print ("set to zero")
                factor = 0

        return self.stroke_width * factor

    @property
    def stroke_factor(self):
        """
        The stroke factor is the ratio of the new to old stroke-width scale.

        @return:
        """
        matrix = self.matrix
        stroke_one = sqrt(abs(matrix.determinant))
        try:
            return stroke_one / self._stroke_zero
        except AttributeError:
            return 1.0

    def stroke_reify(self):
        """Set the stroke width to the real stroke width."""
        if self.stroke_scale:
            self.stroke_width *= self.stroke_factor
        self.stroke_width_zero()

    def stroke_width_zero(self):
        """
        Ensures the current stroke scale is marked as stroke_zero.
        @return:
        """
        matrix = self.matrix
        self._stroke_zero = sqrt(abs(matrix.determinant))
