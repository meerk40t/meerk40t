from copy import copy

from meerk40t.core.node.mixins import (
    FunctionalParameter,
    Stroked,
    LabelDisplay,
    Suppressable,
)
from meerk40t.core.node.node import Fillrule, Linecap, Linejoin, Node
from meerk40t.svgelements import (
    SVG_ATTR_VECTOR_EFFECT,
    SVG_VALUE_NON_SCALING_STROKE,
    Matrix,
    Path,
    Polygon,
    Polyline,
)
from meerk40t.tools.geomstr import Geomstr


class PolylineNode(
    Node, Stroked, FunctionalParameter, LabelDisplay, Suppressable
):
    """
    PolylineNode is the bootstrapped node type for the 'elem polyline' type.
    """

    def __init__(self, *args, **kwargs):
        """
        If args contains 1 object it is expected to be a Geomstr or a Polyline Shape.
        If args contains 2+ objects these are expected to be points within the polyline.

        @param args:
        @param kwargs:
        """
        self.geometry = None
        if len(args) == 1:
            # Single value args.
            if isinstance(args[0], Geomstr):
                kwargs["geometry"] = args[0]
            else:
                kwargs["shape"] = args[0]
        if len(args) >= 2:
            # This is a points args.
            kwargs["geometry"] = Geomstr.lines(*args)
        shape = kwargs.get("shape")
        if shape is not None:
            # We have a polyline shape.
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
            if "closed" not in kwargs:
                kwargs["closed"] = isinstance(shape, Polygon)
            self.geometry = Geomstr.svg(Path(shape))
        self.matrix = None
        self.closed = None
        self.fill = None
        self.stroke = None
        self.stroke_width = None
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

        super().__init__(type="elem polyline", **kwargs)
        if "hidden" in kwargs:
            if isinstance(kwargs["hidden"], str):
                if kwargs["hidden"].lower() == "true":
                    kwargs["hidden"] = True
                else:
                    kwargs["hidden"] = False
            self.hidden = kwargs["hidden"]
        if self.geometry is None:
            self.geometry = Geomstr()
        self._formatter = "{element_type} {id} {stroke}"
        if self.stroke_width is None:
            self.stroke_width = 1000.0
        if self.matrix is None:
            self.matrix = Matrix()
        if self._stroke_zero is None:
            # This defines the stroke-width zero point scale
            self.stroke_width_zero()

        self.set_dirty_bounds()

    def __copy__(self):
        nd = self.node_dict
        nd["geometry"] = copy(self.geometry)
        nd["matrix"] = copy(self.matrix)
        nd["stroke"] = copy(self.stroke)
        nd["fill"] = copy(self.fill)
        return PolylineNode(**nd)

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.type}', {str(self._parent)})"

    def __len__(self):
        return len(self.geometry)

    @property
    def shape(self):
        if self.closed:
            return Polygon(
                points=list(self.geometry.as_points()),
                transform=self.matrix,
                stroke=self.stroke,
                fill=self.fill,
                stroke_width=self.stroke_width,
            )
        else:
            return Polyline(
                points=list(self.geometry.as_points()),
                transform=self.matrix,
                stroke=self.stroke,
                fill=self.fill,
                stroke_width=self.stroke_width,
            )

    @shape.setter
    def shape(self, new_shape):
        self.geometry = Geomstr.svg(Path(new_shape))

    def as_geometry(self, **kws) -> Geomstr:
        path = Geomstr(self.geometry)
        path.transform(self.matrix)
        return path

    def final_geometry(self, **kws) -> Geomstr:
        unit_factor = kws.get("unitfactor", 1)
        path = Geomstr(self.geometry)
        path.transform(self.matrix)
        # This is only true in scene units but will be compensated for devices by unit_factor
        unit_mm = 65535 / 2.54 / 10
        resolution = 0.05 * unit_mm
        # Do we have tabs?
        tablen = self.mktablength
        numtabs = self.mktabpositions
        if tablen and numtabs:
            path = Geomstr.wobble_tab(path, tablen, resolution, numtabs, unit_factor=unit_factor)
        # Is there a dash/dot pattern to apply?
        dashlen = self.stroke_dash
        irrelevant = 50
        if dashlen:
            path = Geomstr.wobble_dash(path, dashlen, resolution, irrelevant, unit_factor=unit_factor)
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
        geometry = self.as_geometry()
        # Polylines have length === raw_length
        return geometry.raw_length()

    def preprocess(self, context, matrix, plan):
        self.stroke_scaled = False
        self.stroke_scaled = True
        self.matrix *= matrix
        self.stroke_scaled = False
        self.set_dirty_bounds()

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Polyline"
        default_map.update(self.__dict__)
        return default_map

    def can_drop(self, drag_node):
        # Dragging element into element.
        return bool(
            hasattr(drag_node, "as_geometry") or
            hasattr(drag_node, "as_image") or
            (drag_node.type.startswith("op ") and drag_node.type != "op dots") or
            drag_node.type in ("file", "group")
        )

    def drop(self, drag_node, modify=True, flag=False):
        # Dragging element into element.
        if not self.can_drop(drag_node):
            return False
        if hasattr(drag_node, "as_geometry") or hasattr(drag_node, "as_image") or drag_node.type in ("file", "group"):
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
        points = list(self.as_geometry().as_points())

        max_index = len(points) - 1
        for idx, pt in enumerate(points):
            if idx == 0:
                self._points.append([pt.real, pt.imag, "endpoint"])
            elif idx == max_index:
                self._points.append([pt.real, pt.imag, "endpoint"])
            else:
                self._points.append([pt.real, pt.imag, "point"])
            if idx > 0:
                midpoint = (pt + lastpt) / 2
                self._points.append([midpoint.real, midpoint.imag, "midpoint"])
            lastpt = pt

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
