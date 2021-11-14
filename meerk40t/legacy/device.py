from meerk40t.kernel import Service


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.add_service("device", LegacyDevice(kernel))
    elif lifecycle == "boot":
        context = kernel.get_context("legacy")
        _ = context._
        choices = [
            {
                "attr": "bed_width",
                "object": context,
                "default": 310,
                "type": int,
                "label": _("Width"),
                "tip": _("Width of the laser bed."),
            },
            {
                "attr": "bed_height",
                "object": context,
                "default": 210,
                "type": int,
                "label": _("Height"),
                "tip": _("Height of the laser bed."),
            },
            {
                "attr": "scale_x",
                "object": context,
                "default": 1.000,
                "type": float,
                "label": _("X Scale Factor"),
                "tip": _(
                    "Scale factor for the X-axis. This defines the ratio of mils to steps. This is usually at 1:1 steps/mils but due to functional issues it can deviate and needs to be accounted for"
                ),
            },
            {
                "attr": "scale_y",
                "object": context,
                "default": 1.000,
                "type": float,
                "label": _("Y Scale Factor"),
                "tip": _(
                    "Scale factor for the Y-axis. This defines the ratio of mils to steps. This is usually at 1:1 steps/mils but due to functional issues it can deviate and needs to be accounted for"
                ),
            },
        ]
        kernel.register_choices("bed_dim", choices)


class LegacyDevice(Service):
    """
    Legacy Device governs the 0.7.x style device connections between spoolers, controllers, and output.
    """

    def __init__(self, kernel, *args, **kwargs):
        Service.__init__(self, kernel, "legacy")

    def attach(self, *args, **kwargs):
        # self.register("plan/interrupt", interrupt)
        _ = self.kernel.translation
        self.setting(float, "current_x", 0.0)
        self.setting(float, "current_y", 0.0)

