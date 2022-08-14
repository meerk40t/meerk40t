from copy import copy
from math import sqrt

from meerk40t.core.node.node import Node
from meerk40t.svgelements import SVG_ATTR_VECTOR_EFFECT, SVG_VALUE_NON_SCALING_STROKE


class TextNode(Node):
    """
    TextNode is the bootstrapped node type for the 'elem text' type.
    """

    def __init__(
        self,
        text=None,
        matrix=None,
        fill=None,
        stroke=None,
        stroke_width=None,
        stroke_scale=True,
        underline=None,
        strikethrough=None,
        overline=None,
        texttransform=None,
        **kwargs,
    ):
        super(TextNode, self).__init__(type="elem text", **kwargs)
        self._formatter = "{element_type} {id}: {text}"
        self.text = text
        self.settings = kwargs
        self.matrix = text.transform if matrix is None else matrix
        self.fill = text.fill if fill is None else fill
        self.stroke = text.stroke if stroke is None else stroke
        self.stroke_width = text.stroke_width if stroke_width is None else stroke_width
        self._stroke_scaled = (
            (text.values.get(SVG_ATTR_VECTOR_EFFECT) != SVG_VALUE_NON_SCALING_STROKE)
            if stroke_scale is None
            else stroke_scale
        )
        self.underline = False if underline is None else underline
        self.strikethrough = False if strikethrough is None else strikethrough

        # For sake of completeness, afaik there is no way to display it with wxpython
        self.overline = False if overline is None else overline
        self.texttransform = "" if texttransform is None else texttransform
        self.lock = False

    def __copy__(self):
        return TextNode(
            text=copy(self.text),
            matrix=copy(self.matrix),
            fill=copy(self.fill),
            stroke=copy(self.stroke),
            stroke_width=self.stroke_width,
            stroke_scale=self._stroke_scaled,
            underline=self.underline,
            strikethrough=self.strikethrough,
            overline=self.overline,
            texttransform=self.texttransform,
            **self.settings,
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
        scalefactor = 1.0 if self._stroke_scaled else sqrt(abs(self.matrix.determinant))
        sw = self.stroke_width / scalefactor
        limit = 25 * sqrt(zoomscale) * scalefactor
        if sw < limit:
            sw = limit
        return sw

    @property
    def bounds(self):
        if self._bounds_dirty:
            self._sync_svg()
            self._bounds = self.text.bbox(with_stroke=True)
        return self._bounds

    def preprocess(self, context, matrix, commands):
        self.stroke_scaled = True
        self.matrix *= matrix
        self.stroke_scaled = False
        self._sync_svg()
        self.text.width = 0
        self.text.height = 0
        self.text.text = context.elements.mywordlist.translate(self.text.text)
        if self.parent.type != "op raster":
            commands.append(self.remove_text)

    def remove_text(self):
        self.remove_node()

    def default_map(self, default_map=None):
        default_map = super(TextNode, self).default_map(default_map=default_map)
        default_map["element_type"] = "Text"
        default_map.update(self.settings)
        default_map["text"] = self.text.text
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
        obj = self.text
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
        self.text.values[SVG_ATTR_VECTOR_EFFECT] = SVG_VALUE_NON_SCALING_STROKE if not self._stroke_scaled else ""
        self.text.transform = self.matrix
        self.text.stroke_width = self.stroke_width
        self._bounds_dirty = True
