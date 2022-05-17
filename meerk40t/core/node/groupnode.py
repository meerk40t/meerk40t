from meerk40t.core.node.node import Node


class GroupNode(Node):
    """
    GroupNode is the bootstrapped node type for the group type.
    All group types are bootstrapped into this node object.
    """

    def __init__(self, **kwargs):
        super(GroupNode, self).__init__(type="group", **kwargs)

    def __repr__(self):
        return "GroupNode('%s', %s)" % (
            self.type,
            str(self._parent),
        )

    @property
    def bounds(self):
        if self._bounds_dirty:
            if len(self.children) == 0:
                # empty, otherwise will recurse forever...
                self._bounds = (
                    float("inf"),
                    float("inf"),
                    -float("inf"),
                    -float("inf"),
                )
            else:
                self._bounds = Node.union_bounds(self._flatten_children(self))
        return self._bounds

    def default_map(self, default_map=None):
        default_map = super(GroupNode, self).default_map(default_map=default_map)
        default_map["element_type"] = "Group"
        return default_map

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
