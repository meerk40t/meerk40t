from meerk40t.core.cutcode.homecut import HomeCut
from meerk40t.core.element_types import *
from meerk40t.core.node.node import Node


class HomeOperation(Node):
    """
    HomeOperation tells the controller to perform homing.

    Node type "util home"
    """

    def __init__(self, **kwargs):
        self.output = True
        super().__init__(type="util home", **kwargs)
        self._formatter = "{enabled}{element_type}"

    def __repr__(self):
        return "HomeOperation()"

    def __len__(self):
        return 1

    @property
    def implicit_passes(self):
        return 1

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Home"
        default_map["enabled"] = "(Disabled) " if not self.output else ""
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
        cut = HomeCut()
        cut.original_op = self.type
        yield cut

    def generate(self):
        yield "home"
