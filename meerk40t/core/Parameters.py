from typing import Dict

from meerk40t.svgelements import Color


class Parameters:
    def __init__(self, settings: Dict = None, **kwargs):
        self.settings = settings
        if self.settings is None:
            self.settings = dict()
        self.settings.update(kwargs)

    @staticmethod
    def validate(settings: Dict):
        for v in ("speed","dratio"):
            if v in settings:
                settings[v] = float(settings[v])
        for v in (
            "power",
            "raster_step",
            "raster_direction",
            "overscan",
            "acceleration",
            "dot_length",
            "passes",
            "raster_direction",
            "raster_preference_top",
            "raster_preference_right",
            "raster_preference_bottom",
        ):
            if v in settings:
                settings[v] = int(float(settings[v]))
        for v in (
            "passes_custom",
            "dot_length_custom",
            "acceleration_custom",
            "dratio_custom",
            "default",
            "output",
            "laser_enabled",
            "ppi_enabled",
            "shift_enabled",
            "raster_swing",
            "advanced",
        ):
            if v in settings:
                settings[v] = settings[v] in ("True", "true")
        for v in ("color", "line_color"):
            if v in settings:
                settings[v] = Color(settings[v])

    @property
    def color(self):
        color = self.settings.get("color")
        if color is None:
            if self.operation == "Cut":
                return Color("red")
            elif self.operation == "Engrave":
                return Color("blue")
            elif self.operation == "Raster":
                return Color("black")
            elif self.operation == "Image":
                return Color("transparent")
            elif self.operation == "Dots":
                return Color("transparent")
            else:
                return Color("white")
        if isinstance(color, Color):
            return color
        return Color(color)

    @color.setter
    def color(self, value):
        if isinstance(value, Color):
            value = value.hexa
        self.settings["color"] = value

    @property
    def operation(self):
        return self.settings.get("operation", "Unknown")

    @operation.setter
    def operation(self, value):
        self.settings["operation"] = value

    @property
    def default(self):
        return self.settings.get("default", False)

    @default.setter
    def default(self, value):
        self.settings["default"] = value

    @property
    def output(self):
        return self.settings.get("output", True)

    @output.setter
    def output(self, value):
        self.settings["output"] = value

    @property
    def raster_step(self):
        return self.settings.get("raster_step", 2 if self.operation == "Raster" else 0)

    @raster_step.setter
    def raster_step(self, value):
        self.settings["raster_step"] = value

    @property
    def overscan(self):
        return self.settings.get("overscan", 20)

    @overscan.setter
    def overscan(self, value):
        self.settings["overscan"] = value

    @property
    def speed(self):
        speed = self.settings.get("speed")
        if speed is None:
            if self.operation == "Cut":
                return 10.0
            elif self.operation == "Engrave":
                return 35.0
            elif self.operation == "Raster":
                return 150.0
            elif self.operation == "Image":
                return 150.0
            elif self.operation == "Dots":
                return 35.0
            else:
                return 10.0
        return speed

    @speed.setter
    def speed(self, value):
        self.settings["speed"] = value

    @property
    def power(self):
        return self.settings.get("power", 1000)

    @power.setter
    def power(self, value):
        self.settings["power"] = value

    @property
    def line_color(self):
        return self.settings.get("line_color", 0)

    @line_color.setter
    def line_color(self, value):
        self.settings["line_color"] = value

    @property
    def laser_enabled(self):
        return self.settings.get("laser_enabled", True)

    @laser_enabled.setter
    def laser_enabled(self, value):
        self.settings["laser_enabled"] = value

    @property
    def ppi_enabled(self):
        return self.settings.get("ppi_enabled", True)

    @ppi_enabled.setter
    def ppi_enabled(self, value):
        self.settings["ppi_enabled"] = value

    @property
    def dot_length(self):
        return self.settings.get("dot_length", 1)

    @dot_length.setter
    def dot_length(self, value):
        self.settings["dot_length"] = value

    @property
    def dot_length_custom(self):
        return self.settings.get("dot_length_custom", False)

    @dot_length_custom.setter
    def dot_length_custom(self, value):
        self.settings["dot_length_custom"] = value

    @property
    def implicit_dotlength(self):
        if not self.dot_length_custom:
            return 1
        return self.dot_length

    @property
    def shift_enabled(self):
        return self.settings.get("shift_enabled", False)

    @shift_enabled.setter
    def shift_enabled(self, value):
        self.settings["shift_enabled"] = value

    @property
    def passes(self):
        return self.settings.get("passes", 0)

    @passes.setter
    def passes(self, value):
        self.settings["passes"] = value

    @property
    def passes_custom(self):
        return self.settings.get("passes_custom", False)

    @passes_custom.setter
    def passes_custom(self, value):
        self.settings["passes_custom"] = value

    @property
    def implicit_passes(self):
        if not self.passes_custom:
            return 1
        return self.passes

    @property
    def raster_direction(self):
        return self.settings.get("raster_direction", 0)

    @raster_direction.setter
    def raster_direction(self, value):
        self.settings["raster_direction"] = value

    @property
    def raster_swing(self):
        return self.settings.get("raster_swing", False)

    @raster_swing.setter
    def raster_swing(self, value):
        self.settings["raster_swing"] = value

    @property
    def acceleration(self):
        return self.settings.get("acceleration", 0)

    @acceleration.setter
    def acceleration(self, value):
        self.settings["acceleration"] = value

    @property
    def acceleration_custom(self):
        return self.settings.get("acceleration_custom", False)

    @acceleration_custom.setter
    def acceleration_custom(self, value):
        self.settings["acceleration_custom"] = value

    @property
    def implicit_accel(self):
        if not self.acceleration_custom:
            return None
        return self.acceleration

    @property
    def dratio(self):
        return self.settings.get("dratio", 0.261)

    @dratio.setter
    def dratio(self, value):
        self.settings["dratio"] = value

    @property
    def dratio_custom(self):
        return self.settings.get("dratio_custom", False)

    @dratio_custom.setter
    def dratio_custom(self, value):
        self.settings["dratio_custom"] = value

    @property
    def implicit_d_ratio(self):
        if not self.dratio_custom:
            return None
        return self.dratio

    @property
    def raster_preference_top(self):
        return self.settings.get("raster_preference_top", 0)

    @raster_preference_top.setter
    def raster_preference_top(self, value):
        self.settings["raster_preference_top"] = value

    @property
    def raster_preference_right(self):
        return self.settings.get("raster_preference_right", 0)

    @raster_preference_right.setter
    def raster_preference_right(self, value):
        self.settings["raster_preference_right"] = value

    @property
    def raster_preference_left(self):
        return self.settings.get("raster_preference_left", 0)

    @raster_preference_left.setter
    def raster_preference_left(self, value):
        self.settings["raster_preference_left"] = value

    @property
    def raster_preference_bottom(self):
        return self.settings.get("raster_preference_bottom", 0)

    @raster_preference_bottom.setter
    def raster_preference_bottom(self, value):
        self.settings["raster_preference_bottom"] = value

    @property
    def horizontal_raster(self):
        return self.raster_step and (
            self.raster_direction == 0 or self.raster_direction == 1
        )

    @property
    def vertical_raster(self):
        return self.raster_step and (
            self.raster_direction == 2 or self.raster_direction == 3
        )
