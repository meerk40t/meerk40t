from copy import copy
from math import sqrt

from meerk40t.core.node.node import Fillrule, Node
from meerk40t.svgelements import (
    SVG_ATTR_VECTOR_EFFECT,
    SVG_VALUE_NON_SCALING_STROKE,
    Path,
)


class EllipseNode(Node):
    """
    EllipseNode is the bootstrapped node type for the 'elem ellipse' type.
    """

    def __init__(
        self,
        shape,
        matrix=None,
        fill=None,
        stroke=None,
        stroke_width=None,
        fillrule=None,
        **kwargs,
    ):
        super(EllipseNode, self).__init__(type="elem ellipse", **kwargs)
        self.__formatter = "{element_type} {id} {stroke}"
        self.shape = shape
        self.settings = kwargs
        self.matrix = shape.transform if matrix is None else matrix
        self.fill = shape.fill if fill is None else fill
        self.stroke = shape.stroke if stroke is None else stroke
        self.stroke_width = shape.stroke_width if stroke_width is None else stroke_width
        self.fillrule = Fillrule.FILLRULE_NONZERO if fillrule is None else fillrule
        self._stroke_scaled = (
            shape.values.get(SVG_ATTR_VECTOR_EFFECT) != SVG_VALUE_NON_SCALING_STROKE
        )
        self.lock = False

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.type}', {str(self.shape)}, {str(self._parent)})"

    def __copy__(self):
        return EllipseNode(
            shape=copy(self.shape),
            matrix=copy(self.matrix),
            fill=copy(self.fill),
            stroke=copy(self.stroke),
            stroke_width=copy(self.stroke_width),
            fillrule=self.fillrule,
            **self.settings,
        )

    @property
    def bounds(self):
        if self._bounds_dirty:
            self._sync_svg()
            self._bounds = self.shape.bbox(with_stroke=True)
            self._bounds_dirty = False
        return self._bounds

    @property
    def stroke_scaled(self):
        return self._stroke_scaled

    @stroke_scaled.setter
    def stroke_scaled(self, v):
        if not v and self._stroke_scaled:
            self.stroke_width *= sqrt(abs(self.matrix.determinant))
        if v and not self._stroke_scaled:
            self.stroke_width /= sqrt(abs(self.matrix.determinant))
        self._stroke_scaled = v

    def implied_stroke_width(self, zoomscale=1.0):
        """If the stroke is not scaled, the matrix scale will scale the stroke, and we
        need to countermand that scaling by dividing by the square root of the absolute
        value of the determinant of the local matrix (1d matrix scaling)"""
        scalefactor = 1.0 if self._stroke_scaled else sqrt(abs(self.matrix.determinant))
        sw = self.stroke_width / scalefactor
        limit = 25 * sqrt(zoomscale) / scalefactor
        if sw < limit:
            sw = limit
        return sw

    def preprocess(self, context, matrix, commands):
        self.matrix *= matrix
        self._sync_svg()

    def default_map(self, default_map=None):
        default_map = super(EllipseNode, self).default_map(default_map=default_map)
        default_map["element_type"] = "Ellipse"
        default_map.update(self.settings)
        default_map["stroke"] = self.stroke
        default_map["fill"] = self.fill
        default_map["stroke-width"] = self.stroke_width
        default_map["matrix"] = self.matrix
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
        if len(self._points) < 9:
            self._points.extend([None] * (9 - len(self._points)))
        self._points[0] = [bounds[0], bounds[1], "bounds top_left"]
        self._points[1] = [bounds[2], bounds[1], "bounds top_right"]
        self._points[2] = [bounds[0], bounds[3], "bounds bottom_left"]
        self._points[3] = [bounds[2], bounds[3], "bounds bottom_right"]
        cx = (bounds[0] + bounds[2]) / 2
        cy = (bounds[1] + bounds[3]) / 2
        self._points[4] = [cx, cy, "bounds center_center"]
        self._points[5] = [cx, bounds[1], "bounds top_center"]
        self._points[6] = [cx, bounds[3], "bounds bottom_center"]
        self._points[7] = [bounds[0], cy, "bounds center_left"]
        self._points[8] = [bounds[2], cy, "bounds center_right"]
        obj = self.shape
        if hasattr(obj, "point"):
            if len(self._points) <= 11:
                self._points.extend([None] * (11 - len(self._points)))
            start = obj.point(0)
            end = obj.point(1)
            self._points[9] = [start[0], start[1], "endpoint"]
            self._points[10] = [end[0], end[1], "endpoint"]

    def update_point(self, index, point):
        return False

    def add_point(self, point, index=None):
        return False

    def _sync_svg(self):
        self.shape.values[SVG_ATTR_VECTOR_EFFECT] = SVG_VALUE_NON_SCALING_STROKE if self._stroke_scaled else ""
        self.shape.transform = self.matrix
        self.shape.stroke_width = self.stroke_width
        self._bounds_dirty = True

    def as_path(self):
        self._sync_svg()
        return abs(Path(self.shape))
