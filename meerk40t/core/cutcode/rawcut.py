from .cutobject import CutObject


class RawCut(CutObject):
    """
    Raw cuts are non-shape based cut objects with location and laser amount.
    """

    def __init__(self, settings=None, passes=1, parent=None):
        CutObject.__init__(self, settings=settings, passes=passes, parent=parent)
        self.plot = []
        self.first = True  # Raw cuts are standalone
        self.last = True

    def __len__(self):
        return len(self.plot)

    def plot_extend(self, plot):
        self.plot.extend(plot)

    def plot_append(self, x, y, laser):
        self.plot.append((x, y, laser))
        try:
            x0, y0, l0 = self.plot[-1]
            x1, y1, l1 = self.plot[-2]
            dx = x1 - x0
            dy = y1 - y0
            assert dx == 0 or dy == 0 or abs(dx) == abs(dy)
        except IndexError:
            pass

    def reverse(self):
        self.plot = list(reversed(self.plot))

    @property
    def start(self):
        try:
            return self.plot[0][:2]
        except IndexError:
            return None

    @property
    def end(self):
        try:
            return self.plot[-1][:2]
        except IndexError:
            return None

    @start.setter
    def start(self, value):
        self._start_x = value[0]
        self._start_y = value[1]

    @end.setter
    def end(self, value):
        self._end_x = value[0]
        self._end_y = value[1]

    def generator(self):
        return self.plot
