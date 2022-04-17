from meerk40t.core.node.node import Node


class BranchElementsNode(Node):
    """
    Branch Element Node.
    Bootstrapped type: 'branch reg'
    """

    def __init__(self, data_object, **kwargs):
        super(BranchElementsNode, self).__init__(data_object)

    def __str__(self):
        return "Elements"

    def is_movable(self):
        return False
