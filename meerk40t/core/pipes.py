from ..kernel import Modifier


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("modifier/Pipes", Pipes)
        kernel.register("pipe/file", FilePipe)
        kernel.register("pipe/tcp", TcpPipe)

    elif lifecycle == "boot":
        kernel_root = kernel.get_context("/")
        kernel_root.activate("modifier/Pipes")


class Pipe:
    def __init__(self):
        self.output = None


class FilePipe(Pipe):
    def __init__(self):
        super().__init__()


class TcpPipe(Pipe):
    def __init__(self):
        super().__init__()


class Pipes(Modifier):

    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, name, channel)
        self._pipes = dict()
        self._default_pipe = "0"

    def get_pipe(self, pipe_name, **kwargs):
        try:
            return self._pipes[pipe_name]
        except KeyError:
            pass
        return None

    def make_pipe(self, pipe_name, pipe_type, **kwargs):
        try:
            return self._pipes[pipe_name]
        except KeyError:
            try:
                for pname in self.context.match("pipe/%s" % pipe_type):
                    pipe_class = self.context.registered[pname]
                    pipe = pipe_class(self.context, pipe_name, **kwargs)
                    self._pipes[pipe_name] = pipe, pipe_name
                    return pipe, pipe_name
            except (KeyError, IndexError):
                pass
        return None

    def default_pipe(self):
        return self.get_pipe(self._default_pipe)

    def attach(self, *a, **kwargs):
        context = self.context
        context.pipes = self
        context.default_pipe = self.default_pipe

        kernel = self.context._kernel
        _ = kernel.translation

        @context.console_command(
            "pipe",
            help="pipe<?> <command>",
            regex=True,
            input_type=(None, "interpret", "pipe"),
            output_type="pipe",
        )
        def pipe(command, channel, _, data=None, data_type=None, remainder=None, **kwargs):
            if len(command) > 4:
                self._default_pipe = command[4:]
                self.context.signal("pipe", self._default_pipe, None)

            pipe_data = self.get_pipe(self._default_pipe)
            if pipe_data is None:
                raise SyntaxError

            pipe, pipe_name = pipe_data
            self.context.signal("pipe", pipe_name, 1)

            if data is not None:
                if data_type == "interpret":
                    dinter, dname = data
                elif data_type == "pipe":
                    dpipe, dname = data
            elif remainder is None:
                pipe, pipe_name = pipe_data
                channel(_("----------"))
                channel(_("Pipe:"))
                for i, pname in enumerate(self._pipes):
                    channel("%d: %s" % (i, pname))
                channel(_("----------"))
                channel(_("Pipe %s: %s" % (pipe_name, str(pipe))))
                channel(_("----------"))

            return "pipe", pipe_data

        @context.console_argument("type")
        @context.console_command(
            "new-pipe",
            help="pipe <command>",
            input_type=(None, "interpret", "pipe"),
            output_type="pipe",
        )
        def pipe(command, channel, _, data=None, data_type=None, type=None, remainder=None, **kwargs):
            if type is None:
                raise SyntaxError("Must specify a valid interpreter type.")
            for i in range(1000):
                if str(i) in self._pipes:
                    continue
                self.default_pipe = str(i)
                break
            pipe_data = self.make_pipe(self._default_pipe, type)
            if pipe_data is None:
                raise SyntaxError

            pipe, pipe_name = pipe_data
            self.context.signal("pipe", pipe_name, 1)

            if data is not None:
                if data_type == "interpret":
                    dinter, dname = data
                    dinter.output = pipe
                elif data_type == "pipe":
                    dpipe, dname = data
                    dpipe.output = pipe
            elif remainder is None:
                pipe, pipe_name = pipe_data
                channel(_("----------"))
                channel(_("Pipe:"))
                for i, pname in enumerate(self._pipes):
                    channel("%d: %s" % (i, pname))
                channel(_("----------"))
                channel(_("Pipe %s: %s" % (pipe_name, str(pipe))))
                channel(_("----------"))

            return "pipe", pipe_data

        @self.context.console_command(
            "list",
            help="pipe<?> list",
            input_type="pipe",
            output_type="pipe",
        )
        def pipe(command, channel, _, data_type=None, data=None, **kwargs):
            pipe, pipe_name = data
            channel(_("----------"))
            channel(_("Pipe:"))
            for i, pname in enumerate(self._pipes):
                channel("%d: %s" % (i, pname))
            channel(_("----------"))
            channel(_("Pipe %s: %s" % (pipe_name, str(pipe))))
            channel(_("----------"))
            return data_type, data

        @context.console_command(
            "type",
            help="list pipe types",
            input_type="pipe"
        )
        def list_type(channel, _, **kwargs):
            channel(_("----------"))
            channel(_("Pipe types:"))
            for i, name in enumerate(context.match("pipe/", suffix=True)):
                channel("%d: %s" % (i + 1, name))
            channel(_("----------"))
