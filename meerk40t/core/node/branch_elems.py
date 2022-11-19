from meerk40t.core.node.node import Node


class BranchElementsNode(Node):
    """
    Branch Element Node.
    Bootstrapped type: 'branch elems'
    """

    def __init__(self, **kwargs):
        super(BranchElementsNode, self).__init__(type="branch elems", **kwargs)
        self._formatter = "{element_type}"

    def default_map(self, default_map=None):
        default_map = super(BranchElementsNode, self).default_map(
            default_map=default_map
        )
        default_map["element_type"] = "Elements"
        return default_map

    def drop(self, drag_node, modify=True):
        if drag_node.type.startswith("elem"):
            if modify:
                self.append_child(drag_node)
            return True
        return False

    def is_draggable(self):
        return False
