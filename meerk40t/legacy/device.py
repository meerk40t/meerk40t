import socket
import threading
import time

from meerk40t.core.spoolers import Spooler
from meerk40t.kernel import Service
from meerk40t.kernel import CommandMatchRejected


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.add_service("device", LegacyDevice(kernel))
        kernel.register("output/file", FileOutput)
        kernel.register("output/tcp", TCPOutput)
    elif lifecycle == "boot":
        legacy_device = kernel.get_context("legacy")
        legacy_device.boot()
        _ = legacy_device._
        choices = [
            {
                "attr": "bedwidth",
                "object": legacy_device,
                "default": 12205.0,
                "type": float,
                "label": _("Width"),
                "tip": _("Width of the laser bed."),
            },
            {
                "attr": "bedheight",
                "object": legacy_device,
                "default": 8268.0,
                "type": float,
                "label": _("Height"),
                "tip": _("Height of the laser bed."),
            },
            {
                "attr": "scale_x",
                "object": legacy_device,
                "default": 1.000,
                "type": float,
                "label": _("X Scale Factor"),
                "tip": _(
                    "Scale factor for the X-axis. This defines the ratio of mils to steps. This is usually at 1:1 steps/mils but due to functional issues it can deviate and needs to be accounted for"
                ),
            },
            {
                "attr": "scale_y",
                "object": legacy_device,
                "default": 1.000,
                "type": float,
                "label": _("Y Scale Factor"),
                "tip": _(
                    "Scale factor for the Y-axis. This defines the ratio of mils to steps. This is usually at 1:1 steps/mils but due to functional issues it can deviate and needs to be accounted for"
                ),
            },
        ]
        legacy_device.register_choices("bed_dim", choices)


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

    def disconnect(self):
        self.context.signal("tcp;status", "disconnected")
        self._stream.close()
        self._stream = None

    def write(self, data):
        self.context.signal("tcp;write", data)
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


