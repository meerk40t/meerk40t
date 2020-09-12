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

        def grblserver(command, *args):
            port = 23
            tcp = True
            try:
                server = active_context.open('module/LaserServer',
                                            port=port,
                                            tcp=tcp,
                                            greet="Grbl 1.1e ['$' for help]\r\n")
                yield _('GRBL Mode.')
                chan = 'grbl'
                active_context.add_watcher(chan, self.channel)
                yield _('Watching Channel: %s') % chan
                chan = 'server'
                active_context.add_watcher(chan, self.channel)
                yield _('Watching Channel: %s') % chan
                server.set_pipe(active_context.open('module/GRBLEmulator'))
            except OSError:
                yield _('Server failed on port: %d') % port
            return
        kernel.register('command/grblserver', grblserver)

        def ruidaserver(command, *args):
            try:
                server = active_context.open_as('module/LaserServer', 'ruidaserver', port=50200, tcp=False)
                jog = active_context.open_as('module/LaserServer', 'ruidajog', port=50207, tcp=False)
                yield _('Ruida Data Server opened on port %d.') % 50200
                yield _('Ruida Jog Server opened on port %d.') % 50207
                chan = 'ruida'
                active_context.add_watcher(chan, self.channel)
                yield _('Watching Channel: %s') % chan
                chan = 'server'
                active_context.add_watcher(chan, self.channel)
                yield _('Watching Channel: %s') % chan
                server.set_pipe(active_context.open('module/RuidaEmulator'))
                jog.set_pipe(active_context.open('module/RuidaEmulator'))
            except OSError:
                yield _('Server failed.')
            return
        kernel.register('command/ruidaserver', ruidaserver)


    def finalize(self, channel=None):
        self.context.unlisten('interpreter;mode', self.on_mode_change)

    def on_mode_change(self, *args):
        self.dx = 0
        self.dy = 0
