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
        while hasattr(device_context, "device-%d" % index):
            line = getattr(device_context, "device-%d" % index)
            device_context(line + "\n")
            index += 1
        device_context._devices = index

    elif lifecycle == "register":

        @kernel.console_command(
            "device",
            help="device",
            output_type="device",
        )
        def device(channel, _, remainder=None, **kwargs):
            data = kernel.get_context("devices")
            if remainder is None:
                channel(_("----------"))
                channel(_("Devices:"))
                index = 0
                while hasattr(data, "device-%d" % index):
                    line = getattr(data, "device-%d" % index)
                    channel("%d: %s" % (index, line))
                    index += 1
                channel("----------")
            return "device", data

        @kernel.console_command(
            "list",
            help="list devices",
            input_type="device",
            output_type="device",
        )
        def list(channel, _, data, **kwargs):
            channel(_("----------"))
            channel(_("Devices:"))
            index = 0
            while hasattr(data, "device-%d" % index):
                line = getattr(data, "device-%d" % index)
                channel("%d: %s" % (index, line))
                index += 1
            channel("----------")
            return "device", data

        @kernel.console_command(
            "add",
            help="add <device-string>",
            input_type="device",
        )
        def add(channel, _, data, remainder, **kwargs):
            if not remainder.startswith("spool") and not remainder.startswith("source"):
                raise SyntaxError("Device string must start with 'spool' or 'source'")
            index = 0
            while hasattr(data, "device-%d" % index):
                index += 1
            setattr(data, "device-%d" % index, remainder)

        @kernel.console_command(
            "delete",
            help="delete <index>",
            input_type="device",
        )
        def delete(channel, _, data, remainder, **kwargs):
            try:
                delattr(data, "device-%d" % index)
            except KeyError:
                raise SyntaxError("Invalid device-string index.")
