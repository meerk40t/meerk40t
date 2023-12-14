"""
Ruida Device

Ruida device interfacing. We do not send or interpret ruida code, but we can emulate ruidacode into cutcode and read
ruida files (*.rd) and turn them likewise into cutcode.
"""
from meerk40t.core.view import View
from meerk40t.kernel import Service, signal_listener

from ..core.spoolers import Spooler
from ..core.units import UNITS_PER_NM, Length
from ..device.mixins import Status
from .driver import RuidaDriver


class RuidaDevice(Service):
    """
    RuidaDevice is driver for the Ruida Controllers
    """

    def __init__(self, kernel, path, *args, choices=None, **kwargs):
        Service.__init__(self, kernel, path)
        Status.__init__(self)
        self.name = "RuidaDevice"

        if choices is not None:
            for c in choices:
                attr = c.get("attr")
                default = c.get("default")
                if attr is not None and default is not None:
                    setattr(self, attr, default)

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
            {
                "attr": "interpolate",
                "object": self,
                "default": 50,
                "type": int,
                "label": _("Curve Interpolation"),
                "section": "_10_Parameters",
                "tip": _("Number of curve interpolation points"),
            },
        ]
        self.register_choices("bed_dim", choices)
        choices = [
            {
                "attr": "default_power",
                "object": self,
                "default": 20.0,
                "type": float,
                "label": _("Laser Power"),
                "trailer": "%",
                "tip": _("What power level do we cut at?"),
            },
            {
                "attr": "default_speed",
                "object": self,
                "default": 40.0,
                "type": float,
                "trailer": "mm/s",
                "label": _("Cut Speed"),
                "tip": _("How fast do we cut?"),
            },
        ]
        self.register_choices("ruida-global", choices)

        self.driver = RuidaDriver(self)

        self.spooler = Spooler(self, driver=self.driver)
        self.add_service_delegate(self.spooler)
        self.add_service_delegate(self.driver)
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
        self.view = View(self.bedwidth, self.bedheight, dpi=UNITS_PER_NM)
        self.realize()
        self.state = 0

        self.viewbuffer = ""

        _ = self.kernel.translation

    def service_attach(self, *args, **kwargs):
        self.realize()

    @signal_listener("bedwidth")
    @signal_listener("bedheight")
    @signal_listener("scale_x")
    @signal_listener("scale_y")
    def realize(self, origin=None, *args):
        self.view.set_dims(self.bedwidth, self.bedheight)
        self.view.transform(
            user_scale_x=self.scale_x,
            user_scale_y=self.scale_y,
        )
        self.signal("view;realized")

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
