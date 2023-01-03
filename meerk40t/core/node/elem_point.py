from copy import copy

from meerk40t.core.node.node import Node
from meerk40t.svgelements import Matrix, Point


class PointNode(Node):
    """
    PointNode is the bootstrapped node type for the 'elem point' type.
    """

    def __init__(self, **kwargs):
        self.point = None
        self.x = 0
        self.y = 0
        self.matrix = None
        self.fill = None
        self.stroke = None
        self.stroke_width = None
        super().__init__(type="elem point", **kwargs)
        self._formatter = "{element_type} {id} {stroke}"

    def __copy__(self):
        nd = self.node_dict
        nd["point"] = copy(self.point)
        nd["matrix"] = copy(self.matrix)
        nd["fill"] = copy(self.fill)
        nd["stroke_width"] = copy(self.stroke_width)
        return PointNode(**nd)

    def validate(self):
        if self.matrix is None:
            self.matrix = Matrix()
        if self.point is None:
            x = float(self.x)
            y = float(self.y)
            self.matrix.pre_translate(x, y)
            self.point = Point(0, 0)

    def preprocess(self, context, matrix, plan):
        self.matrix *= matrix
        self.set_dirty_bounds()

    def bbox(self, transformed=True, with_stroke=False):
        if self.point is None:
            return None
        p = self.matrix.point_in_matrix_space(self.point)
        return p[0], p[1], p[0], p[1]

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Point"
        if self.point is not None:
            default_map["x"] = self.point[0]
            default_map["y"] = self.point[1]
        else:
            default_map["x"] = 0
            default_map["y"] = 0
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
        self._points.append([self.point.x, self.point.y, "point"])

    def update_point(self, index, point):
        return False

    def add_point(self, point, index=None):
        return False
