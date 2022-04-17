from meerk40t.core.node.node import Node


class CommandOperation(Node):
    """
    CommandOperation is a basic command operation. It contains nothing except a single command to be executed.

    Node type "cmdop"
    """

    def __init__(self, name=None, command=None, *args, **kwargs):
        super().__init__(type="cmdop")
        self.name = name
        self.command = command
        self.args = args
        self.output = True

    def __repr__(self):
        return "CommandOperation('%s', '%s')" % (self.label, str(self.command))

    def __str__(self):
        parts = list()
        if not self.output:
            parts.append("(Disabled)")
        parts.append(self.name)
        return " ".join(parts)

    def __copy__(self):
        return CommandOperation(self.label, self.command, *self.args)

    def __len__(self):
        return 1

    def drop(self, drag_node):
        if drag_node.type in (
            "op cut",
            "op raster",
            "op image",
            "op engrave",
            "op dots",
            "op hatch",
            "op console",
        ):
            self.insert_sibling(drag_node)
            return True
        elif self.type == "branch ops":
            # Dragging operation to op branch to effectively move to bottom.
            self.append_child(drag_node)
            return True
        return False

    def load(self, settings, section):
        self.name = settings.read_persistent(str, section, "label")
        self.command = settings.read_persistent(int, section, "command")
        settings.read_persistent_attributes(section, self)

    def save(self, settings, section):
        settings.write_persistent_attributes(section, self)

    def generate(self):
        yield (self.command,) + self.args
