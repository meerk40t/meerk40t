from .cutobject import CutObject


class DwellCut(CutObject):
    def __init__(self, start_point, wait, parameter_object=None, passes=1, parent=None):
        CutObject.__init__(
            self,
            start_point,
            start_point,
            parameter_object=parameter_object,
            passes=passes,
            parent=parent,
        )
        self.dwell_time = wait
        self.first = True  # Dwell cuts are standalone
        self.last = True
        self.raster_step = 0

    def reversible(self):
        return False

    def reverse(self):
        pass

    def generate(self):
        yield "rapid_mode"
        start = self.start
        yield "move_abs", start[0], start[1]
        yield "dwell", self.dwell_time
