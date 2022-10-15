from abc import ABC
from typing import Optional

from ..svgelements import Color, Path, Point
from ..tools.rasterplotter import RasterPlotter
from ..tools.zinglplotter import ZinglPlotter
from .parameters import Parameters

"""
Cutcode is a list of cut objects. These are line, quad, cubic, arc, and raster. And anything else that should be
considered a laser primitive. These are disjointed objects. If the distance between one and the next exist the laser
should be toggled and move by anything executing these in the planning process. Various other laser-file types should
be converted into cut code. This should be the parsed form of file-blobs. Cutcode can convert easily to both SVG and
to LaserCode.

All CutObjects have a .start .end and .generator() functions. They also have a settings object that contains all
properties for that cuts may need or use. Or which may be used by the CutPlanner, PlotPlanner, or local objects. These
are references to settings which may be shared by all CutObjects created by a LaserOperation.
"""


class CutObject(Parameters):
    """
    CutObjects are small vector cuts which have on them a laser settings object.
    These store the start and end point of the cut. Whether this cut is normal or
    reversed.
    """

    def __init__(
        self, start=None, end=None, settings=None, parent=None, passes=1, **kwargs
    ):
        super().__init__(settings)
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
        self.parent = parent
        self.next = None
        self.previous = None
        self.passes = passes
        if passes != 1:
            # If passes is greater than 1 we must flag custom passes as on.
            self.passes_custom = True
        self._burns_done = 0

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
            if isinstance(c, CutGroup):
                if c.burn_started:
                    return True
            elif c.burns_done == c.implicit_passes:
                return True
        return False

    def contains_unburned_groups(self):
        if self.contains is None:
            return False
        for c in self.contains:
            if c.burns_done < c.implicit_passes:
                return True
        return False

    def flat(self):
        yield self

    def candidate(self):
        if self.burns_done < self.implicit_passes:
            yield self

    def is_burned(self):
        return self.burns_done == self.implicit_passes


class CutGroup(list, CutObject, ABC):
    """
    CutGroups are group container CutObject. They are used to group objects together such as
    to maintain the relationship between within a closed path object.
    """

    def __init__(
        self,
        parent,
        children=(),
        settings=None,
        passes=1,
        constrained=False,
        closed=False,
    ):
        list.__init__(self, children)
        CutObject.__init__(self, parent=parent, settings=settings, passes=passes)
        self.closed = closed
        self.constrained = constrained
        self.burn_started = False

    def __copy__(self):
        return CutGroup(self.parent, self)

    def __str__(self):
        return f"CutGroup(children={list.__str__(self)}, parent={str(self.parent)})"

    def __repr__(self):
        return f"CutGroup(children={list.__repr__(self)}, parent={str(self.parent)})"

    def reversible(self):
        return False

    def reverse(self):
        pass

    @property
    def start(self):
        if self._start_x is not None and self._start_y is not None:
            return self._start_x, self._start_y
        if len(self) == 0:
            return None
        # handle group normal/reverse - start and end already handle segment reverse
        return self[0].start if self.normal else self[-1].end

    @property
    def end(self):
        if len(self) == 0:
            return None
        # handle group normal/reverse - start and end already handle segment reverse
        return self[-1].end if self.normal else self[0].start

    def flat(self):
        """
        Flat list of cut objects with a depth first search.
        """
        for c in self:
            if not isinstance(c, CutGroup):
                yield c
                continue
            for s in c.flat():
                yield s

    def candidate(
        self,
        complete_path: Optional[bool] = False,
        grouped_inner: Optional[bool] = False,
    ):
        """
        Candidates are CutObjects:
        1. That do not contain one or more unburned inner constrained cutcode objects.
        2. With Group Inner Burns, containing object is a candidate only if:
            a. It already has one containing object already burned; or
            b. There are no containing objects with at least one inner element burned.
        3. With burns done < passes (> 1 only if merge passes)
        4. With Burn Complete Paths on and non-closed subpath, only first and last segments of the subpath else all segments
        """
        candidates = list(self)
        if grouped_inner:
            # Create list of exactly those groups which are:
            #   a.  Unburned; and either
            #   b1. Inside an outer which has at least one inner burned; or
            #   b2. An outer which has all inner burned.
            # by removing from the list:
            #   1. Candidates already burned
            #   2. Candidates which are neither inner nor outer
            #   3. Candidates which are outer and have at least one inner not yet burned
            #   4. Candidates which are inner and all outers have no inners burned
            # If the resulting list is empty then normal rules apply instead.
            for grp in self:
                if (
                    grp.is_burned()
                    or (grp.contains is None and grp.inside is None)
                    or (grp.contains is not None and grp.contains_unburned_groups())
                ):
                    candidates.remove(grp)
                    continue
                if grp.inside is not None:
                    for outer in grp.inside:
                        if outer.contains_burned_groups():
                            break
                    else:
                        candidates.remove(grp)
            if len(candidates) == 0:
                candidates = list(self)

        for grp in candidates:
            # Do not burn this CutGroup if it contains unburned groups
            # Contains is only set when Cut Inner First is set, so this
            # so when not set this does nothing.
            if grp.contains_unburned_groups():
                continue
            # If we are only burning complete subpaths then
            # if this is not a closed path we should only yield first and last segments
            # Planner will need to determine which end of the subpath is yielded
            # and only consider the direction starting from the end
            if complete_path and not grp.closed and isinstance(grp, CutGroup):
                if grp[0].burns_done < grp[0].implicit_passes:
                    yield grp[0]
                # Do not yield same segment a 2nd time if only one segment
                if len(grp) > 1 and grp[-1].burns_done < grp[-1].implicit_passes:
                    yield grp[-1]
                continue
            # If we are either burning any path segment
            # or this is a closed path
            # then we should yield all segments.
            for seg in grp.flat():
                if seg is not None and seg.burns_done < seg.implicit_passes:
                    yield seg


