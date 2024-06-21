from meerk40t.core.node.node import Node


class GroupNode(Node):
    """
    GroupNode is the bootstrapped node type for the group type.
    All group types are bootstrapped into this node object.
    """

    def __init__(self, **kwargs):
        super().__init__(type="group", **kwargs)
        self._formatter = "{element_type} {id} ({children} elems)"
        self.set_dirty_bounds()

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

    def bbox_group(self):
        if self._bounds_dirty or self._bounds is None:
            xmin = float("inf")
            ymin = float("inf")
            xmax = -float("inf")
            ymax = -float("inf")
            for n in self.children:
                if n.type == "group":
                    bb = n.bbox_group()
                else:
                    bb = n.bbox()
                if bb[0] < xmin:
                    xmin = bb[0]
                if bb[1] < ymin:
                    ymin = bb[1]
                if bb[2] > xmax:
                    xmax = bb[2]
                if bb[3] > ymax:
                    ymax = bb[3]
            self._bounds = (xmin, ymin, xmax, ymax)
            self._bounds_dirty = False
        return self._bounds

    def default_map(self, default_map=None):
        def elem_count(node):
            res = 0
            for e in node.children:
                if e.type in ("file", "group"):
                    res += elem_count(e)
                else:
                    res += 1
            return res

        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Group"

        default_map["children"] = str(len(self.children))
        elemcount = elem_count(self)
        default_map["total"] = str(elemcount)
        default_map["id"] = str(self.id)
        return default_map

    def is_a_child_of(self, node):
        candidate = self
        while candidate is not None:
            if candidate is node:
                return True
            candidate = candidate.parent
        return False

    def drop(self, drag_node, modify=True):
        # Do not allow dragging onto children
        if self.is_a_child_of(drag_node):
            return False

        if hasattr(drag_node, "as_geometry") or hasattr(drag_node, "as_image"):
            # Dragging element onto a group moves it to the group node.
            if modify:
                self.append_child(drag_node)
            return True
        elif drag_node.type == "group":
            # Move a group
            if modify:
                self.append_child(drag_node)
            return True
        elif drag_node.type.startswith("op"):
            # If we drag an operation to this node,
            # then we will reverse the game
            return drag_node.drop(self, modify=modify)
        return False

    @property
    def name(self):
        if self.id is None:
            return f"Group ({len(self.children)} elems)"
        return f"Group ({len(self.children)} elems): {self.id}"
