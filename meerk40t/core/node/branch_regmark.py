from meerk40t.core.node.node import Node


class BranchRegmarkNode(Node):
    """
    Branch Regmark Node.
    Bootstrapped type: 'branch reg'
    """

    def __init__(self, data_object, **kwargs):
        super(BranchRegmarkNode, self).__init__(data_object)

    def __str__(self):
        return "Regmarks"

    def is_movable(self):
        return False
