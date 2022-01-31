from typing import Dict


class LaserSettings:
    def __init__(self, settings: Dict = None, **kwargs):
        self.settings = settings
        if self.settings is None:
            self.settings = dict()
        self.settings.update(kwargs)

        self.operation = "Unknown"
        try:
            self.operation = kwargs["operation"]
        except KeyError:
            pass
        self.color = None
        self.output = True
        self.show = True
        self.default = False

        try:
            self.color = Color(kwargs["color"])
        except (ValueError, TypeError, KeyError):
            pass
        try:
            self.output = bool(kwargs["output"])
        except (ValueError, TypeError, KeyError):
            pass
        try:
            self.show = bool(kwargs["show"])
        except (ValueError, TypeError, KeyError):
            pass
        try:
            self.default = bool(kwargs["default"])
        except (ValueError, TypeError, KeyError):
            pass

        if self.operation == "Cut":
            if self.settings.speed is None:
                self.settings.speed = 10.0
            if self.settings.power is None:
                self.settings.power = 1000.0
            if self.color is None:
                self.color = Color("red")
        elif self.operation == "Engrave":
            if self.settings.speed is None:
                self.settings.speed = 35.0
            if self.settings.power is None:
                self.settings.power = 1000.0
            if self.color is None:
                self.color = Color("blue")
        elif self.operation == "Raster":
            if self.settings.raster_step == 0:
                self.settings.raster_step = 2
            if self.settings.speed is None:
                self.settings.speed = 150.0
            if self.settings.power is None:
                self.settings.power = 1000.0
            if self.color is None:
                self.color = Color("black")
        elif self.operation == "Image":
            if self.settings.speed is None:
                self.settings.speed = 150.0
            if self.settings.power is None:
                self.settings.power = 1000.0
            if self.color is None:
                self.color = Color("transparent")
        elif self.operation == "Dots":
            if self.settings.speed is None:
                self.settings.speed = 35.0
            if self.settings.power is None:
                self.settings.power = 1000.0
            if self.color is None:
                self.color = Color("transparent")
        else:
            if self.settings.speed is None:
                self.settings.speed = 10.0
            if self.settings.power is None:
                self.settings.power = 1000.0
            if self.color is None:
                self.color = Color("white")

        self.line_color = None

        self.laser_enabled = True
        self.speed = None
        self.power = None
        self.dratio_custom = False
        self.dratio = 0.261
        self.acceleration_custom = False
        self.acceleration = 1

        self.raster_step = 0
        self.raster_direction = 1  # Bottom To Top - Default.
        self.raster_swing = False  # False = bidirectional, True = Unidirectional
        self.raster_preference_top = 0
        self.raster_preference_right = 0
        self.raster_preference_left = 0
        self.raster_preference_bottom = 0
        self.overscan = 20

        self.advanced = False

        self.ppi_enabled = True

        self.dot_length_custom = False
        self.dot_length = 1

        self.shift_enabled = False

        self.passes_custom = False
        self.passes = 1

        self.jog_distance = 255
        self.jog_enable = True

        for k in kwargs:
            value = kwargs[k]
            if hasattr(self, k):
                q = getattr(self, k)
                if q is None:
                    setattr(self, k, value)
                else:
                    t = type(q)
                    setattr(self, k, t(value))

    def set_values(self, obj):
        for q in dir(obj):
            if q.startswith("_") or q.startswith("implicit"):
                continue
            obj_type = type(obj)
            if hasattr(obj_type, q) and isinstance(getattr(obj_type, q), property):
                # Do not set property values
                continue

            value = getattr(obj, q)
            if isinstance(value, (int, float, bool, str)):
                setattr(self, q, value)

    @property
    def horizontal_raster(self):
        return self.raster_step and (self.raster_direction == 0 or self.raster_direction == 1)

    @property
    def vertical_raster(self):
        return self.raster_step and (self.raster_direction == 2 or self.raster_direction == 3)

    @property
    def implicit_accel(self):
        if not self.acceleration_custom:
            return None
        return self.acceleration

    @property
    def implicit_d_ratio(self):
        if not self.dratio_custom:
            return None
        return self.dratio

    @property
    def implicit_dotlength(self):
        if not self.dot_length_custom:
            return 1
        return self.dot_length

    @property
    def implicit_passes(self):
        if not self.passes_custom:
            return 1
        return self.passes
