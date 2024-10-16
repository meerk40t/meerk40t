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

    def can_drop(self, drag_node):
        # Move operation to a different position.
        return bool(drag_node.type in op_nodes)

    def drop(self, drag_node, modify=True, flag=False):
        # Default routine for drag + drop for an op node - irrelevant for others...
        drop_node = self
        if not self.can_drop(drag_node):
            return False
        if modify:
            drop_node.insert_sibling(drag_node)
        return True

    def generate(self):
        command = self.command
        if not command.endswith("\n"):
            command += "\n"
        yield "console", command
