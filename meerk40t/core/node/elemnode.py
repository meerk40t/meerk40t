
class ElemNode(Node):
    """
    ElemNode is the bootstrapped node type for the elem type. All elem types are bootstrapped into this node object.
    """

    def __init__(self, data_object):
        super(ElemNode, self).__init__(data_object)
        self.last_transform = None
        data_object.node = self

    def __repr__(self):
        return "ElemNode('%s', %s, %s)" % (
            self.type,
            str(self.object),
            str(self._parent),
        )

    def drop(self, drag_node):
        drop_node = self
        # Dragging element into element.
        if drag_node.type == "elem":
            drop_node.insert_sibling(drag_node)
            return True
        return False
