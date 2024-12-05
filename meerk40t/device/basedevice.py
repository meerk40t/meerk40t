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
            "viewport_update",
            hidden=True,
            help=_("Update Coordinate System"),
        )
        def viewport_update(**kwargs):
            try:
                kernel.device.realize()
            except AttributeError:
                pass

        def display_devices(channel):
            channel(_("Defined Devices:"))
            channel(_("----------------"))
            channel("#\tLabel\tType\tFamily\tStatus")
            dev_infos = list(kernel.find("dev_info"))
            dev_infos.sort(key=lambda e: e[0].get("priority", 0), reverse=True)
            for i, device in enumerate(kernel.services("device")):
                suffix = "    "
                if device.path == kernel.device.path:
                    suffix = " (*)"
                label = device.label
                msg = f"{i}{suffix}:\t{label}"
                type_info = getattr(device, "name", device.path)
                family_default = ""
                for obj, name, sname in dev_infos:
                    if device.registered_path == obj.get("provider", ""):
                        if "choices" in obj:
                            for prop in obj["choices"]:
                                if (
                                    "attr" in prop
                                    and "default" in prop
                                    and prop["attr"] == "source"
                                ):
                                    family_default = prop["default"]
                                    break
                    if family_default:
                        break

                family_info = device.setting(str, "source", family_default)
                if family_info:
                    family_info = family_info.capitalize()
                active_status = ""
                try:
                    if hasattr(device, "laser_status"):
                        active_status = device.laser_status
                except AttributeError:
                    active_status = "??"

                try:
                    if hasattr(device, "driver") and hasattr(device.driver, "paused"):
                        if device.driver.paused:
                            active_status = "paused"
                except AttributeError:
                    pass
                msg += f"\t{type_info}\t{family_info}\t{active_status}"
                channel(msg)


        @kernel.console_command(
            "devinfo",
            help=_("Show current device info."),
            input_type=None,
            output_type=None,
        )
        def devinfo(channel, _, remainder=None, **kwargs):
            """
            Display device status info.
            """
            x, y = kernel.device.current
            nx, ny = kernel.device.native
            channel(_(f"{x},{y};{nx},{ny};"))

        @kernel.console_command(
            "device",
            help=_("show device providers"),
            input_type=None,
            output_type="device",
        )
        def device_info_cmd(channel, _, remainder=None, **kwargs):
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
            help=_("Add a new device and start it"),
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

        @kernel.console_argument("name", type=str)
        @kernel.console_command(
            "activate",
            help=_("Activate a particular device entry"),
            input_type="device",
        )
        def device_activate(channel, _, data, name=None, **kwargs):
            """
            Activate a given device.
            """
            from ..kernel.exceptions import CommandSyntaxError
            available_devices = kernel.services("device")
            if not name:
                display_devices(channel)
                return
            found = False
            index = -1
            try:
                index = int(name)
            except ValueError:
                index = -1
            for i, spool in enumerate(available_devices):
                if spool.label == name or i == index:
                    kernel.activate_service_path("device", spool.path)
                    found = True
                    channel(f"Device '{spool.label}' is now the active device")
                    break
            if not found:
                channel(f"Did not find a device with that name '{name}'")

        @kernel.console_argument("name", type=str)
        @kernel.console_argument("label", type=str)
        @kernel.console_command(
            "duplicate",
            help=_("Duplicate a particular device entry"),
            input_type="device",
        )
        def device_duplicate(channel, _, data, name=None, label=None, **kwargs):
            """
            Duplicate a given device.
            """
            from ..kernel.exceptions import CommandSyntaxError
            available_devices = kernel.services("device")
            if not name:
                display_devices(channel)
                return
            found = False
            index = -1
            try:
                index = int(name)
            except ValueError:
                index = -1
            given_names = list((d.label for d in available_devices))
            for i, device in enumerate(available_devices):
                if device.label == name or i == index:
                    if label is None:
                        baselabel = device.label
                        ipos = baselabel.find(" #")
                        if ipos > 0: # after first character
                            baselabel = baselabel[:ipos]
                        idx = 1
                        while True:
                            label = f"{baselabel} #{idx}"
                            if label not in given_names:
                                break
                            idx += 1
                    found = True
                    provider_path = device.registered_path
                    provider = kernel.lookup(provider_path)
                    if provider is None:
                        raise CommandSyntaxError("Bad provider.")
                    path = list(provider_path.split("/"))[-1]
                    service_path = path
                    i = 1
                    while service_path in kernel.contexts:
                        service_path = path + str(i)
                        i += 1
                        choices = [
                            {
                                "attr": "label",
                                "default": label,
                            },
                        ]

                    service = provider(kernel, service_path, choices=choices)
                    # Let's copy properties across
                    for d in device.__dict__:
                        if d == "label" or d.startswith("_"):
                            continue
                        try:
                            value = getattr(device, d)
                            if isinstance(value, (str, int, float, bool, list, tuple)):
                                # print (f"Copying over value {d}: {value}")
                                setattr(service, d, value)
                        except (AttributeError, ValueError) as e:
                            # print (f"Could not copy {d}: {e}")
                            pass

                    kernel.add_service("device", service, provider_path)

                    channel(f"Device '{device.label}' has been copied to {label}")
                    break
            if not found:
                channel(f"Did not find a device with that name '{name}'")

        @kernel.console_argument("name", type=str)
        @kernel.console_command(
            "delete",
            help=_("Delete a particular device entry"),
            input_type="device",
        )
        def device_delete(channel, _, data, name=None, label=None, **kwargs):
            """
            Delete a given device.
            """
            from ..kernel.exceptions import CommandSyntaxError
            available_devices = kernel.services("device")
            if not name:
                display_devices(channel)
                return
            found = False
            index = -1
            try:
                index = int(name)
            except ValueError:
                index = -1
            for i, device in enumerate(available_devices):
                if device.label == name or i == index:
                    if device.path == kernel.device.path:
                        channel("You can't delete the active device")
                        return
                    found = True
                    device.destroy()
                    channel(f"Device '{device.label}' has been deleted")
                    kernel.root.signal("device;renamed")
                    break
            if not found:
                channel(f"Did not find a device with that name '{name}'")


    if lifecycle == "preshutdown":
        setattr(kernel.root, "activated_device", kernel.device.path)
