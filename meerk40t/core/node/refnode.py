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

    def default_map(self, default_map=None):
        default_map = super(RefElemNode, self).default_map(default_map=default_map)
        default_map['element_type'] = "Reference"
        default_map['reference'] = str(self.object)
        default_map['ref_id'] = str(self.object.id)
        default_map['ref_nid'] = str(self.object.node.id)
        if self.object is not None:
            default_map.update(self.object.values)
        return default_map

    def drop(self, drag_node):
        if drag_node.type == "elem":
            op = self.parent
            drop_index = op.children.index(self)
            op.add(drag_node.object, type="ref elem", pos=drop_index)
            return True
        elif drag_node.type == "ref elem":
            self.insert_sibling(drag_node)
            return True
        return False

    def notify_destroyed(self, node=None, **kwargs):
        self.object.node._references.remove(self)
        super(RefElemNode, self).notify_destroyed()
