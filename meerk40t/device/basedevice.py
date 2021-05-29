from meerk40t.kernel import CommandMatchRejected

DRIVER_STATE_RAPID = 0
DRIVER_STATE_FINISH = 1
DRIVER_STATE_PROGRAM = 2
DRIVER_STATE_RASTER = 3
DRIVER_STATE_MODECHANGE = 4

PLOT_FINISH = 256
PLOT_RAPID = 4
PLOT_JOG = 2
PLOT_SETTING = 128
PLOT_AXIS = 64
PLOT_DIRECTION = 32


def plugin(kernel, lifecycle=None):
    if lifecycle == "boot":
        device_context = kernel.get_context("devices")
        index = 0
        for d in device_context._kernel.keylist(device_context._path):
            suffix = d.split("/")[-1]
            if not suffix.startswith("device_"):
                continue
            line = device_context.setting(str, suffix, None)
            if line is not None and len(line):
                device_context(line + "\n")
                device_context.setting(str, "device_%d" % index, None)
            index += 1
        device_context._devices = index
        kernel.root.setting(str, "active", "0")
    elif lifecycle == "register":
        root = kernel.root

        def device():
            try:
                return root.registered["device/%s" % root.active]
            except (KeyError, AttributeError):
                return None, None, None

        root.device = device

        @kernel.console_option(
            "out", "o", action="store_true", help="match on output rather than driver"
        )
        @kernel.console_command(
            "dev",
            help="delegate commands to currently selected device by input/driver",
            output_type="dev",
            hidden=True,
        )
        def dev(channel, _, remainder=None, out=False, **kwargs):
            try:
                spooler, input_driver, output = root.registered[
                    "device/%s" % root.active
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
        def virtual_dev(command, channel, _, remainder=None, **kwargs):
            try:
                spooler, input_driver, output = root.registered[
                    "device/%s" % root.active
                ]
            except (KeyError, ValueError, AttributeError):
                raise CommandMatchRejected("No device selected.")

            if input_driver is not None:
                try:
                    t = input_driver.type
                    match = "command/%s/%s" % (str(t), command)
                    for command_name in root.match(match):
                        command_funct = root.registered[command_name]
                        if command_funct is not None:
                            if remainder is not None:
                                root(".dev %s %s\n" % (command, remainder))
                            else:
                                root(".dev %s\n" % command)
                            return
                except AttributeError:
                    pass
            if output is not None:
                try:
                    t = output.type + "out"
                    match = "command/%s/%s" % (str(t), command)
                    for command_name in root.match(match):
                        command_funct = root.registered[command_name]
                        if command_funct is not None:
                            if remainder is not None:
                                root(".dev -o %s %s\n" % (command, remainder))
                            else:
                                root(".dev -o %s\n" % command)
                            return
                except AttributeError:
                    pass
            raise CommandMatchRejected("No matching command.")

        @kernel.console_argument(
            "index", type=int, help="Index of device being activated"
        )
        @kernel.console_command(
            "activate",
            help="delegate commands to currently selected device",
            input_type="device",
            output_type="device",
        )
        def device(channel, _, index, **kwargs):
            root.active = str(index)
            root.signal("active", index)
            return "device", (None, str(index))

        @kernel.console_command(
            "device",
            help="device",
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
            return "device", (None, root.active)

        @kernel.console_command(
            "list",
            help="list devices",
            input_type="device",
            output_type="device",
        )
        def list(channel, _, data, **kwargs):
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

        @kernel.console_argument("index", type=int, help="Index of device deleted")
        @kernel.console_command(
            "delete",
            help="delete <index>",
            input_type="device",
        )
        def delete(index, **kwargs):
            device_context = kernel.get_context("devices")
            try:
                setattr(device_context, "device_%d" % index, "")
                device = root.registered["device/%d" % index]
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
                root.registered["device/%d" % index] = [None, None, None]
            except (KeyError, ValueError):
                raise SyntaxError("Invalid device-string index.")
