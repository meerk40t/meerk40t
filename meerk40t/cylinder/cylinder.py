from meerk40t.kernel import lookup_listener, signal_listener


def plugin(service, lifecycle=None):
    if lifecycle == "plugins":
        from .gui import gui

        return [gui.plugin]
    if lifecycle == "service":
        # Responding to "service" makes this a service plugin for the specific services created via the provider
        return ("provider/device/balor",)
    elif lifecycle == "added":
        service.add_service_delegate(CylinderCorrection(service, 0))


class CylinderCorrection:
    """
    CylinderCorrection Service provides cylinder information about the selected cylinder you intend to use.
    """

    def __init__(self, service, index=0, *args, **kwargs):
        self.index = index
        self.service = service
        self.service.cylinder = self

        _ = service._
        from meerk40t.core.units import Length

        choices = [
            {
                "attr": "cylinder_active",
                "object": service,
                "default": False,
                "type": bool,
                "label": _("Cylinder-Correction-Mode active"),
                "tip": _("Is the cylinder correction mode active for this device"),
            },
            {
                "attr": "cylinder_mirror_distance",
                "object": service,
                "default": "100mm",
                "type": Length,
                "label": _("Mirror Distance"),
                "tip": _("Distance from cylinder to mirror"),
                "conditional": (service, "cylinder_active"),
                "subsection": _("Distances"),
            },
            {
                "attr": "cylinder_x_axis",
                "object": service,
                "default": False,
                "type": bool,
                "label": _("Axis X"),
                "tip": _("Cylinder along X-Axis"),
                "conditional": (service, "cylinder_active"),
                "subsection": _("X Axis"),
            },
            {
                "attr": "cylinder_x_diameter",
                "object": service,
                "default": "50mm",
                "type": Length,
                "label": _("Cylinder Diameter"),
                "tip": _("Diameter of the object being engraved"),
                "conditional": (service, "cylinder_x_axis"),
                "subsection": _("X Axis"),
            },
            {
                "attr": "cylinder_x_concave",
                "object": service,
                "default": False,
                "type": bool,
                "label": _("Cylinder is Concave"),
                "tip": _("Cylinder is concave rather than convex"),
                # "conditional": (service, "cylinder_x_axis"),
                "subsection": _("X Axis"),
                "hidden": True,
                "enabled": False,
            },
            {
                "attr": "cylinder_y_axis",
                "object": service,
                "default": False,
                "type": bool,
                "label": _("Axis Y"),
                "tip": _("Cylinder along Y-Axis"),
                "conditional": (service, "cylinder_active"),
                "subsection": _("Y Axis"),
            },
            {
                "attr": "cylinder_y_diameter",
                "object": service,
                "default": "50mm",
                "type": Length,
                "label": _("Cylinder Diameter"),
                "tip": _("Diameter of the object being engraved"),
                "conditional": (service, "cylinder_y_axis"),
                "subsection": _("Y Axis"),
            },
            {
                "attr": "cylinder_y_concave",
                "object": service,
                "default": False,
                "type": bool,
                "label": _("Cylinder is Concave"),
                "tip": _("Cylinder is concave rather than convex"),
                # "conditional": (service, "cylinder_y_axis"),
                "subsection": _("Y Axis"),
                "hidden": True,
                "enabled": False,
            },
        ]
        service.register_choices("cylinder", choices)
        @service.console_command(
            "cylinder",
            help="Cylinder base command",
            output_type="cylinder",
        )
        def cylinder(command, channel, _, data=None, remainder=None, **kwargs):
            if remainder is None:
                provide_status(channel)

            return "cylinder", None

        def provide_status(channel):
            if service.cylinder_active:
                channel(f"Distance from mirror to object: {Length(service.cylinder_mirror_distance).length_mm}")
                channel(
                    f"Cylinder Mode X: {'on' if service.cylinder_x_axis else 'off'}, object diameter: {Length(service.cylinder_x_diameter).length_mm}, concave: {'on' if service.cylinder_x_concave else 'off'}."
                )
                channel(
                    f"Cylinder Mode Y: {'on' if service.cylinder_y_axis else 'off'}, object diameter: {Length(service.cylinder_y_diameter).length_mm}, concave: {'on' if service.cylinder_y_concave else 'off'}."
                )
                channel(
                    "Notabene: Updates occur only when toggled off and on. Concave is unused."
                )
            else:
                channel("Cylinder mode is not active, use 'cylinder on' or 'cylinder axis X <object diameter>' to activate it")

        def validate_cylinder_signal():
            device = service.device
            device.driver.cylinder_validate()
            service.signal("cylinder_update")

        @service.console_command("off", help="Turn cylinder correction off", input_type="cylinder", output_type="cylinder")
        def cylinder_off(command, channel, _, data=None, **kwargs):
            state = service.cylinder_active
            service.cylinder_active = False
            validate_cylinder_signal()
            provide_status(channel)
            return "cylinder", None

        @service.console_command("on", help="Turn cylinder correction on", input_type="cylinder", output_type="cylinder")
        def cylinder_on(command, channel, _, data=None, **kwargs):
            state = service.cylinder_active
            service.cylinder_active = True
            validate_cylinder_signal()
            provide_status(channel)
            return "cylinder", None

        @service.console_argument("dist", type=Length, help="Distance between mirror and cylinder")
        @service.console_command("distance", help="Sets mirror cylinder distance", input_type="cylinder", output_type="cylinder")
        def cylinder_distance(command, channel, _, data=None, dist=None, **kwargs):
            if dist is None:
                channel ("You did not provide a valid distance")
                return
            try:
                c_dist = float(Length(dist))
            except ValueError:
                channel ("You did not provide a valid distance")
                return
            service.cylinder_mirror_distance = c_dist
            validate_cylinder_signal()
            provide_status(channel)
            return "cylinder", None

        @service.console_argument("axis", type=str, help="Axis X or Y")
        @service.console_argument("diam", type=Length, help="Diameter of to be engraved object")
        @service.console_command("axis", help="Sets the to be used axis (X or Y)", input_type="cylinder", output_type="cylinder")
        def cylinder_axis_parameter(command, channel, _, data=None, axis=None, diam=None, **kwargs):
            if axis is None:
                channel("You need to provide X or Y as parameter to choose which axis to use")
            if diam is None:
                channel ("You did not provide a valid diameter")
                return
            use_x = axis.lower() == "x"
            try:
                c_dist = float(Length(diam))
            except ValueError:
                channel ("You did not provide a valid diameter")
                return
            service.cylinder_x_axis = use_x
            service.cylinder_y_axis = not use_x
            if use_x:
                service.cylinder_x_diameter = c_dist
            else:
                service.cylinder_y_diameter = c_dist
            service.cylinder_active = True
            validate_cylinder_signal()
            provide_status(channel)
            return "cylinder", None


    @lookup_listener("service/device/active")
    @signal_listener("cylinder_active")
    @signal_listener("cylinder_x_axis")
    @signal_listener("cylinder_x_diameter")
    @signal_listener("cylinder_x_concave")
    @signal_listener("cylinder_y_axis")
    @signal_listener("cylinder_y_diameter")
    @signal_listener("cylinder_y_concave")
    @signal_listener("cylinder_mirror_distance")
    def cylinder_settings_changed(self, origin=None, *args):
        """
        Cylinder settings were changed. We force the local settings wrap to update.

        @param origin:
        @param args:
        @return:
        """
        if origin is not None and origin != self.service.path:
            return
        device = self.service.device
        device.driver.cylinder_validate()

    @signal_listener("view;realized")
    def realize(self, origin=None, *args):
        """
        Realization of current device requires that device to be additionally updated with rotary
        @param origin:
        @param args:
        @return:
        """
        device = self.service.device
        try:
            device.driver.cylinder_validate()
        except AttributeError:
            pass

    def service_detach(self, *args, **kwargs):
        pass

    def service_attach(self, *args, **kwargs):
        pass

    def shutdown(self, *args, **kwargs):
        pass
