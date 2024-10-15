import os

from meerk40t.core.node.node import Node


class FileNode(Node):
    """
    Branch Element Node.
    Bootstrapped type: 'file'
    """

    def __init__(self, **kwargs):
        self.filepath = None
        super().__init__(type="file", **kwargs)
        self._formatter = "{element_type}: {filename}"

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "File"
        if self.filepath is None:
            s = "None"
        else:
            s = os.path.basename(self.filepath)
        default_map["full_filename"] = self.filepath
        default_map["filename"] = s
        return default_map

    def is_a_child_of(self, node):
        candidate = self
        while candidate is not None:
            if candidate is node:
                return True
            candidate = candidate.parent
        return False

    def drop(self, drag_node, modify=True, flag=False):
        # Do not allow dragging onto children
        if self.is_a_child_of(drag_node):
            return False
        if drag_node.type == "group":
            if modify:
                self.append_child(drag_node)
        return False

    def would_accept_drop(self, drag_nodes):
        # drag_nodes can be a single node or a list of nodes
        if isinstance(drag_nodes, (list, tuple)):
            data = drag_nodes
        else:
            data = list(drag_nodes)
        for drag_node in data:
            if self.is_a_child_of(drag_node):
                continue
            if (
                drag_node.type == "group"
            ):
                return True
        return False

    @property
    def name(self):
        if self.filepath is None:
            s = None
        else:
            s = os.path.basename(self.filepath)
        return s
