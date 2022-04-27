from meerk40t.core.element_types import *
from meerk40t.core.node.node import Node


class ConsoleOperation(Node):
    """
    ConsoleOperation contains a console command (as a string) to be run.

    NOTE: This will eventually replace ConsoleOperation.

    Node type "op console"
    """

    def __init__(self, command=None, **kwargs):
        super().__init__(type="op console", **kwargs)
        self.settings = {}
        if command is not None:
            self.settings["command"] = command
        self.settings["output"] = True

    def set_command(self, command):
        self.settings["command"] = command

    @property
    def command(self):
        return self.settings.get("command")

    @property
    def output(self):
        return self.settings.get("output", True)

    def __repr__(self):
        return f"ConsoleOperation('{self.command}')"

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

    def default_map(self, default_map=None):
        default_map = super(ConsoleOperation, self).default_map(default_map=default_map)
        default_map["element_type"] = "Console"
        default_map["enabled"] = "(Disabled) " if not self.output else ""
        default_map["command"] = self.command
        default_map.update(self.settings)
        return default_map

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
        update_dict = settings.read_persistent_string_dict(section, suffix=True)
        self.settings.update(update_dict)

    def save(self, settings, section):
        settings.write_persistent_dict(section, self.settings)

    def generate(self):
        command = self.command
        if not command.endswith("\n"):
            command += "\n"
        yield "console", command
