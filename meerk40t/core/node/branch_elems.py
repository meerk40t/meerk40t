from meerk40t.core.node.node import Node


class BranchElementsNode(Node):
    """
    Branch Element Node.
    Bootstrapped type: 'branch elems'
    """

    def __init__(self, **kwargs):
        super().__init__(type="branch elems", **kwargs)
        self._formatter = "{element_type}"

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Elements"
        return default_map

    def drop(self, drag_node, modify=True, flag=False):
        if hasattr(drag_node, "as_geometry") or hasattr(drag_node, "as_image"):
            if modify:
                self.append_child(drag_node)
            return True
        elif drag_node.type == "group":
            if modify:
                self.append_child(drag_node)
            return True
        return False
    
    def would_accept_drop(self, drag_nodes):
        # drag_nodes can be a single node or a list of nodes
        if isinstance(drag_nodes, (list, tuple)):
            data = drag_nodes
        else:
            data = list(drag_nodes)
        for drag_node in data:
            if hasattr(drag_node, "as_geometry") or hasattr(drag_node, "as_image") or drag_node.type == "group":
                return True
        return False

    def is_draggable(self):
        return False
