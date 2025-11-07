"""
Placements are representations of a laserjob origin.
A project may contain multiple such placements, for every placement
a copy of the plan will be executed with the placement indicating
the relative position
"""

from meerk40t.core.node.node import Node
from meerk40t.svgelements import Matrix


class PlaceCurrentNode(Node):
    """
    PlacePointNode is the bootstrapped node type for the 'place point' type.
    """

    def __init__(self, **kwargs):
        super().__init__(type="place current", **kwargs)
        # Active?
        self.output = True
        self._formatter = "{enabled}{element_type}"

    def placements(self, context, outline, matrix, plan):
        if outline is None:
            return
        x, y = context.device.native
        x -= outline[0][0]
        y -= outline[0][1]
        shift_matrix = Matrix.translate(x, y)
        yield matrix * shift_matrix

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Placement: Current Position"
        default_map["enabled"] = "(Disabled) " if not self.output else ""
        default_map.update(self.__dict__)
        return default_map
