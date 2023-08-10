"""
Ruida Device

Ruida device interfacing. We do not send or interpret ruida code, but we can emulate ruidacode into cutcode and read
ruida files (*.rd) and turn them likewise into cutcode.
"""


from meerk40t.kernel import Service

from ..core.spoolers import Spooler
from ..core.units import Length, ViewPort
from .driver import RuidaDriver


class RuidaDevice(Service, ViewPort):
    """
    RuidaDevice is driver for the Ruida Controllers
    """

    def __init__(self, kernel, path, *args, choices=None, **kwargs):
        Service.__init__(self, kernel, path)
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
            {
                "attr": "coolant",
                "object": self,
                "default": "",
                "type": str,
                "style": "option",
                "label": _("Coolant"),
                "tip": _("Does this device has a method to turn on / off a coolant associated to it?"),
                "section": "_99_" + _("Coolant Support"),
                "dynamic": self.kernel.root.coolant.coolant_choice_helper,
                "signals": "coolant_changed"
            },
        ]
        self.register_choices("bed_dim", choices)
        choices = [
            {
                "attr": "rotary_active",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Rotary-Mode active"),
                "tip": _("Is the rotary mode active for this device"),
            },
            {
                "attr": "rotary_scale_x",
                "object": self,
                "default": 1.0,
                "type": float,
                "label": _("X-Scale"),
                "tip": _("Scale that needs to be applied to the X-Axis"),
                "conditional": (self, "rotary_active"),
                "subsection": _("Scale"),
            },
            {
                "attr": "rotary_scale_y",
                "object": self,
                "default": 1.0,
                "type": float,
                "label": _("Y-Scale"),
                "tip": _("Scale that needs to be applied to the Y-Axis"),
                "conditional": (self, "rotary_active"),
                "subsection": _("Scale"),
            },
            {
                "attr": "rotary_supress_home",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Ignore Home"),
                "tip": _("Ignore Home-Command"),
                "conditional": (self, "rotary_active"),
            },
            {
                "attr": "rotary_flip_x",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Mirror X"),
                "tip": _("Mirror the elements on the X-Axis"),
                "conditional": (self, "rotary_active"),
                "subsection": _("Mirror Output"),
            },
            {
                "attr": "rotary_flip_y",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Mirror Y"),
                "tip": _("Mirror the elements on the Y-Axis"),
                "conditional": (self, "rotary_active"),
                "subsection": _("Mirror Output"),
            },
        ]
        self.register_choices("rotary", choices)

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
        self.kernel.root.coolant.claim_coolant(self, self.coolant)
        ViewPort.__init__(
            self,
            self.bedwidth,
            self.bedheight,
            user_scale_x=self.scale_x,
            user_scale_y=self.scale_y,
            rotary_active=self.rotary_active,
            rotary_scale_x=self.rotary_scale_x,
            rotary_scale_y=self.rotary_scale_y,
            rotary_flip_x=self.rotary_flip_x,
            rotary_flip_y=self.rotary_flip_y,
        )
        self.state = 0

        self.viewbuffer = ""

        _ = self.kernel.translation

    def service_attach(self, *args, **kwargs):
        self.realize()

    def realize(self, origin=None):
        self.width = self.bedwidth
        self.height = self.bedheight
        super().realize()
        self.space.update_bounds(0, 0, self.width, self.height)

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
