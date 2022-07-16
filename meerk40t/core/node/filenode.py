import os

from meerk40t.core.element_types import elem_nodes
from meerk40t.core.node.node import Node


class FileNode(Node):
    """
    Branch Element Node.
    Bootstrapped type: 'file'
    """

    def __init__(self, filepath=None, **kwargs):
        super(FileNode, self).__init__(type="file", **kwargs)
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

    def drop(self, drag_node):
        if drag_node.type == "group":
            self.append_child(drag_node)
        return False

    @property
    def bounds(self):
        if self._bounds_dirty:
            self._bounds = Node.union_bounds(self.flat(types=elem_nodes))
            self._bounds_dirty = False
        return self._bounds

    @property
    def filepath(self):
        return self._filepath

    @filepath.setter
    def filepath(self, value):
        self._filepath = value
