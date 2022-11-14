from meerk40t.core.element_types import *
from meerk40t.core.node.node import Node


class ConsoleOperation(Node):
    """
    ConsoleOperation contains a console command (as a string) to be run.

    Node type "util console"
    """

    def __init__(self, command=None, id=None, label=None, lock=False, **kwargs):
        super().__init__(type="util console", id=id, label=label, lock=lock, **kwargs)
        self._formatter = "{enabled}{command}"
        self.settings = {}
        if command is not None:
            self.settings["command"] = command
        self.settings["output"] = True

    def __repr__(self):
        return f"ConsoleOperation('{self.command}')"

    def __copy__(self):
        return ConsoleOperation(
            self.command, id=self.id, label=self.label, lock=self.lock, **self.settings
        )

    def __len__(self):
        return 1

    def set_command(self, command):
        self.settings["command"] = command

    @property
    def command(self):
        return self.settings.get("command")

    @command.setter
    def command(self, v):
        self.settings["command"] = v

    @property
    def output(self):
        return self.settings.get("output", True)

    @output.setter
    def output(self, v):
        self.settings["output"] = v

    def validate(self):
        parameters = [
            ("output", lambda v: str(v).lower() == "true"),
            ("command", str),
        ]
        settings = self.settings
        for param, cast in parameters:
            try:
                if param in settings and settings[param] is not None:
                    settings[param] = (
                        cast(settings[param]) if settings[param] != "None" else None
                    )
            except (KeyError, ValueError):
                pass

    def default_map(self, default_map=None):
        default_map = super(ConsoleOperation, self).default_map(default_map=default_map)
        default_map["element_type"] = "Console"
        default_map["enabled"] = "(Disabled) " if not self.output else ""
        default_map["command"] = self.command
        default_map.update(self.settings)
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

    def load(self, settings, section):
        update_dict = settings.read_persistent_string_dict(section, suffix=True)
        self.settings.update(update_dict)
        self.validate()

    def save(self, settings, section):
        settings.write_persistent_dict(section, self.settings)

    def generate(self):
        command = self.command
        if not command.endswith("\n"):
            command += "\n"
        yield "console", command
