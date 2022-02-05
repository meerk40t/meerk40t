from meerk40t.core.node.node import Node


class CommandOperation(Node):
    """
    CommandOperation is a basic command operation. It contains nothing except a single command to be executed.

    Node type "cmdop"
    """

    def __init__(self, name=None, command=None, *args, **kwargs):
        super().__init__(type="cmdop")
        self.label = self.name = name
        self.command = command
        self.args = args
        self.output = True
        self.operation = "Command"

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

    def load(self, settings, section):
        self.name = settings.read_persistent(str, section, "label")
        self.command = settings.read_persistent(int, section, "command")
        settings.read_persistent_attributes(section, self)

    def save(self, settings, section):
        settings.write_persistent_attributes(section, self)

    def generate(self):
        yield (self.command,) + self.args
