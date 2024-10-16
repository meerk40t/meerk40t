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

    def can_drop(self, drag_node):
        return bool(
            drag_node.type.startswith("op ") or drag_node.type.startswith("util ")
        )

    def drop(self, drag_node, modify=True, flag=False):
        if not self.can_drop(drag_node):
            return False
        if drag_node.type.startswith("op ") or drag_node.type.startswith("util "):
            # Dragging operation to op branch to effectively move to bottom.
            if modify:
                self.append_child(drag_node)
            return True
        return False
        
    def is_draggable(self):
        return False
