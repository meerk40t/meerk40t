
class CommandOperation(Node):
    """
    CommandOperation is a basic command operation. It contains nothing except a single command to be executed.

    Node type "cmdop"
    """

    def __init__(self, name, command, *args, **kwargs):
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

    def generate(self):
        yield (self.command,) + self.args
