from meerk40t.core.node.node import Node


class BranchElementsNode(Node):
    """
    Branch Element Node.
    Bootstrapped type: 'branch reg'
    """

    def __init__(self, **kwargs):
        super(BranchElementsNode, self).__init__(**kwargs)

    def __str__(self):
        return "Elements"

    def drop(self, drag_node):
        if drag_node.type.startswith("elem"):
            self.append_child(drag_node)
            return True
        return False

    def is_movable(self):
        return False
