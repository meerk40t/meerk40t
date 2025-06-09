from copy import copy
from math import cos, sin, sqrt, tau

from meerk40t.core.node.mixins import (
    FunctionalParameter,
    LabelDisplay,
    Stroked,
    Suppressable,
)
from meerk40t.core.node.node import Fillrule, Node
from meerk40t.svgelements import (
    SVG_ATTR_VECTOR_EFFECT,
    SVG_VALUE_NON_SCALING_STROKE,
    Ellipse,
    Matrix,
    Point,
)
from meerk40t.tools.geomstr import Geomstr


class EllipseNode(Node, Stroked, FunctionalParameter, LabelDisplay, Suppressable):
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
        self.stroke_dash = None  # None or "" Solid
        self.fillrule = Fillrule.FILLRULE_EVENODD
        unit_mm = 65535 / 2.54 / 10
        self.mktablength = 2 * unit_mm
        # tab_positions is a list of relative positions (percentage) of the overall path length
        self.mktabpositions = ""

        super().__init__(type="elem ellipse", **kwargs)
        if "hidden" in kwargs:
            if isinstance(kwargs["hidden"], str):
                if kwargs["hidden"].lower() == "true":
                    kwargs["hidden"] = True
                else:
                    kwargs["hidden"] = False
            self.hidden = kwargs["hidden"]
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
        if self.rx == self.ry:
            self.functional_parameter = (
                "circle",
                0,
                self.cx,
                self.cy,
                0,
                self.cx + cos(tau * 7 / 8) * self.rx,
                self.cy + sin(tau * 7 / 8) * self.ry,
            )
        else:
            # store two extreme points
            self.functional_parameter = (
                "ellipse",
                0,
                self.cx,
                self.cy,
                0,
                self.cx + self.rx,
                self.cy,
                0,
                self.cx,
                self.cy + self.ry,
            )
            # print(
            #     f"Old: ({self.cx:.0f}, {self.cy:.0f}), rx={self.rx:.0f}, ry={self.ry:.0f}"
            # )

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

    def as_geometry(self, **kws) -> Geomstr:
        path = Geomstr.ellipse(self.rx, self.ry, self.cx, self.cy, 0, 12)
        path.transform(self.matrix)
        return path

    def final_geometry(self, **kws) -> Geomstr:
        """
        This will resolve and apply all effects like tabs and dashes/dots
        """
        unit_factor = kws.get("unitfactor", 1)
        path = Geomstr.ellipse(self.rx, self.ry, self.cx, self.cy, 0, 12)
        path.transform(self.matrix)
        # This is only true in scene units but will be compensated for devices by unit_factor
        unit_mm = 65535 / 2.54 / 10
        resolution = 0.05 * unit_mm
        # Do we have tabs?
        tablen = self.mktablength
        numtabs = self.mktabpositions
        if tablen and numtabs:
            path = Geomstr.wobble_tab(
                path, tablen, resolution, numtabs, unit_factor=unit_factor
            )
        # Is there a dash/dot pattern to apply?
        dashlen = self.stroke_dash
        irrelevant = 50
        if dashlen:
            path = Geomstr.wobble_dash(
                path, dashlen, resolution, irrelevant, unit_factor=unit_factor
            )

        return path

    def scaled(self, sx, sy, ox, oy, interim=False):
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
        self.set_dirty()
        self.notify_scaled(self, sx=sx, sy=sy, ox=ox, oy=oy, interim=interim)

    def bbox(self, transformed=True, with_stroke=False):
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

    def length(self):
        """
        The calculation of the length of an ellipse using the Ramanujan approximation
        @return:
        """
        a = abs(complex(*self.matrix.transform_vector([self.rx, 0])))
        b = abs(complex(*self.matrix.transform_vector([0, self.ry])))
        if a == b:
            return tau * self.rx
        if b > a:
            a, b = b, a
        h = ((a - b) * (a - b)) / ((a + b) * (a + b))
        return tau / 2 * (a + b) * (1 + (3 * h / (10 + sqrt(4 - 3 * h))))

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

    def can_drop(self, drag_node):
        if self.is_a_child_of(drag_node):
            return False
        # Dragging element into element.
        return bool(
            hasattr(drag_node, "as_geometry")
            or hasattr(drag_node, "as_image")
            or (drag_node.type.startswith("op ") and drag_node.type != "op dots")
            or drag_node.type in ("file", "group")
        )

    def drop(self, drag_node, modify=True, flag=False):
        # Dragging element into element.
        if not self.can_drop(drag_node):
            return False
        if (
            hasattr(drag_node, "as_geometry")
            or hasattr(drag_node, "as_image")
            or drag_node.type in ("file", "group")
        ):
            if modify:
                self.insert_sibling(drag_node)
            return True

        elif drag_node.type.startswith("op"):
            # If we drag an operation to this node,
            # then we will reverse the game, but we will take the operations color
            old_references = list(self._references)
            result = drag_node.drop(self, modify=modify, flag=flag)
            if result and modify:
                if hasattr(drag_node, "color") and drag_node.color is not None:
                    self.stroke = drag_node.color
                for ref in old_references:
                    ref.remove_node()
            return result
        return False

    def revalidate_points(self):
        bounds = self.bounds
        if bounds is None:
            return
        self._points = []
        # cx = (bounds[0] + bounds[2]) / 2
        # cy = (bounds[1] + bounds[3]) / 2
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

    @property
    def functional_parameter(self):
        return self.mkparam

    @functional_parameter.setter
    def functional_parameter(self, value):
        def getit(data, idx, default):
            if idx < len(data):
                return data[idx]
            else:
                return default

        if isinstance(value, (list, tuple)):
            self.mkparam = value
            if self.mkparam:
                method = self.mkparam[0]
                if method == "circle":
                    ncx = getit(self.mkparam, 2, self.cx)
                    ncy = getit(self.mkparam, 3, self.cy)
                    ptx = getit(self.mkparam, 5, self.cx + self.rx)
                    pty = getit(self.mkparam, 6, self.cy)
                    radius = sqrt((ncx - ptx) ** 2 + (ncy - pty) ** 2)
                    if radius > 0:
                        self.cx = ncx
                        self.cy = ncy
                        self.rx = radius
                        self.ry = radius
                        self.altered()
                elif method == "ellipse":
                    ncx = getit(self.mkparam, 2, self.cx)
                    ncy = getit(self.mkparam, 3, self.cy)
                    pt1x = getit(self.mkparam, 5, self.cx + self.rx)
                    pt1y = getit(self.mkparam, 6, self.cy)
                    pt2x = getit(self.mkparam, 8, self.cx)
                    pt2y = getit(self.mkparam, 9, self.cy + self.ry)
                    if ncx != self.cx or ncy != self.cy:
                        self.cx = ncx
                        self.cy = ncy
                    else:
                        rx = pt1x - pt2x
                        ry = pt2y - pt1y
                        ncx = pt1x - rx
                        ncy = pt2y - ry
                        rx = abs(rx)
                        ry = abs(ry)
                        self.cx = ncx
                        self.cy = ncy
                        self.rx = rx
                        self.ry = ry
                    self.mkparam = (
                        "ellipse",
                        0,
                        self.cx,
                        self.cy,
                        0,
                        self.cx + self.rx,
                        self.cy,
                        0,
                        self.cx,
                        self.cy + self.ry,
                    )
                    self.altered()
