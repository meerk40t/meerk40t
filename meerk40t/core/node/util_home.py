from meerk40t.core.cutcode.homecut import HomeCut
from meerk40t.core.elements.element_types import op_nodes
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

    def can_drop(self, drag_node):
        # Move operation to a different position.
        return bool(drag_node.type in op_nodes)

    def drop(self, drag_node, modify=True, flag=False):
        # Default routine for drag + drop for an op node - irrelevant for others...
        drop_node = self
        if not self.can_drop(drag_node):
            return False
        if modify:
            drop_node.insert_sibling(drag_node)
        return True

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