class LegacyDevice(Service):
    """
    Legacy Device governs the 0.7.x style device connections between spoolers, controllers, and output.

    Legacy Devices read the values in `devices` and boots the needed devices up, by running the lines found in
    device_*. These refer to local commands registered in the service.
    """

    def __init__(self, kernel, *args, **kwargs):
        Service.__init__(self, kernel, "legacy")

        _ = kernel.translation
        self.setting(str, "active", "0")
        self.signal("active", self.active)

        ########################
        # OUTPUT COMMANDS
        ########################

        @self.console_option("new", "n", type=str, help=_("new output type"))
        @self.console_command(
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
                    self.set_active(device_name)
                else:
                    device_name = self.active
            else:
                input_driver, device_name = data

            output = self.get_or_make_output(device_name, new)

            if output is None:
                raise SyntaxError("No Output")

            self.signal("output", device_name, 1)

            if input_driver is not None:
                input_driver.next = output
                output.prev = input_driver

                input_driver.output = output
                output.input = input_driver
            elif remainder is None:
                pass

            return "output", (output, device_name)

        @self.console_argument("filename")
        @self.console_command(
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
                    device_name = self.active
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

        @self.console_argument("address", type=str, help=_("tcp address"))
        @self.console_argument("port", type=int, help=_("tcp/ip port"))
        @self.console_command(
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
                    device_name = self.active
            else:
                input_driver, device_name = data

            output = TCPOutput(self, address, port)
            self.put_output(device_name, output)

            if input_driver is not None:
                input_driver.next = output
                output.prev = input_driver

                input_driver.output = output
                output.input = input_driver
            return "output", (output, device_name)

        @self.console_command(
            "list",
            help=_("output<?> list, list current outputs"),
            input_type="output",
            output_type="output",
        )
        def output_list(command, channel, _, data_type=None, data=None, **kwgs):
            output, output_name = data
            channel(_("----------"))
            channel(_("Output:"))
            for i, pname in enumerate(self._outputs):
                channel("%d: %s" % (i, pname))
            channel(_("----------"))
            channel(_("Output %s: %s" % (output_name, str(output))))
            channel(_("----------"))
            return data_type, data

        @self.console_command(
            "type", help=_("list output types"), input_type="output"
        )
        def output_types(channel, _, **kwgs):
            channel(_("----------"))
            channel(_("Output types:"))
            for i, name in enumerate(self.match("output/", suffix=True)):
                channel("%d: %s" % (i + 1, name))
            channel(_("----------"))

        @self.console_argument(
            "port", type=int, help=_("Port of TCPOutput to change.")
        )
        @self.console_command(
            "port",
            help=_("change the port of the tcpdevice"),
            input_type="tcpout",
        )
        def tcpport(channel, _, port, data=None, **kwargs):
            spooler, input_driver, output = data
            old_port = output.port
            output.port = port
            channel(_("TCP port changed: %s -> %s" % (str(old_port), str(port))))

        ########################
        # DRIVERS COMMANDS
        ########################

        @self.console_option("new", "n", type=str, help=_("new driver type"))
        @self.console_command(
            "driver",
            help=_("driver<?> <command>"),
            regex=True,
            input_type=(None, "spooler"),
            output_type="driver",
        )
        def driver_base(
                command, channel, _, data=None, new=None, remainder=None, **kwgs
        ):
            spooler = None
            if data is None:
                if len(command) > 6:
                    device_name = command[6:]
                    self.set_active(device_name)
                else:
                    device_name = self.active
            else:
                spooler = data
                device_name = data.name

            driver = self.get_or_make_driver(device_name, new)
            if driver is None:
                raise SyntaxError("No Driver.")

            if spooler is not None:
                try:
                    driver.spooler = spooler
                    spooler.next = driver
                    driver.prev = spooler
                except AttributeError:
                    pass
            elif remainder is None:
                channel(_("----------"))
                channel(_("Driver:"))
                for i, drv in enumerate(self.match("device", suffix=True)):
                    channel("%d: %s" % (i, drv))
                channel(_("----------"))
                channel(_("Driver %s:" % device_name))
                channel(str(driver))
                channel(_("----------"))
            return "driver", (driver, device_name)

        @self.console_command(
            "list",
            help=_("driver<?> list"),
            input_type="driver",
            output_type="driver",
        )
        def driver_list(command, channel, _, data_type=None, data=None, **kwgs):
            driver_obj, name = data
            channel(_("----------"))
            channel(_("Driver:"))
            for i, drv in enumerate(self.match("device", suffix=True)):
                channel("%d: %s" % (i, drv))
            channel(_("----------"))
            channel(_("Driver %s:" % name))
            channel(str(driver_obj))
            channel(_("----------"))
            return data_type, data

        @self.console_command(
            "type",
            help=_("list driver types"),
            input_type="driver",
        )
        def list_type(channel, _, **kwgs):
            channel(_("----------"))
            channel(_("Drivers permitted:"))
            for i, name in enumerate(self.match("driver/", suffix=True)):
                channel("%d: %s" % (i + 1, name))
            channel(_("----------"))

        @self.console_command(
            "reset",
            help=_("driver<?> reset"),
            input_type="driver",
            output_type="driver",
        )
        def driver_reset(data_type=None, data=None, **kwargs):
            driver_obj, name = data
            driver_obj.reset()
            return data_type, data

        ########################
        # SPOOLER DEVICE COMMANDS
        ########################

        @self.console_option(
            "register",
            "r",
            type=bool,
            action="store_true",
            help=_("Register this device"),
        )
        @self.console_command(
            "spool",
            help=_("spool<?> <command>"),
            regex=True,
            input_type=(None, "plan", "device"),
            output_type="spooler",
        )
        def spool(
            command, channel, _, data=None, register=False, remainder=None, **kwgs
        ):
            if len(command) > 5:
                device_name = command[5:]
            else:
                if register:
                    device_context = self.get_context("devices")
                    index = 0
                    while hasattr(device_context, "device_%d" % index):
                        index += 1
                    device_name = str(index)
                else:
                    device_name = self.active
            if register:
                device_context = self.get_context("devices")
                setattr(
                    device_context,
                    "device_%s" % device_name,
                    ("spool%s -r " % device_name) + remainder + "\n",
                )

            spooler = self.get_or_make_spooler(device_name)
            if data is not None:
                # If plan data is in data, then we copy that and move on to next step.
                spooler.jobs(data.plan)
                channel(_("Spooled Plan."))
                self.signal("plan", data.name, 6)

            if remainder is None:
                channel(_("----------"))
                channel(_("Spoolers:"))
                for d, d_name in enumerate(self.match("device", suffix=True)):
                    channel("%d: %s" % (d, d_name))
                channel(_("----------"))
                channel(_("Spooler %s:" % device_name))
                for s, op_name in enumerate(spooler.queue):
                    channel("%d: %s" % (s, op_name))
                channel(_("----------"))

            return "spooler", spooler

        ########################
        # BASE DEVICE COMMANDS
        ########################

        @self.console_option(
            "out",
            "o",
            action="store_true",
            help=_("match on output rather than driver"),
        )
        @self.console_command(
            "dev",
            help=_("delegate commands to currently selected device by input/driver"),
            output_type="dev",
            hidden=True,
        )
        def dev(channel, _, remainder=None, out=False, **kwargs):
            try:
                spooler, input_driver, output = self.lookup("device", self.active)
            except TypeError:
                return
            if remainder is None:
                channel(
                    _(
                        "Device %s, %s, %s"
                        % (str(spooler), str(input_driver), str(output))
                    )
                )
            if out:
                if output is not None:
                    try:
                        t = output.type + "out"
                        return t, (spooler, input_driver, output)
                    except AttributeError:
                        pass
            elif input_driver is not None:
                try:
                    t = input_driver.type
                    return t, (spooler, input_driver, output)
                except AttributeError:
                    pass

            return "dev", (spooler, input_driver, output)

        @self.console_command(".+", regex=True, hidden=True)
        def virtual_dev(command, remainder=None, **kwargs):
            try:
                spooler, input_driver, output = self.lookup("device", self.active)
            except TypeError:
                raise CommandMatchRejected(_("No device selected."))

            if input_driver is not None:
                try:
                    t = input_driver.type
                    match = "command/%s/%s$" % (str(t), command)
                    match = "".join([i for i in match if i not in "(){}[]"])
                    for command_funct, command_name, suffix in self.find(match):
                        if command_funct is not None:
                            if remainder is not None:
                                self(".dev %s %s\n" % (command, remainder))
                            else:
                                self(".dev %s\n" % command)
                            return
                except AttributeError:
                    pass
            if output is not None:
                try:
                    t = output.type + "out"
                    match = "command/%s/%s" % (str(t), command)
                    match = "".join([i for i in match if i not in "(){}[]"])
                    for command_funct, command_name, sname in self.find(match):
                        if command_funct is not None:
                            if remainder is not None:
                                self(".dev -o %s %s\n" % (command, remainder))
                            else:
                                self(".dev -o %s\n" % command)
                            return
                except AttributeError:
                    pass
            raise CommandMatchRejected(_("No matching command."))

        @self.console_argument(
            "index", type=int, help=_("Index of device being activated")
        )
        @self.console_command(
            "activate",
            help=_("delegate commands to currently selected device"),
            input_type="device",
            output_type="device",
        )
        def device(channel, _, index, **kwargs):
            spools = list(self.match("device", suffix=True))
            self.set_active(spools[index])
            channel(_("Activated device %s at index %d." % (self.active, index)))
            return "device", (None, str(index))

        @self.console_command(
            "device",
            help=_("device"),
            output_type="device",
        )
        def device(channel, _, remainder=None, **kwargs):
            device_context = self.get_context("devices")
            if remainder is None:
                channel(_("----------"))
                channel(_("Devices:"))
                index = 0
                while hasattr(device_context, "device_%d" % index):
                    line = getattr(device_context, "device_%d" % index)
                    channel("%d: %s" % (index, line))
                    index += 1
                channel("----------")
            return "device", (None, self.active)

        @self.console_command(
            "list",
            help=_("list devices"),
            input_type="device",
            output_type="device",
        )
        def list_devices(channel, _, data, **kwargs):
            device_context = self.get_context("devices")
            channel(_("----------"))
            channel(_("Devices:"))
            index = 0
            while hasattr(device_context, "device_%d" % index):
                line = getattr(device_context, "device_%d" % index)
                channel("%d: %s" % (index, line))
                index += 1
            channel("----------")
            return "device", data

        @self.console_argument("index", type=int, help=_("Index of device deleted"))
        @self.console_command(
            "delete",
            help=_("delete <index>"),
            input_type="device",
        )
        def delete(channel, _, index, **kwargs):
            spools = list(self.match("device", suffix=True))
            device_name = spools[index]

            device_context = self.get_context("devices")
            try:
                setattr(device_context, "device_%s" % device_name, "")
                device = self.lookup("device", device_name)
                if device is not None:
                    spooler, driver, output = device
                    if driver is not None:
                        try:
                            driver.shutdown()
                        except AttributeError:
                            pass
                    if output is not None:
                        try:
                            output.finalize()
                        except AttributeError:
                            pass
                self.register("device/%s" % device_name, [None, None, None])
                self.root.unregister("spooler/%s" % device_name)
            except (KeyError, ValueError):
                raise SyntaxError(_("Invalid device-string index."))

    def boot(self):
        ########################
        # LEGACY DEVICE BOOT SEQUENCE
        ########################

        device_context = self.get_context("devices")
        devices_booted = 0
        for d in device_context.kernel.keylist(device_context.path):
            suffix = d.split("/")[-1]
            if not suffix.startswith("device_"):
                continue
            line = device_context.setting(str, suffix, None)
            if line is not None and len(line):
                device_context(line + "\n")
                device_context.setting(str, suffix, None)
                devices_booted += 1

        for i in range(5):
            self.get_or_make_spooler(str(i))

        if devices_booted == 0:
            # Check if there are no devices. Initialize one if needed.
            if self.kernel.args.device == "Moshi":
                dev = "spool0 -r driver -n moshi output -n moshi\n"
            else:
                dev = "spool0 -r driver -n lhystudios output -n lhystudios\n"
            self(dev)

        def activate_device(device_name):
            def specific():
                self.kernel.activate_service_path("device", "legacy")
                self("device activate %s\n" % device_name)

            return specific

        for device in self.lookup_all("device"):
            device[0].label = device_as_name(device)
            device[0].activate = activate_device(device[0].name)

    def __str__(self):
        return 'LegacyDevice(<kernel>, "%s")' % (str(self.path))

    @property
    def current_y(self):
        driver = self.default_driver()
        return driver.current_y if driver is not None else None

    @property
    def current_x(self):
        driver = self.default_driver()
        return driver.current_x if driver is not None else None

    @property
    def settings(self):
        driver = self.default_driver()
        return driver.settings if driver is not None else None

    @property
    def state(self):
        driver = self.default_driver()
        return driver.state if driver is not None else None

    @property
    def spooler(self):
        return self.default_spooler()

    @property
    def viewbuffer(self):
        output = self.default_output()
        return output.viewbuffer() if output is not None else None

    @property
    def name(self):
        return device_as_name([self.spooler, self.default_driver(), self.default_output()])

    def set_active(self, active):
        self.active = active
        self.signal("active", self.active)

    def get_spooler(self, device_name):
        device = self.lookup("device", device_name)
        if device is None:
            return None
        return device[0]

    def get_or_make_spooler(self, device_name):
        device = self.lookup("device", device_name)
        if device is None:
            device = [None, None, None]
            self.register("device/%s" % device_name, device)
        if device[0] is None:
            device[0] = Spooler(self, device_name)
            self.root.register("spooler/%s" % device_name, device[0])
        return device[0]

    def default_spooler(self):
        return self.get_spooler(self.active)

    def get_driver(self, driver_name, **kwargs):
        try:
            return self.lookup("device", driver_name)[1]
        except (TypeError, IndexError):
            return None

    def get_or_make_driver(self, device_name, driver_type=None, **kwargs):
        device = self.lookup("device", device_name)
        if device is None:
            device = [None, None, None]
            self.register("device/%s" % device_name, device)
        if device[1] is not None and driver_type is None:
            return device[1]
        try:
            for driver_class, itype, sname in self.find("driver", driver_type):
                driver = driver_class(self, device_name, **kwargs)
                device[1] = driver
                return driver
        except (KeyError, IndexError):
            return None

    def default_driver(self):
        return self.get_driver(self.active)

    def device(self):
        v = self.lookup("device", self.active)
        if v is not None:
            return v
        return None, None, None

    def get_or_make_output(self, device_name, output_type=None, **kwargs):
        device = self.lookup("device", device_name)
        if device is None:
            device = [None, None, None]
            self.register("device/%s" % device_name, device)
        if device[2] is not None and output_type is None:
            return device[2]
        try:
            for output_class, itype, sname in self.find("output", output_type):
                output = output_class(self, device_name, **kwargs)
                device[2] = output
                return output
        except TypeError:
            return None

    def put_output(self, device_name, output):
        device = self.lookup("device", device_name)
        if device is None:
            device = [None, None, None]
            self.register("device/%s" % device_name, device)

        try:
            device[2] = output
        except (KeyError, IndexError):
            pass

    def default_output(self):
        return self.get_or_make_output(self.active)


def device_as_name(device):
    spooler_name = "None"
    try:
        spooler_name = device[0].name
    except AttributeError:
        pass
    driver_type = "None"
    try:
        driver_type = device[1].type
    except AttributeError:
        pass
    output_type = "None"
    try:
        output_type = device[2].type
    except AttributeError:
        pass
    return "(%s -> %s -> %s)" % (
        spooler_name,
        driver_type,
        output_type,
    )
