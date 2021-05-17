from ..kernel import Modifier


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("modifier/Outputs", Outputs)
        kernel.register("output/file", FileOutput)
        kernel_root = kernel.get_context("/")
        kernel_root.activate("modifier/Outputs")


class FileOutput:
    def __init__(self, filename, name=None):
        super().__init__()
        self.next = None
        self.prev = None
        self.filename = filename
        self._stream = None
        self.name = name

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

    def __repr__(self):
        if self.name is not None:
            return "FileOutput('%s','%s')" % (self.filename, self.name)
        return "FileOutput(%s)" % self.filename

    def __len__(self):
        return 0

    realtime_write = write


class Outputs(Modifier):
    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, name, channel)
        self._outputs = dict()
        self._default_output = "0"

    def get_output(self, output_name, **kwargs):
        try:
            return self._outputs[output_name]
        except KeyError:
            pass
        return None

    def make_output(self, output_name, output_type, **kwargs):
        try:
            return self._outputs[output_name]
        except KeyError:
            try:
                for pname in self.context.match("output/%s" % output_type):
                    output_class = self.context.registered[pname]
                    output = output_class(self.context, output_name, **kwargs)
                    self._outputs[output_name] = output, output_name
                    return output, output_name
            except (KeyError, IndexError):
                pass
        return None

    def default_output(self):
        return self.get_output(self._default_output)

    def attach(self, *a, **kwargs):
        context = self.context
        context.outputs = self
        context.default_output = self.default_output

        kernel = self.context._kernel
        _ = kernel.translation

        @context.console_option("new", "n", type=str, help="new output type")
        @context.console_command(
            "output",
            help="output<?> <command>",
            regex=True,
            input_type=(None, "source", "driver"),
            output_type="output",
        )
        def output(
            command,
            channel,
            _,
            data=None,
            data_type=None,
            new=None,
            remainder=None,
            **kwargs
        ):
            if len(command) > 6:
                self._default_output = command[6:]
                self.context.signal("output", self._default_output, None)
            if new is not None and self._default_output in self._outputs:
                for i in range(1000):
                    if str(i) in self._outputs:
                        continue
                    self._default_output = str(i)
                    break

            if new is not None:
                output_data = self.make_output(self._default_output, new)
            else:
                output_data = self.get_output(self._default_output)

            if output_data is None:
                raise SyntaxError("No Output")

            output, output_name = output_data
            self.context.signal("output", output_name, 1)

            if data is not None:
                input_driver, dname = data
                input_driver.next = output
                output.prev = input_driver
                input_driver.data_output = output.write
                input_driver.data_output_realtime = output.realtime_write
            elif remainder is None:
                output, output_name = output_data
                channel(_("----------"))
                channel(_("Output:"))
                for i, pname in enumerate(self._outputs):
                    channel("%d: %s" % (i, pname))
                channel(_("----------"))
                channel(_("Output %s: %s" % (output_name, str(output))))
                channel(_("----------"))

            return "output", output_data

        @context.console_argument("filename")
        @context.console_command(
            "outfile",
            help="outfile filename",
            input_type=(None, "source", "driver"),
            output_type="output",
        )
        def outfile(command, channel, _, data=None, filename=None, **kwargs):
            if filename is None:
                raise SyntaxError("No file specified.")

            for i in range(1000):
                if str(i) in self._outputs:
                    continue
                self.default_output = str(i)
                break
            output_name = self.default_output
            fileoutput = FileOutput(filename)
            self._outputs[output_name] = fileoutput, output_name

            if data is not None:
                input_driver, dname = data
                input_driver.next = fileoutput
                input_driver.data_output = fileoutput.write
                input_driver.data_output_realtime = fileoutput.realtime_write
            return "output", (fileoutput, output_name)

        @self.context.console_command(
            "list",
            help="output<?> list, list current outputs",
            input_type="output",
            output_type="output",
        )
        def output(command, channel, _, data_type=None, data=None, **kwargs):
            output, output_name = data
            channel(_("----------"))
            channel(_("Output:"))
            for i, pname in enumerate(self._outputs):
                channel("%d: %s" % (i, pname))
            channel(_("----------"))
            channel(_("Output %s: %s" % (output_name, str(output))))
            channel(_("----------"))
            return data_type, data

        @context.console_command("type", help="list output types", input_type="output")
        def list_type(channel, _, **kwargs):
            channel(_("----------"))
            channel(_("Output types:"))
            for i, name in enumerate(context.match("output/", suffix=True)):
                channel("%d: %s" % (i + 1, name))
            channel(_("----------"))
