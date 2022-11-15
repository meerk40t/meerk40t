import os

from meerk40t.core.node.node import Node


class FileNode(Node):
    """
    Branch Element Node.
    Bootstrapped type: 'file'
    """

    def __init__(self, **kwargs):
        self.filepath = None
        super(FileNode, self).__init__(type="file", **kwargs)
        self._formatter = "{element_type}: {filename}"

    def default_map(self, default_map=None):
        default_map = super(FileNode, self).default_map(default_map=default_map)
        default_map["element_type"] = "File"
        if self.filepath is None:
            s = "None"
        else:
            s = os.path.basename(self._filepath)
        default_map["full_filename"] = self._filepath
        default_map["filename"] = s
        return default_map

    def drop(self, drag_node, modify=True):
        if drag_node.type == "group":
            if modify:
                self.append_child(drag_node)
        return False

    @property
    def name(self):
        if self.filepath is None:
            s = None
        else:
            s = os.path.basename(self._filepath)
        return s
