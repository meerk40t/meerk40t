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
                "conditional": (service, "cylinder_x_axis"),
                "subsection": _("X Axis"),
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
                "conditional": (service, "cylinder_y_axis"),
                "subsection": _("Y Axis"),
            },
        ]
        service.register_choices("cylinder", choices)

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
