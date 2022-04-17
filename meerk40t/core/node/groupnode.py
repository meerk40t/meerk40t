from meerk40t.core.node.node import Node


class GroupNode(Node):
    """
    GroupNode is the bootstrapped node type for the group type.
    All group types are bootstrapped into this node object.
    """

    def __init__(self, data_object=None, **kwargs):
        super(GroupNode, self).__init__(data_object)
        self.last_transform = None

    def __repr__(self):
        return "GroupNode('%s', %s, %s)" % (
            self.type,
            str(self.object),
            str(self._parent),
        )

    @property
    def label(self):
        if self.id is None:
            return f"Group {len(self.children)}"
        return f"Group {len(self.children)}: %s" % self.id

    def drop(self, drag_node):
        drop_node = self
        # Dragging element into group.
        if drag_node.type.startswith("elem"):
            drop_node.insert_sibling(drag_node)
            return True
        return False
