from meerk40t.kernel import Service
from meerk40t.svgelements import Matrix


def plugin(kernel, lifecycle=None):
    if lifecycle == "plugins":
        from .gui import gui

        return [gui.plugin]
    if lifecycle == "register":
        kernel.add_service("rotary", Rotary(kernel, 0))
    elif lifecycle == "boot":
        _ = kernel.root._
        rotary = kernel.rotary
        # # TODO: Flesh out implementation into proper device info.
        choices = [
            {
                "attr": "rotary_active",
                "object": rotary,
                "default": False,
                "type": bool,
                "label": _("Rotary-Mode active"),
                "tip": _("Is the rotary mode active for this device"),
            },
            {
                "attr": "rotary_scale_x",
                "object": rotary,
                "default": 1.0,
                "type": float,
                "label": _("X-Scale"),
                "tip": _("Scale that needs to be applied to the X-Axis"),
                "conditional": (rotary, "rotary_active"),
                "subsection": _("Scale"),
            },
            {
                "attr": "rotary_scale_y",
                "object": rotary,
                "default": 1.0,
                "type": float,
                "label": _("Y-Scale"),
                "tip": _("Scale that needs to be applied to the Y-Axis"),
                "conditional": (rotary, "rotary_active"),
                "subsection": _("Scale"),
            },
            {
                "attr": "rotary_supress_home",
                "object": rotary,
                "default": False,
                "type": bool,
                "label": _("Ignore Home"),
                "tip": _("Ignore Home-Command"),
                "conditional": (rotary, "rotary_active"),
            },
            {
                "attr": "rotary_mirror_x",
                "object": rotary,
                "default": False,
                "type": bool,
                "label": _("Mirror X"),
                "tip": _("Mirror the elements on the X-Axis"),
                "conditional": (rotary, "rotary_active"),
                "subsection": _("Mirror Output"),
            },
            {
                "attr": "rotary_mirror_y",
                "object": rotary,
                "default": False,
                "type": bool,
                "label": _("Mirror Y"),
                "tip": _("Mirror the elements on the Y-Axis"),
                "conditional": (rotary, "rotary_active"),
                "subsection": _("Mirror Output"),
            },
        ]
        kernel.register_choices("rotary", choices)

        choices = [
            {
                "attr": "rotary_enabled",
                "object": rotary,
                "default": False,
                "type": bool,
                "label": _("Rotary Enabled"),
                "tip": _("Turn on rotary"),
            },
            {
                "attr": "axis",
                "object": rotary,
                "default": 1,
                "type": int,
                "label": _("Rotary Axis:"),
                "tip": _("Which axis does the rotary use?"),
            },
            {
                "attr": "scale_x",
                "object": rotary,
                "default": 1.0,
                "type": float,
                "label": _("Rotary X Scale Factor"),
                "tip": _("Scale Rotary X"),
            },
            {
                "attr": "scale_y",
                "object": rotary,
                "default": 1.0,
                "type": float,
                "label": _("Rotary Y Scale Factor"),
                "tip": _("Scale Rotary X"),
            },
        ]
        kernel.register_choices("rotary", choices)


class Rotary(Service):
    """
    Rotary Service provides rotary information about the selected rotary you intend to use.
    """

    def __init__(self, kernel, index=0, *args, **kwargs):
        Service.__init__(self, kernel, f"rotary/{index}")
        self.index = index
        _ = kernel.translation

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

    def service_detach(self, *args, **kwargs):
        pass

    def service_attach(self, *args, **kwargs):
        pass

    def shutdown(self, *args, **kwargs):
        pass
