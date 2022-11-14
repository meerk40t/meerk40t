from meerk40t.core.node.node import Node


class CutNode(Node):
    """
    Node type "cutcode"
    Cutcode nodes store cutcode within the tree. When processing in a plan this should be converted to a normal cutcode
    object.
    """

    def __init__(self, cutcode=None, id=None, label=None, lock=False, **kwargs):
        super().__init__(type="cutcode", id=id, label=label, lock=lock, **kwargs)
        self.output = True
        self.cutcode = cutcode
        self._formatter = "{element_type}"

    def __repr__(self):
        return f"CutNode('{self.type}', {str(self.cutcode)}, {str(self._parent)})"

    def __copy__(self):
        return CutNode(self.cutcode, id=self.id, label=self.label, lock=self.lock)

    def __len__(self):
        return 1

    def default_map(self, default_map=None):
        default_map = super(CutNode, self).default_map(default_map=default_map)
        default_map["element_type"] = "Cutcode"
        return default_map

    def drop(self, drag_node, modify=True):
        return False

    def as_cutobjects(self, closed_distance=15):
        yield from self.cutcode
