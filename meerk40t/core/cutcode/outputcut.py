from .cutobject import CutObject


class OutputCut(CutObject):
    def __init__(
        self,
        output_mask,
        output_value,
        output_message=None,
        settings=None,
        passes=1,
        parent=None,
        color=None,
    ):
        CutObject.__init__(
            self,
            (0, 0),
            (0, 0),
            settings=settings,
            passes=passes,
            parent=parent,
            color=color,
        )
        self.output_mask = output_mask
        self.output_value = output_value
        self.output_message = output_message
        self.first = True  # Dwell cuts are standalone
        self.last = True
        self.raster_step = 0

    def reversible(self):
        return False

    def reverse(self):
        pass
