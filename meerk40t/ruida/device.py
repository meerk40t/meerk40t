from meerk40t.kernel import Service

from ..core.spoolers import Spooler
from ..core.units import Length, ViewPort

"""
Ruida device interfacing. We do not send or interpret ruida code, but we can emulator ruidacode into cutcode and read
ruida files (*.rd) and turn them likewise into cutcode.
"""


class RuidaDevice(Service, ViewPort):
    """
    RuidaDevice is driver for the Ruida Controllers
    """

    def __init__(self, kernel, path, *args, **kwargs):
        Service.__init__(self, kernel, path)
        self.name = "RuidaDevice"
        self.setting(str, "label", path)

        _ = self._
        choices = [
            {
                "attr": "bedwidth",
                "object": self,
                "default": "24in",
                "type": Length,
                "label": _("Width"),
                "tip": _("Width of the laser bed."),
            },
            {
                "attr": "bedheight",
                "object": self,
                "default": "16in",
                "type": Length,
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
            self.bedwidth,
            self.bedheight,
            user_scale_x=self.scale_x,
            user_scale_y=self.scale_y,
        )
        self.current_x = 0.0
        self.current_y = 0.0
        self.state = 0

        self.spooler = Spooler(self)

        self.viewbuffer = ""

        _ = self.kernel.translation

    def realize(self):
        self.width = self.bedwidth
        self.height = self.bedheight
        super().realize()

    @property
    def native(self):
        """
        @return: the location in device native units for the current known position.
        """
        return 0, 0
