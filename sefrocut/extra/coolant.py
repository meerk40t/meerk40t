"""
This module provides interfaces to coolants (airassist or others).
External modules can register the existence of an airassist.
Devices can then claim ownership of such a registered device
and react on device specific coolant commands
"""


class Coolants:
    """
    Base class
    """

    def __init__(self, kernel):
        self.kernel = kernel
        self._coolants = []
        # {
        #     "id": cool_id,
        #     "label": label,
        #     "function": cool_function,
        #     "config": config_function,
        #     "devices": [],
        #     "constraints": constraints,
        # }

    def remove_coolant_method(self, cool_id):
        cool_id = cool_id.lower()
        if cool_id in ("popup", "gcode_m7", "gcode_m8"):
            # builtin...
            return 0
        to_be_deleted = []
        for idx, cool in enumerate(self._coolants):
            if cool_id == cool["id"]:
                to_be_deleted.insert(0, idx)
        for idx in to_be_deleted:
            self._coolants.pop(idx)
        return len(to_be_deleted)

    def register_coolant_method(
        self, cool_id, cool_function, config_function=None, label=None, constraints=None
    ):
        """
        Announces the availability of a new coolant method.
        Mainly used from plugins.
        Args:
            cool_id ([str]): unique identifier for the method. There are two predefined
                methods generated from within meerk40t:
                a) 'popup' which just popups an instruction message
                    to turn on / off the airassist
                b) 'grbl' which uses the internal M7 / M9 commands ofa grbl compatible
                    device. So it has a 'grbl' constraint (see below)
            cool_function ([function]): The routine to call when coolant needs
                to be activated / deactivated. This routine expects two parameters:
                    def coolant_method (device, flag)
                        device: device that uses the routine
                        flag: indicator to turn it on (True) or off (False)
            config_function ([function], optional): The routine to call, if you want
                to edit parameters for this method. It expects one
                Defaults to None, indicating it has no such function.
            label ([str], optional): A description of the method.
                Defaults to None which will use the cool_id as label
            constraints ([str], optional): [description].
                Defaults to None, so available to all devices.
        Returns:
            [type]: [description]
        """
        cool_id = cool_id.lower()

        for cool in self._coolants:
            # A coolant method with that id had already been registered
            # so we just update it. Honestly this should not happen.
            if cool_id == cool["id"]:
                cool["label"] = label
                cool["function"] = cool_function
                cool["config"] = config_function
                cool["constraints"] = constraints
                return True
        self._coolants.append(
            {
                "id": cool_id,
                "label": label,
                "function": cool_function,
                "config": config_function,
                "devices": [],
                "constraints": constraints,
                "current_state": [],
            }
        )
        return True

    def coolant_on(self, device):
        for cool in self._coolants:
            if device in cool["devices"]:
                idx = cool["devices"].index(device)
                if not cool["current_state"][idx]:
                    cool["current_state"][idx] = True
                    routine = cool["function"]
                    routine(device, True)
                    self.kernel.signal("coolant_set", device.label, True)
                return True
        return False

    def coolant_off(self, device):
        for cool in self._coolants:
            if device in cool["devices"]:
                idx = cool["devices"].index(device)
                if cool["current_state"][idx]:
                    cool["current_state"][idx] = False
                    routine = cool["function"]
                    routine(device, False)
                    self.kernel.signal("coolant_set", device.label, False)
                return True
        return False

    def coolant_toggle(self, device):
        for cool in self._coolants:
            if device in cool["devices"]:
                idx = cool["devices"].index(device)
                new_state = not cool["current_state"][idx]
                cool["current_state"][idx] = new_state
                routine = cool["function"]
                routine(device, new_state)
                self.kernel.signal("coolant_set", device.label, new_state)
                return True
        return False

    def coolant_state(self, device):
        for cool in self._coolants:
            if device in cool["devices"]:
                idx = cool["devices"].index(device)
                return cool["current_state"][idx]
        # Nothing found
        return False

    def coolant_on_by_id(self, identifier):
        # Caveat, this will be executed independently of devices registered!
        cool_id = identifier.lower()
        for cool in self._coolants:
            if cool_id == cool["id"]:
                routine = cool["function"]
                routine(None, True)
                return True
        return False

    def coolant_off_by_id(self, identifier):
        # Caveat, this will be executed independently of devices registered!
        cool_id = identifier.lower()
        for cool in self._coolants:
            if cool_id == cool["id"]:
                routine = cool["function"]
                routine(None, False)
                return True
        return False

    def registered_coolants(self):
        """
        Returns the dictionary of all registered coolants
        """
        return self._coolants

    def claim_coolant(self, device, coolant):
        found = None
        if coolant is None:
            coolant = ""
        devname = device.name.lower()
        # print (f"Claim: {device.label} ({devname}): {coolant}")
        for cool in self._coolants:
            relevant = True
            if cool["constraints"]:
                allowed = cool["constraints"].split(",")
                relevant = any(candidate.lower() in devname for candidate in allowed)
            if not relevant:
                # Skipped as not relevant...
                continue
            if cool["id"] == coolant.lower():
                found = cool["function"]
                if device not in cool["devices"]:
                    cool["devices"].append(device)
                    cool["current_state"].append(False)
            else:
                try:
                    idx = cool["devices"].index(device)
                    cool["devices"].pop(idx)
                    cool["current_state"].pop(idx)
                except ValueError:
                    # wasn't inside
                    pass

        return found

    def get_device_function(self, device, coolant=None):
        found = None
        for cool in self._coolants:
            if coolant is None:
                if device in cool["devices"]:
                    found = cool["function"]
                    break
            elif cool["id"] == coolant.lower():
                found = cool["function"]
                break

        return found

    def get_device_coolant(self, device, coolant=None):
        found = None
        for cool in self._coolants:
            if coolant is None:
                if device in cool["devices"]:
                    found = cool
                    break
            elif cool["id"] == coolant.lower():
                found = cool
                break

        return found

    def get_devices_using(self, coolant_id):
        dev_str = ""
        multiple = False
        for cool in self._coolants:
            if cool["id"] == coolant_id.lower():
                for idx, dev in enumerate(cool["devices"]):
                    if multiple:
                        dev_str += ", "
                    multiple = True
                    dev_str += (
                        f"{dev.label} [{'on' if cool['current_state'][idx] else 'off'}]"
                    )
                break

        return dev_str

    def coolant_choice_helper(self, device):
        """
        Sets the choices and display of the coolant values dynamically
        @param choice_dict:
        @return:
        """

        def update(choice_dict):
            _ = self.kernel.translation
            devname = device.name.lower()
            choices = []
            display = []
            choices.append("")
            display.append(_("Nothing"))
            for cool in self._coolants:
                relevant = True
                if cool["constraints"]:
                    relevant = False
                    allowed = cool["constraints"].split(",")
                    for candidate in allowed:
                        if candidate.lower() in devname:
                            relevant = True
                            break
                if not relevant:
                    continue
                choices.append(cool["id"])
                if cool["label"]:
                    display.append(cool["label"])
                else:
                    display.append(cool["id"])
            choice_dict["choices"] = choices
            choice_dict["display"] = display

        return update


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation
        context = kernel.root
        context.coolant = Coolants(kernel)

        def base_coolant_popup(context, mode):
            if hasattr(context, "label"):
                lasername = context.label
            else:
                lasername = "your laser"
            if mode:
                msg = _("Please switch the airassist for {laser} on").format(
                    laser=lasername
                )
            else:
                msg = _("Please switch the airassist for {laser} off").format(
                    laser=lasername
                )
            context.kernel.yesno(
                msg, caption=_("Air-Assist"), option_yes=_("OK"), option_no=_("OK")
            )

        def base_coolant_grbl_m7(context, mode):
            if mode:
                context("gcode M7\n")
            else:
                context("gcode M9\n")

        def base_coolant_grbl_m8(context, mode):
            if mode:
                context("gcode M8\n")
            else:
                context("gcode M9\n")

        context.coolant.register_coolant_method(
            "popup", base_coolant_popup, config_function=None, label=_("Warnmessage")
        )
        context.coolant.register_coolant_method(
            "gcode_m7",
            base_coolant_grbl_m7,
            config_function=None,
            label=_("GCode M7/M9"),
            constraints="grbl",
        )
        context.coolant.register_coolant_method(
            "gcode_m8",
            base_coolant_grbl_m8,
            config_function=None,
            label=_("GCode M8/M9"),
            constraints="grbl",
        )

        @context.console_command(
            ("coolants", "vents"), help=_("displays registered coolant methods")
        )
        def display_coolant(command, channel, _, **kwargs):
            # elements = context.elements
            coolant = kernel.root.coolant
            cool = coolant.registered_coolants()
            if len(cool):
                channel(_("Registered coolant-interfaces:"))
                for cool_instance in cool:
                    c_name = cool_instance["id"]
                    c_label = cool_instance["label"]
                    claimed = coolant.get_devices_using(c_name)
                    if c_label:
                        c_name += " - " + c_label
                    if claimed == "":
                        claimed = _("Not used")

                    channel(_("{name}: {devices}").format(name=c_name, devices=claimed))

            else:
                channel(_("There are no coolant-interfaces known to MeerK40t"))

        @context.console_command(
            ("coolant_on", "vent_on"), help=_("Turns on the coolant for the active device")
        )
        def turn_coolant_on(command, channel, _, **kwargs):
            try:
                device = context.device
            except AttributeError:
                channel("No active device found")
                return

            coolant = kernel.root.coolant
            if coolant.coolant_on(device):
                channel("Coolant turned on")
            else:
                channel("Active device does not support coolant")

        @context.console_command(
            ("coolant_off", "vent_off"), help=_("Turns off the coolant for the active device")
        )
        def turn_coolant_off(command, channel, _, **kwargs):
            try:
                device = context.device
            except AttributeError:
                channel("No active device found")
                return

            coolant = kernel.root.coolant
            if coolant.coolant_off(device):
                channel("Coolant turned off")
            else:
                channel("Active device does not support coolant")

        @context.console_argument("id", type=str)
        @context.console_command(
            ("coolant_on_by_id", "vent_on_by_id"), help=_("Turns the coolant on using the given method")
        )
        def turn_coolant_on_by_id(command, channel, _, id=None, **kwargs):
            if id is None:
                channel("You need to provide an identifier")
                return
            coolant = kernel.root.coolant
            if coolant.coolant_on_by_id(id):
                channel(f"Coolant {id} turned on")
            else:
                channel(f"Method {id} could not be found")
        
        @context.console_argument("id", type=str)
        @context.console_command(
            ("coolant_off_by_id", "vent_off_by_id"), help=_("Turns the coolant off using the given method")
        )
        def turn_coolant_off_by_id(command, channel, _, id=None, **kwargs):
            if id is None:
                channel("You need to provide an identifier")
                return
            coolant = kernel.root.coolant
            if coolant.coolant_off_by_id(id):
                channel(f"Coolant {id} turned off")
            else:
                channel(f"Method {id} could not be found")
