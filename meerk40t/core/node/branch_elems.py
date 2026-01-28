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
        default_map["element_type"] = "Elements" if self.label is None else self.label
        return default_map

    def can_drop(self, drag_node):
        return bool(
            hasattr(drag_node, "as_geometry")
            or hasattr(drag_node, "as_image")
            or drag_node.type == "group"
        )

    def drop(self, drag_node, modify=True, flag=False):
        if not self.can_drop(drag_node):
            return False
        if hasattr(drag_node, "as_geometry") or hasattr(drag_node, "as_image"):
            if modify:
                self.append_child(drag_node)
            return True
        elif drag_node.type == "group":
            if modify:
                self.append_child(drag_node)
            return True
        return False

    def drop_multi(self, drag_nodes, modify=True, flag=False):
        """Drop multiple nodes at once for better performance"""
        if not drag_nodes:
            return False

        valid_nodes = [node for node in drag_nodes if self.can_drop(node)]

        if valid_nodes and modify:
            self.append_children(valid_nodes, fast=True)

        return len(valid_nodes) > 0

    def is_draggable(self):
        return False
