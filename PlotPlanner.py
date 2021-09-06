"""
The PlotPlanner simplifies the plotting modifications routines. This works by providing iterables with
plotted coordinates. The input plots can be gapped-positions or adjacent-positions. And the generated output is
controlled by a number of attributes that can be switched on the fly.

* PPI does pulses per inch carry forward with the given power.
* Shift moves isolated single pulses to be adjacent to other pulses.
* Singles gives the output as single positional shifts. Where each position is explicitly generated.
* Groups gives the output as max-length changeless orthogonal/diagonal positions.
* Dot Length requires any train of on values must be of at least the proscribed length.
"""


class PlotPlanner:
    def __init__(self):
        self.single_default = True
        self.single_x = None
        self.single_y = None

        self.ppi_total = 0
        self.ppi_enabled = True
        self.ppi = 1000.0

        self.laser_enabled = True
        self.laser_disabled = False

        self.group_enabled = True
        self.group_x = None
        self.group_y = None
        self.group_on = None
        self.group_dx = 0
        self.group_dy = 0

        self.shift_enabled = False
        self.shift_buffer = []
        self.shift_pixels = 0

        self.dot_length = 1

    def plot(self, plot):
        """
        Process plot values. Iterable plot values

        :param plot:
        :return:
        """
        if plot is None:
            plot = [None]
        for event in plot:
            event = self.process(event)
            for p in event:
                yield p

    def process(self, event):
        """
        Process converts a series of inputs into a series of outputs. There is not a 1:1 input to output conversion.
        Processes can buffer data and return None. Any processes are required to surrender any buffer they have if the
        given sequence ends with, or is None.

        Input sequence are (x, y, on) positions.
        Output sequences are iterables of x, y, on positions.

        :param input: process inputs are started
        :return: output sequences of iterable x, y, on values.
        """
        plot = self.single(event)
        if self.ppi_enabled:
            plot = self.apply_ppi(plot)
        if self.shift_enabled:
            plot = self.shift(plot)
        if self.group_enabled:
            plot = self.group(plot)
        return plot

    def single(self, event):
        """
        Convert a sequence set of positions into single unit plotted sequences.

        :param event:
        :return:
        """
        if event is None:
            return None
        if len(event) == 3:
            x, y, on = event
        else:
            x, y = event
            on = self.single_default
        index = 1
        if self.single_x is None:
            self.single_x = x
            index = 0
        if self.single_y is None:
            self.single_y = y
            index = 0
        if x > self.single_x:
            dx = 1
        elif x < self.single_x:
            dx = -1
        else:
            dx = 0
        if y > self.single_y:
            dy = 1
        elif y < self.single_y:
            dy = -1
        else:
            dy = 0
        total_dx = x - self.single_x
        total_dy = y - self.single_y
        if total_dy * dx != total_dx * dy:
            # TODO: Add in a line draw algorithm here.
            raise ValueError("Must be uniformly diagonal or orthogonal: (%d, %d) is not." % (total_dx, total_dy))
        count = max(abs(total_dx), abs(total_dy)) + 1
        plot = [(self.single_x + (i * dx), self.single_y + (i * dy), on) for i in range(index, count)]
        self.single_x = x
        self.single_y = y
        return plot

    def group(self, plot):
        """
        Converts a generated series of single stepped plots into grouped orthogonal/diagonal plots.

        :param plot: single stepped plots to be grouped into orth/diag sequences.
        :return:
        """
        for event in plot:
            if event is None:
                yield self.group_x, self.group_y, self.group_on
                self.group_dx = 0
                self.group_dy = 0
                return
            x, y, on = event
            if self.group_x is None:
                self.group_x = x
            if self.group_y is None:
                self.group_y = y
            if self.group_on is None:
                self.group_on = on
            if self.group_dx == 0 and self.group_dy == 0:
                self.group_dx = x - self.group_x
                self.group_dy = y - self.group_y
            if self.group_dx != 0 or self.group_dy != 0:
                if x == self.group_x + self.group_dx and y == self.group_y + self.group_dy and on == self.group_on:
                    # This is an orthogonal/diagonal step along the same path.
                    self.group_x = x
                    self.group_y = y
                    continue
            yield self.group_x, self.group_y, self.group_on
            self.group_dx = x - self.group_x
            self.group_dy = y - self.group_y
            if abs(self.group_dx) > 1 or abs(self.group_dy) > 1:
                # The last step was not valid.
                raise ValueError("dx(%d) or dy(%d) exceeds 1" % (self.group_dx, self.group_dy))
            self.group_x = x
            self.group_y = y
            self.group_on = on

    def apply_ppi(self, plot):
        """
        Converts single stepped plots, to apply PPI.

        Implements PPI power modulation.

        :param plot: generator of single stepped plots
        :return:
        """
        if plot is None:
            yield None
            return
        for event in plot:
            if event is None:
                yield None
                return
            x, y, on = event
            self.ppi_total += self.ppi * int(on)
            if self.ppi_total >= 1000.0:
                on = True
                self.ppi_total -= 1000.0
            else:
                on = False
            yield x, y, on

    def shift(self, plot):
        """
        Modulates pixel groups to simplify them into more coherent subsections.
        """
        for event in plot:
            if event is None:
                while len(self.shift_buffer) > 0:
                    self.shift_pixels <<= 1
                    bx, by = self.shift_buffer.pop()
                    bon = (self.shift_pixels >> 3) & 1
                    yield bx, by, bon
                yield None
                return
            x, y, on = event
            self.shift_pixels <<= 1
            if on:
                self.shift_pixels |= 1
            self.shift_pixels &= 0b1111

            self.shift_buffer.insert(0, (x, y))
            if self.shift_pixels == 0b0101:
                self.shift_pixels = 0b0011
            elif self.shift_pixels == 0b1010:
                self.shift_pixels = 0b1100
            if len(self.shift_buffer) >= 4:
                bx, by = self.shift_buffer.pop()
                bon = (self.shift_pixels >> 3) & 1
                yield bx, by, bon
