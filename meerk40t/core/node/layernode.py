from meerk40t.core.node.node import Node


class LayerNode(Node):
    """
    Bootstrapped type: 'layer'
    """

    def __init__(self, layer_name=None, **kwargs):
        super(LayerNode, self).__init__(type="layer", **kwargs)
        self.layer_name = layer_name

    def __str__(self):
        return f"Layer-{self.layer_name}"

    def default_map(self, default_map=None):
        default_map = super(LayerNode, self).default_map(default_map=default_map)
        default_map["name"] = self.layer_name
        default_map["element_type"] = "Layer"
        return default_map

    def notify_selected(self, node=None, **kwargs):
        if node is self:
            if hasattr(self.parent, "activate"):
                self.parent.activate(self.layer_name)

    def drop(self, drag_node):
        return False

    @property
    def bounds(self):
        return None
