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

    def get_or_make_output(self, device_name, output_type=None, **kwargs):
        dev = 'device/%s' % device_name
        try:
            device = self.context.registered[dev]
        except KeyError:
            device = [None, None, None]
            self.context.registered[dev] = device
        if device[2] is not None and output_type is None:
            return device[2]
        try:
            for itype in self.context.match("output/%s" % output_type):
                output_class = self.context.registered[itype]
                output = output_class(
                    self.context, device_name, **kwargs
                )
                device[2] = output
                return output
        except (KeyError, IndexError):
            return None

    def put_output(self, device_name, output):
        dev = 'device/%s' % device_name
        try:
            device = self.context.registered[dev]
        except KeyError:
            device = [None, None, None]
            self.context.registered[dev] = device

        try:
            device[2] = output
        except (KeyError, IndexError):
            pass

    def default_output(self):
        return self.get_or_make_output(self.context.root.active)

    def attach(self, *a, **kwargs):
        context = self.context
        context.outputs = self

        kernel = self.context._kernel
        _ = kernel.translation

        @context.console_option("new", "n", type=str, help="new output type")
        @context.console_command(
            "output",
            help="output<?> <command>",
            regex=True,
            input_type=(None, "input", "driver"),
            output_type="output",
        )
        def output(
            command,
            channel,
            _,
            data=None,
            new=None,
            remainder=None,
            **kwargs
        ):
            input_driver = None
            if data is None:
                if len(command) > 6:
                    device_name = command[6:]
                    self.context.active = device_name
                else:
                    device_name = self.context.active
            else:
                input_driver, device_name = data

            output = self.get_or_make_output(device_name, new)

            if output is None:
                raise SyntaxError("No Output")

            self.context.signal("output", device_name, 1)

            if input_driver is not None:
                input_driver.next = output
                output.prev = input_driver
                input_driver.data_output = output.write
                input_driver.data_output_realtime = output.realtime_write
            elif remainder is None:
                pass

            return "output", (output, device_name)

        @context.console_argument("filename")
        @context.console_command(
            "outfile",
            help="outfile filename",
            input_type=(None, "input", "driver"),
            output_type="output",
        )
        def outfile(command, channel, _, data=None, filename=None, **kwargs):
            if filename is None:
                raise SyntaxError("No file specified.")
            input_driver = None
            if data is None:
                if len(command) > 6:
                    device_name = command[6:]
                else:
                    device_name = self.context.active
            else:
                input_driver, device_name = data

            output = FileOutput(filename)
            self.put_output(device_name, output)

            if input_driver is not None:
                input_driver.next = output
                output.prev = input_driver
                input_driver.data_output = output.write
                input_driver.data_output_realtime = output.realtime_write
            return "output", (output, device_name)

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
