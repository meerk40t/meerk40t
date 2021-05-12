from ..kernel import Modifier


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("modifier/Pipes", Pipes)
        kernel.register("pipe/file", FilePipe)

    elif lifecycle == "boot":
        kernel_root = kernel.get_context("/")
        kernel_root.activate("modifier/Pipes")


class FilePipe:
    def __init__(self, filename):
        super().__init__()
        self.source = None
        self.filename = filename
        self._stream = None

    def writable(self):
        return True

    def write(self, data):
        if self._stream is None:
            if isinstance(data, (bytes, bytearray)):
                self._stream = open(self.filename, "wb")
            else:
                self._stream = open(self.filename, "w")
        self._stream.write(data)
        self._stream.flush()

    def __len__(self):
        return 0

    realtime_write = write


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

        @context.console_option("new", "n", type=str, help="new pipe type")
        @context.console_command(
            "pipe",
            help="pipe<?> <command>",
            regex=True,
            input_type=(None, "source", "interpret"),
            output_type="pipe"
        )
        def pipe(command, channel, _, data=None, data_type=None, new=None, remainder=None, **kwargs):
            if len(command) > 4:
                self._default_pipe = command[4:]
                self.context.signal("pipe", self._default_pipe, None)
            if new is not None and self._default_pipe in self._pipes:
                for i in range(1000):
                    if str(i) in self._pipes:
                        continue
                    self.default_pipe = str(i)
                    break

            if new is not None:
                pipe_data = self.make_pipe(self._default_pipe, new)
            else:
                pipe_data = self.get_pipe(self._default_pipe)

            if pipe_data is None:
                raise SyntaxError("No Pipe")

            pipe, pipe_name = pipe_data
            self.context.signal("pipe", pipe_name, 1)

            if data is not None:
                dsource, dname = data
                dsource.output = pipe
                pipe.source = dsource
                dsource.data_output = pipe.write
                dsource.data_output_realtime = pipe.realtime_write
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

        @context.console_argument("filename")
        @context.console_command(
            "outfile",
            help="outfile filename",
            input_type=(None, "source", "interpret"),
            output_type="pipe"
        )
        def outfile(command, channel, _, data=None, data_type=None, filename=None, remainder=None, **kwargs):
            if filename is None:
                raise SyntaxError("No file specified.")

            for i in range(1000):
                if str(i) in self._pipes:
                    continue
                self.default_pipe = str(i)
                break
            pipe_name = self.default_pipe
            filepipe = FilePipe(filename)
            self._pipes[pipe_name] = filepipe, pipe_name

            if data is not None:
                dsource, dname = data
                dsource.output = pipe
                pipe.source = dsource
                dsource.data_output = filepipe.write
                dsource.data_output_realtime = filepipe.realtime_write
            return "pipe", (filepipe, pipe_name)

        @self.context.console_command(
            "list",
            help="pipe<?> list, list current pipes",
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
