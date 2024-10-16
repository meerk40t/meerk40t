from meerk40t.core.node.node import Node


class BranchRegmarkNode(Node):
    """
    Branch Regmark Node.
    Bootstrapped type: 'branch reg'
    """

    def __init__(self, **kwargs):
        super().__init__(type="branch reg", **kwargs)
        self._formatter = "{element_type}"

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Regmarks"
        return default_map

    def remove_references(self, node):
        ct = 0
        for ref in list(node.references):
            ct += 1
            ref.remove_node(fast=False)
        for ref in list(node.children):
            self.remove_references(ref)

    def can_drop(self, drag_node):
        if hasattr(drag_node, "as_geometry") or hasattr(drag_node, "as_image") or drag_node.type == "group":
            return True
        return False
    
    def drop(self, drag_node, modify=True, flag=False):
        if not self.can_drop(drag_node):
            return False
        if hasattr(drag_node, "as_geometry") or hasattr(drag_node, "as_image"):
            if modify:
                self.remove_references(drag_node)
                self.append_child(drag_node)
            return True
        elif drag_node.type == "group":
            if modify:
                self.remove_references(drag_node)
                self.append_child(drag_node)
            return True
        return False

    def is_draggable(self):
        return False
