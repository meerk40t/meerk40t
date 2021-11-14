from meerk40t.core.spoolers import Spooler
from meerk40t.kernel import Service
from meerk40t.kernel import CommandMatchRejected


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.add_service("device", LegacyDevice(kernel))
    elif lifecycle == "boot":
        context = kernel.get_context("legacy")
        _ = context._
        choices = [
            {
                "attr": "bed_width",
                "object": context,
                "default": 310,
                "type": int,
                "label": _("Width"),
                "tip": _("Width of the laser bed."),
            },
            {
                "attr": "bed_height",
                "object": context,
                "default": 210,
                "type": int,
                "label": _("Height"),
                "tip": _("Height of the laser bed."),
            },
            {
                "attr": "scale_x",
                "object": context,
                "default": 1.000,
                "type": float,
                "label": _("X Scale Factor"),
                "tip": _(
                    "Scale factor for the X-axis. This defines the ratio of mils to steps. This is usually at 1:1 steps/mils but due to functional issues it can deviate and needs to be accounted for"
                ),
            },
            {
                "attr": "scale_y",
                "object": context,
                "default": 1.000,
                "type": float,
                "label": _("Y Scale Factor"),
                "tip": _(
                    "Scale factor for the Y-axis. This defines the ratio of mils to steps. This is usually at 1:1 steps/mils but due to functional issues it can deviate and needs to be accounted for"
                ),
            },
        ]
        kernel.register_choices("bed_dim", choices)


class LegacyDevice(Service):
    """
    Legacy Device governs the 0.7.x style device connections between spoolers, controllers, and output.

    Legacy Devices read the values in `devices` and boots the needed devices up, by running the lines found in
    device_*. These refer to local commands registered in the service.
    """

    def __init__(self, kernel, *args, **kwargs):
        Service.__init__(self, kernel, "legacy")

    def attach(self, *args, **kwargs):
        # self.register("plan/interrupt", interrupt)
        _ = self.kernel.translation
        self.setting(float, "current_x", 0.0)
        self.setting(float, "current_y", 0.0)
        self.setting(str, "active", "0")

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
                    self.active = device_name
                else:
                    device_name = self.active
            else:
                spooler, device_name = data

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

            return "spooler", (spooler, device_name)

        @self.console_command(
            "list",
            help=_("spool<?> list"),
            input_type="spooler",
            output_type="spooler",
        )
        def spooler_list(command, channel, _, data_type=None, data=None, **kwgs):
            spooler, device_name = data
            channel(_("----------"))
            channel(_("Spoolers:"))
            for d, d_name in enumerate(self.match("device", suffix=True)):
                channel("%d: %s" % (d, d_name))
            channel(_("----------"))
            channel(_("Spooler %s:" % device_name))
            for s, op_name in enumerate(spooler.queue):
                channel("%d: %s" % (s, op_name))
            channel(_("----------"))
            return data_type, data

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
            self.active = spools[index]
            self.signal("active", index)
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
            except (KeyError, ValueError):
                raise SyntaxError(_("Invalid device-string index."))

        ########################
        # LEGACY DEVICE BOOT SEQUENCE
        ########################

        device_context = self.get_context("devices")
        index = 0
        for d in device_context.kernel.keylist(device_context.path):
            suffix = d.split("/")[-1]
            if not suffix.startswith("device_"):
                continue
            line = device_context.setting(str, suffix, None)
            if line is not None and len(line):
                device_context(line + "\n")
                device_context.setting(str, "device_%d" % index, None)
            index += 1
        device_context._devices = index

        for i in range(5):
            self.get_or_make_spooler(str(i))

    def get_or_make_spooler(self, device_name):
        device = self.lookup("device", device_name)
        if device is None:
            device = [None, None, None]
            self.register("device/%s" % device_name, device)
        if device[0] is None:
            device[0] = Spooler(self, device_name)
        return device[0]

    def default_spooler(self):
        return self.get_or_make_spooler(self.active)

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
        if v is None:
            return None, None, None
        return v
