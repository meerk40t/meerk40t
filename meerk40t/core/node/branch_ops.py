from meerk40t.core.node.node import Node


class BranchOperationsNode(Node):
    """
    Branch Operations Node.
    Bootstrapped type: 'branch reg'
    """

    def __init__(self, **kwargs):
        self.loop_enabled = False
        self.loop_continuous = False
        self.loop_n = 1
        super().__init__(type="branch ops", **kwargs)
        self._formatter = "{element_type} {loops}"

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Operations"
        if self.loop_continuous:
            default_map["loops"] = "∞"
        else:
            if self.loop_enabled:
                default_map["loops"] = str(self.loop_n)
            else:
                default_map["loops"] = ""
        return default_map

    def drop(self, drag_node, modify=True, flag=False):
        if drag_node.type.startswith("op"):
            # Dragging operation to op branch to effectively move to bottom.
            if modify:
                self.append_child(drag_node)
            return True
        return False
        
    def would_accept_drop(self, drag_nodes):
        # drag_nodes can be a single node or a list of nodes
        if isinstance(drag_nodes, (list, tuple)):
            data = drag_nodes
        else:
            data = list(drag_nodes)
        for drag_node in data:
            if drag_node.type.startswith("op"):
                return True
        return False

    def is_draggable(self):
        return False
