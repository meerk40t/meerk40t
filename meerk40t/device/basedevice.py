from meerk40t.kernel import CommandMatchRejected, Modifier

DRIVER_STATE_RAPID = 0
DRIVER_STATE_FINISH = 1
DRIVER_STATE_PROGRAM = 2
DRIVER_STATE_RASTER = 3
DRIVER_STATE_MODECHANGE = 4

PLOT_START = 2048
PLOT_FINISH = 256
PLOT_RAPID = 4
PLOT_JOG = 2
PLOT_SETTING = 128
PLOT_AXIS = 64
PLOT_DIRECTION = 32
PLOT_LEFT_UPPER = 512
PLOT_RIGHT_LOWER = 1024


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.add_modifier(Devices)


class Devices(Modifier):
    def __init__(self, kernel, *args, **kwargs):
        Modifier.__init__(self, kernel, "devices")

        index = 0
        for d in self.kernel.keylist(self.path):
            suffix = d.split("/")[-1]
            if not suffix.startswith("device_"):
                continue
            line = self.setting(str, suffix, None)
            if line is not None and len(line):
                self(line + "\n")
                self.setting(str, "device_%d" % index, None)
            index += 1
        self._devices = index
        kernel.root.setting(str, "active", "0")

        _ = kernel.translation
        def device():
            try:
                return self.registered["device/%s" % self.active]
            except (KeyError, AttributeError):
                return None, None, None

        @kernel.console_option(
            "out",
            "o",
            action="store_true",
            help=_("match on output rather than driver"),
        )
        @kernel.console_command(
            "dev",
            help=_("delegate commands to currently selected device by input/driver"),
            output_type="dev",
            hidden=True,
        )
        def dev(channel, _, remainder=None, out=False, **kwargs):
            try:
                spooler, input_driver, output = self.registered[
                    "device/%s" % self.active
                ]
            except (KeyError, ValueError):
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

        @kernel.console_command(".+", regex=True, hidden=True)
        def virtual_dev(command, remainder=None, **kwargs):
            try:
                spooler, input_driver, output = self.registered[
                    "device/%s" % self.active
                ]
            except (KeyError, ValueError, AttributeError):
                raise CommandMatchRejected(_("No device selected."))

            if input_driver is not None:
                try:
                    t = input_driver.type
                    match = "command/%s/%s$" % (str(t), command)
                    match = "".join([i for i in match if i not in "(){}[]"])
                    for command_name in self.match(match):
                        command_funct = self.registered[command_name]
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
                    for command_name in self.match(match):
                        command_funct = self.registered[command_name]
                        if command_funct is not None:
                            if remainder is not None:
                                self(".dev -o %s %s\n" % (command, remainder))
                            else:
                                self(".dev -o %s\n" % command)
                            return
                except AttributeError:
                    pass
            raise CommandMatchRejected(_("No matching command."))

        @kernel.console_argument(
            "index", type=int, help=_("Index of device being activated")
        )
        @kernel.console_command(
            "activate",
            help=_("delegate commands to currently selected device"),
            input_type="device",
            output_type="device",
        )
        def device(channel, _, index, **kwargs):
            spools = [str(i) for i in kernel.root.match("device", suffix=True)]
            self.active = spools[index]
            self.signal("active", index)
            channel(_("Activated device %s at index %d." % (self.active, index)))
            return "device", (None, str(index))

        @kernel.console_command(
            "device",
            help=_("device"),
            output_type="device",
        )
        def device(channel, _, remainder=None, **kwargs):
            device_context = kernel.get_context("devices")
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

        @kernel.console_command(
            "list",
            help=_("list devices"),
            input_type="device",
            output_type="device",
        )
        def list_devices(channel, _, data, **kwargs):
            device_context = kernel.get_context("devices")
            channel(_("----------"))
            channel(_("Devices:"))
            index = 0
            while hasattr(device_context, "device_%d" % index):
                line = getattr(device_context, "device_%d" % index)
                channel("%d: %s" % (index, line))
                index += 1
            channel("----------")
            return "device", data

        @kernel.console_argument("index", type=int, help=_("Index of device deleted"))
        @kernel.console_command(
            "delete",
            help=_("delete <index>"),
            input_type="device",
        )
        def delete(channel, _, index, **kwargs):
            spools = [str(i) for i in kernel.root.match("device", suffix=True)]
            device_name = spools[index]

            device_context = kernel.get_context("devices")
            try:
                setattr(device_context, "device_%s" % device_name, "")
                device = self.registered["device/%s" % device_name]
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
                self.registered["device/%s" % device_name] = [None, None, None]
            except (KeyError, ValueError):
                raise SyntaxError(_("Invalid device-string index."))
