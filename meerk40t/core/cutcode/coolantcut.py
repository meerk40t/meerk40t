from .cutobject import CutObject


class CoolantCut(CutObject):
    def __init__(
        self,
        cool_on_off,
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
        self.on_off = cool_on_off if cool_on_off is not None else False
        self.first = True  # Dwell cuts are standalone
        self.last = True

    def reversible(self):
        return False

    def reverse(self):
        pass