class CutCode(CutGroup):
    def __init__(self, seq=(), settings=None):
        CutGroup.__init__(self, None, seq, settings=settings)
        self.output = True
        self.mode = None

    def __str__(self):
        parts = list()
        if len(self) <= 3:
            parts.extend([type(p).__name__ for p in self])
        else:
            parts.append(f"{len(self)} items")
        return f"CutCode({', '.join(parts)})"

    def __copy__(self):
        return CutCode(self)

    def as_elements(self):
        last = None
        path = None
        previous_settings = None
        for e in self.flat():
            start = e.start
            end = e.end
            if path is None:
                path = Path()
                c = e.line_color if e.line_color is not None else "blue"
                path.stroke = Color(c)

            if len(path) == 0 or last[0] != start[0] or last[1] != start[1]:
                path.move(e.start)
            if isinstance(e, LineCut):
                path.line(end)
            elif isinstance(e, QuadCut):
                path.quad(e.c(), end)
            elif isinstance(e, CubicCut):
                path.quad(e.c1(), e.c2(), end)
            elif isinstance(e, RawCut):
                for x, y, laser in e.plot:
                    if laser:
                        path.line((x, y))
                    else:
                        path.move((x, y))
            elif isinstance(e, PlotCut):
                for x, y, laser in e.plot:
                    if laser:
                        path.line((x, y))
                    else:
                        path.move((x, y))
            if previous_settings is not e.settings and previous_settings is not None:
                if path is not None and len(path) != 0:
                    yield path
                    path = None
            previous_settings = e.settings
            last = end
        if path is not None and len(path) != 0:
            yield path

    def cross(self, j, k):
        """
        Reverses subpaths flipping the individual elements from position j inclusive to
        k exclusive.

        @param j:
        @param k:
        @return:
        """
        for q in range(j, k):
            self[q].direct_close()
            self[q].reverse()
        self[j:k] = self[j:k][::-1]

    def generate(self):
        for cutobject in self.flat():
            yield "plot", cutobject
        yield "plot_start"

    def length_travel(self, include_start=False, stop_at=-1):
        """
        Calculates the distance traveled between cutcode objects.

        @param include_start: should the distance include the start
        @param stop_at: stop position
        @return:
        """
        cutcode = list(self.flat())
        if len(cutcode) == 0:
            return 0
        if stop_at < 0:
            stop_at = len(cutcode)
        if stop_at > len(cutcode):
            stop_at = len(cutcode)
        distance = 0
        if include_start:
            if self.start is not None:
                distance += abs(complex(*self.start) - complex(*cutcode[0].start))
            else:
                distance += abs(0 - complex(*cutcode[0].start))
        for i in range(1, stop_at):
            prev = cutcode[i - 1]
            curr = cutcode[i]
            delta = Point.distance(prev.end, curr.start)
            distance += delta
        return distance

    def length_cut(self, stop_at=-1):
        """
        Calculated the length of the cutcode code distance.

        @param stop_at: stop index
        @return:
        """
        cutcode = list(self.flat())
        distance = 0
        if stop_at < 0:
            stop_at = len(cutcode)
        if stop_at > len(cutcode):
            stop_at = len(cutcode)
        for i in range(0, stop_at):
            curr = cutcode[i]
            distance += curr.length()
        return distance

    def extra_time(self, stop_at=-1):
        """
        Raw calculation of extra time within this cutcode objects.

        @param stop_at:
        @return:
        """
        cutcode = list(self.flat())
        extra = 0
        if stop_at < 0:
            stop_at = len(cutcode)
        if stop_at > len(cutcode):
            stop_at = len(cutcode)
        for i in range(0, stop_at):
            current = cutcode[i]
            extra += current.extra()
        return extra

    def duration_cut(self, stop_at=None):
        """
        Time taken to cut this cutcode object. Since objects can cut at different speed each individual object
        speed is taken into account.

        @param stop_at: stop index
        @return:
        """
        cutcode = list(self.flat())
        duration = 0
        if stop_at is None:
            stop_at = len(cutcode)
        if stop_at > len(cutcode):
            stop_at = len(cutcode)
        for current in cutcode[0:stop_at]:
            native_speed = current.settings.get("native_speed", current.speed)
            if native_speed != 0:
                duration += current.length() / native_speed
        return duration

    def _native_speed(self, cutcode):
        if cutcode:
            for current in cutcode:
                native_speed = current.settings.get(
                    "native_rapid_speed",
                    current.settings.get("native_speed", None),
                )
                if native_speed is not None:
                    return native_speed
        # No element had a rapid speed value.
        native_speed = self.settings.get(
            "native_rapid_speed", self.settings.get("native_speed", None)
        )
        return native_speed

    def duration_travel(self, stop_at=None):
        """
        Duration of travel time taken within the cutcode.

        @param stop_at: stop index
        @return:
        """
        travel = self.length_travel()
        cutcode = list(self.flat())
        rapid_speed = self._native_speed(cutcode)
        if rapid_speed is None:
            return 0
        return travel / rapid_speed

    @classmethod
    def from_lasercode(cls, lasercode):
        cutcode = cls()
        x = 0
        y = 0
        settings = dict()
        for code in lasercode:
            if isinstance(code, int):
                cmd = code
            elif isinstance(code, (tuple, list)):
                cmd = code[0]
            else:
                continue
            if cmd == "plot":
                cutcode.extend(code[1])
            elif cmd == "move_rel":
                nx = code[1]
                ny = code[2]
                nx = x + nx
                ny = y + ny
                x = nx
                y = ny
            elif cmd == "move_ori":
                nx = code[1]
                ny = code[2]
                x = nx
                y = ny
            elif cmd == "move_abs":
                nx = code[1]
                ny = code[2]
                x = nx
                y = ny
            elif cmd == "home":
                x = 0
                y = 0
            elif cmd == "cut_abs":
                nx = code[1]
                ny = code[2]
                cut = LineCut(Point(x, y), Point(nx, ny), settings=settings)
                cutcode.append(cut)
                x = nx
                y = ny
            elif cmd == "cut_rel":
                nx = code[1]
                ny = code[2]
                nx = x + nx
                ny = y + ny
                cut = LineCut(Point(x, y), Point(nx, ny), settings=settings)
                cutcode.append(cut)
                x = nx
                y = ny
            elif cmd == "dwell":
                time = code[1]
                cut = DwellCut((x, y), time)
                cutcode.append(cut)

        return cutcode

    def reordered(self, order):
        """
        Reorder the cutcode based on the given order.

        Negative numbers are taken to mean these are inverted with ~ and reversed.

        @param order: order indexed of new positions
        @return:
        """
        reordered = list()
        for pos in order:
            try:
                if pos < 0:
                    pos = ~pos
                    self[pos].reverse()
            except ValueError:
                pass  # May not reverse a segment that does not permit reversal.
            try:
                reordered.append(self[pos])
            except IndexError:
                pass
        self.clear()
        self.extend(reordered)


