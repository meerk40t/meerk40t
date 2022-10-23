from copy import copy
from math import sqrt

from meerk40t.core.node.node import Fillrule, Linejoin, Node
from meerk40t.svgelements import (
    SVG_ATTR_VECTOR_EFFECT,
    SVG_VALUE_NON_SCALING_STROKE,
    Path,
    Rect,
)


class RectNode(Node):
    """
    RectNode is the bootstrapped node type for the 'elem rect' type.
    """

    def __init__(
        self,
        shape=None,
        matrix=None,
        fill=None,
        stroke=None,
        stroke_width=None,
        stroke_scale=None,
        linejoin=None,
        fillrule=None,
        label=None,
        lock=False,
        settings=None,
        **kwargs,
    ):
        if settings is None:
            settings = dict()
        settings.update(kwargs)
        if "type" in settings:
            del settings["type"]
        super(RectNode, self).__init__(type="elem rect", **settings)
        self._formatter = "{element_type} {id} {stroke}"
        assert isinstance(shape, Rect)
        self.shape = shape
        self.settings = settings
        self.matrix = shape.transform if matrix is None else matrix
        self.fill = shape.fill if fill is None else fill
        self.stroke = shape.stroke if stroke is None else stroke
        self.stroke_width = shape.stroke_width if stroke_width is None else stroke_width
        self._stroke_scaled = (
            (shape.values.get(SVG_ATTR_VECTOR_EFFECT) != SVG_VALUE_NON_SCALING_STROKE)
            if stroke_scale is None
            else stroke_scale
        )
        self.set_dirty_bounds()
        self.linejoin = Linejoin.JOIN_MITER if linejoin is None else linejoin
        self.fillrule = Fillrule.FILLRULE_EVENODD if fillrule is None else fillrule
        self.label = label
        self.lock = lock

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.type}', {str(self.shape)}, {str(self._parent)})"

    def __copy__(self):
        return RectNode(
            shape=copy(self.shape),
            matrix=copy(self.matrix),
            fill=copy(self.fill),
            stroke=copy(self.stroke),
            stroke_width=self.stroke_width,
            stroke_scale=self._stroke_scaled,
            linejoin=self.linejoin,
            fillrule=self.fillrule,
            label=self.label,
            lock=self.lock,
            settings=self.settings,
        )

    @property
    def stroke_scaled(self):
        return self._stroke_scaled

    @stroke_scaled.setter
    def stroke_scaled(self, v):
        if not v and self._stroke_scaled:
            matrix = self.matrix
            self.stroke_width *= sqrt(abs(matrix.determinant))
        if v and not self._stroke_scaled:
            matrix = self.matrix
            self.stroke_width /= sqrt(abs(matrix.determinant))
        self._stroke_scaled = v

    def implied_stroke_width(self, zoomscale=1.0):
        """If the stroke is not scaled, the matrix scale will scale the stroke, and we
        need to countermand that scaling by dividing by the square root of the absolute
        value of the determinant of the local matrix (1d matrix scaling)"""
        scalefactor = sqrt(abs(self.matrix.determinant))
        if self.stroke_scaled:
            # Our implied stroke-width is prescaled.
            return self.stroke_width
        else:
            sw = self.stroke_width / scalefactor
            return sw

    def bbox(self, transformed=True, with_stroke=False):
        self._sync_svg()
        return self.shape.bbox(transformed=transformed, with_stroke=with_stroke)

    def preprocess(self, context, matrix, plan):
        self.stroke_scaled = True
        self.matrix *= matrix
        self.stroke_scaled = False
        self._sync_svg()
        self.set_dirty_bounds()

    def default_map(self, default_map=None):
        default_map = super(RectNode, self).default_map(default_map=default_map)
        default_map["element_type"] = "Rect"
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
        self.shape.values[SVG_ATTR_VECTOR_EFFECT] = (
            SVG_VALUE_NON_SCALING_STROKE if not self._stroke_scaled else ""
        )
        self.shape.transform = self.matrix
        self.shape.stroke_width = self.stroke_width
        self.shape.stroke = self.stroke
        try:
            del self.shape.values["viewport_transform"]
            # If we had transforming viewport that is no longer relevant
        except KeyError:
            pass

    def as_path(self):
        self._sync_svg()
        return abs(Path(self.shape))
