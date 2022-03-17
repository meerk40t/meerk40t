from typing import Dict


FLOAT_PARAMETERS = (
    "travel_speed",
    "cut_speed",
    "q_switch_frequency",
    "power",
    "delay_laser_on",
    "delay_laser_off",
    "delay_polygon",
)


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

    @staticmethod
    def validate(settings: Dict):
        for v in FLOAT_PARAMETERS:
            if v in settings:
                settings[v] = float(settings[v])

    @property
    def cut_speed(self):
        return self.settings.get("cut_speed", 100.0)

    @cut_speed.setter
    def cut_speed(self, value):
        self.settings["cut_speed"] = value

    @property
    def travel_speed(self):
        return self.settings.get("travel_speed", 2000.0)

    @travel_speed.setter
    def travel_speed(self, value):
        self.settings["travel_speed"] = value

    @property
    def laser_power(self):
        return self.settings.get("laser_power", 50.0)

    @laser_power.setter
    def laser_power(self, value):
        self.settings["laser_power"] = value

    @property
    def q_switch_frequency(self):
        return self.settings.get("q_switch_frequency", 30.0)

    @q_switch_frequency.setter
    def q_switch_frequency(self, value):
        self.settings["q_switch_frequency"] = value

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
    def dwell_time(self):
        return self.settings.get("dwell_time", 50.0)

    @dwell_time.setter
    def dwell_time(self, value):
        self.settings["dwell_time"] = value
