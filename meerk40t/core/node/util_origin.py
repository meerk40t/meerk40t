from meerk40t.core.cutcode import SetOriginCut
from meerk40t.core.element_types import *
from meerk40t.core.node.node import Node


class SetOriginOperation(Node):
    """
    SetOriginOperation tells the controller to return to origin.

    Node type "util origin"
    """

    def __init__(self, **kwargs):
        self.x = None
        self.y = None
        self.output = True
        super().__init__(type="util origin", **kwargs)
        self._formatter = "{enabled}{element_type} {x} {y}"

    def __repr__(self):
        return f"SetOriginOperation('{self.x}, {self.y}')"

    def __copy__(self):
        return SetOriginOperation(**self.node_dict)

    def __len__(self):
        return 1

    @property
    def implicit_passes(self):
        return 1

    def default_map(self, default_map=None):
        default_map = super(SetOriginOperation, self).default_map(
            default_map=default_map
        )
        default_map["element_type"] = "SetOrigin"
        default_map["enabled"] = "(Disabled) " if not self.output else ""
        default_map["adjust"] = (
            f" ({self.x}, {self.y})"
            if self.x is not None and self.y is not None
            else "<Current>"
        )
        default_map["x"] = self.x
        default_map["y"] = self.y
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
        if self.x is None or self.y is None:
            cut = SetOriginCut()
        else:
            cut = SetOriginCut((self.x, self.y))
        cut.original_op = self.type
        yield cut

    def generate(self):
        yield "set_origin", self.x, self.y
