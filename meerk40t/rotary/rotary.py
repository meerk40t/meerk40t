from meerk40t.kernel import lookup_listener, signal_listener
from meerk40t.svgelements import Matrix


def plugin(service, lifecycle=None):
    if lifecycle == "plugins":
        from .gui import gui

        return [gui.plugin]
    if lifecycle == "service":
        # Responding to "service" makes this a service plugin for the specific services created via the provider
        return (
            "provider/device/lhystudios",
            "provider/device/grbl",
            "provider/device/balor",
            "provider/device/newly",
            "provider/device/moshi",
        )
    elif lifecycle == "added":
        service.add_service_delegate(Rotary(service, 0))


class Rotary:
    """
    Rotary Service provides rotary information about the selected rotary you intend to use.
    """

    def __init__(self, service, index=0, *args, **kwargs):
        self.index = index
        self.service = service
        self.service.rotary = self

        _ = service._
        choices = [
            {
                "attr": "rotary_active_roller",
                "object": service,
                "default": False,
                "type": bool,
                "label": _("Rotary-Mode active"),
                "tip": _("Is the roller rotary mode active for this device"),
                "signals": "device;modified",
                "conditional": (service, "supports_rotary_roller"),
            },
            # {
            #     "attr": "axis",
            #     "object": rotary,
            #     "default": 1,
            #     "type": int,
            #     "label": _("Rotary Axis:"),
            #     "tip": _("Which axis does the rotary use?"),
            # },
            {
                "attr": "rotary_scale_x",
                "object": service,
                "default": 1.0,
                "type": float,
                "label": _("X-Scale"),
                "tip": _("Scale that needs to be applied to the X-Axis"),
                "conditional": (service, "rotary_active_roller"),
                "subsection": _("Scale"),
            },
            {
                "attr": "rotary_scale_y",
                "object": service,
                "default": 1.0,
                "type": float,
                "label": _("Y-Scale"),
                "tip": _("Scale that needs to be applied to the Y-Axis"),
                "conditional": (service, "rotary_active_roller"),
                "subsection": _("Scale"),
            },
            {
                "attr": "suppress_home",
                "object": service,
                "default": False,
                "type": bool,
                "label": _("Ignore Home"),
                "tip": _("Ignore Home-Command"),
                "conditional": (service, "rotary_active_roller"),
            },
            {
                "attr": "rotary_flip_x",
                "object": service,
                "default": False,
                "type": bool,
                "label": _("Mirror X"),
                "tip": _("Mirror the elements on the X-Axis"),
                "conditional": (service, "rotary_active_roller"),
                "subsection": _("Mirror Output"),
            },
            {
                "attr": "rotary_flip_y",
                "object": service,
                "default": False,
                "type": bool,
                "label": _("Mirror Y"),
                "tip": _("Mirror the elements on the Y-Axis"),
                "conditional": (service, "rotary_active_roller"),
                "subsection": _("Mirror Output"),
            },
        ]
        service.register_choices("rotary_roller", choices)

        choices = [
            {
                "attr": "rotary_active_chuck",
                "object": service,
                "default": False,
                "type": bool,
                "label": _("Rotary-Mode active"),
                "tip": _("Is the chuck rotary mode active for this device"),
                "signals": "device;modified",
                "conditional": (service, "supports_rotary_chuck"),
            },
            {
                "attr": "rotary_microsteps_per_revolution",
                "object": service,
                "default": False,
                "type": int,
                "label": _("Micro-Steps"),
                "tip": _("How many microsteps are required for a single revolution"),
                "style": "combosmall",
                "exclusive": False,
                "choices": (200, 400, 800, 1600, 3200, 6400, 12800, 25600, 1000, 2000, 4000, 8000, 10000, 20000, 25000),
                "signals": "device;modified",
                "conditional": (service, "rotary_active_chuck"),
            },
        ]
        service.register_choices("rotary_chuck", choices)

        @service.console_command(
            "rotary",
            help=_("Rotary base command"),
            output_type="rotary",
        )
        def rotary(command, channel, _, data=None, **kwargs):
            channel(
                f"Rotary {self.index} set to scale: {service.rotary_scale_x}, scale:{service.rotary_scale_y}"
            )
            return "rotary", None

        @service.console_command(
            "rotaryscale", help=_("Rotary Scale selected elements")
        )
        def apply_rotary_scale(*args, **kwargs):
            sx = service.rotary_scale_x
            sy = service.rotary_scale_y
            x, y = service.device.current
            matrix = Matrix(f"scale({sx}, {sy}, {x}, {y})")
            for node in service.elements.elems():
                if hasattr(node, "rotary_scale"):
                    # This element is already scaled
                    return
                try:
                    node.rotary_scale = sx, sy
                    node.matrix *= matrix
                    node.modified()
                except AttributeError:
                    pass

    @property
    def scale_x(self):
        return self.service.rotary_scale_x

    @property
    def scale_y(self):
        return self.service.rotary_scale_y

    @property
    def active(self):
        return self.service.rotary_active_roller

    @property
    def flip_x(self):
        return self.service.rotary_flip_x

    @property
    def flip_y(self):
        return self.service.rotary_flip_y

    @property
    def suppress_home(self):
        return self.service.suppress_home

    @lookup_listener("service/device/active")
    @signal_listener("rotary_scale_x")
    @signal_listener("rotary_scale_y")
    @signal_listener("rotary_active_roller")
    @signal_listener("rotary_flip_x")
    @signal_listener("rotary_flip_y")
    def rotary_settings_changed(self, origin=None, *args):
        """
        Rotary settings were changed. We force the current device to realize

        @param origin:
        @param args:
        @return:
        """
        if origin is not None and origin != self.service.path:
            return
        device = self.service.device
        device.realize()

    @signal_listener("view;realized")
    def realize(self, origin=None, *args):
        """
        Realization of current device requires that device to be additionally updated with rotary
        @param origin:
        @param args:
        @return:
        """
        if not self.service.rotary_active_roller:
            return
        device = self.service.device
        device.view.scale(self.service.rotary_scale_x, self.service.rotary_scale_y)
        if self.service.rotary_flip_x:
            device.view.flip_x()
        if self.service.rotary_flip_y:
            device.view.flip_y()

    def service_detach(self, *args, **kwargs):
        pass

    def service_attach(self, *args, **kwargs):
        pass

    def shutdown(self, *args, **kwargs):
        pass
