from meerk40t.core.spoolers import Spooler
from meerk40t.kernel import Service

from ..core.cutcode import LaserSettings


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("service/device/dummy", DummyDevice)


class DummyDevice(Service):
    """
    DummyDevice is a mock device service. It provides no actual device.

    This is mostly for testing.
    """

    def __init__(self, kernel, *args, index=0, **kwargs):
        Service.__init__(self, kernel, "dummy")
        self.name = "Dummy Device"
        self.current_x = 0.0
        self.current_y = 0.0
        self.settings = LaserSettings()
        self.state = 0
        self.spooler = Spooler(self, "default")
        self.spooler.activate = self.activate_spooler
        self.viewbuffer = ""
        self.root.register("spooler/default", self.spooler)

        _ = self.kernel.translation
        choices = [
            {
                "attr": "bedwidth",
                "object": self,
                "default": 12205.0,
                "type": float,
                "label": _("Width"),
                "tip": _("Width of the laser bed."),
            },
            {
                "attr": "bedheight",
                "object": self,
                "default": 8268.0,
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
                    "Scale factor for the X-axis. This defines the ratio of mils to steps. This is usually at 1:1 steps/mils but due to functional issues it can deviate and needs to be accounted for"
                ),
            },
            {
                "attr": "scale_y",
                "object": self,
                "default": 1.000,
                "type": float,
                "label": _("Y Scale Factor"),
                "tip": _(
                    "Scale factor for the Y-axis. This defines the ratio of mils to steps. This is usually at 1:1 steps/mils but due to functional issues it can deviate and needs to be accounted for"
                ),
            },
        ]
        self.register_choices("bed_dim", choices)

        @self.console_command(
            "spool",
            help=_("spool <command>"),
            regex=True,
            input_type=(None, "plan", "device"),
            output_type="spooler",
        )
        def spool(
            command, channel, _, data=None, remainder=None, **kwgs
        ):
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
                channel(_("Spooler %s:" % self.spooler.name))
                for s, op_name in enumerate(spooler.queue):
                    channel("%d: %s" % (s, op_name))
                channel(_("----------"))

            return "spooler", spooler

    def activate_spooler(self):
        self.kernel.activate_service_path("device", "default_device")