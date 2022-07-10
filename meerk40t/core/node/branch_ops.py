from meerk40t.core.node.node import Node


class BranchOperationsNode(Node):
    """
    Branch Operations Node.
    Bootstrapped type: 'branch reg'
    """

    def __init__(self, **kwargs):
        super(BranchOperationsNode, self).__init__(**kwargs)
        self.loop_enabled = False
        self.loop_continuous = False
        self.loop_n = 1

    def __str__(self):
        return "Operations"

    def default_map(self, default_map=None):
        default_map = super(BranchOperationsNode, self).default_map(default_map=default_map)
        if self.loop_continuous:
            default_map["loops"] = "∞"
        else:
            if self.loop_enabled:
                default_map["loops"] = str(self.loop_n)
            else:
                default_map["loops"] = ""
        return default_map

    def drop(self, drag_node):
        if drag_node.type.startswith("op"):
            # Dragging operation to op branch to effectively move to bottom.
            self.append_child(drag_node)
            return True
        return False

    def is_movable(self):
        return False
