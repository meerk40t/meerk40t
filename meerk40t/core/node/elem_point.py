from copy import copy

from meerk40t.core.node.node import Node
from meerk40t.svgelements import Matrix, Point, Color
from meerk40t.tools.geomstr import Geomstr


class PointNode(Node):
    """
    PointNode is the bootstrapped node type for the 'elem point' type.
    """

    def __init__(self, **kwargs):
        self.x = 0
        self.y = 0
        self.matrix = None
        self.fill = None
        self.stroke = Color("black")
        self.stroke_width = 1000.0
        super().__init__(type="elem point", **kwargs)
        if self.matrix is None:
            self.matrix = Matrix()

        self._formatter = "{element_type} {id} {stroke}"
        self.set_dirty_bounds()

    def __copy__(self):
        nd = self.node_dict
        nd["matrix"] = copy(self.matrix)
        nd["fill"] = copy(self.fill)
        nd["stroke_width"] = copy(self.stroke_width)
        return PointNode(**nd)

    def preprocess(self, context, matrix, plan):
        self.matrix *= matrix
        self.set_dirty_bounds()

    def bbox(self, transformed=True, with_stroke=False):
        if transformed:
            p = self.matrix.point_in_matrix_space((self.x, self.y))
            return p[0], p[1], p[0], p[1]
        else:
            return self.x, self.y, self.x, self.y

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Point"
        default_map["x"] = self.x
        default_map["y"] = self.y
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
        self._points.append([self.x, self.y, "point"])

    def update_point(self, index, point):
        return False

    def add_point(self, point, index=None):
        return False

    def as_path(self):
        path = Geomstr()
        path.point(complex(self.x, self.y))
        return path
