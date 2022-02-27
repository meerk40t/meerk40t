from meerk40t.kernel import Service
from meerk40t.svgelements import Matrix


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.add_service("rotary", Rotary(kernel, 0))
    elif lifecycle == "boot":
        _ = kernel.root._
        rotary = kernel.rotary
        # TODO: Flesh out implementation into proper device info.
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
        Service.__init__(self, kernel, "rotary/{index}".format(index=index))
        self.index = index
        _ = kernel.translation

        @self.console_command(
            "rotary",
            help=_("Rotary base command"),
            output_type="rotary",
        )
        def rotary(command, channel, _, data=None, **kwargs):
            channel(
                "Rotary {index} set to scale: {x}, scale:{y}".format(
                    index=self.index, x=self.scale_x, y=self.scale_y
                )
            )
            return "rotary", None

        @self.console_command("rotaryscale", help=_("Rotary Scale selected elements"))
        def apply_rotary_scale(*args, **kwargs):
            sx = self.scale_x
            sy = self.scale_y
            x, y = self.device.current
            mx = Matrix(
                "scale(%f, %f, %f, %f)"
                % (sx, sy, x, y)
            )
            for element in self.elements.elems():
                if hasattr(element, "rotary_scale"):
                    # This element is already scaled
                    return
                try:
                    element.rotary_scale = sx, sy
                    element *= mx
                    element.node.modified()
                except AttributeError:
                    pass

    def service_detach(self, *args, **kwargs):
        pass

    def service_attach(self, *args, **kwargs):
        pass

    def shutdown(self, *args, **kwargs):
        pass
