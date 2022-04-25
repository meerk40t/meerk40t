from meerk40t.core.node.node import Node


class ReferenceNode(Node):
    """
    ReferenceNode is the bootstrapped node type for the reference type.

    ReferenceNode track referenced nodes within the tree.
    """

    def __init__(self, node):
        super(ReferenceNode, self).__init__()
        node._references.append(self)
        self.node = node

    def __repr__(self):
        return "ReferenceNode('%s', %s, %s)" % (
            self.type,
            str(self.node),
            str(self._parent),
        )

    @property
    def bounds(self):
        return self.node.bounds

    def default_map(self, default_map=None):
        default_map = super(ReferenceNode, self).default_map(default_map=default_map)
        default_map['element_type'] = "Reference"
        default_map['reference'] = str(self.node)
        default_map['ref_nid'] = str(self.node.id)
        default_map['ref_id'] = str(self.id)
        return default_map

    def drop(self, drag_node):
        if drag_node.type.startswith("elem"):
            op = self.parent
            drop_index = op.children.index(self)
            op.add_reference(drag_node, pos=drop_index)
            return True
        elif drag_node.type == "reference":
            self.insert_sibling(drag_node)
            return True
        return False

    def notify_destroyed(self, node=None, **kwargs):
        self.node._references.remove(self)
        super(ReferenceNode, self).notify_destroyed()
