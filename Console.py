from Kernel import *
from svgelements import *


class Console(Modifier):
    """
    Console is a central element within MeerK40t which controls the parsing and commands
    of console commands. These are commands passed to bind as well as batch-commands and
    terminal commands. Most command line operations will be done with console commands running
    with the -c flag.
    """

    def initialize(self, context, path):
        kernel = self.context._kernel


    def finalize(self, channel=None):
        self.context.unlisten('interpreter;mode', self.on_mode_change)

    def on_mode_change(self, *args):
        self.dx = 0
        self.dy = 0
