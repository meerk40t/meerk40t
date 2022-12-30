from copy import copy
from math import sqrt

from meerk40t.core.node.node import Fillrule, Linecap, Linejoin, Node
from meerk40t.core.parameters import Parameters
from meerk40t.svgelements import Matrix


class GeomstrNode(Node, Parameters):
    """
    GeomstrNode is the bootstrapped node type for the 'elem geomstr' type.
    """

    def __init__(self, **kwargs):
        self.path = None
        self.matrix = None
        self.fill = None
        self.stroke = None
        self.stroke_width = 1000
        self.stroke_scale = False
        self.linecap = Linecap.CAP_BUTT
        self.linejoin = Linejoin.JOIN_MITER
        self.fillrule = Fillrule.FILLRULE_EVENODD
        super().__init__(type="elem geomstr", **kwargs)
        self._formatter = "{element_type} {id} {stroke}"
        if self.matrix is None:
            self.matrix = Matrix()

    def __copy__(self):
        nd = self.node_dict
        nd["path"] = copy(self.path)
        nd["matrix"] = copy(self.matrix)
        nd["fill"] = copy(self.fill)
        nd["stroke_width"] = copy(self.stroke_width)
        return GeomstrNode(**nd)

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.type}', {str(len(self.path))}, {str(self._parent)})"

    @property
    def stroke_scaled(self):
        return self.stroke_scale

    @stroke_scaled.setter
    def stroke_scaled(self, v):
        if not v and self.stroke_scale:
            matrix = self.matrix
            self.stroke_width *= sqrt(abs(matrix.determinant))
        if v and not self.stroke_scale:
            matrix = self.matrix
            self.stroke_width /= sqrt(abs(matrix.determinant))
        self.stroke_scale = v

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
        return self.path.bbox(self.matrix)

    def preprocess(self, context, matrix, plan):
        self.path.transform(self.matrix)
        self.path.transform(matrix)
        self.set_dirty_bounds()

    def default_map(self, default_map=None):
        default_map = super(GeomstrNode, self).default_map(default_map=default_map)
        default_map["element_type"] = "Geomstr"
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

    def update_point(self, index, point):
        return False

    def add_point(self, point, index=None):
        return False

    def as_path(self):
        return None
