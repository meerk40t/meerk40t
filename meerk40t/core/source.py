from ..kernel import Modifier


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("modifier/Source", Source)
        kernel.register("source/file", FileSource)
        kernel.register("source/tcp", TcpSource)

    elif lifecycle == "boot":
        kernel_root = kernel.get_context("/")
        kernel_root.activate("modifier/Sources")


class Source:
    def __init__(self):
        self.output = None
        self.input = None


class FileSource(Source):
    def __init__(self):
        super().__init__()


class TcpSource(Source):
    def __init__(self):
        super().__init__()


class Sources(Modifier):

    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, name, channel)
        self._sources = dict()
        self._default_source = "0"

    def get_source(self, source_name, **kwargs):
        try:
            return self._sources[source_name]
        except KeyError:
            pass
        return None

    def make_source(self, source_name, source_type, **kwargs):
        try:
            return self._sources[source_name]
        except KeyError:
            try:
                for pname in self.context.match("source/%s" % source_type):
                    source_class = self.context.registered[pname]
                    source = source_class(self.context, source_name, **kwargs)
                    self._sources[source_name] = source, source_name
                    return source, source_name
            except (KeyError, IndexError):
                pass
        return None

    def default_source(self):
        return self.get_source(self._default_source)

    def attach(self, *a, **kwargs):
        context = self.context
        context.sources = self
        context.default_source = self.default_source

        kernel = self.context._kernel
        _ = kernel.translation

        @context.console_option("new", "n", type=str, help="new source type")
        @context.console_command(
            "source",
            help="source<?> <command>",
            regex=True,
            input_type=None,
            output_type="source",
        )
        def source(command, channel, _, data=None, data_type=None, new=None, remainder=None, **kwargs):
            if len(command) > 6:
                self._default_source = command[6:]
                self.context.signal("source", self._default_source, None)
            if new is not None and self._default_source in self._sources:
                for i in range(1000):
                    if str(i) in self._sources:
                        continue
                    self.default_source = str(i)
                    break

            if new is not None:
                source_data = self.make_source(self._default_source, new)
            else:
                source_data = self.get_source(self._default_source)

            if source_data is None:
                raise SyntaxError("No source")

            source, source_name = source_data
            self.context.signal("source", source_name, 1)

            if data is not None:
                if data_type == "interpret":
                    dinter, dname = data
                    dinter.output = source
                elif data_type == "source":
                    dsource, dname = data
                    dsource.output = source
            elif remainder is None:
                source, source_name = source_data
                channel(_("----------"))
                channel(_("Source:"))
                for i, pname in enumerate(self._sources):
                    channel("%d: %s" % (i, pname))
                channel(_("----------"))
                channel(_("Source %s: %s" % (source_name, str(source))))
                channel(_("----------"))

            return "source", source_data

        @self.context.console_command(
            "list",
            help="source<?> list, list current sources",
            input_type="source",
            output_type="source",
        )
        def source(command, channel, _, data_type=None, data=None, **kwargs):
            source, source_name = data
            channel(_("----------"))
            channel(_("Source:"))
            for i, pname in enumerate(self._sources):
                channel("%d: %s" % (i, pname))
            channel(_("----------"))
            channel(_("Source %s: %s" % (source_name, str(source))))
            channel(_("----------"))
            return data_type, data

        @context.console_command(
            "type",
            help="list source types",
            input_type="source"
        )
        def list_type(channel, _, **kwargs):
            channel(_("----------"))
            channel(_("Source types:"))
            for i, name in enumerate(context.match("source/", suffix=True)):
                channel("%d: %s" % (i + 1, name))
            channel(_("----------"))
