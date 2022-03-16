from meerk40t.core.spoolers import Spooler
from meerk40t.kernel import Service

from ..core.units import ViewPort


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("provider/device/dummy", DummyDevice)


class DummyDevice(Service, ViewPort):
    """
    DummyDevice is a mock device service. It provides no actual device.

    This is mostly for testing.
    """

    def __init__(self, kernel, path, *args, **kwargs):
        Service.__init__(self, kernel, path)
        self.name = "Dummy Device"
        self.current_x = 0.0
        self.current_y = 0.0
        self.settings = dict()
        self.state = 0
        self.spooler = Spooler(self, "default")
        self.viewbuffer = ""
        self.label = "Dummy Device"

        _ = self.kernel.translation
        choices = [
            {
                "attr": "bedwidth",
                "object": self,
                "default": "320mm",
                "type": str,
                "label": _("Width"),
                "tip": _("Width of the laser bed."),
            },
            {
                "attr": "bedheight",
                "object": self,
                "default": "220mm",
                "type": float,
                "label": _("Height"),
                "tip": _("Height of the laser bed."),
            },
            {
                "attr": "scale_x",
                "object": self,
                "default": 1.000,
                "type": float,
                "label": _("X Scale Factor"),
                "tip": _(
                    "Scale factor for the X-axis. Board units to actual physical units."
                ),
            },
            {
                "attr": "scale_y",
                "object": self,
                "default": 1.000,
                "type": float,
                "label": _("Y Scale Factor"),
                "tip": _(
                    "Scale factor for the Y-axis. Board units to actual physical units."
                ),
            },
        ]
        self.register_choices("bed_dim", choices)
        ViewPort.__init__(self, 0, 0, self.width, self.height)

        @self.console_command(
            "spool",
            help=_("spool <command>"),
            regex=True,
            input_type=(None, "plan", "device"),
            output_type="spooler",
        )
        def spool(command, channel, _, data=None, remainder=None, **kwgs):
            spooler = self.spooler
            if data is not None:
                # If plan data is in data, then we copy that and move on to next step.
                spooler.jobs(data.plan)
                channel(_("Spooled Plan."))
                self.signal("plan", data.name, 6)

            if remainder is None:
                channel(_("----------"))
                channel(_("Spoolers:"))
                for d, d_name in enumerate(self.match("device", suffix=True)):
                    channel("%d: %s" % (d, d_name))
                channel(_("----------"))
                channel(_("Spooler on device %s:" % str(self.label)))
                for s, op_name in enumerate(spooler.queue):
                    channel("%d: %s" % (s, op_name))
                channel(_("----------"))

            return "spooler", spooler
