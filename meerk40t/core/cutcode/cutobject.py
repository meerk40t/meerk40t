from ...svgelements import Point


class CutObject:
    """
    CutObjects are small vector cuts which have on them a laser settings object.
    These store the start and end point of the cut. Whether this cut is normal or
    reversed.
    """

    def __init__(
        self, start=None, end=None, settings=None, parent=None, passes=1, **kwargs
    ):
        self.settings = settings
        self.parent = parent
        self.passes = passes
        if start is not None:
            self._start_x = int(round(start[0]))
            self._start_y = int(round(start[1]))
        else:
            self._start_x = None
            self._start_y = None
        if end is not None:
            self._end_x = int(round(end[0]))
            self._end_y = int(round(end[1]))
        else:
            self._end_x = None
            self._end_y = None
        self.normal = True  # Normal or Reversed.
        self.next = None
        self.previous = None
        self._burns_done = 0
        self.highlighted = False

        self.mode = None
        self.inside = None
        self.contains = None
        self.first = False
        self.last = False
        self.closed = False
        self.original_op = None
        self.pass_index = -1

    @property
    def burns_done(self):
        return self._burns_done

    @burns_done.setter
    def burns_done(self, burns):
        """
        Maintain parent burns_done
        """
        self._burns_done = burns
        if self.parent is not None:
            # If we are resetting then we are going to be resetting all
            # so don't bother looping
            if burns == 0:
                self.parent._burns_done = 0
                self.parent.burn_started = False
                return
            for o in self.parent:
                burns = min(burns, o._burns_done)
            self.parent.burn_started = True
            self.parent._burns_done = burns

    def reversible(self):
        return True

    @property
    def start(self):
        return (
            (self._start_x, self._start_y)
            if self.normal
            else (self._end_x, self._end_y)
        )

    @property
    def end(self):
        return (
            (self._start_x, self._start_y)
            if not self.normal
            else (self._end_x, self._end_y)
        )

    @start.setter
    def start(self, value):
        if self.normal:
            self._start_x = value[0]
            self._start_y = value[1]
        else:
            self._end_x = value[0]
            self._end_y = value[1]

    @end.setter
    def end(self, value):
        if self.normal:
            self._end_x = value[0]
            self._end_y = value[1]
        else:
            self._start_x = value[0]
            self._start_y = value[1]

    def length(self):
        return Point.distance(
            (self._start_x, self._start_y), (self._end_x, self._end_y)
        )

    def upper(self):
        return min(self._start_y, self._end_y)

    def lower(self):
        return max(self._start_y, self._end_y)

    def left(self):
        return min(self._start_x, self._end_x)

    def right(self):
        return max(self._start_x, self._end_x)

    def extra(self):
        return 0

    def major_axis(self):
        if abs(self._start_x - self._end_x) > abs(self._start_y - self._end_y):
            return 0  # X-Axis
        else:
            return 1  # Y-Axis

    def x_dir(self):
        if self.normal:
            return 1 if self._start_x < self._end_x else -1
        else:
            return 1 if self._end_x < self._start_x else -1

    def y_dir(self):
        if self.normal:
            return 1 if self._start_y < self._end_y else -1
        else:
            return 1 if self._end_y < self._start_y else -1

    def reverse(self):
        if not self.reversible():
            raise ValueError(
                "Attempting to reverse a cutsegment that does not permit that."
            )
        self.normal = not self.normal

    def generator(self):
        raise NotImplementedError

    def point(self, t):
        raise NotImplementedError

    def contains_burned_groups(self):
        if self.contains is None:
            return False
        for c in self.contains:
            if isinstance(c, list):
                if c.burn_started:
                    return True
            elif c.burns_done == c.passes:
                return True
        return False

    def contains_unburned_groups(self):
        if self.contains is None:
            return False
        for c in self.contains:
            if c.burns_done < c.passes:
                return True
        return False

    def flat(self):
        yield self

    def candidate(self):
        if self.burns_done < self.passes:
            yield self

    def is_burned(self):
        return self.burns_done == self.passes
