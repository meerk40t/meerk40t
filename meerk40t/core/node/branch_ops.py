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

    def is_movable(self):
        return False
