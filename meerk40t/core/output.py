import threading
import socket

from ..kernel import Modifier


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("modifier/Outputs", Outputs)
        kernel.register("output/file", FileOutput)
        kernel.register("output/tcp", TCPOutput)
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
        with open(self.filename, "ab" if isinstance(data, (bytes, bytearray)) else "a") as stream:
            stream.write(data)
            stream.flush()

    def __repr__(self):
        if self.name is not None:
            return "FileOutput('%s','%s')" % (self.filename, self.name)
        return "FileOutput(%s)" % self.filename

    def __len__(self):
        return 0

    realtime_write = write

    @property
    def type(self):
        return "file"


class TCPOutput:
    def __init__(self, context, address, port, name=None):
        super().__init__()
        self.context = context
        self.next = None
        self.prev = None
        self.address = address
        self.port = port
        self._stream = None
        self.name = name

        self.lock = threading.Lock()
        self.buffer = bytearray()

    def writable(self):
        return True

    def write(self, data):
        self.context.signal("tcp;write", data)
        self.buffer += data
        self.context.signal("tcp;buffer", len(self.buffer))
        try:
            if self._stream is None:
                self._stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._stream.connect((self.address, self.port))
                self.context.signal("tcp;status", "connected")
            self._stream.sendall(self.buffer)
            self.buffer = bytearray()
            self.context.signal("tcp;buffer", 0)
        except ConnectionError:
            self.context.signal("tcp;status", "disconnected")
            self._stream.close()
            self._stream = None

    def __repr__(self):
        if self.name is not None:
            return "TCPOutput('%s:%s','%s')" % (self.address, self.port, self.name)
        return "TCPOutput('%s:%s')" % (self.address, self.port)

    def __len__(self):
        return len(self.buffer)

    realtime_write = write

    @property
    def type(self):
        return "tcp"


class Outputs(Modifier):
    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, name, channel)

    def get_or_make_output(self, device_name, output_type=None, **kwargs):
        dev = "device/%s" % device_name
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
                output = output_class(self.context, device_name, **kwargs)
                device[2] = output
                return output
        except (KeyError, IndexError):
            return None

    def put_output(self, device_name, output):
        dev = "device/%s" % device_name
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
        def output(command, channel, _, data=None, new=None, remainder=None, **kwargs):
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

                input_driver.output = output
                output.input = input_driver
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

                input_driver.output = output
                output.input = input_driver
            return "output", (output, device_name)

        @context.console_argument("address", type=str, help="tcp address")
        @context.console_argument("port", type=int, help="tcp/ip port")
        @context.console_command(
            "tcp",
            help="network <address> <port>",
            input_type=(None, "input", "driver"),
            output_type="output",
        )
        def outtcp(command, channel, _, data=None, address=None, port=None, **kwargs):
            if port is None:
                raise SyntaxError("No address/port specified")
            input_driver = None
            if data is None:
                if len(command) > 6:
                    device_name = command[6:]
                else:
                    device_name = self.context.active
            else:
                input_driver, device_name = data

            output = TCPOutput(context, address, port)
            self.put_output(device_name, output)

            if input_driver is not None:
                input_driver.next = output
                output.prev = input_driver

                input_driver.output = output
                output.input = input_driver
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
