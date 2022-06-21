from typing import Dict

from meerk40t.svgelements import Color

INT_PARAMETERS = (
    "power",
    "raster_direction",
    "acceleration",
    "dot_length",
    "passes",
    "jog_distance",
    "raster_direction",
    "raster_preference_top",
    "raster_preference_right",
    "raster_preference_left",
    "raster_preference_bottom",
)

FLOAT_PARAMETERS = (
    "dpi",
    "raster_step_x",
    "raster_step_y",
    "speed",
    "dratio",
    "dwell_time",
    "frequency",
)

BOOL_PARAMETERS = (
    "passes_custom",
    "dot_length_custom",
    "acceleration_custom",
    "dratio_custom",
    "default",
    "output",
    "laser_enabled",
    "job_enabled",
    "ppi_enabled",
    "shift_enabled",
    "raster_swing",
    "advanced",
    "raster_alt",
    "force_twitchless",
)

STRING_PARAMETERS = ("overscan", "hatch_distance", "hatch_angle", "hatch_type", "penbox_value", "penbox_pass")

COLOR_PARAMETERS = ("color", "line_color")


class Parameters:
    """
    Parameters is a helper class which seeks to normalize, validate, and extract values from an underlying
    dictionary. This class isn't required and in many cases it's better and more consistent to extract the
    values of various settings directly as keys in the dictionary. This class is provided to simplify those set
    and get operations as well as to normalize the keys used to store and extract the information. Since different
    drivers can have completely different and alien settings the dictionary is the primary storage for these
    settings. Settings outside the scope of this class are still legal and will be passed to the drivers which
    may or may not implement or respect them.
    """
    def __init__(self, settings: Dict = None, **kwargs):
        self.settings = settings
        if self.settings is None:
            self.settings = dict()
        self.settings.update(kwargs)

    def derive(self):
        derived_dict = dict(self.settings)
        for attr in dir(self):
            if attr.startswith("_"):
                continue
            value = getattr(self, attr)
            if value is None:
                continue
            derived_dict[attr] = value
        return derived_dict

    def validate(self):
        settings = self.settings
        for v in FLOAT_PARAMETERS:
            if v in settings:
                settings[v] = float(settings[v])
        for v in INT_PARAMETERS:
            if v in settings:
                settings[v] = int(float(settings[v]))
        for v in BOOL_PARAMETERS:
            if v in settings:
                settings[v] = str(settings[v]).lower() == "true"
        for v in STRING_PARAMETERS:
            if v in settings:
                settings[v] = settings[v]
        for v in COLOR_PARAMETERS:
            if v in settings:
                settings[v] = Color(settings[v])

    @property
    def color(self):
        color = self.settings.get("color")
        if color is None:
            try:
                type = self.type
            except AttributeError:
                type = None
            if type == "op cut":
                return Color("red")
            elif type == "op engrave":
                return Color("blue")
            elif type == "op hatch":
                return Color("green")
            elif type == "op raster":
                return Color("black")
            elif type == "op image":
                return Color("transparent")
            elif type == "op dots":
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
    def raster_step_x(self):
        return self.settings.get("raster_step_x", 0)

    @raster_step_x.setter
    def raster_step_x(self, value):
        self.settings["raster_step_x"] = value

    @property
    def raster_step_y(self):
        return self.settings.get("raster_step_y", 0)

    @raster_step_y.setter
    def raster_step_y(self, value):
        self.settings["raster_step_y"] = value

    @property
    def dpi(self):
        return self.settings.get("dpi", 500)

    @dpi.setter
    def dpi(self, value):
        self.settings["dpi"] = value

    @property
    def overscan(self):
        return self.settings.get("overscan", "0.5mm")

    @overscan.setter
    def overscan(self, value):
        self.settings["overscan"] = value

    @property
    def speed(self):
        speed = self.settings.get("speed")
        if speed is None:
            try:
                type = self.type
            except AttributeError:
                type = None
            if type == "op cut":
                return 10.0
            elif type == "op engrave":
                return 35.0
            elif type == "op hatch":
                return 35.0
            elif type == "op raster":
                return 150.0
            elif type == "op image":
                return 150.0
            elif type == "op dots":
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
    def frequency(self):
        return self.settings.get("frequency", 20.0)

    @frequency.setter
    def frequency(self, value):
        self.settings["frequency"] = value

    @property
    def rapid_speed(self):
        return self.settings.get("rapid_speed", 100.0)

    @rapid_speed.setter
    def rapid_speed(self, value):
        self.settings["rapid_speed"] = value

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
        return self.settings.get("raster_direction", 1)

    @raster_direction.setter
    def raster_direction(self, value):
        self.settings["raster_direction"] = value

    @property
    def raster_swing(self):
        return self.settings.get("raster_swing", False)

    @raster_swing.setter
    def raster_swing(self, value):
        self.settings["raster_swing"] = value

    #####################
    # HATCH PROPERTIES
    #####################

    @property
    def hatch_type(self):
        return self.settings.get("hatch_type", "scanline")

    @hatch_type.setter
    def hatch_type(self, value):
        self.settings["hatch_type"] = value

    @property
    def hatch_angle(self):
        return self.settings.get("hatch_angle", "0deg")

    @hatch_angle.setter
    def hatch_angle(self, value):
        self.settings["hatch_angle"] = value

    @property
    def hatch_distance(self):
        return self.settings.get("hatch_distance", "1mm")

    @hatch_distance.setter
    def hatch_distance(self, value):
        self.settings["hatch_distance"] = value

    #####################
    # PENBOX PROPERTIES
    #####################

    @property
    def penbox_pass(self):
        return self.settings.get("penbox_pass")

    @penbox_pass.setter
    def penbox_pass(self, value):
        self.settings["penbox_pass"] = value

    @property
    def penbox_value(self):
        return self.settings.get("penbox_value")

    @penbox_value.setter
    def penbox_value(self, value):
        self.settings["penbox_value"] = value

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
    def jog_distance(self):
        return self.settings.get("jog_distance", 15)

    @jog_distance.setter
    def jog_distance(self, value):
        self.settings["jog_distance"] = value

    @property
    def jog_enable(self):
        return self.settings.get("jog_enable", True)

    @jog_enable.setter
    def jog_enable(self, value):
        self.settings["jog_enable"] = value

    @property
    def dwell_time(self):
        return self.settings.get("dwell_time", 50.0)

    @dwell_time.setter
    def dwell_time(self, value):
        self.settings["dwell_time"] = value

    @property
    def raster_alt(self):
        return self.settings.get("raster_alt", False)

    @raster_alt.setter
    def raster_alt(self, value):
        self.settings["raster_alt"] = value

    @property
    def force_twitchless(self):
        return self.settings.get("force_twitchless", False)

    @force_twitchless.setter
    def force_twitchless(self, value):
        self.settings["force_twitchless"] = value

    @property
    def constant_move_x(self):
        return self.settings.get("constant_move_x", False)

    @constant_move_x.setter
    def constant_move_x(self, value):
        self.settings["constant_move_x"] = value

    @property
    def constant_move_y(self):
        return self.settings.get("constant_move_y", False)

    @constant_move_y.setter
    def constant_move_y(self, value):
        self.settings["constant_move_y"] = value
