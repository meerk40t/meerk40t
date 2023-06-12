from meerk40t.core.node.node import Node


class BlobNode(Node):
    """
    BlobNode is a basic operation containing raw data of some type. This consists of a series of bytes.

    Node type "blob"
    """

    def __init__(self, **kwargs):
        self.data = None
        self.data_type = None
        self.label = "Blob"
        self.output = True
        super().__init__(type="blob", **kwargs)
        self._formatter = "{element_type}:{data_type}:{label} @{length}"

    def __len__(self):
        if self.data is None:
            return 0
        return len(self.data)

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Blob"
        default_map["data_type"] = self.data_type
        default_map["label"] = self.label
        d = 0
        if self.data is not None:
            d = len(self.data)
        default_map["length"] = d
        return default_map

    def drop(self, drag_node, modify=True):
        return False

    def allow_save(self):
        """
        Returns false to prevent saving of blob types into operations.
        @return:
        """
        return False

    def generate(self):
        if self.data:
            yield "blob", self.data_type, self.data
