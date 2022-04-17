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

    def drop(self, drag_node):
        if drag_node.type.startswith("elem"):
            # Dragging element onto a group moves it to the group node.
            self.append_child(drag_node)
            return True
        elif drag_node.type == "group":
            # Move a group
            self.append_child(drag_node)
            return True
        return False

    @property
    def label(self):
        if self.id is None:
            return f"Group {len(self.children)}"
        return f"Group {len(self.children)}: %s" % self.id