class LineCut(CutObject):
    def __init__(self, start_point, end_point, settings=None, passes=1, parent=None):
        CutObject.__init__(
            self,
            start_point,
            end_point,
            settings=settings,
            passes=passes,
            parent=parent,
        )
        self.raster_step = 0

    def __repr__(self):
        return f'LineCut({repr(self.start)}, {repr(self.end)}, settings="{self.settings}", passes={self.implicit_passes})'

    def generator(self):
        # pylint: disable=unsubscriptable-object
        start = self.start
        end = self.end
        return ZinglPlotter.plot_line(start[0], start[1], end[0], end[1])

    def point(self, t):
        x0, y0 = self.start
        x1, y1 = self.end
        x = x1 * t + x0
        y = y1 * t + y0
        return x, y


class QuadCut(CutObject):
    def __init__(
        self,
        start_point,
        control_point,
        end_point,
        settings=None,
        passes=1,
        parent=None,
    ):
        CutObject.__init__(
            self,
            start_point,
            end_point,
            settings=settings,
            passes=passes,
            parent=parent,
        )
        self.raster_step = 0
        self._control = control_point

    def __repr__(self):
        return f'QuadCut({repr(self.start)}, {repr(self.c())}, {repr(self.end)}, settings="{self.settings}", passes={self.implicit_passes})'

    def __str__(self):
        return f"QuadCut({repr(self.start)}, {repr(self.c())}, {repr(self.end)}, passes={self.implicit_passes})"

    def c(self):
        return self._control

    def length(self):
        return Point.distance(self.start, self.c()) + Point.distance(self.c(), self.end)

    def generator(self):
        # pylint: disable=unsubscriptable-object
        start = self.start
        c = self.c()
        end = self.end
        return ZinglPlotter.plot_quad_bezier(
            start[0],
            start[1],
            c[0],
            c[1],
            end[0],
            end[1],
        )

    def point(self, t):
        x0, y0 = self.start
        x1, y1 = self.c()
        x2, y2 = self.end
        e = 1 - t
        x = e * e * x0 + 2 * e * t * x1 + t * t * x2
        y = e * e * y0 + 2 * e * t * y1 + t * t * y2
        return x, y


