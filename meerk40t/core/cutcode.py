from abc import ABC
from typing import Optional

from ..device.lasercommandconstants import (
    COMMAND_CUT,
    COMMAND_HOME,
    COMMAND_MODE_PROGRAM,
    COMMAND_MODE_RAPID,
    COMMAND_MOVE,
    COMMAND_PLOT,
    COMMAND_PLOT_START,
    COMMAND_SET_ABSOLUTE,
    COMMAND_SET_INCREMENTAL,
)
from ..svgelements import Color, Path, Point
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

"""
Cutcode is a list of cut objects. These are line, quad, cubic, arc, and raster. And anything else that should be
considered a laser primitive. These are disjointed objects. If the distance between one and the next exist the laser
should be toggled and move by anything executing these in the planning process. Various other laser-file types should
be converted into cut code. This should be the parsed form of file-blobs. Cutcode can convert easily to both SVG and
to LaserCode.

All CutObjects have a .start() .end() and .generator() functions. They also have a settings object that contains all
properties for that cuts may need or use. Or which may be used by the CutPlanner, PlotPlanner, or local objects. These
are references to settings which may be shared by all CutObjects created by a LaserOperation.
"""

MILS_IN_MM = 39.3701


class LaserSettings:
    def __init__(self, *args, **kwargs):
        self.line_color = None

        self.laser_enabled = True
        self.speed = None
        self.power = None
        self.dratio_custom = False
        self.dratio = 0.261
        self.acceleration_custom = False
        self.acceleration = 1

        self.force_twitchless = False
        self.raster_alt = False
        self.constant_move_x = False
        self.constant_move_y = False
        self.raster_step = 0
        self.raster_direction = 1  # Bottom To Top - Default.
        self.raster_swing = False  # False = bidirectional, True = Unidirectional
        self.raster_preference_top = 0
        self.raster_preference_right = 0
        self.raster_preference_left = 0
        self.raster_preference_bottom = 0
        self.overscan = 20

        self.advanced = False

        self.ppi_enabled = True

        self.dot_length_custom = False
        self.dot_length = 1

        self.shift_enabled = False

        self.passes_custom = False
        self.passes = 1

        self.jog_distance = 255
        self.jog_enable = True

        for k in kwargs:
            value = kwargs[k]
            if hasattr(self, k):
                q = getattr(self, k)
                if q is None:
                    setattr(self, k, value)
                else:
                    t = type(q)
                    setattr(self, k, t(value))
        if len(args) == 1:
            obj = args[0]
            try:
                obj = obj.settings
            except AttributeError:
                pass
            if isinstance(obj, LaserSettings):
                self.set_values(obj)

    def set_values(self, obj):
        for q in dir(obj):
            if q.startswith("_") or q.startswith("implicit"):
                continue
            obj_type = type(obj)
            if hasattr(obj_type, q) and isinstance(getattr(obj_type, q), property):
                # Do not set property values
                continue

            value = getattr(obj, q)
            if isinstance(value, (int, float, bool, str)):
                setattr(self, q, value)

    @property
    def horizontal_raster(self):
        return self.raster_step and (
            self.raster_direction == 0 or self.raster_direction == 1
        )

    @property
    def vertical_raster(self):
        return self.raster_step and (
            self.raster_direction == 2 or self.raster_direction == 3
        )

    @property
    def implicit_accel(self):
        if not self.acceleration_custom:
            return None
        return self.acceleration

    @property
    def implicit_d_ratio(self):
        if not self.dratio_custom:
            return None
        return self.dratio

    @property
    def implicit_dotlength(self):
        if not self.dot_length_custom:
            return 1
        return self.dot_length

    @property
    def implicit_passes(self):
        if not self.passes_custom:
            return 1
        return self.passes


