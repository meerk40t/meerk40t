from .cutobject import CutObject


class WaitCut(CutObject):
    def __init__(self, wait, parameter_object=None, passes=1, parent=None):
        """
        Establish a wait cut.
        @param wait: wait time in ms.
        @param parameter_object: Settings for wait cut.
        @param passes: Number of passes.
        @param parent: CutObject parent.
        """
        CutObject.__init__(
            self,
            (0, 0),
            (0, 0),
            parameter_object=parameter_object,
            passes=passes,
            parent=parent,
        )
        self.dwell_time = wait
        self.first = True  # Wait cuts are standalone
        self.last = True
        self.raster_step = 0

    def reversible(self):
        return False

    def reverse(self):
        pass

    def generate(self):
        # Dwell time is already in ms.
        yield "wait", self.dwell_time
