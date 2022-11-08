from meerk40t.core.node.node import Node


class ReferenceNode(Node):
    """
    ReferenceNode is the bootstrapped node type for the reference type.
    """

    def __init__(self, node, **kwargs):
        super(ReferenceNode, self).__init__(type="reference", **kwargs)
        self._formatter = "*{reference}"
        self.node = node

    def __repr__(self):
        return f"ReferenceNode('{self.type}', {str(self.node)}, {str(self._parent)})"

    def __copy__(self):
        return ReferenceNode(self.node)

    @property
    def bounds(self):
        return self.node.bounds

    def bbox(self, transformed=True, with_stroke=False):
        return self.node.bbox(transformed=transformed, with_stroke=with_stroke)

    def default_map(self, default_map=None):
        default_map = super(ReferenceNode, self).default_map(default_map=default_map)
        default_map["element_type"] = "Reference"
        default_map["reference"] = str(self.node)
        default_map["ref_nid"] = str(self.node.id)
        default_map["ref_id"] = str(self.id)
        return default_map

    def drop(self, drag_node, modify=True):
        if drag_node.type.startswith("elem"):
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

    def notify_destroyed(self, node=None, **kwargs):
        self.node._references.remove(self)
        super(ReferenceNode, self).notify_destroyed()
