from .cutobject import CutObject


class GotoCut(CutObject):
    def __init__(
        self, offset_point=None, settings=None, passes=1, parent=None, color=None
    ):
        if offset_point is None:
            offset_point = (0, 0)
        CutObject.__init__(
            self,
            offset_point,
            offset_point,
            settings=settings,
            passes=passes,
            parent=parent,
            color=color,
        )
        self.first = True  # Dwell cuts are standalone
        self.last = True

    def reversible(self):
        return False

    def reverse(self):
        pass

    def generate(self):
        yield "move_abs", self._start_x, self._start_y
