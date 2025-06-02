from copy import copy

from meerk40t.core.node.mixins import (
    FunctionalParameter,
    LabelDisplay,
    Stroked,
    Suppressable,
)
from meerk40t.core.node.node import Fillrule, Linecap, Linejoin, Node
from meerk40t.svgelements import (
    SVG_ATTR_VECTOR_EFFECT,
    SVG_VALUE_NON_SCALING_STROKE,
    Matrix,
    Point,
    SimpleLine,
)
from meerk40t.tools.geomstr import Geomstr


class LineNode(Node, Stroked, FunctionalParameter, LabelDisplay, Suppressable):
    """
    LineNode is the bootstrapped node type for the 'elem line' type.
    """

    def __init__(self, **kwargs):
        shape = kwargs.get("shape")
        if shape is not None:
            if "x1" not in kwargs:
                kwargs["x1"] = shape.x1
            if "y1" not in kwargs:
                kwargs["y1"] = shape.y1
            if "x2" not in kwargs:
                kwargs["x2"] = shape.x2
            if "y2" not in kwargs:
                kwargs["y2"] = shape.y2
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
        self.x1 = 0
        self.y1 = 0
        self.x2 = 0
        self.y2 = 0
        self.matrix = None
        self.fill = None
        self.stroke = None
        self.stroke_width = 1000.0
        self.stroke_scale = False
        self._stroke_zero = None
        self.linecap = Linecap.CAP_BUTT
        self.linejoin = Linejoin.JOIN_MITER
        self.fillrule = Fillrule.FILLRULE_EVENODD
        self.stroke_dash = None  # None or "" Solid
        unit_mm = 65535 / 2.54 / 10
        self.mktablength = 2 * unit_mm
        # tab_positions is a list of relative positions (percentage) of the overall path length
        self.mktabpositions = ""
        super().__init__(type="elem line", **kwargs)
        if "hidden" in kwargs:
            if isinstance(kwargs["hidden"], str):
                if kwargs["hidden"].lower() == "true":
                    kwargs["hidden"] = True
                else:
                    kwargs["hidden"] = False
            self.hidden = kwargs["hidden"]
        if self.x1 is None:
            self.x1 = 0
        if self.y1 is None:
            self.y1 = 0
        if self.x2 is None:
            self.x2 = 0
        if self.y2 is None:
            self.y2 = 0
        self._formatter = "{element_type} {id} {stroke}"
        if self.matrix is None:
            self.matrix = Matrix()

        if self._stroke_zero is None:
            # This defines the stroke-width zero point scale
            self.stroke_width_zero()

        self.set_dirty_bounds()
        self.functional_parameter = (
            "line",
            0,
            self.x1,
            self.y1,
            0,
            self.x2,
            self.y2,
            0,
            (self.x1 + self.x2) / 2.0,
            (self.y1 + self.y2) / 2.0,
        )

    def __copy__(self):
        nd = self.node_dict
        nd["matrix"] = copy(self.matrix)
        nd["stroke"] = copy(self.stroke)
        nd["fill"] = copy(self.fill)
        return LineNode(**nd)

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.type}', {str(self._parent)})"

    @property
    def p1(self):
        return complex(*self.matrix.point_in_matrix_space((self.x1, self.y1)))

    @property
    def p2(self):
        return complex(*self.matrix.point_in_matrix_space((self.x2, self.y2)))

    @property
    def shape(self):
        return SimpleLine(
            x1=self.x1,
            y1=self.y1,
            x2=self.x2,
            y2=self.y2,
            transform=self.matrix,
            stroke=self.stroke,
            fill=self.fill,
            stroke_width=self.stroke_width,
        )

    def as_geometry(self, **kws) -> Geomstr:
        path = Geomstr.lines(self.x1, self.y1, self.x2, self.y2)
        path.transform(self.matrix)
        return path

    def final_geometry(self, **kws) -> Geomstr:
        unit_factor = kws.get("unitfactor", 1)
        path = Geomstr.lines(self.x1, self.y1, self.x2, self.y2)
        path.transform(self.matrix)
        # This is only true in scene units but will be compensated for devices by unit_factor
        unit_mm = 65535 / 2.54 / 10
        resolution = 0.05 * unit_mm
        # Do we have tabs?
        tablen = 2 * unit_mm
        numtabs = 4
        numtabs = 0
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
        # self._sync_svg()
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

    def length(self):
        return abs(self.p1 - self.p2)

    def preprocess(self, context, matrix, plan):
        self.stroke_scaled = False
        self.stroke_scaled = True
        self.matrix *= matrix
        self.stroke_scaled = False
        # self._sync_svg()
        self.set_dirty_bounds()

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Line"
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
        p1 = Point(self.x1, self.y1)
        p2 = Point(self.x2, self.y2)
        p3 = Point(self.x1 + self.x2, self.y1 + self.y2)
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
                # method = self.mkparam[0]

                cx = (self.x1 + self.x2) / 2
                cy = (self.y1 + self.y2) / 2
                mx = getit(self.mkparam, 8, cx)
                my = getit(self.mkparam, 9, cy)

                if self.x1 != self.mkparam[2] or self.y1 != self.mkparam[3]:
                    # Start changed.
                    self.x1 = getit(self.mkparam, 2, self.x1)
                    self.y1 = getit(self.mkparam, 3, self.y1)
                    self.mkparam[8] = cx
                    self.mkparam[9] = cy
                elif self.x2 != self.mkparam[5] or self.y2 != self.mkparam[6]:
                    # End changed
                    self.x2 = getit(self.mkparam, 5, self.x2)
                    self.y2 = getit(self.mkparam, 6, self.y2)
                    self.mkparam[8] = cx
                    self.mkparam[9] = cy
                elif cx != mx or cy != my:
                    # Midpoint changed.
                    dx = mx - cx
                    dy = my - cy
                    self.x1 += dx
                    self.y1 += dy
                    self.x2 += dx
                    self.y2 += dy
                    self.mkparam[2] = self.x1
                    self.mkparam[3] = self.y1
                    self.mkparam[5] = self.x2
                    self.mkparam[6] = self.y2
                self.altered()
