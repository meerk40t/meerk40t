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

        for d in kernel.keylist(self.path, suffix=True):
            if not d.startswith("dev_"):
                continue
            line = self.setting(str, d, None)
            if line is not None:
                driver_class = kernel.registered["driver/%f" % line]
                driver = driver_class(self)
                self.add_aspect(driver)

        _ = kernel.translation

        @kernel.console_command(
            "device",
            regex=True,
            help=_("device"),
            output_type="device",
        )
        def device(command, channel, _, remainder=None, **kwargs):
            if len(command) > 6:
                device_name = command[6:]
            else:
                try:
                    device_name = self.active.name
                except AttributeError:
                    channel(_("Active device no valid."))
                    return

            device_context = self
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
