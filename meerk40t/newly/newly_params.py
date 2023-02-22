"""
Newly Parameters is a helper class which serves to treat a dict settings object as an attribute object. This differs
from the core parameters in the parameters it uses.
"""

from typing import Dict

FLOAT_PARAMETERS = (
    "acceleration",
)
INT_PARAMETERS = tuple()

BOOL_PARAMETERS = tuple()


STRING_PARAMETERS = tuple()


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
    def acceleration(self):
        return self.settings.get("acceleration", 24)

    @acceleration.setter
    def acceleration(self, value):
        self.settings["acceleration"] = value
