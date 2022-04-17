from meerk40t.core.node.node import Node


class BranchOperationsNode(Node):
    """
    Branch Operations Node.
    Bootstrapped type: 'branch reg'
    """

    def __init__(self, data_object, **kwargs):
        super(BranchOperationsNode, self).__init__(data_object)

    def __str__(self):
        return "Operations"

    def drop(self, drag_node):
        if drag_node.type.startswith("op"):
            # Dragging operation to op branch to effectively move to bottom.
            self.append_child(drag_node)
            return True
        return False

    def is_movable(self):
        return False
