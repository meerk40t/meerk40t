import random

from meerk40t.tools.zinglplotter import ZinglPlotter

from ..device.basedevice import (
    PLOT_AXIS,
    PLOT_DIRECTION,
    PLOT_FINISH,
    PLOT_JOG,
    PLOT_LEFT_UPPER,
    PLOT_RAPID,
    PLOT_RIGHT_LOWER,
    PLOT_SETTING,
    PLOT_START,
)
from .parameters import Parameters

"""
The PlotPlanner simplifies the plotting and pulsing modifications routines. These are buffered with plottable elements.
These can be submitted as destination graphics commands, or by submitting a plot routine. Which may yield either 2 or
3 value coordinates. These are x, y, and on. Where on is a number between 0 and 1 which designates the on-value. In the
graphics commands the move is given a 0 and all other plots are given a 1. All graphics commands take an optional
on-value. If PPI is enabled, fractional on values are made non-fractional by carrying forward the value of on as a
factor applied of the total value.

All plots are queued and processed in order. This queueing scheme is threadsafe, and should permit one thread reading
the plot values while another thread adds additional items to the queue. If the queue completely empties any processes
being applied to the plot stream are flushed prior to terminating the iterator.

Provided positions can be gapped or single, with adjacent or distant values. The on value is expected to denote whether
the transition from the current position to the new position should be drawn or not. Values that have an initial value
of zero will remain zero.

* Singles converts input into single positional shifts. This must be done to process the plot stream.
* PPI does pulses per inch carry forward with the given value.
* Dot Length requires any train of on-values must be of at least the proscribed length.
* Shift moves isolated single-on values to be adjacent to other on-values.
* Groups manipulates the output as max-length changeless orthogonal/diagonal positions.
"""


