"""
Ruida Device

Ruida device interfacing. We do not send or interpret ruida code, but we can emulate ruidacode into cutcode and read
ruida files (*.rd) and turn them likewise into cutcode.
"""


from meerk40t.kernel import Service

from ..core.spoolers import Spooler
from ..core.units import Length, ViewPort, UNITS_PER_uM


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
                "signals": "bedsize",
                "nonzero": True,
            },
            {
                "attr": "bedheight",
                "object": self,
                "default": "16in",
                "type": Length,
                "label": _("Height"),
                "tip": _("Height of the laser bed."),
                "signals": "bedsize",
                "nonzero": True,
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
        width = float(Length(self.bedwidth))
        height = float(Length(self.bedheight))
        ViewPort.__init__(
            self,
            scene1=(width / 2, height / 2),
            scene2=(-width / 2, height / 2),
            scene3=(-width / 2, -height / 2),
            scene4=(width / 2, -height / 2),
            laser1=(UNITS_PER_uM / width, 0),
            laser2=(0, 0),
            laser3=(0, UNITS_PER_uM / height),
            laser4=(UNITS_PER_uM / width, UNITS_PER_uM / height),
        )
        self.state = 0

        self.spooler = Spooler(self)

        self.viewbuffer = ""

        _ = self.kernel.translation

    def realize(self):
        super().realize()

    @property
    def current(self):
        """
        @return: the location in scene units for the current known x value.
        """
        return 0, 0

    @property
    def native(self):
        """
        @return: the location in device native units for the current known position.
        """
        return 0, 0