class CubicCut(CutObject):
    def __init__(
        self,
        start_point,
        control1,
        control2,
        end_point,
        settings=None,
        passes=1,
        parent=None,
    ):
        CutObject.__init__(
            self,
            start_point,
            end_point,
            settings=settings,
            passes=passes,
            parent=parent,
        )
        self.raster_step = 0
        self._control1 = control1
        self._control2 = control2

    def __repr__(self):
        return f'CubicCut({repr(self.start)}, {repr(self.c1())},  {repr(self.c2())}, {repr(self.end)}, settings="{self.settings}", passes={self.implicit_passes})'

    def __str__(self):
        return f"CubicCut({repr(self.start)}, {repr(self.c1())},  {repr(self.c2())}, {repr(self.end)}, passes={self.implicit_passes})"

    def c1(self):
        return self._control1 if self.normal else self._control2

    def c2(self):
        return self._control2 if self.normal else self._control1

    def length(self):
        return (
            Point.distance(self.start, self.c1())
            + Point.distance(self.c1(), self.c2())
            + Point.distance(self.c2(), self.end)
        )

    def generator(self):
        start = self.start
        c1 = self.c1()
        c2 = self.c2()
        end = self.end
        return ZinglPlotter.plot_cubic_bezier(
            start[0],
            start[1],
            c1[0],
            c1[1],
            c2[0],
            c2[1],
            end[0],
            end[1],
        )

    def point(self, t):
        x0, y0 = self.start
        x1, y1 = self.c1()
        x2, y2 = self.c2()
        x3, y3 = self.end
        e = 1 - t
        x = e * e * e * x0 + 3 * e * e * t * x1 + 3 * e * t * t * x2 + t * t * t * x3
        y = e * e * e * y0 + 3 * e * e * t * y1 + 3 * e * t * t * y2 + t * t * t * y3
        return x, y


