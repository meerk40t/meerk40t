from meerk40t.core.element_types import *
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

    def __copy__(self):
        return ConsoleOperation(**self.node_dict)

    def __len__(self):
        return 1

    def default_map(self, default_map=None):
        default_map = super(ConsoleOperation, self).default_map(default_map=default_map)
        default_map["element_type"] = "Console"
        default_map["enabled"] = "(Disabled) " if not self.output else ""
        default_map.update(self.__dict__)
        return default_map

    def drop(self, drag_node, modify=True):
        drop_node = self
        if drag_node.type in op_nodes:
            if modify:
                drop_node.insert_sibling(drag_node)
            return True
        elif drop_node.type == "branch ops":
            # Dragging operation to op branch to effectively move to bottom.
            if modify:
                drop_node.append_child(drag_node)
            return True
        return False

    def generate(self):
        command = self.command
        if not command.endswith("\n"):
            command += "\n"
        yield "console", command
