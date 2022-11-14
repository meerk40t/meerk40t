import os

from meerk40t.core.node.node import Node


class FileNode(Node):
    """
    Branch Element Node.
    Bootstrapped type: 'file'
    """

    def __init__(self, filepath=None, id=None, label=None, lock=False, **kwargs):
        super(FileNode, self).__init__(
            type="file", id=id, label=label, lock=lock, **kwargs
        )
        self._filepath = filepath
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
    def filepath(self):
        return self._filepath

    @filepath.setter
    def filepath(self, value):
        self._filepath = value

    @property
    def name(self):
        if self.filepath is None:
            s = None
        else:
            s = os.path.basename(self._filepath)
        return s
