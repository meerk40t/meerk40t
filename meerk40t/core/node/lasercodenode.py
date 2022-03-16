from meerk40t.core.node.node import Node


class LaserCodeNode(Node):
    """
    LaserCode is basic command operations. It contains nothing except a list of commands to be executed.

    Node type "lasercode"
    """

    def __init__(self, commands, **kwargs):
        super().__init__(commands, type="lasercode")
        if "name" in kwargs:
            self.name = kwargs["name"]
        else:
            self.name = "LaserCode"
        self.commands = commands
        self.output = True

    def __repr__(self):
        return "LaserCode('%s', '%s')" % (self.name, str(self.commands))

    def __str__(self):
        return "LaserCode: %s, %s commands" % (self.name, str(len(self.commands)))

    def __copy__(self):
        return LaserCodeNode(self.commands, name=self.name)

    def __len__(self):
        return len(self.commands)

    def generate(self):
        for cmd in self.commands:
            yield cmd