class CutObject:
    """
    CutObjects are small vector cuts which have on them a laser settings object.
    These store the start and end point of the cut. Whether this cut is normal or
    reversed.
    """

    def __init__(self, start=None, end=None, settings=None, parent=None, passes=1):
        if settings is None:
            settings = LaserSettings()
        self.settings = settings
        self._start = start
        self._end = end
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
                self.parent.burn_started = False
                return
            for o in self.parent:
                burns = min(burns, o._burns_done)
            self.parent.burn_started = True
            self.parent._burns_done = burns

    def reversible(self):
        return True

    def start(self):
        return self._start if self.normal else self._end

    def end(self):
        return self._end if self.normal else self._start

    def length(self):
        return Point.distance(self.start(), self.end())

    def upper(self):
        return min(self.start()[0], self.end()[0])

    def lower(self):
        return max(self.start()[0], self.end()[0])

    def left(self):
        return min(self.start()[1], self.end()[1])

    def right(self):
        return max(self.start()[1], self.end()[1])

    def extra(self):
        return 0

    def major_axis(self):
        start = self.start()
        end = self.end()
        if abs(start.x - end.x) > abs(start.y - end.y):
            return 0  # X-Axis
        else:
            return 1  # Y-Axis

    def x_dir(self):
        start = self.start()
        end = self.end()
        if start.x < end.x:
            return 1
        else:
            return -1

    def y_dir(self):
        start = self.start()
        end = self.end()
        if start.y < end.y:
            return 1
        else:
            return -1

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

    def start(self):
        if len(self) == 0:
            return None
        # handle group normal/reverse - start and end already handle segment reverse
        return self[0].start() if self.normal else self[-1].end()

    def end(self):
        if len(self) == 0:
            return None
        # handle group normal/reverse - start and end already handle segment reverse
        return self[-1].end() if self.normal else self[0].start()

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
                if seg is not None and seg.burns_done < seg.passes:
                    yield seg


class CutCode(CutGroup):
    def __init__(self, seq=(), settings=None):
        CutGroup.__init__(self, None, seq, settings=settings)
        self.output = True
        self.operation = "CutCode"

        self.travel_speed = 20.0
        self.start = None
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
            start = e.start()
            end = e.end()
            settings = e.settings
            if path is None:
                path = Path()
                c = settings.line_color if settings.line_color is not None else "blue"
                path.stroke = Color(c)

            if len(path) == 0 or last.x != start.x or last.y != start.y:
                path.move(e.start())
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
            if previous_settings is not settings and previous_settings is not None:
                if path is not None and len(path) != 0:
                    yield path
                    path = None
            previous_settings = settings
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
            yield COMMAND_PLOT, cutobject
        yield COMMAND_PLOT_START

    def length_travel(self, include_start=False):
        cutcode = list(self.flat())
        if len(cutcode) == 0:
            return 0
        distance = 0
        if include_start:
            if self.start is not None:
                distance += abs(complex(self.start) - complex(cutcode[0].start()))
            else:
                distance += abs(0 - complex(cutcode[0].start()))
        for i in range(1, len(cutcode)):
            prev = cutcode[i - 1]
            curr = cutcode[i]
            delta = Point.distance(prev.end(), curr.start())
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
            if curr.settings.speed:
                distance += (curr.length() / MILS_IN_MM) / curr.settings.speed
        return distance

    @classmethod
    def from_lasercode(cls, lasercode):
        cutcode = cls()
        x = 0
        y = 0
        relative = False
        settings = LaserSettings()
        for code in lasercode:
            if isinstance(code, int):
                cmd = code
            elif isinstance(code, (tuple, list)):
                cmd = code[0]
            else:
                continue
            # print(lasercode_string(cmd))
            if cmd == COMMAND_PLOT:
                cutcode.extend(code[1])
            elif cmd == COMMAND_SET_ABSOLUTE:
                pass
            elif cmd == COMMAND_SET_INCREMENTAL:
                pass
            elif cmd == COMMAND_MODE_PROGRAM:
                pass
            elif cmd == COMMAND_MODE_RAPID:
                pass
            elif cmd == COMMAND_MOVE:
                nx = code[1]
                ny = code[2]
                if relative:
                    nx = x + nx
                    ny = y + ny
                x = nx
                y = ny
            elif cmd == COMMAND_HOME:
                x = 0
                y = 0
            elif cmd == COMMAND_CUT:
                nx = code[1]
                ny = code[2]
                if relative:
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
        settings.raster_step = 0

    def __repr__(self):
        return f'LineCut({repr(self.start())}, {repr(self.end())}, settings="{self.settings}", passes={self.passes})'

    def generator(self):
        # pylint: disable=unsubscriptable-object
        start = self.start()
        end = self.end()
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
        settings.raster_step = 0
        self._control = control_point

    def c(self):
        return self._control

    def length(self):
        return Point.distance(self.start(), self.c()) + Point.distance(
            self.c(), self.end()
        )

    def generator(self):
        # pylint: disable=unsubscriptable-object
        start = self.start()
        c = self.c()
        end = self.end()
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
        settings.raster_step = 0
        self._control1 = control1
        self._control2 = control2

    def c1(self):
        return self._control1 if self.normal else self._control2

    def c2(self):
        return self._control2 if self.normal else self._control1

    def length(self):
        return (
            Point.distance(self.start(), self.c1())
            + Point.distance(self.c1(), self.c2())
            + Point.distance(self.c2(), self.end())
        )

    def generator(self):
        start = self.start()
        c1 = self.c1()
        c2 = self.c2()
        end = self.end()
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

        step = self.settings.raster_step
        self.step = step
        assert step > 0

        direction = self.settings.raster_direction
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
        if self.settings.raster_swing:
            traverse |= UNIDIRECTIONAL
        width, height = image.size
        self.width = width
        self.height = height

        def image_filter(pixel):
            return (255 - pixel) / 255.0

        overscan = self.settings.overscan
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

    def start(self):
        return Point(self.plot.initial_position_in_scene())

    def end(self):
        return Point(self.plot.final_position_in_scene())

    def lower(self):
        return self.plot.offset_x + self.height

    def upper(self):
        return self.plot.offset_x

    def right(self):
        return self.plot.offset_y + self.width

    def left(self):
        return self.plot.offset_y

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

    def start(self):
        try:
            return Point(self.plot[0][:2])
        except IndexError:
            return None

    def end(self):
        try:
            return Point(self.plot[-1][:2])
        except IndexError:
            return None

    def generator(self):
        return self.plot


