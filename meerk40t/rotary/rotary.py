from meerk40t.kernel import Service, signal_listener, lookup_listener
from meerk40t.svgelements import Matrix


def plugin(kernel, lifecycle=None):
    if lifecycle == "plugins":
        from .gui import gui

        return [gui.plugin]
    if lifecycle == "configure":
        # Must occur after devices are registered.
        kernel.add_service("rotary", Rotary(kernel, 0))


class Rotary(Service):
    """
    Rotary Service provides rotary information about the selected rotary you intend to use.
    """

    def __init__(self, kernel, index=0, *args, **kwargs):
        Service.__init__(self, kernel, f"rotary/{index}")
        self.index = index
        _ = kernel.translation
        choices = [
            {
                "attr": "rotary_active",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Rotary-Mode active"),
                "tip": _("Is the rotary mode active for this device"),
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
                "object": self,
                "default": 1.0,
                "type": float,
                "label": _("X-Scale"),
                "tip": _("Scale that needs to be applied to the X-Axis"),
                "conditional": (self, "rotary_active"),
                "subsection": _("Scale"),
            },
            {
                "attr": "rotary_scale_y",
                "object": self,
                "default": 1.0,
                "type": float,
                "label": _("Y-Scale"),
                "tip": _("Scale that needs to be applied to the Y-Axis"),
                "conditional": (self, "rotary_active"),
                "subsection": _("Scale"),
            },
            {
                "attr": "rotary_supress_home",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Ignore Home"),
                "tip": _("Ignore Home-Command"),
                "conditional": (self, "rotary_active"),
            },
            {
                "attr": "rotary_flip_x",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Mirror X"),
                "tip": _("Mirror the elements on the X-Axis"),
                "conditional": (self, "rotary_active"),
                "subsection": _("Mirror Output"),
            },
            {
                "attr": "rotary_flip_y",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Mirror Y"),
                "tip": _("Mirror the elements on the Y-Axis"),
                "conditional": (self, "rotary_active"),
                "subsection": _("Mirror Output"),
            },
        ]
        self.register_choices("rotary", choices)

        @self.console_command(
            "rotary",
            help=_("Rotary base command"),
            output_type="rotary",
        )
        def rotary(command, channel, _, data=None, **kwargs):
            channel(
                f"Rotary {self.index} set to scale: {self.scale_x}, scale:{self.scale_y}"
            )
            return "rotary", None

        @self.console_command("rotaryscale", help=_("Rotary Scale selected elements"))
        def apply_rotary_scale(*args, **kwargs):
            sx = self.scale_x
            sy = self.scale_y
            x, y = self.device.current
            matrix = Matrix(f"scale({sx}, {sy}, {x}, {y})")
            for node in self.elements.elems():
                if hasattr(node, "rotary_scale"):
                    # This element is already scaled
                    return
                try:
                    node.rotary_scale = sx, sy
                    node.matrix *= matrix
                    node.modified()
                except AttributeError:
                    pass

    @lookup_listener("service/device/active")
    @signal_listener("rotary_scale_x")
    @signal_listener("rotary_scale_y")
    @signal_listener("rotary_active")
    @signal_listener("rotary_flip_x")
    @signal_listener("rotary_flip_y")
    def rotary_settings_changed(self, origin=None, *args):
        """
        We force the current device to realize
        @param origin:
        @param args:
        @return:
        """
        device = self.device
        device.realize()

    @signal_listener("view;realized")
    def realize(self, origin=None, *args):
        device = self.device
        if not self.rotary_active:
            return
        device.view.scale(self.rotary_scale_x, self.rotary_scale_y)
        if self.rotary_flip_x:
            device.view.flip_x()
        if self.rotary_flip_y:
            device.view.flip_y()

    def service_detach(self, *args, **kwargs):
        pass

    def service_attach(self, *args, **kwargs):
        pass

    def shutdown(self, *args, **kwargs):
        pass
