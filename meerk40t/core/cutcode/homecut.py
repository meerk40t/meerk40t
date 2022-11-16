from .cutobject import CutObject


class HomeCut(CutObject):
    def __init__(self, offset_point=None, parameter_object=None, passes=1, parent=None):
        if offset_point is None:
            offset_point = (0, 0)
        CutObject.__init__(
            self,
            offset_point,
            offset_point,
            parameter_object=parameter_object,
            passes=passes,
            parent=parent,
        )
        self.first = True  # Dwell cuts are standalone
        self.last = True
        self.raster_step = 0

    def reversible(self):
        return False

    def reverse(self):
        pass

    def generate(self):
        yield "home"
