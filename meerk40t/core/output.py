import socket
import threading
import time

from ..kernel import Modifier


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        _ = kernel.translation
        kernel.register("modifier/Outputs", Outputs)
        kernel.register("output/file", FileOutput)
        kernel.register("output/tcp", TCPOutput)
        kernel_root = kernel.root
        kernel_root.activate("modifier/Outputs")

        @kernel.console_argument(
            "port", type=int, help=_("Port of TCPOutput to change.")
        )
        @kernel.console_command(
            "port",
            help=_("change the port of the tcpdevice"),
            input_type="tcpout",
        )
        def tcpport(channel, _, port, data=None, **kwargs):
            spooler, input_driver, output = data
            old_port = output.port
            output.port = port
            channel(_("TCP port changed: %s -> %s" % (str(old_port), str(port))))


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
        filename = self.filename.replace("?", "").replace(":", "")
        with open(
            filename, "ab" if isinstance(data, (bytes, bytearray)) else "a"
        ) as stream:
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

        self.lock = threading.RLock()
        self.buffer = bytearray()
        self.thread = None

    def writable(self):
        return True

    def connect(self):
        try:
            self._stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._stream.connect((self.address, self.port))
            self.context.signal("tcp;status", "connected")
        except (ConnectionError, TimeoutError):
            self.disconnect()
        except socket.gaierror as e:
            self.disconnect()
            self.context.signal("warning", "Socket Error", f"Socket error: {e}")

    def disconnect(self):
        self.context.signal("tcp;status", "disconnected")
        self._stream.close()
        self._stream = None

    def write(self, data):
        self.context.signal("tcp;write", data)
        if isinstance(data, str):
            data = data.encode("utf-8")
        with self.lock:
            self.buffer += data
            self.context.signal("tcp;buffer", len(self.buffer))
        self._start()

    realtime_write = write

    def _start(self):
        if self.thread is None:
            self.thread = self.context.threaded(
                self._sending, thread_name="sender-%d" % self.port, result=self._stop
            )

    def _stop(self, *args):
        self.thread = None

    def _sending(self):
        tries = 0
        while True:
            try:
                if len(self.buffer):
                    if self._stream is None:
                        self.connect()
                        if self._stream is None:
                            return
                    with self.lock:
                        sent = self._stream.send(self.buffer)
                        del self.buffer[:sent]
                        self.context.signal("tcp;buffer", len(self.buffer))
                    tries = 0
                else:
                    tries += 1
                    time.sleep(0.1)
            except (ConnectionError, OSError):
                tries += 1
                self.disconnect()
                time.sleep(0.05)
            if tries >= 20:
                with self.lock:
                    if len(self.buffer) == 0:
                        break

    def __repr__(self):
        if self.name is not None:
            return "TCPOutput('%s:%s','%s')" % (self.address, self.port, self.name)
        return "TCPOutput('%s:%s')" % (self.address, self.port)

    def __len__(self):
        return len(self.buffer)

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
            self.context.signal("legacy_spooler_label", device_name)
        if device[2] is not None and output_type is None:
            return device[2]
        try:
            for itype in self.context.match("output/%s" % output_type):
                output_class = self.context.registered[itype]
                output = output_class(self.context, device_name, **kwargs)
                device[2] = output
                self.context.signal("legacy_spooler_label", device_name)
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

        _ = self.context._

        @context.console_option("new", "n", type=str, help=_("new output type"))
        @context.console_command(
            "output",
            help=_("output<?> <command>"),
            regex=True,
            input_type=(None, "input", "driver"),
            output_type="output",
        )
        def output_base(
            command, channel, _, data=None, new=None, remainder=None, **kwgs
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

                input_driver.output = output
                output.input = input_driver
            elif remainder is None:
                pass

            return "output", (output, device_name)

        @context.console_argument("filename")
        @context.console_command(
            "outfile",
            help=_("outfile filename"),
            input_type=(None, "input", "driver"),
            output_type="output",
        )
        def output_outfile(command, channel, _, data=None, filename=None, **kwgs):
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

        @context.console_argument("address", type=str, help=_("tcp address"))
        @context.console_argument("port", type=int, help=_("tcp/ip port"))
        @context.console_command(
            "tcp",
            help=_("network <address> <port>"),
            input_type=(None, "input", "driver"),
            output_type="output",
        )
        def output_tcp(command, channel, _, data=None, address=None, port=None, **kwgs):
            if port is None:
                raise SyntaxError(_("No address/port specified"))
            input_driver = None
            if data is None:
                if len(command) > 3:
                    device_name = command[3:]
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
            help=_("output<?> list, list current outputs"),
            input_type="output",
            output_type="output",
        )
        def output_list(command, channel, _, data_type=None, data=None, **kwgs):
            output, output_name = data
            channel(_("----------"))
            channel(_("Output:"))
            for i, pname in enumerate(data):
                channel("%d: %s" % (i, pname))
            channel(_("----------"))
            channel(_("Output %s: %s" % (output_name, str(output))))
            channel(_("----------"))
            return data_type, data

        @context.console_command(
            "type", help=_("list output types"), input_type="output"
        )
        def output_types(channel, _, **kwgs):
            channel(_("----------"))
            channel(_("Output types:"))
            for i, name in enumerate(context.match("output/", suffix=True)):
                channel("%d: %s" % (i + 1, name))
            channel(_("----------"))
