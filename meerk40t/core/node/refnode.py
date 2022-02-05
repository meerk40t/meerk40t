from meerk40t.core.node.node import Node


class RefElemNode(Node):
    """
    RefElemNode is the bootstrapped node type for the refelem type.

    RefElemNodes track referenced copies of vector element data.
    """

    def __init__(self, data_object):
        super(RefElemNode, self).__init__(data_object)
        data_object.node._references.append(self)

    def __repr__(self):
        return "RefElemNode('%s', %s, %s)" % (
            self.type,
            str(self.object),
            str(self._parent),
        )

    def notify_destroyed(self, node=None, **kwargs):
        self.object.node._references.remove(self)
        super(RefElemNode, self).notify_destroyed()