class RasterCut(CutObject):
    """
    Rastercut accepts an image of type "L" or "1", and an offset in the x and y.
    """

    def __init__(
        self,
        image,
        offset_x,
        offset_y,
        step_x,
        step_y,
        inverted=False,
        bidirectional=True,
        horizontal=True,
        start_on_top=True,
        start_on_left=True,
        overscan=0,
        settings=None,
        passes=1,
        parent=None,
    ):
        CutObject.__init__(self, settings=settings, passes=passes, parent=parent)
        assert image.mode in ("L", "1")
        self.first = True  # Raster cuts are always first within themselves.
        self.image = image
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.step_x = step_x
        self.step_y = step_y
        self.bidirectional = bidirectional
        self.horizontal = horizontal
        self.start_on_top = start_on_top
        self.start_on_left = start_on_left
        self.width, self.height = image.size
        self.inverted = inverted
        self.scan = overscan
        if inverted:
            skip_pixel = 255

            def image_filter(pixel):
                return pixel / 255.0

        else:
            skip_pixel = 0

            def image_filter(pixel):
                return (255 - pixel) / 255.0

        self.plot = RasterPlotter(
            data=image.load(),
            width=self.width,
            height=self.height,
            horizontal=self.horizontal,
            start_on_top=self.start_on_top,
            start_on_left=self.start_on_left,
            bidirectional=self.bidirectional,
            skip_pixel=skip_pixel,
            overscan=self.scan,
            offset_x=self.offset_x,
            offset_y=self.offset_y,
            step_x=self.step_x,
            step_y=self.step_y,
            filter=image_filter,
        )

    def reversible(self):
        return False

    def reverse(self):
        pass

    @property
    def start(self):
        return self.plot.initial_position_in_scene()

    @property
    def end(self):
        return self.plot.final_position_in_scene()

    def lower(self):
        return self.plot.offset_y + self.height

    def upper(self):
        return self.plot.offset_y

    def right(self):
        return self.plot.offset_x + self.width

    def left(self):
        return self.plot.offset_x

    def length(self):
        return (
            self.width * self.height
            + (self.overscan * self.height)
            + (self.height * self.raster_step_y)
        )

    def extra(self):
        return self.width * 0.105  # 105ms for the turnaround.

    def major_axis(self):
        return 0 if self.plot.horizontal else 1

    def x_dir(self):
        return 1 if self.plot.start_on_left else -1

    def y_dir(self):
        return 1 if self.plot.start_on_top else -1

    def generator(self):
        return self.plot.plot()


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


class DwellCut(CutObject):
    def __init__(self, start_point, settings=None, passes=1, parent=None):
        CutObject.__init__(
            self,
            start_point,
            start_point,
            settings=settings,
            passes=passes,
            parent=parent,
        )
        self.first = True  # Dwell cuts are standalone
        self.last = True
        self.raster_step = 0

    def reversible(self):
        return False

    def reverse(self):
        pass

    def generate(self):
        yield "rapid_mode"
        start = self.start
        yield "move_abs", start[0], start[1]
        yield "dwell", self.dwell_time


