from meerk40t.core.node.node import Node


class LayerNode(Node):
    """
    Bootstrapped type: 'layer'
    """

    def __init__(self, **kwargs):
        self.layer_name = None
        super(LayerNode, self).__init__(type="layer", **kwargs)
        self._formatter = "{element_type} {id} ({children} elems)"

    def default_map(self, default_map=None):
        default_map = super(LayerNode, self).default_map(default_map=default_map)
        default_map["name"] = self.layer_name
        default_map["element_type"] = "Layer"
        default_map["children"] = str(len(self.count_children()))
        return default_map

    def notify_selected(self, node=None, **kwargs):
        if node is self:
            if hasattr(self.parent, "activate"):
                self.parent.activate(self.layer_name)

    def drop(self, drag_node, modify=True):
        return False

    @property
    def bounds(self):
        return None
