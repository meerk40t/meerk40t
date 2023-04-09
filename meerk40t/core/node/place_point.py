from copy import copy

from meerk40t.core.node.node import Node
from meerk40t.core.units import Length
from meerk40t.svgelements import Matrix, Point


class PlacePointNode(Node):
    """
    PlacePointNode is the bootstrapped node type for the 'place point' type.
    """

    def __init__(self, x=0, y=0, **kwargs):
        self.x = x
        self.y = y
        super().__init__(type="place point", **kwargs)
        self._formatter = "{element_type} {x} {y}"

    def __copy__(self):
        nd = self.node_dict
        nd["x"] = self.x
        nd["y"] = self.y
        return PlacePointNode(**nd)

    def placements(self, context, outline, matrix, plan):
        scene_width = context.device.unit_width
        scene_height = context.device.unit_height
        unit_x = Length(self.x, relative_length=scene_width).units
        unit_y = Length(self.y, relative_length=scene_height).units
        x, y = matrix.point_in_matrix_space((unit_x, unit_y))
        if outline is not None:
            x -= outline[0][0]
            y -= outline[0][1]
            shift_matrix = Matrix.translate(x, y)
            yield matrix * shift_matrix

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Placement"
        default_map["position"] = str((self.x, self.y))
        default_map.update(self.__dict__)
        return default_map

    def drop(self, drag_node, modify=True):
        # if drag_node.type.startswith("op"):
        #     if modify:
        #         self.insert_sibling(drag_node)
        #     return True
        return False
