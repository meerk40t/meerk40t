from meerk40t.core.node.node import Node


class CutNode(Node):
    """
    Node type "cutcode"
    Cutcode nodes store cutcode within the tree. When processing in a plan this should be converted to a normal cutcode
    object.
    """

    def __init__(self, data_object, **kwargs):
        super().__init__(data_object, type="cutcode", **kwargs)
        self.output = True

    def __repr__(self):
        return "CutNode('%s', %s, %s)" % (
            self.type,
            str(self.object),
            str(self._parent),
        )

    def __copy__(self):
        return CutNode(self.object)

    def __len__(self):
        return 1

    def as_cutobjects(self, closed_distance=15):
        yield from self.object
