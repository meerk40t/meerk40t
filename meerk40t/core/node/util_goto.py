from meerk40t.core.cutcode.gotocut import GotoCut
from meerk40t.core.elements.element_types import *
from meerk40t.core.node.node import Node


class GotoOperation(Node):
    """
    GotoOperation tells the controller to return to origin.

    Node type "util goto"
    """

    def __init__(self, **kwargs):
        self.output = True
        self.x = 0.0
        self.y = 0.0
        super().__init__(type="util goto", **kwargs)
        self._formatter = "{enabled}{element_type} {x} {y}"

    def __repr__(self):
        return f"GotoOperation('{self.x}, {self.y}')"

    def __len__(self):
        return 1

    @property
    def implicit_passes(self):
        return 1

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        origin = self.x == 0 and self.y == 0
        default_map["element_type"] = "Origin" if origin else "Goto"
        default_map["enabled"] = "(Disabled) " if not self.output else ""
        default_map["adjust"] = f" ({self.x}, {self.y})" if not origin else ""
        default_map.update(self.__dict__)
        return default_map

    def drop(self, drag_node, modify=True):
        drop_node = self
        if drag_node.type in op_nodes:
            if modify:
                drop_node.insert_sibling(drag_node)
            return True
        elif drop_node.type == "branch ops":
            # Dragging operation to op branch to effectively move to bottom.
            if modify:
                drop_node.append_child(drag_node)
            return True
        return False

    def as_cutobjects(self, closed_distance=15, passes=1):
        """
        Generator of cutobjects for a raster operation. This takes any image node children
        and converts them into rastercut objects. These objects should have already been converted
        from vector shapes.

        The preference for raster shapes is to use the settings set on this operation rather than on the image-node.
        """
        cut = GotoCut((self.x, self.y))
        cut.original_op = self.type
        yield cut

    def generate(self):
        yield "move_ori", self.x, self.y
