import os

from meerk40t.core.node.node import Node


class FileNode(Node):
    """
    Branch Element Node.
    Bootstrapped type: 'file'
    """

    def __init__(self, data_object, filepath=None, **kwargs):
        super(FileNode, self).__init__(data_object)
        self._filepath = filepath

    def __str__(self):
        if self.filepath is None:
            return "File: None"
        return os.path.basename(self._filepath)

    @property
    def filepath(self):
        return self._filepath

    @filepath.setter
    def filepath(self, value):
        self._filepath = value
        self.label = None