class WaitCut(CutObject):
    def __init__(self, wait, settings=None, passes=1, parent=None):
        """
        Establish a wait cut.
        @param wait: wait time in ms.
        @param settings: Settings for wait cut.
        @param passes: Number of passes.
        @param parent: CutObject parent.
        """
        CutObject.__init__(
            self,
            (0, 0),
            (0, 0),
            settings=settings,
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


class HomeCut(CutObject):
    def __init__(self, offset_point=None, settings=None, passes=1, parent=None):
        if offset_point is None:
            offset_point = (0, 0)
        CutObject.__init__(
            self,
            offset_point,
            offset_point,
            settings=settings,
            passes=passes,
            parent=parent,
        )
        self.first = True  # Dwell cuts are standalone
        self.last = True
        self.raster_step = 0

    def reversible(self):
        return False

    def reverse(self):
        pass

    def generate(self):
        yield "home"


class GotoCut(CutObject):
    def __init__(self, offset_point=None, settings=None, passes=1, parent=None):
        if offset_point is None:
            offset_point = (0, 0)
        CutObject.__init__(
            self,
            offset_point,
            offset_point,
            settings=settings,
            passes=passes,
            parent=parent,
        )
        self.first = True  # Dwell cuts are standalone
        self.last = True
        self.raster_step = 0

    def reversible(self):
        return False

    def reverse(self):
        pass

    def generate(self):
        yield "move_ori", self._start_x, self._start_y


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


class OutputCut(CutObject):
    def __init__(
        self,
        output_mask,
        output_value,
        output_message=None,
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


class PlotCut(CutObject):
    """
    Plot cuts are a series of lineto values with laser on and off info. These positions are not necessarily next
    to each other and can be any distance apart. This is a compact way of writing a large series of line positions.

    There is a raster-create value.
    """

    def __init__(self, settings=None, passes=1):
        CutObject.__init__(self, settings=settings, passes=passes)
        self.plot = []
        self.max_dx = None
        self.max_dy = None
        self.min_x = None
        self.min_y = None
        self.max_x = None
        self.max_y = None
        self.v_raster = False
        self.h_raster = False
        self.travels_top = False
        self.travels_bottom = False
        self.travels_right = False
        self.travels_left = False
        self._calc_lengths = None
        self._length = None
        self.first = True  # Plot cuts are standalone
        self.last = True

    def __len__(self):
        return len(self.plot)

    def __str__(self):
        parts = list()
        parts.append(f"{len(self.plot)} points")
        parts.append(f"xmin: {self.min_x}")
        parts.append(f"ymin: {self.min_y}")
        parts.append(f"xmax: {self.max_x}")
        parts.append(f"ymax: {self.max_y}")
        return f"PlotCut({', '.join(parts)})"

    def check_if_rasterable(self):
        """
        Rasterable plotcuts are heuristically defined as having a max step of less than 15 and
        must have an unused travel direction.

        @return: whether the plot can travel
        """
        # Default to vector settings.
        self.settings["_raster_alt"] = False
        self.settings["_constant_move_x"] = False
        self.settings["_constant_move_y"] = False
        self.settings["raster_step"] = 0
        if self.settings.get("speed", 0) < 80:
            # Twitchless gets sketchy at 80.
            self.settings["_force_twitchless"] = True
            return False
            # if self.max_dy >= 15 and self.max_dy >= 15:
            #     return False  # This is probably a vector.
        if self.max_dx is None:
            return False
        if self.max_dy is None:
            return False
        # Above 80 we're likely dealing with a raster.
        if 0 < self.max_dx <= 15:
            self.v_raster = True
            self.settings["_constant_move_y"] = True
        if 0 < self.max_dy <= 15:
            self.h_raster = True
            self.settings["_constant_move_x"] = True
        # if self.vertical_raster or self.horizontal_raster:
        self.settings["raster_step"] = min(self.max_dx, self.max_dy)
        self.settings["_raster_alt"] = True
        return True

    def plot_extend(self, plot):
        for x, y, laser in plot:
            self.plot_append(x, y, laser)

    def plot_append(self, x, y, laser):
        self._length = None
        self._calc_lengths = None
        if self.plot:
            last_x, last_y, last_laser = self.plot[-1]
            dx = x - last_x
            dy = y - last_y
            if self.max_dx is None or abs(dx) > self.max_dx:
                self.max_dx = abs(dx)
            if self.max_dy is None or abs(dy) > self.max_dy:
                self.max_dy = abs(dy)
            if dy > 0:
                self.travels_bottom = True
            if dy < 0:
                self.travels_top = True
            if dx > 0:
                self.travels_right = True
            if dx < 0:
                self.travels_left = True

        self.plot.append((x, y, laser))
        if self.min_x is None or x < self.min_x:
            self.min_x = x
        if self.min_y is None or y < self.min_y:
            self.min_y = y
        if self.max_x is None or x > self.max_x:
            self.max_x = x
        if self.max_y is None or y > self.max_y:
            self.max_y = y

    def major_axis(self):
        """
        If both vertical and horizontal are set we prefer vertical as major axis because vertical rastering is heavier
        with the movement of the gantry bar.
        @return:
        """
        if self.v_raster:
            return 1
        if self.h_raster:
            return 0

        if len(self.plot) < 2:
            return 0
        start = Point(self.plot[0])
        end = Point(self.plot[1])
        if abs(start.x - end.x) > abs(start.y - end.y):
            return 0  # X-Axis
        else:
            return 1  # Y-Axis

    def x_dir(self):
        if self.travels_left and not self.travels_right:
            return -1  # right
        if self.travels_right and not self.travels_left:
            return 1  # left

        if len(self.plot) < 2:
            return 0
        start = Point(self.plot[0])
        end = Point(self.plot[1])
        if start.x < end.x:
            return 1
        else:
            return -1

    def y_dir(self):
        if self.travels_top and not self.travels_bottom:
            return -1  # top
        if self.travels_bottom and not self.travels_top:
            return 1  # bottom

        if len(self.plot) < 2:
            return 0
        start = Point(self.plot[0])
        end = Point(self.plot[1])
        if start.y < end.y:
            return 1
        else:
            return -1

    def upper(self):
        return self.min_x

    def lower(self):
        return self.max_x

    def left(self):
        return self.min_y

    def right(self):
        return self.max_y

    def length(self):
        length = 0
        last_x = None
        last_y = None
        for x, y, on in self.plot:
            if last_x is not None:
                length += Point.distance((x, y), (last_x, last_y))
            last_x = 0
            last_y = 0
        return length

    def reverse(self):
        # Strictly speaking this is wrong. Point with power-to-value means that we need power n-1 to the number of
        # The reverse would shift everything by 1 since all power-to are really power-from values.
        self.plot = list(reversed(self.plot))

    @property
    def start(self):
        try:
            return Point(self.plot[0][:2])
        except IndexError:
            return None

    @property
    def end(self):
        try:
            return Point(self.plot[-1][:2])
        except IndexError:
            return None

    def generator(self):
        last_xx = None
        last_yy = None
        ix = 0
        iy = 0
        for x, y, on in self.plot:
            idx = int(round(x - ix))
            idy = int(round(y - iy))
            ix += idx
            iy += idy
            if last_xx is not None:
                for zx, zy in ZinglPlotter.plot_line(last_xx, last_yy, ix, iy):
                    yield zx, zy, on
            last_xx = ix
            last_yy = iy

        return self.plot

    def point(self, t):
        if len(self.plot) == 0:
            raise ValueError
        if t == 0:
            return self.plot[0]
        if t == 1:
            return self.plot[-1]
        if self._calc_lengths is None:
            # Need to calculate lengths
            lengths = list()
            total_length = 0
            for i in range(len(self.plot) - 1):
                x0, y0, _ = self.plot[i]
                x1, y1, _ = self.plot[i + 1]
                length = abs(complex(x0, y0) - complex(x1, y1))
                lengths.append(length)
                total_length += length
            self._calc_lengths = lengths
            self._length = total_length
        if self._length == 0:
            # Degenerate fallback. (All points are coincident)
            v = int((len(self.plot) - 1) * t)
            return self.plot[v]
        v = t * self._length
        for length in self._calc_lengths:
            if v < length:
                x0, y0 = self.start
                x1, y1 = self.end
                x = x1 * v + x0
                y = y1 * v + y0
                return x, y
            v -= length
        raise ValueError
