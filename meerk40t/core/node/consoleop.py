
class ConsoleOperation(Node):
    """
    ConsoleOperation contains a console command (as a string) to be run.

    NOTE: This will eventually replace ConsoleOperation.

    Node type "consoleop"
    """

    def __init__(self, command, **kwargs):
        super().__init__(type="consoleop")
        self.command = command
        self.output = True
        self.operation = "Console"

    def set_command(self, command):
        self.command = command
        self.label = command

    def __repr__(self):
        return "ConsoleOperation('%s', '%s')" % (self.command)

    def __str__(self):
        parts = list()
        if not self.output:
            parts.append("(Disabled)")
        parts.append(self.command)
        return " ".join(parts)

    def __copy__(self):
        return ConsoleOperation(self.command)

    def __len__(self):
        return 1

    def generate(self):
        command = self.command
        if not command.endswith("\n"):
            command += "\n"
        yield "console", command

