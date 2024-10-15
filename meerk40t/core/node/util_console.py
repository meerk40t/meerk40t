from meerk40t.core.elements.element_types import op_nodes
from meerk40t.core.node.node import Node


class ConsoleOperation(Node):
    """
    ConsoleOperation contains a console command (as a string) to be run.

    Node type "util console"
    """

    def __init__(self, **kwargs):
        self.output = True
        self.command = None
        self._formatter = "{enabled}{command}"
        super().__init__(type="util console", **kwargs)

    def __repr__(self):
        return f"ConsoleOperation('{self.command}')"

    def __len__(self):
        return 1

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Console"
        default_map["enabled"] = "(Disabled) " if not self.output else ""
        default_map.update(self.__dict__)
        return default_map

    def drop(self, drag_node, modify=True, flag=False):
        drop_node = self
        if drag_node.type in op_nodes:
            if modify:
                drop_node.insert_sibling(drag_node)
            return True
        return False    

    def would_accept_drop(self, drag_nodes):
        # drag_nodes can be a single node or a list of nodes
        if isinstance(drag_nodes, (list, tuple)):
            data = drag_nodes
        else:
            data = list(drag_nodes)
        for drag_node in data:
            if (
                drag_node.type in op_nodes
            ):
                return True
        return False

    def generate(self):
        command = self.command
        if not command.endswith("\n"):
            command += "\n"
        yield "console", command
