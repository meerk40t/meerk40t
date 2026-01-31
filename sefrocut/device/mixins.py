class Status:
    """
    Common functionality for all devices:
    - Status information
    - Sensible defaults
    """

    def __init__(self):
        self._laser_status = "idle"

    @property
    def laser_status(self):
        return self._laser_status

    @laser_status.setter
    def laser_status(self, new_value):
        self._laser_status = new_value
        flag = bool(new_value == "active")
        self.signal("pipe;running", flag)

    # helper function for default values
    def get_effect_defaults(self, effect_type: str) -> dict:
        """
        Returns the default settings for a specific effect type.
        """
        settings = {}
        try:
            if effect_type == "effect hatch":
                settings.update(
                    {
                        "hatch_distance": self.effect_hatch_default_distance,
                        "hatch_angle": self.effect_hatch_default_angle,
                        "hatch_angle_delta": self.effect_hatch_default_angle_delta,
                        "hatch_type": self.effect_hatch_default_type,
                    }
                )
            elif effect_type == "effect wobble":
                settings.update(
                    {
                        "wobble_radius": self.effect_wobble_default_radius,
                        "wobble_interval": self.effect_wobble_default_interval,
                        "wobble_speed": self.effect_wobble_default_speed,
                        "wobble_type": self.effect_wobble_default_type,
                    }
                )
        except AttributeError:
            pass
        return settings

    def get_operation_power_speed_defaults(self, operation_type: str) -> dict:
        """
        Returns the default power and speed settings for an operation.
        """
        settings = {}
        op_type = operation_type.replace(" ", "_").lower()
        for prop in ("power", "speed", "engrave_speed"):
            if hasattr(self, f"default_{prop}_{op_type}"):
                settings[prop] = getattr(self, f"default_{prop}_{op_type}")
        return settings
