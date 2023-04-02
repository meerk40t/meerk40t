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
    if lifecycle == "plugins":
        from .ch341 import ch341

        return [ch341.plugin]

    if lifecycle == "boot":
        last_device = kernel.read_persistent(str, "/", "activated_device", None)
        if last_device:
            try:
                kernel.activate_service_path("device", last_device)
            except ValueError:
                pass

        if not hasattr(kernel, "device"):
            preferred_device = kernel.root.setting(
                str, "preferred_device", "lhystudios"
            )
            # Nothing has yet established a device. Boot this device.
            kernel.root(f"service device start {preferred_device}\n")

        _ = kernel.translation

        @kernel.console_command(
            "device",
            help=_("show device providers"),
            input_type=None,
            output_type="device",
        )
        def device_info(channel, _, remainder=None, **kwargs):
            """
            Display device info.
            """
            info_entries = list(kernel.find("dev_info"))
            if not remainder:
                channel(_("----------"))
                channel(_("Device Entries:"))
                for i, reg_entry in enumerate(info_entries):
                    device_info, name, sname = reg_entry
                    parts = [f"[bold]{sname}[normal]"]
                    if "friendly_name" in device_info:
                        parts.append(f"[blue]{device_info['friendly_name']}[normal]")
                    if "provider" in device_info:
                        parts.append(f"[red]{device_info['provider']}[normal]")
                    channel(" ".join(parts), ansi=True)
                    if "extended_info" in device_info:
                        channel(device_info["extended_info"])
                channel(_("----------"))
            return "device", info_entries

        @kernel.console_option(
            "label",
            "l",
            help="optional label for the service to start",
            type=str,
        )
        @kernel.console_argument("name", type=str)
        @kernel.console_command(
            "add",
            help=_("start a particular device entry"),
            input_type="device",
            all_arguments_required=True,
        )
        def device_start(channel, _, name, data, label=None, **kwargs):
            """
            Display device info.
            """
            from ..kernel.exceptions import CommandSyntaxError

            try:
                entry = kernel.lookup("dev_info", name)
                if entry is None:
                    raise CommandSyntaxError(_("Invalid Device Info"))
                provider_path = entry.get("provider")
                provider = kernel.lookup(provider_path)
                if provider is None:
                    raise CommandSyntaxError("Bad provider.")
                choices = entry.get("choices")
                if label:
                    # There is a label, override the otherwise preferred label.
                    choices = dict(choices)  # create copy rather than modify original
                    choices["label"] = label
                path = list(provider_path.split("/"))[-1]
                service_path = path
                i = 1
                while service_path in kernel.contexts:
                    service_path = path + str(i)
                    i += 1

                service = provider(kernel, service_path, choices=choices)
                kernel.add_service("device", service, provider_path)
                kernel.activate("device", service, assigned=True)
            except IndexError:
                raise CommandSyntaxError("Index is not valid.")

    if lifecycle == "preshutdown":
        setattr(kernel.root, "activated_device", kernel.device.path)
