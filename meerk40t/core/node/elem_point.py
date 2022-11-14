from copy import copy

from meerk40t.core.node.node import Node
from meerk40t.svgelements import Matrix, Point


class PointNode(Node):
    """
    PointNode is the bootstrapped node type for the 'elem point' type.
    """

    def __init__(
        self,
        point=None,
        matrix=None,
        fill=None,
        stroke=None,
        stroke_width=None,
        id=None,
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
        super(PointNode, self).__init__(
            type="elem point", id=id, label=label, lock=lock, **settings
        )
        self._formatter = "{element_type} {id} {stroke}"
        self.point = point
        self.matrix = matrix
        self.settings = settings
        self.fill = fill
        self.stroke = stroke
        self.stroke_width = stroke_width

    def __copy__(self):
        return PointNode(
            point=copy(self.point),
            matrix=copy(self.matrix),
            fill=copy(self.fill),
            stroke=copy(self.stroke),
            stroke_width=self.stroke_width,
            id=self.id,
            label=self.label,
            lock=self.lock,
            settings=self.settings,
        )

    def validate(self):
        if self.matrix is None:
            self.matrix = Matrix()
        if self.point is None:
            x = float(self.settings.get("x", 0))
            y = float(self.settings.get("y", 0))
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
        default_map = super(PointNode, self).default_map(default_map=default_map)
        default_map["element_type"] = "Point"
        if self.point is not None:
            default_map["x"] = self.point[0]
            default_map["y"] = self.point[1]
        else:
            default_map["x"] = 0
            default_map["y"] = 0
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
        self._points.append([self.point.x, self.point.y, "point"])

    def update_point(self, index, point):
        return False

    def add_point(self, point, index=None):
        return False
