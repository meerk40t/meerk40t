from meerk40t.core.node.node import Node


class GroupNode(Node):
    """
    GroupNode is the bootstrapped node type for the group type.
    All group types are bootstrapped into this node object.
    """

    def __init__(self, **kwargs):
        super(GroupNode, self).__init__(type="group", **kwargs)
        self._formatter = "{element_type} {id} ({children} elems)"

    def __repr__(self):
        return f"GroupNode('{self.type}', {str(self._parent)})"

    def bbox(self, transformed=True, with_stroke=False):
        """
        Group default bbox is empty. If childless there are no bounds.

        empty, otherwise will recurse forever...

        @param transformed:
        @param with_stroke:
        @return:
        """

        return (
            float("inf"),
            float("inf"),
            -float("inf"),
            -float("inf"),
        )

    def default_map(self, default_map=None):
        def elem_count(node):
            res = 0
            for e in node.children:
                res += 1
                if e.type in ("file", "group"):
                    res += elem_count(e)
            return res

        default_map = super(GroupNode, self).default_map(default_map=default_map)
        default_map["element_type"] = "Group"

        default_map["children"] = str(len(self.children))
        elemcount = elem_count(self)
        default_map["total"] = str(elemcount)
        default_map["id"] = str(self.id)
        return default_map

    def drop(self, drag_node, modify=True):
        if drag_node.type.startswith("elem"):
            # Dragging element onto a group moves it to the group node.
            if modify:
                self.append_child(drag_node)
            return True
        elif drag_node.type == "group":
            # Move a group
            if modify:
                self.append_child(drag_node)
            return True
        return False

    @property
    def name(self):
        if self.id is None:
            return f"Group ({len(self.children)} elems)"
        return f"Group ({len(self.children)} elems): {self.id}"
