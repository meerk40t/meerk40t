from meerk40t.core.element_types import *
from meerk40t.core.node.node import Node


class ConsoleOperation(Node):
    """
    ConsoleOperation contains a console command (as a string) to be run.

    NOTE: This will eventually replace ConsoleOperation.

    Node type "op console"
    """

    def __init__(self, command=None, **kwargs):
        super().__init__(type="op console")
        self.command = command
        self.output = True

    def set_command(self, command):
        self.command = command

    def __repr__(self):
        return "ConsoleOperation('%s', '%s')" % (self.command)

    def __str__(self):
        parts = list()
        if not self.output:
            parts.append("(Disabled)")
        if self.command is not None:
            parts.append(self.command)
        return " ".join(parts)

    def __copy__(self):
        return ConsoleOperation(self.command)

    def __len__(self):
        return 1

    def drop(self, drag_node):
        drop_node = self
        if drag_node.type in op_nodes:
            drop_node.insert_sibling(drag_node)
            return True
        elif drop_node.type == "branch ops":
            # Dragging operation to op branch to effectively move to bottom.
            drop_node.append_child(drag_node)
            return True
        return False

    def load(self, settings, section):
        command = settings.read_persistent(int, section, "command")
        self.command = command
        settings.read_persistent_attributes(section, self)

    def save(self, settings, section):
        settings.write_persistent_attributes(section, self)

    def generate(self):
        command = self.command
        if not command.endswith("\n"):
            command += "\n"
        yield "console", command
