from meerk40t.kernel import Service


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.add_service("rotary", Rotary(kernel, 0))
    elif lifecycle == "boot":
        _ = kernel.root._
        rotary = kernel.rotary

        choices = [
            {
                "attr": "rotary",
                "object": rotary,
                "default": False,
                "type": bool,
                "label": _("Rotary Enabled"),
                "tip": _("Turn on rotary"),
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

    def service_detach(self, *args, **kwargs):
        pass

    def service_attach(self, *args, **kwargs):
        pass

    def shutdown(self, *args, **kwargs):
        pass
