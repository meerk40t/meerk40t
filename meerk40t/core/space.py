from meerk40t.core.units import UNITS_PER_INCH, Length
from meerk40t.core.view import View
from meerk40t.kernel import Service, signal_listener


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "register":
        kernel.add_service("space", CoordinateSystem(kernel))


class CoordinateSystem(Service):
    def __init__(self, kernel, *args, **kwargs):
        Service.__init__(self, kernel, "space")
        _ = kernel.translation
        choices = [
            {
                "attr": "origin_x",
                "object": self,
                "default": 0.0,
                "type": float,
                "label": _("Origin X"),
                "tip": _(
                    "Value between 0-1 for the location of the origin x parameter"
                ),
            },
            {
                "attr": "origin_y",
                "object": self,
                "default": 0.0,
                "type": float,
                "label": _("Origin Y"),
                "tip": _(
                    "Value between 0-1 for the location of the origin y parameter"
                ),
            },
            {
                "attr": "right_positive",
                "object": self,
                "default": True,
                "type": bool,
                "label": _("Right Positive"),
                "tip": _("Are positive values to the right?"),
            },
            {
                "attr": "bottom_positive",
                "object": self,
                "default": True,
                "type": bool,
                "label": _("Bottom Positive"),
                "tip": _("Are positive values towards the bottom?"),
            },
            {
                "attr": "swap_xy",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Swap XY"),
                "tip": _("XY coordinates are swapped"),
            },
            {
                "attr": "rotation",
                "object": self,
                "default": 0,
                "type": int,
                "label": _("Rotation"),
                "tip": _("Rotation in degrees"),
            },
            {
                "attr": "units",
                "object": self,
                "default": 0,
                "type": int,
                "label": _("Preferred Units"),
                "tip": _("Set default units for positions"),
                "style": "option",
                "display": (_("tat"), _("mm"), _("cm"), _("inch"), _("mil")),
                "choices": (0, 1, 2, 3, 4),
            },
        ]
        kernel.register_choices("space", choices)
        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.display = None
        self.update_bounds(0, 0, "100mm", "100mm")

    @signal_listener("right_positive")
    @signal_listener("bottom_positive")
    @signal_listener("origin_x")
    @signal_listener("origin_y")
    @signal_listener("swap_xy")
    def update(self, origin, *args):
        self.update_bounds(self.x, self.y, self.width, self.height)

    @signal_listener("view;realized")
    def update_realize(self, origin, *args):
        try:
            self.update_bounds(0, 0, self.device.view.width, self.device.view.height)
        except AttributeError:
            pass

    def origin_zero(self):
        return self.origin_x * self.width, self.origin_y * self.height

    def update_bounds(self, x, y, width, height):
        self.x = float(Length(x))
        self.y = float(Length(y))
        self.width = float(Length(width))
        self.height = float(Length(height))
        self.display = View(
            self.width, self.height, dpi_x=UNITS_PER_INCH, dpi_y=UNITS_PER_INCH
        )
        self.display.transform(
            flip_x=not self.right_positive,
            flip_y=not self.bottom_positive,
            swap_xy=self.swap_xy,
        )
        self.signal("refresh_scene", "Scene")
