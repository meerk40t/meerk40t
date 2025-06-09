from copy import copy

from meerk40t.core.node.mixins import FunctionalParameter, LabelDisplay, Suppressable
from meerk40t.core.node.node import Node
from meerk40t.svgelements import Matrix, Point
from meerk40t.tools.geomstr import Geomstr


class PointNode(Node, FunctionalParameter, LabelDisplay, Suppressable):
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
            del kwargs["point"]
        self.x = 0
        self.y = 0
        self.matrix = None
        self.fill = None
        self.stroke = None
        self.stroke_width = 1000.0
        super().__init__(type="elem point", **kwargs)
        if "hidden" in kwargs:
            if isinstance(kwargs["hidden"], str):
                if kwargs["hidden"].lower() == "true":
                    kwargs["hidden"] = True
                else:
                    kwargs["hidden"] = False
            self.hidden = kwargs["hidden"]
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

    def as_geometry(self, **kws) -> Geomstr:
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

    def length(self):
        return 0

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

    def can_drop(self, drag_node):
        if self.is_a_child_of(drag_node):
            return False
        # Dragging element into element.
        return bool(
            hasattr(drag_node, "as_geometry")
            or hasattr(drag_node, "as_image")
            or drag_node.type in ("op dots", "file", "group")
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
        x = float(self.x)
        y = float(self.y)
        p = self.matrix.point_in_matrix_space((x, y))
        self._points.append([p[0], p[1], "point"])

    def update_point(self, index, point):
        return False

    def add_point(self, point, index=None):
        return False
