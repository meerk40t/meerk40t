from .cutobject import CutObject


class InputCut(CutObject):
    def __init__(
        self,
        input_mask,
        input_value,
        input_message=None,
        settings=None,
        passes=1,
        parent=None,
    ):
        CutObject.__init__(
            self,
            (0, 0),
            (0, 0),
            settings=settings,
            passes=passes,
            parent=parent,
        )
        self.input_mask = input_mask
        self.input_value = input_value
        self.input_message = input_message
        self.first = True  # Dwell cuts are standalone
        self.last = True
        self.raster_step = 0

    def reversible(self):
        return False

    def reverse(self):
        pass
