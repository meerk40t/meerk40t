"""
This module provides interfaces to coolants (airassist or others).
External modules can register the existence of an airassist.
Devices can then claim ownership of such a registered device
and react on device specific coolant commands
"""
class Coolants():
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

    def register_coolant_method(self, cool_id, cool_function, config_function=None, label=None, constraints=None):
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
            }
        )
        return True

    def coolant_on(self, device):
        for cool in self._coolants:
            if device in cool["devices"]:
                routine = cool["function"]
                routine(device, True)
                break

    def coolant_off(self, device):
        for cool in self._coolants:
            if device in cool["devices"]:
                routine = cool["function"]
                routine(device, False)
                break

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
                relevant = False
                allowed = cool["constraints"].split(",")
                for candidate in allowed:
                    if candidate.lower() in devname:
                        relevant = True
                        break
            if not relevant:
                # Skipped as not relevant...
                continue
            if cool["id"] == coolant.lower():
                found = cool["function"]
                if device not in cool["devices"]:
                    cool["devices"].append(device)
            else:
                try:
                    cool["devices"].remove(device)
                except ValueError:
                    # wasn't inside
                    pass

        return found

    def get_device_coolant(self, device, coolant=None):
        found = None
        for cool in self._coolants:
            if coolant is None:
                if device in cool["devices"]:
                    found = cool["function"]
                    break
            else:
                if cool["id"] == coolant.lower():
                    found = cool["function"]
                    break

        return found

    def get_devices_using(self, coolant_id):
        dev_str = ""
        multiple = False
        for cool in self._coolants:
            if cool["id"] == coolant_id.lower():
                for dev in cool["devices"]:
                    if multiple:
                        dev_str += ", "
                    multiple = True
                    dev_str += dev.label
                break

        return dev_str

    def coolant_choice_helper(self, device):
        """
        Sets the choices and display of the coolant values dynamically
        @param choice_dict:
        @return:
        """
        def update(choice_dict):
            devname = device.name.lower()
            choices = list()
            display = list()
            choices.append("")
            display.append("Nothing")
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
                msg = _("Please switch the airassist for {laser} on").format(laser=lasername)
            else:
                msg = _("Please switch the airassist for {laser} off").format(laser=lasername)
            context.kernel.yesno(msg, caption=_("Air-Assist"))

        def base_coolant_grbl(context, mode):
            if mode:
                context("gcode M7\n")
            else:
                context("gcode M9\n")

        context.coolant.register_coolant_method("popup", base_coolant_popup, config_function=None, label=_("Warnmessage"))
        context.coolant.register_coolant_method("gcode", base_coolant_grbl, config_function=None, label=_("GCode M7/M9"), constraints="grbl")

        @context.console_command("coolants", help=_("displays registered coolant methods"))
        def display_coolant(command, channel, _, **kwargs):
            # elements = context.elements
            coolant = kernel.root.coolant
            cool = coolant.registered_coolants()
            if len(cool):
                channel (_("Registered coolant-interfaces:"))
                for cool_instance in cool:
                    c_name = cool_instance["id"]
                    c_label = cool_instance["label"]
                    claimed = coolant.get_devices_using(c_name)
                    if c_label:
                        c_name += " - " + c_label
                    if claimed == "":
                        claimed = _("Not used")

                    channel (_("{name}: {devices}").format(name=c_name, devices=claimed))

            else:
                channel (_("There are no coolant-interfaces known to MeerK40t"))

        @context.console_command("coolant_on", help=_("Turns the coolant for the active device off"))
        def turn_coolant_on(command, channel, _, **kwargs):
            try:
                device = context.device
            except AttributeError:
                channel("No active device found")
                return

            coolant = kernel.root.coolant

            cool = coolant.registered_coolants()
            found = False
            for cool_instance in cool:
                if device in cool_instance["devices"]:
                    try:
                        cool_instance["function"](device, True)
                        found = True
                    except AttributeError:
                        pass
            if found:
                channel(_(f"Coolant activated for device {device.label}"))
            else:
                channel (_("No coolant method found."))

        @context.console_command("coolant_off", help=_("Turns the coolant for the active device off"))
        def turn_coolant_on(command, channel, _, **kwargs):
            try:
                device = context.device
            except AttributeError:
                channel("No active device found")
                return

            coolant = kernel.root.coolant

            cool = coolant.registered_coolants()
            found = False
            for cool_instance in cool:
                if device in cool_instance["devices"]:
                    try:
                        cool_instance["function"](device, False)
                        found = True
                    except AttributeError:
                        pass
            if found:
                channel(f"Coolant deactivated for device {device.label}")
            else:
                channel ("No method found.")