class PlotCut(CutObject):
    """
    Plot cuts are a series of lineto informations with laser on and off info. These positions are not necessarily next
    to each other and can be any distance apart. This is a compact way of writing a large series of line positions.

    There is a raster-create value.
    """

    def __init__(self, settings=None):
        CutObject.__init__(self, settings=settings)
        self.plot = []
        self.max_dx = None
        self.max_dy = None
        self.min_x = None
        self.min_y = None
        self.max_x = None
        self.max_y = None
        self.vertical_raster = False
        self.horizontal_raster = False
        self.travels_top = False
        self.travels_bottom = False
        self.travels_right = False
        self.travels_left = False

    def __len__(self):
        return len(self.plot)

    def __str__(self):
        parts = list()
        parts.append("{points} points".format(points=len(self.plot)))
        parts.append("xmin: {v}".format(v=self.min_x))
        parts.append("ymin: {v}".format(v=self.min_y))
        parts.append("xmax: {v}".format(v=self.max_x))
        parts.append("ymax: {v}".format(v=self.max_y))
        return "PlotCut(%s)" % ", ".join(parts)

    def check_if_rasterable(self):
        """
        Rasterable plotcuts are heuristically defined as having a max step of less than 15 and
        must have an unused travel direction.

        @return: whether the plot can travel
        """
        # Default to vector settings.
        self.settings.raster_alt = False
        self.settings.constant_move_x = False
        self.settings.constant_move_y = False
        self.settings.raster_step = 0
        if self.max_dx is None:
            return False
        if self.max_dy is None:
            return False
        if self.settings.speed < 80:
            # Twitchless gets sketchy at 80.
            self.settings.force_twitchless = True
            return False
            # if self.max_dy >= 15 and self.max_dy >= 15:
            #     return False  # This is probably a vector.
        # Above 80 we're likely dealing with a raster.
        if 0 < self.max_dx <= 15:
            self.vertical_raster = True
            self.settings.constant_move_y = True
        if 0 < self.max_dy <= 15:
            self.horizontal_raster = True
            self.settings.constant_move_x = True
        # if self.vertical_raster or self.horizontal_raster:
        self.settings.raster_step = min(self.max_dx, self.max_dy)
        self.settings.raster_alt = True
        return True

    def plot_extend(self, plot):
        for x, y, laser in plot:
            self.plot_append(x, y, laser)

    def plot_append(self, x, y, laser):
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
        if self.vertical_raster:
            return 1
        if self.horizontal_raster:
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
        self.plot = list(reversed(self.plot))

    def start(self):
        try:
            return Point(self.plot[0][:2])
        except IndexError:
            return None

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
