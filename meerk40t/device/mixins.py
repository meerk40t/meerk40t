class Status:
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
