from copy import copy

from meerk40t.core.node.node import Node
from meerk40t.svgelements import Matrix, Point
from meerk40t.tools.geomstr import Geomstr


class PointNode(Node):
    """
    PointNode is the bootstrapped node type for the 'elem point' type.
    """

    def __init__(self, **kwargs):
        point = kwargs.get("point")
        if point is not None:
            if "x" not in kwargs:
                kwargs["x"] = point.x
            if "y" not in kwargs:
                kwargs["y"] = point.y
        self.x = 0
        self.y = 0
        self.matrix = None
        self.fill = None
        self.stroke = None
        self.stroke_width = 1000.0
        super().__init__(type="elem point", **kwargs)
        self._formatter = "{element_type} {id} {stroke}"
        if self.x is None:
            self.x = 0
        if self.y is None:
            self.y = 0
        if self.matrix is None:
            self.matrix = Matrix()

    def __copy__(self):
        nd = self.node_dict
        nd["matrix"] = copy(self.matrix)
        nd["stroke"] = copy(self.stroke)
        nd["fill"] = copy(self.fill)
        return PointNode(**nd)

    def as_geometry(self):
        path = Geomstr()
        path.point(complex(self.x, self.y))
        path.transform(self.matrix)
        return path

    @property
    def point(self):
        x = float(self.x)
        y = float(self.y)
        return Point(*self.matrix.point_in_matrix_space((x, y)))

    def preprocess(self, context, matrix, plan):
        self.matrix *= matrix
        self.set_dirty_bounds()

    def bbox(self, transformed=True, with_stroke=False):
        x = float(self.x)
        y = float(self.y)
        p = self.matrix.point_in_matrix_space((x, y))
        return p[0], p[1], p[0], p[1]

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Point"
        x = float(self.x)
        y = float(self.y)
        p = self.matrix.point_in_matrix_space((x, y))
        default_map["x"] = p[0]
        default_map["y"] = p[1]
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
        x = float(self.x)
        y = float(self.y)
        p = self.matrix.point_in_matrix_space((x, y))
        self._points.append([p[0], p[1], "point"])

    def update_point(self, index, point):
        return False

    def add_point(self, point, index=None):
        return False
