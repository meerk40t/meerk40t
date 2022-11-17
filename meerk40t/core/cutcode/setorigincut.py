from .cutobject import CutObject


class SetOriginCut(CutObject):
    def __init__(self, offset_point=None, settings=None, passes=1, parent=None):
        self.set_current = False
        if offset_point is None:
            offset_point = (0, 0)
            self.set_current = True

        CutObject.__init__(
            self,
            offset_point,
            offset_point,
            settings=settings,
            passes=passes,
            parent=parent,
        )
        self.first = True  # SetOrigin cuts are standalone
        self.last = True
        self.raster_step = 0

    def reversible(self):
        return False

    def reverse(self):
        pass

    def generate(self):
        if self.set_current:
            yield "set_origin"
        else:
            yield "set_origin", self._start_x, self._start_y
