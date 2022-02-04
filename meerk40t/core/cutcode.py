from abc import ABC
from typing import Any, Callable, Dict, Generator, Optional, Tuple, Union

from .parameters import Parameters
from ..tools.rasterplotter import (
    BOTTOM,
    LEFT,
    RIGHT,
    TOP,
    UNIDIRECTIONAL,
    X_AXIS,
    Y_AXIS,
    RasterPlotter,
)
from ..tools.zinglplotter import ZinglPlotter


from ..svgelements import Color, Path, Point

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

MILS_IN_MM = 39.3701


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

    def contains_burned_groups(self):
        if self.contains is None:
            return False
        for c in self.contains:
            if isinstance(c, CutGroup):
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

    def __repr__(self):
        return "CutGroup(children=%s, parent=%s)" % (
            list.__repr__(self),
            str(self.parent),
        )

    def reversible(self):
        return False

    def reverse(self):
        pass

    @property
    def start(self):
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
            #   2. Candidates which are neither inner or outer
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
            if grp.contains_unburned_groups():
                continue
            # If we are only burning complete subpaths then
            # if this is not a closed path we should only yield first and last segments
            # Planner will need to determine which end of the subpath is yielded
            # and only consider the direction starting from the end
            if complete_path and not grp.closed and isinstance(grp, CutGroup):
                if grp[0].burns_done < grp[0].passes:
                    yield grp[0]
                # Do not yield same segment a 2nd time if only one segment
                if len(grp) > 1 and grp[-1].burns_done < grp[-1].passes:
                    yield grp[-1]
                continue
            # If we are either burning any path segment
            # or this is a closed path
            # then we should yield all segments.
            for seg in grp.flat():
                if seg is None:
                    continue
                if seg.burns_done < seg.passes:
                    yield seg


class CutCode(CutGroup):
    def __init__(self, seq=(), settings=None):
        CutGroup.__init__(self, None, seq, settings=settings)
        self.output = True
        self.operation = "CutCode"

        self.travel_speed = 20.0
        self.mode = None

    def __str__(self):
        parts = list()
        parts.append("%d items" % len(self))
        return "CutCode(%s)" % " ".join(parts)

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
                        path.line(x, y)
                    else:
                        path.move(x, y)
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

        :param j:
        :param k:
        :return:
        """
        for q in range(j, k):
            self[q].direct_close()
            self[q].reverse()
        self[j:k] = self[j:k][::-1]

    def generate(self):
        for cutobject in self.flat():
            yield "plot", cutobject
        yield "plot_start"

    def length_travel(self, include_start=False):
        cutcode = list(self.flat())
        if len(cutcode) == 0:
            return 0
        distance = 0
        if include_start:
            if self.start is not None:
                distance += abs(complex(self.start) - complex(cutcode[0].start))
            else:
                distance += abs(0 - complex(cutcode[0].start))
        for i in range(1, len(cutcode)):
            prev = cutcode[i - 1]
            curr = cutcode[i]
            delta = Point.distance(prev.end, curr.start)
            distance += delta
        return distance

    def length_cut(self):
        cutcode = list(self.flat())
        distance = 0
        for i in range(0, len(cutcode)):
            curr = cutcode[i]
            distance += curr.length()
        return distance

    def extra_time(self):
        cutcode = list(self.flat())
        extra = 0
        for i in range(0, len(cutcode)):
            curr = cutcode[i]
            extra += curr.extra()
        return extra

    def duration_cut(self):
        cutcode = list(self.flat())
        distance = 0
        for i in range(0, len(cutcode)):
            curr = cutcode[i]
            if curr.speed != 0:
                distance += (curr.length() / MILS_IN_MM) / curr.speed
        return distance

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

    def generator(self):
        start = self.start
        end = self.end
        return ZinglPlotter.plot_line(start[0], start[1], end[0], end[1])


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

    def c(self):
        return self._control

    def length(self):
        return Point.distance(self.start, self.c()) + Point.distance(self.c(), self.end)

    def generator(self):
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


class RasterCut(CutObject):
    """
    Rastercut accepts a image of type "L" or "1", and an offset in the x and y and information as to whether
    this is a crosshatched cut or not.
    """

    def __init__(
        self, image, tx, ty, settings=None, crosshatch=False, passes=1, parent=None
    ):
        CutObject.__init__(self, settings=settings, passes=passes, parent=parent)
        assert image.mode in ("L", "1")
        self.first = True  # Raster cuts are always first within themselves.
        self.image = image
        self.tx = tx
        self.ty = ty

        step = self.raster_step
        self.step = step
        assert step > 0

        direction = self.raster_direction
        traverse = 0
        if direction == 0 or direction == 4 and not crosshatch:
            traverse |= X_AXIS
            traverse |= TOP
        elif direction == 1:
            traverse |= X_AXIS
            traverse |= BOTTOM
        elif direction == 2 or direction == 4 and crosshatch:
            traverse |= Y_AXIS
            traverse |= RIGHT
        elif direction == 3:
            traverse |= Y_AXIS
            traverse |= LEFT
        if self.raster_swing:
            traverse |= UNIDIRECTIONAL
        width, height = image.size
        self.width = width
        self.height = height

        def image_filter(pixel):
            return (255 - pixel) / 255.0

        overscan = self.overscan
        if overscan is None:
            overscan = 20
        else:
            try:
                overscan = int(overscan)
            except ValueError:
                overscan = 20
        self.overscan = overscan
        self.plot = RasterPlotter(
            image.load(),
            width,
            height,
            traverse,
            0,
            overscan,
            tx,
            ty,
            step,
            image_filter,
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
            + (self.height * self.step)
        )

    def extra(self):
        return self.width * 0.105  # 105ms for the turnaround.

    def major_axis(self):
        return 0 if self.plot.horizontal else 1

    def x_dir(self):
        return 1 if self.plot.rightward else -1

    def y_dir(self):
        return 1 if self.plot.bottomward else -1

    def generator(self):
        return self.plot.plot()


class RawCut(CutObject):
    """
    Raw cuts are non-shape based cut objects with location and laser amount.
    """

    def __init__(self, settings=None, passes=1, parent=None):
        CutObject.__init__(self, settings=settings, passes=passes, parent=parent)
        self.plot = []

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