class PlotPlanner(Parameters):
    def __init__(
        self,
        settings,
        single=True,
        ppi=True,
        shift=True,
        group=True,
        **kwargs,
    ):
        super().__init__(settings, **kwargs)
        self.debug = False

        self.abort = False
        self.force_shift = False
        self.group_enabled = True  # Grouped Output Required for Lhymicro-gl.
        self.phase_type = 0  # Sequential, random, progressive, static.
        self.phase_value = 0

        self.queue = []

        self.single = None
        self.ppi = None
        self.shift = None
        self.group = None

        if single:
            self.single = Single(self)
        if ppi:
            self.ppi = PPI(self)
        if shift:
            self.shift = Shift(self)
        if group:
            self.group = Group(self)

        self.pos_x = None
        self.pos_y = None
        self.settings_then_jog = False

    def push(self, plot):
        self.abort = False
        self.queue.append(plot)

    def clear(self):
        self.queue.clear()
        self.abort = True

    def gen(self):
        """
        Main method of generating the plot stream.

        The plotplanner emits a series of 3 item values. These are x, y and on. For most plotting
        the values for on is 0 or 1 for off and on respectively. Values for on greater than 0 give
        additional information. This includes an initial jog. Settings change. Major axis. Plot direction.
        left_upper position and right_lower position.

        * If new position is not coincident with previous position
             * If new position is close
                  * Plot line if close within current settings
        * Flush steps from planner if going to new location or using new settings.
             * If new position is far
                  * Send jog if too far away.
        * Send PLOT_SETTING: None, None - if settings have changed.
        * Send PLOT_AXIS: major_axis, None - Major axis is horizontal vs. vertical raster
        * Send PLOT_DIRECTION: x_dir(), y_dir() - Direction X, Direction Y for initial cut.
        * Send PLOT_LEFT_UPPER: left point, upper point - Point at upper left
        * Send PLOT_RIGHT_LOWER: right point, left point - Point at lower right
        * Send all X, Y points for cut.

        If the next position is too far away and jogging is allowed we jog to the position. This
        jog is sent after the previous data is flushed out of the planner.

        cut.settings can be the same object between different cut.

        @return:
        """
        self.pos_x = None
        self.pos_y = None
        while len(self.queue):
            cut = self.queue.pop(0)
            start = cut.start
            new_start_x = start[0]
            new_start_y = start[1]
            assert isinstance(new_start_x, int)
            assert isinstance(new_start_y, int)
            flush = False
            jog = 0
            if self.pos_x != new_start_x or self.pos_y != new_start_y:
                # This location is disjointed. We must flush and jog.
                # Jog is executed in current settings.
                if (
                    self.pos_x is None
                    or self.raster_step_x != 0
                    or self.raster_step_y != 0
                ):
                    # First movement or raster_step exists we must rapid_jog.
                    # Request rapid move new location
                    flush = True
                    jog |= PLOT_RAPID
                else:
                    # Slow Jog to position.
                    distance = self.jog_distance
                    if (
                        abs(self.pos_x - new_start_x) < distance
                        and abs(self.pos_y - new_start_y) < distance
                    ) or not self.jog_enable:
                        # Jog distance smaller than threshold. Or jog isn't allowed
                        def walk():
                            for event in ZinglPlotter.plot_line(
                                self.pos_x, self.pos_y, new_start_x, new_start_y
                            ):
                                yield event[0], event[1], 0

                        yield from self.process_plots(walk())
                    else:
                        # Request standard jog new location required.
                        flush = True
                        jog |= PLOT_JOG

            # Laser Setting has changed, we must flush the buffer.
            if cut.settings is not self.settings:
                flush = True

            # Flush executed in current settings.
            if flush:  # Flush if needed.
                yield from self.flush()
                self.pos_x = self.single.single_x
                self.pos_y = self.single.single_y

            # Jog was needed.
            if self.settings_then_jog:
                if cut.settings is not self.settings:
                    self.settings = cut.settings
                    yield None, None, PLOT_SETTING

                if jog:
                    yield new_start_x, new_start_y, jog
                    self.warp(new_start_x, new_start_y)
            else:
                if jog:
                    yield new_start_x, new_start_y, jog
                    self.warp(new_start_x, new_start_y)

                if cut.settings is not self.settings:
                    self.settings = cut.settings
                    yield None, None, PLOT_SETTING

            if jog or self.raster_step_x != 0 or self.raster_step_y != 0:
                # set the directions. Post Jog, Post Settings.
                yield cut.major_axis(), None, PLOT_AXIS
                yield cut.x_dir(), cut.y_dir(), PLOT_DIRECTION
                yield cut.left(), cut.upper(), PLOT_LEFT_UPPER
                yield cut.right(), cut.lower(), PLOT_RIGHT_LOWER

            # Plot the current.
            # Current is executed in cut settings.
            yield None, None, PLOT_START
            yield from self.process_plots(cut.generator())
            self.pos_x = self.single.single_x
            self.pos_y = self.single.single_y

        if not self.abort:
            # If we were not aborted, flush and finish the last positions.
            yield from self.flush()
            self.pos_x = self.single.single_x
            self.pos_y = self.single.single_y

        self.reset()
        self.abort = False
        yield None, None, PLOT_FINISH

    def process_plots(self, plot):
        """
        Converts a series of inputs into a series of outputs. There is not a 1:1 input to output conversion.
        Processes can buffer data and return None. Processes are required to surrender any buffer they have if the
        given sequence ends with, or is None. This flushes out any data.

        If an input sequence still lacks an on-value then the single_default value will be utilized.
        Output sequences are iterables of x, y, on positions.

        @param plot: plottable element that should be wrapped
        @return: generator to produce plottable elements.
        """

        def debug(plot, manipulator):
            for q in plot:
                print(f"Manipulator: {str(q)}, {str(manipulator)}")
                yield q

        if self.single is not None:
            plot = self.single.process(plot)
        if self.debug:
            plot = debug(plot, self.single)
        if self.ppi is not None:
            plot = self.ppi.process(plot)
        if self.debug:
            plot = debug(plot, self.ppi)
        if self.shift is not None:
            plot = self.shift.process(plot)
        if self.debug:
            plot = debug(plot, self.shift)
        if self.group is not None:
            plot = self.group.process(plot)
        if self.debug:
            plot = debug(plot, self.group)
        return plot

    def step_move(self, x0, y0, x1, y1):
        """
        Step move walks a line from a point to another point.
        """
        for event in ZinglPlotter.plot_line(x0, y0, x1, y1):
            yield event[0], event[1], 0
        self.pos_x = x1
        self.pos_y = y1

    def flush(self):
        if self.debug:
            print("Flushing PlotPlanner")
        yield from self.process_plots(None)

    def warp(self, x, y):
        self.pos_x = x
        self.pos_y = y
        if self.single:
            self.single.warp(x, y)
        if self.ppi:
            self.ppi.warp(x, y)
        if self.shift:
            self.shift.warp(x, y)
        if self.group:
            self.group.warp(x, y)

    def reset(self):
        if self.single:
            self.single.clear()
        if self.shift:
            self.shift.clear()
        if self.ppi:
            self.ppi.clear()
        if self.group:
            self.group.clear()


class PlotManipulation:
    def __init__(self, planner: PlotPlanner):
        self.planner = planner

    def process(self, plot):
        pass

    def flush(self):
        pass

    def warp(self, x, y):
        pass

    def clear(self):
        pass

    def flushed(self):
        return True


