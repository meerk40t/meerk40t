from meerk40t.core.node.node import Node


class ReferenceNode(Node):
    """
    ReferenceNode is the bootstrapped node type for the reference type.
    """

    def __init__(self, **kwargs):
        self.node = None
        super().__init__(type="reference", **kwargs)
        self._formatter = "*{reference}"

    def __repr__(self):
        return f"ReferenceNode('{self.type}', {str(self.node)}, {str(self._parent)})"

    @property
    def bounds(self):
        return self.node.bounds

    def bbox(self, transformed=True, with_stroke=False):
        return self.node.bbox(transformed=transformed, with_stroke=with_stroke)

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Reference"
        default_map["reference"] = str(self.node)
        default_map["ref_nid"] = str(self.node.id)
        default_map["ref_id"] = str(self.id)
        return default_map

    def drop(self, drag_node, modify=True, flag=False):
        if hasattr(drag_node, "as_geometry") or hasattr(drag_node, "as_image"):
            op = self.parent
            drop_index = op.children.index(self)
            if modify:
                op.add_reference(drag_node, pos=drop_index)
            return True
        elif drag_node.type == "reference":
            if modify:
                self.insert_sibling(drag_node)
            return True
        return False

    def would_accept_drop(self, drag_nodes):
        # drag_nodes can be a single node or a list of nodes
        if isinstance(drag_nodes, (list, tuple)):
            data = drag_nodes
        else:
            data = list(drag_nodes)
        for drag_node in data:
            if drag_node.has_ancestor("branch reg"):
                continue
            if (
                hasattr(drag_node, "as_geometry") or
                hasattr(drag_node, "as_image") or 
                drag_node.type == "reference"
            ):
                return True
        return False

    def notify_destroyed(self, node=None, **kwargs):
        self.node._references.remove(self)
        super().notify_destroyed()
