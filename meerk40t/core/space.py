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
                "style": "slider",
                "min": 0.0,
                "max": 1.0,
                "label": _("Origin X"),
                "tip": _(
                    "Value between 0-1 for the location of the origin x parameter"
                ),
                "subsection": "_10_X-Axis",
            },
            {
                "attr": "origin_y",
                "object": self,
                "default": 0.0,
                "type": float,
                "style": "slider",
                "min": 0.0,
                "max": 1.0,
                "label": _("Origin Y"),
                "tip": _(
                    "Value between 0-1 for the location of the origin y parameter"
                ),
                "subsection": "_20_Y-Axis",
            },
            {
                "attr": "right_positive",
                "object": self,
                "default": True,
                "type": bool,
                "label": _("Right Positive"),
                "tip": _("Are positive values to the right?"),
                "subsection": "_10_X-Axis",
            },
            {
                "attr": "bottom_positive",
                "object": self,
                "default": True,
                "type": bool,
                "label": _("Bottom Positive"),
                "tip": _("Are positive values towards the bottom?"),
                "subsection": "_20_Y-Axis",
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
    def update(self, origin, *args):
        self.update_bounds(self.x, self.y, self.width, self.height)

    @signal_listener("view;realized")
    def update_realize(self, origin, *args):
        # Fallback to default if device or view is not available
        view = getattr(getattr(self, "device", None), "view", None)
        if view is not None:
            self.update_bounds(0, 0, view.width, view.height)
        else:
            self.update_bounds(0, 0, "100mm", "100mm")

    def origin_zero(self):
        width = self.width if self.width is not None else 100.0
        height = self.height if self.height is not None else 100.0
        return self.origin_x * width, self.origin_y * height

    def update_bounds(self, x, y, width, height):
        def safe_float(val):
            try:
                return float(Length(val))
            except Exception:
                return 0.0

        self.x = safe_float(x)
        self.y = safe_float(y)
        self.width = safe_float(width)
        self.height = safe_float(height)
        self.display = View(
            self.width, self.height, dpi_x=UNITS_PER_INCH, dpi_y=UNITS_PER_INCH
        )
        self.display.transform(
            flip_x=not self.right_positive,
            flip_y=not self.bottom_positive,
        )
        self.signal("refresh_scene", "Scene")

    def scene_coordinates(self, x, y):
        """
        Convert real coordinates (e.g., device or view coordinates) to space coordinates
        considering origin and axis direction.
        """
        width = self.width if self.width is not None else 100.0
        height = self.height if self.height is not None else 100.0
        # Step 1: Subtract origin offset
        x = x - self.origin_x * width
        y = y - self.origin_y * height
        # Step 2: Invert axes if needed
        if not self.right_positive:
            x = -x
        if not self.bottom_positive:
            y = -y
        return x, y

    def native_coordinates(self, x, y):
        """
        Convert space coordinates to real coordinates (e.g., device or view coordinates)
        considering origin, axis direction, and swap_xy.
        """
        width = self.width if self.width is not None else 100.0
        height = self.height if self.height is not None else 100.0
        # Step 1: Invert axes if needed
        if not self.right_positive:
            x = -x
        if not self.bottom_positive:
            y = -y
        # Step 2: Add origin offset
        x = x + self.origin_x * width
        y = y + self.origin_y * height
        return x, y