class Single(PlotManipulation):
    def __init__(self, planner: PlotPlanner):
        super().__init__(planner)
        self.single_default = 1
        self.single_x = None
        self.single_y = None

    def __str__(self):
        return f"{self.__class__.__name__}({str(self.single_x)},{str(self.single_y)})"

    def process(self, plot):
        """
        Convert a sequence set of positions into single unit plotted sequences.

        This accepts 3 (X,Y,On) or 2 (X,Y) item events

        single_default sets the default for any unmarked processes.
        single_x sets the last known x position this routine has encountered.
        single_y sets the last known y position this routine has encountered.

        @param plot: plot generator
        @return:
        """
        if plot is None:
            # None calls for a flush routine.
            yield from self.flush()
            return
        for event in plot:
            x = event[0]
            y = event[1]
            if self.single_x is None or self.single_y is None:
                # Our single_x or single_y position is not established.
                self.single_x = x
                self.single_y = y
            on = event[2] if len(event) >= 3 else self.single_default

            total_dx = x - self.single_x
            total_dy = y - self.single_y
            if total_dx == 0 and total_dy == 0:
                continue
            dx = 1 if total_dx > 0 else 0 if total_dx == 0 else -1
            dy = 1 if total_dy > 0 else 0 if total_dy == 0 else -1

            if total_dy * dx != total_dx * dy:
                # Check for cross-equality.
                raise ValueError(
                    f"Must be uniformly diagonal or orthogonal: ({total_dx}, {total_dy}) is not."
                )
            cx = self.single_x
            cy = self.single_y
            for i in range(1, max(abs(total_dx), abs(total_dy)) + 1):
                if self.planner.abort:
                    self.single_x = None
                    self.single_y = None
                    return
                self.single_x = cx + (i * dx)
                self.single_y = cy + (i * dy)
                yield self.single_x, self.single_y, on

    def flush(self):
        yield None, None, self.single_default

    def warp(self, x, y):
        self.single_x = x
        self.single_y = y

    def clear(self):
        self.single_x = None
        self.single_y = None


class PPI(PlotManipulation):
    def __init__(self, planner: PlotPlanner):
        super().__init__(planner)
        self.ppi_total = 0
        self.dot_left = 0

    def __str__(self):
        return f"{self.__class__.__name__}({str(self.ppi_total)},{str(self.dot_left)})"

    def process(self, plot):
        """
        Converts single stepped plots, to apply PPI.

        Implements PPI power modulation.

        @param plot: generator of single stepped plots, with PPI.
        @return:
        """
        px = None
        py = None
        for x, y, on in plot:
            if x is None or y is None:
                yield x, y, on
                continue
            if px is not None and py is not None:
                assert abs(px - x) <= 1 or abs(py - y) <= 1
            px = x
            py = y
            # PPI is always on.
            self.ppi_total += self.planner.power * on
            if on and self.dot_left > 0:
                # Process remaining dot_length, must be on or partially on.
                self.dot_left -= 1
                on = 1
            else:
                # No dot length.
                if self.ppi_total >= 1000.0:
                    # PPI >= 1000: triggers on.
                    on = 1
                    self.ppi_total -= 1000.0 * self.planner.implicit_dotlength
                    self.dot_left = self.planner.implicit_dotlength - 1
                else:
                    # PPI < 1000: triggers off.
                    on = 0
            yield x, y, on


class Shift(PlotManipulation):
    def __init__(self, planner: PlotPlanner):
        super().__init__(planner)
        self.shift_buffer = []
        self.shift_pixels = 0

    def __str__(self):
        return f"{self.__class__.__name__}({str(self.shift_buffer)},{bin(self.shift_pixels)})"

    def process(self, plot):
        """
        Tweaks on-values to simplify them into more coherent subsections.

        This code requires a buffer of 4 path plots.

        @param plot: generator of single stepped plots
        @return:
        """
        for x, y, on in plot:
            if (x is None or y is None) or (
                not self.planner.force_shift and not self.planner.shift_enabled
            ):
                # If we have an established buffer, flush the buffer.
                yield from self.flush()
                # Yield the current event.
                yield x, y, on
                continue

            # Shift() is on.
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
                # When buffer is full start popping off values.
                bx, by = self.shift_buffer.pop()
                bon = (self.shift_pixels >> 3) & 1
                yield bx, by, bon
        # There are no more plots.

    def flush(self):
        while len(self.shift_buffer) > 0:
            self.shift_pixels <<= 1
            bx, by = self.shift_buffer.pop()
            bon = (self.shift_pixels >> 3) & 1
            yield bx, by, bon
        self.clear()

    def flushed(self):
        return not len(self.shift_buffer)

    def warp(self, x, y):
        self.clear()

    def clear(self):
        self.shift_pixels = 0
        self.shift_buffer.clear()


