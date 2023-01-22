"""
Balor Parameters is a helper class which serves to treat a dict settings object as an attribute object. This differs
from the core parameters in the parameters it uses.
"""

from typing import Dict

FLOAT_PARAMETERS = (
    "speed",
    "frequency",
    "power",
    "rapid_speed",
    "delay_laser_on",
    "delay_laser_off",
    "delay_polygon",
    "wobble_speed",
)
INT_PARAMETERS = ("pulse_width",)

BOOL_PARAMETERS = (
    "wobble_enabled",
    "timing_enabled",
    "rapid_enabled",
    "pulse_width_enabled",
)


STRING_PARAMETERS = ("wobble_type", "wobble_radius", "wobble_interval")


class Parameters:
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
                settings[v] = int(settings[v])
        for v in BOOL_PARAMETERS:
            if v in settings:
                settings[v] = str(settings[v]).lower() == "true"
        for v in STRING_PARAMETERS:
            if v in settings:
                settings[v] = str(settings[v])

    @property
    def rapid_enabled(self):
        return self.settings.get("rapid_enabled", False)

    @rapid_enabled.setter
    def rapid_enabled(self, value):
        self.settings["rapid_enabled"] = value

    @property
    def pulse_width_enabled(self):
        return self.settings.get("pulse_width_enabled", False)

    @pulse_width_enabled.setter
    def pulse_width_enabled(self, value):
        self.settings["pulse_width_enabled"] = value

    @property
    def pulse_width(self):
        return self.settings.get("pulse_width", 4)

    @pulse_width.setter
    def pulse_width(self, value):
        self.settings["pulse_width"] = value

    @property
    def timing_enabled(self):
        return self.settings.get("timing_enabled", False)

    @timing_enabled.setter
    def timing_enabled(self, value):
        self.settings["timing_enabled"] = value

    @property
    def wobble_enabled(self):
        return self.settings.get("wobble_enabled", False)

    @wobble_enabled.setter
    def wobble_enabled(self, value):
        self.settings["wobble_enabled"] = value

    @property
    def wobble_radius(self):
        return self.settings.get("wobble_radius", "1.5mm")

    @wobble_radius.setter
    def wobble_radius(self, value):
        self.settings["wobble_radius"] = value

    @property
    def wobble_speed(self):
        return self.settings.get("wobble_speed", 50.0)

    @wobble_speed.setter
    def wobble_speed(self, value):
        self.settings["wobble_speed"] = value

    @property
    def wobble_interval(self):
        return self.settings.get("wobble_interval", "0.3mm")

    @wobble_interval.setter
    def wobble_interval(self, value):
        self.settings["wobble_interval"] = value

    @property
    def wobble_type(self):
        return self.settings.get("wobble_type", "circle")

    @wobble_type.setter
    def wobble_type(self, value):
        self.settings["wobble_type"] = value

    @property
    def speed(self):
        return self.settings.get("speed", 100.0)

    @speed.setter
    def speed(self, value):
        self.settings["speed"] = value

    @property
    def rapid_speed(self):
        return self.settings.get("rapid_speed", 2000.0)

    @rapid_speed.setter
    def rapid_speed(self, value):
        self.settings["rapid_speed"] = value

    @property
    def power(self):
        return self.settings.get("power", 500)

    @power.setter
    def power(self, value):
        self.settings["power"] = value

    @property
    def frequency(self):
        return self.settings.get("frequency", 30.0)

    @frequency.setter
    def frequency(self, value):
        self.settings["frequency"] = value

    @property
    def delay_laser_on(self):
        return self.settings.get("delay_laser_on", 100.0)

    @delay_laser_on.setter
    def delay_laser_on(self, value):
        self.settings["delay_laser_on"] = value

    @property
    def delay_laser_off(self):
        return self.settings.get("delay_laser_off", 100.0)

    @delay_laser_off.setter
    def delay_laser_off(self, value):
        self.settings["delay_laser_off"] = value

    @property
    def delay_polygon(self):
        return self.settings.get("delay_polygon", 100.0)

    @delay_polygon.setter
    def delay_polygon(self, value):
        self.settings["delay_polygon"] = value

    @property
    def delay_end(self):
        return self.settings.get("delay_end", 800.0)

    @delay_end.setter
    def delay_end(self, value):
        self.settings["delay_end"] = value

    @property
    def dwell_time(self):
        return self.settings.get("dwell_time", 50.0)

    @dwell_time.setter
    def dwell_time(self, value):
        self.settings["dwell_time"] = value
