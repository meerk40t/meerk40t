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
        #     "id": "coolant_id",
        #     "function": coolant_function,
        #     "devices": [],
        # }

    def register_coolant_method(self, cool_id, cool_function, config_function=None, label=None):
        cool_id = cool_id.lower()
        if cool_id in (v["id"] for v in self._coolants):
            print (f"A coolant method with Id '{cool_id}' has already been registered")
            return False
        self._coolants.append(
            {
                "id": cool_id,
                "function": cool_function,
                "config": config_function,
                "devices": [],
                "label": label,
            }
        )
        return True

    def registered_coolants(self):
        """
        Returns the dictionary of all registered coolants
        """
        return self._coolants

    def claim_coolant(self, device, coolant):
        found = None
        if coolant is None:
            coolant = ""
        # print (f"Claim: {device.label}: {coolant}")
        for cool in self._coolants:
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

    def get_device_coolant(self, device, coolant):
        found = None
        for cool in self._coolants:
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

    def coolant_choice_helper(self, choice_dict):
        """
        Sets the choices and display of the coolant values dynamically
        @param choice_dict:
        @return:
        """
        choices = list()
        display = list()
        choices.append("")
        display.append("Nothing")
        for cool in self._coolants:
            choices.append(cool["id"])
            if cool["label"]:
                display.append(cool["label"])
            else:
                display.append(cool["id"])
        choice_dict["choices"] = choices
        choice_dict["display"] = display

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


        context.coolant.register_coolant_method("popup", base_coolant_popup, config_function=None, label=_("Warnmessage"))

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
            # For testpurposes, bind the current device to the basic logic
            coolant.claim_coolant(device, "popup")

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
            coolant.claim_coolant(device, "popup")

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

