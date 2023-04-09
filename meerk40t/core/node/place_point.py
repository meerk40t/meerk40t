from copy import copy

from meerk40t.core.node.node import Node
from meerk40t.svgelements import Matrix, Point


class PlacePointNode(Node):
    """
    PlacePointNode is the bootstrapped node type for the 'place point' type.
    """

    def __init__(self, matrix=None, **kwargs):
        self.matrix = matrix
        super().__init__(type="place point", **kwargs)
        self._formatter = "{element_type} {id} {stroke}"

    def __copy__(self):
        nd = self.node_dict
        nd["matrix"] = copy(self.matrix)
        return PlacePointNode(**nd)

    def preprocess(self, context, bounds, matrix, plan):
        self.matrix *= matrix

    def bbox(self, transformed=True, with_stroke=False):
        p = self.matrix.point_in_matrix_space((0, 0))
        return p[0], p[1], p[0], p[1]

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Placement"
        default_map.update(self.__dict__)
        return default_map

    def drop(self, drag_node, modify=True):
        # if drag_node.type.startswith("op"):
        #     if modify:
        #         self.insert_sibling(drag_node)
        #     return True
        return False

    def revalidate_points(self):
        bounds = self.bounds
        if bounds is None:
            return
        self._points.append([bounds[0], bounds[1], "point"])

    def update_point(self, index, point):
        return False

    def add_point(self, point, index=None):
        return False
