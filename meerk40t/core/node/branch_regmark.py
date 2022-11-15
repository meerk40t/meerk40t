from meerk40t.core.node.node import Node


class BranchRegmarkNode(Node):
    """
    Branch Regmark Node.
    Bootstrapped type: 'branch reg'
    """

    def __init__(self, **kwargs):
        super(BranchRegmarkNode, self).__init__(type="branch reg", **kwargs)
        self._formatter = "{element_type}"

    def default_map(self, default_map=None):
        default_map = super(BranchRegmarkNode, self).default_map(
            default_map=default_map
        )
        default_map["element_type"] = "Regmarks"
        return default_map

    def drop(self, drag_node, modify=True):
        if drag_node.type.startswith("elem"):
            if modify:
                for ref in list(drag_node._references):
                    ref.remove_node()
                self.append_child(drag_node)
            return True
        elif drag_node.type == "group":
            if modify:
                self.append_child(drag_node)
            return True
        return False

    def is_draggable(self):
        return False
