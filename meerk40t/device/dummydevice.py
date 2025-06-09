from meerk40t.core.spoolers import Spooler
from meerk40t.core.view import View
from meerk40t.device.devicechoices import get_effect_choices
from meerk40t.kernel import Service, signal_listener

from .mixins import Status


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("provider/device/dummy", DummyDevice)
        _ = kernel.translation
        kernel.register(
            "dev_info/dummy_info",
            {
                "provider": "provider/device/dummy",
                "friendly_name": _("The device name goes here"),
                "extended_info": _("Extended device info would go here."),
                "priority": -1,
                "family": "",
                "choices": [
                    {
                        "attr": "label",
                        "default": "dummy",
                    },
                ],
            },
        )


class DummyDevice(Service, Status):
    """
    DummyDevice is a mock device service. It provides no actual device.

    This is mostly for testing.
    """

    def __init__(self, kernel, path, *args, choices=None, **kwargs):
        Service.__init__(self, kernel, path)
        Status.__init__(self)
        self.name = "Dummy Device"
        if choices is not None:
            for c in choices:
                attr = c.get("attr")
                default = c.get("default")
                if attr is not None and default is not None:
                    setattr(self, attr, default)
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

        self.register_choices("dummy-effects", get_effect_choices(self))

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
        self.view = View(self.bedwidth, self.bedheight)

    @property
    def safe_label(self):
        """
        Provides a safe label without spaces or / which could cause issues when used in timer or other names.
        @return:
        """
        if not hasattr(self, "label"):
            return self.name
        name = self.label.replace(" ", "-")
        return name.replace("/", "-")

    @signal_listener("bedwidth")
    @signal_listener("bedheight")
    @signal_listener("scale_x")
    @signal_listener("scale_y")
    def realize(self, origin=None, *args):
        """
        We implement realize which always calls `view;realized` signal.
        @param origin:
        @param args:
        @return:
        """
        if origin is not None and origin != self.path:
            return
        self.view.set_dims(self.bedwidth, self.bedheight)
        self.view.transform(
            user_scale_x=self.scale_x,
            user_scale_y=self.scale_y,
        )
        self.signal("view;realized")

    @property
    def current(self):
        """
        @return: the location in units for the current known position.
        """
        return self.view.iposition(self.native_x, self.native_y)

    @property
    def native(self):
        """
        @return: the location in device native units for the current known position.
        """
        return self.native_x, self.native_y

    def location(self):
        """
        Provide information about the device interface
        """
        return "mock"