class Group(PlotManipulation):
    def __init__(self, planner: PlotPlanner):
        super().__init__(planner)
        self.last_x = None
        self.last_y = None
        self.last_on = None

        self.group_x = None
        self.group_y = None
        self.group_on = None

        self.group_dx = 0
        self.group_dy = 0

    def __str__(self):
        return f"{self.__class__.__name__}({str(self.group_x)},{str(self.group_y)},{str(self.group_dx)},{str(self.group_dy)})"

    def flushed(self):
        return (
            self.last_x == self.group_x
            and self.last_y == self.group_y
            and self.last_on == self.group_on
        )

    def process(self, plot):
        """
        Converts a generated series of single stepped plots into grouped orthogonal/diagonal plots.

        group_x, group_y: is the last known inputted. This is not necessarily the current position given by the planner.
        If group_dx and group_dy are not zero, then we have buffered a move.

        @param plot: single stepped plots to be grouped into orth/diag sequences.
        @return:
        """
        px = None
        py = None
        for x, y, on in plot:
            if x is None or y is None:
                yield from self.flush()
                continue
            if px is not None and py is not None:
                assert abs(px - x) <= 1 or abs(py - y) <= 1
            px = x
            py = y
            if not self.planner.group_enabled:
                yield from self.flush()
                # Yield the current event.
                self.last_x = x
                self.last_y = y
                self.last_on = on
                yield x, y, on
                continue
            # Group() is enabled
            if self.group_x is None:
                self.group_x = x
            if self.group_y is None:
                self.group_y = y
            if self.group_on is None:
                self.group_on = on
            if self.group_dx != 0 or self.group_dy != 0:
                if (
                    x == self.group_x + self.group_dx
                    and y == self.group_y + self.group_dy
                    and on == self.group_on
                ):
                    # This is an orthogonal/diagonal step along the same path.
                    self.group_x = x
                    self.group_y = y
                    # Mark the latest position and continue.
                    continue
                # This is non orth-diag point. Must drop a point.
                self.last_x = self.group_x
                self.last_y = self.group_y
                self.last_on = self.group_on
                yield self.group_x, self.group_y, self.group_on
            # If we do not have a defined direction, set our current direction.
            self.group_dx = x - self.group_x
            self.group_dy = y - self.group_y
            if abs(self.group_dx) > 1 or abs(self.group_dy) > 1:
                # The last step was not valid. Group() requires single step values.
                raise ValueError(
                    f"dx({self.group_dx}) or dy({self.group_dy}) exceeds 1"
                )
            # Save our buffered position.
            self.group_x = x
            self.group_y = y
            self.group_on = on
        # There are no more plots.

    def flush(self):
        if not self.flushed():
            # If we have an established buffer, flush the buffer.
            self.group_dx = 0
            self.group_dy = 0
            self.last_x = self.group_x
            self.last_y = self.group_y
            self.last_on = self.group_on
            if self.group_x is not None and self.group_y is not None:
                yield self.group_x, self.group_y, self.group_on

    def warp(self, x, y):
        self.group_x = x
        self.group_y = y
        self.group_dx = 0
        self.group_dy = 0
        self.last_x = x
        self.last_y = y

    def clear(self):
        self.group_x = None
        self.group_y = None
        self.group_dx = 0
        self.group_dy = 0


def grouped(plot):
    """
    Converts a generated series of single stepped plots into grouped orthogonal/diagonal plots.

    @param plot: single stepped plots to be grouped into orth/diag sequences.
    @return:
    """
    group_x = None
    group_y = None
    group_dx = 0
    group_dy = 0

    for x, y in plot:
        if group_x is None:
            group_x = x
        if group_y is None:
            group_y = y
        if x == group_x + group_dx and y == group_y + group_dy:
            # This is an orthogonal/diagonal step along the same path.
            group_x = x
            group_y = y
            continue
        # This is non orth-diag point. Must drop a point.
        yield group_x, group_y
        # If we do not have a defined direction, set our current direction.
        group_dx = x - group_x
        group_dy = y - group_y
        if abs(group_dx) > 1 or abs(group_dy) > 1:
            # The last step was not valid.
            raise ValueError(f"dx({group_dx}) or dy({group_dy}) exceeds 1")
        group_x = x
        group_y = y
    # There are no more plots.
    yield group_x, group_y
