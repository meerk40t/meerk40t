from meerk40t.core.node.node import Node


class BlobNode(Node):
    """
    BlobNode is a basic operation containing raw data of some type. This consists of a series of bytes.

    Node type "blob"
    """

    def __init__(self, **kwargs):
        self.data = None
        self.data_type = None
        self.views = {}
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

    @staticmethod
    def hex_view(data, data_type):
        header1 = f"Data-Type: {data_type}, Length={len(data)}\n"
        header2 = "Offset | Hex                                             | Ascii          \n"
        header2 += "-------+-------------------------------------------------+----------------\n"
        if isinstance(data, str):
            data = data.encode("latin-1")

        def create_table():
            ascii_list = list()
            for i, c in enumerate(data):
                q = i % 16
                if q == 0:
                    yield f"{i:06x}  "
                yield f"{c:02x} "
                if c in (0x00, 0x0d, 0x0a, 0x09) or c > 0x80:
                    ascii_list.append('.')
                else:
                    ascii_list.append(chr(c))
                if q == 7:
                    yield " "
                if q == 15:
                    ascii_line = "".join(ascii_list)
                    ascii_list.clear()
                    yield f" {ascii_line}\n"

        hex_data = list(create_table())
        return header1 + header2 + "".join(hex_data)

    @staticmethod
    def ascii_view(data, data_type):
        header1 = f"Data-Type: {data_type}, Length={len(data)}\n"
        header2 = "Offset | Hex                                             | Ascii          \n"
        header2 += "-------+-------------------------------------------------+----------------\n"
        if isinstance(data, str):
            data = data.encode("latin-1")
        return header1 + data.decode("latin-1")

    def generate(self):
        if self.data:
            yield "blob", self.data_type, self.data
