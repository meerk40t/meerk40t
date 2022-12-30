from meerk40t.core.spoolers import Spooler
from meerk40t.kernel import Service

from ..core.units import UNITS_PER_MIL, ViewPort


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
        self.native_x = 0.0
        self.native_y = 0.0
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
                "type": str,
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
        # Tuple contains 4 value pairs: Speed Low, Speed High, Power Low, Power High, each with enabled, value
        self.setting(
            list, "dangerlevel_op_cut", (False, 0, False, 0, False, 0, False, 0)
        )
        self.setting(
            list, "dangerlevel_op_engrave", (False, 0, False, 0, False, 0, False, 0)
        )
        self.setting(
            list, "dangerlevel_op_hatch", (False, 0, False, 0, False, 0, False, 0)
        )
        self.setting(
            list, "dangerlevel_op_raster", (False, 0, False, 0, False, 0, False, 0)
        )
        self.setting(
            list, "dangerlevel_op_image", (False, 0, False, 0, False, 0, False, 0)
        )
        self.setting(
            list, "dangerlevel_op_dots", (False, 0, False, 0, False, 0, False, 0)
        )
        ViewPort.__init__(
            self,
            width=self.bedwidth,
            height=self.bedheight,
            native_scale_x=UNITS_PER_MIL,
            native_scale_y=UNITS_PER_MIL,
            origin_x=0.0,
            origin_y=0.0,
        )

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
                label = None
                # If plan data is in data, then we copy that and move on to next step.
                spooler.laserjob(data.plan, label=label)
                channel(_("Spooled Plan."))
                self.signal("plan", data.name, 6)

            if remainder is None:
                channel(_("----------"))
                channel(_("Spoolers:"))
                for d, d_name in enumerate(self.match("device", suffix=True)):
                    channel(f"{d}: {d_name}")
                channel(_("----------"))
                channel(_("Spooler on device {name}:").format(name=str(self.label)))
                for s, op_name in enumerate(spooler.queue):
                    channel(f"{s}: {op_name}")
                channel(_("----------"))

            return "spooler", spooler

    @property
    def current(self):
        """
        @return: the location in nm for the current known x value.
        """
        return self.device_to_scene_position(self.native_x, self.native_y)

    @property
    def native(self):
        """
        @return: the location in device native units for the current known position.
        """
        return self.native_x, self.native_y
