from abc import ABC
from copy import copy

from meerk40t.tools.rasterplotter import (
    BOTTOM,
    LEFT,
    RIGHT,
    TOP,
    UNIDIRECTIONAL,
    X_AXIS,
    Y_AXIS,
    RasterPlotter,
)
from meerk40t.tools.zinglplotter import ZinglPlotter

from ..device.lasercommandconstants import COMMAND_PLOT, COMMAND_PLOT_START
from ..svgelements import Color, Group, Path, Point, Polygon
from ..tools.pathtools import VectorMontonizer

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

MILS_PER_MM = 39.3701


class LaserSettings:
    def __init__(self, *args, **kwargs):
        self.line_color = None

        self.laser_enabled = True
        self.speed = 20.0
        self.power = 1000.0
        self.dratio_custom = False
        self.dratio = 0.261
        self.acceleration_custom = False
        self.acceleration = 1

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
            value = getattr(obj, q)
            if isinstance(value, (int, float, bool, str)):
                setattr(self, q, value)

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

    def __init__(self, start=None, end=None, settings=None, parent=None):
        if settings is None:
            settings = LaserSettings()
        self.settings = settings
        self._start = start
        self._end = end
        self.normal = True  # Normal or Reversed.
        self.parent = parent
        self.inside = None
        self.contains = None
        self.permitted = True

    def reversible(self):
        return True

    def start(self):
        return self._start if self.normal else self._end

    def end(self):
        return self._end if self.normal else self._start

    def length(self):
        return Point.distance(self.start(), self.end())

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
        self.normal = not self.normal

    def generator(self):
        raise NotImplementedError

    def _contains_uncut_objects(self):
        if self.contains is None:
            return False
        for c in self.contains:
            for pp in c.flat():
                if pp.permitted:
                    return True
        return False

    def flat(self):
        yield self

    def candidate(self):
        if self.permitted:
            yield self


class CutGroup(list, CutObject, ABC):
    """
    Cut groups are effectively constraints. They may contain CutObjects or other
    CutGroups. However, the CutObjects must be cut *after* the groups within the
    CutGroup is cut.
    """

    def __init__(
        self, parent, children=(), settings=None, constrained=False, closed=False
    ):
        list.__init__(self, children)
        CutObject.__init__(self, parent=parent, settings=settings)
        self.closed = closed
        self.constrained = constrained

    def __copy__(self):
        return CutGroup(self.parent, self)

    def __repr__(self):
        return "CutGroup(children=%s, parent=%s)" % (
            list.__repr__(self),
            str(self.parent),
        )

    def reversible(self):
        return False

    def start(self):
        if len(self) == 0:
            return None
        return self[0].start() if self.normal else self[-1].end()

    def end(self):
        if len(self) == 0:
            return None
        return self[-1].end() if self.normal else self[0].start()

    def flat(self):
        for c in self:
            if not isinstance(c, CutGroup):
                yield c
                continue
            for s in c.flat():
                yield s

    def candidate(self):
        """
        Candidates are permitted cutobjects permitted to be cut, this is any cut object that
        is not itself containing another constrained cutcode object. Which is to say that the
        inner-most non-containing cutcode are the only candidates for cutting.
        """
        for c in self:
            if c._contains_uncut_objects():
                continue
            for s in c.flat():
                if s is None:
                    continue
                if s.permitted:
                    yield s


class CutCode(CutGroup):
    def __init__(self, seq=()):
        CutGroup.__init__(self, None, seq)
        self.output = True
        self.operation = "CutCode"

        self.travel_speed = 20.0
        self.start = None
        self.mode = None

    def __str__(self):
        parts = list()
        parts.append("%d items" % len(self))
        return "CutCode(%s)" % " ".join(parts)

    def as_elements(self):
        elements = list()
        last = None
        path = None
        previous_settings = None
        for e in self:
            start = e.start()
            end = e.end()
            settings = e.settings
            if path is None:
                path = Path()
                path.stroke = Color(settings.line_color)

            if len(path) == 0 or last.x != start.x or last.y != start.y:
                path.move(e.start())
            if isinstance(e, LineCut):
                path.line(end)
            elif isinstance(e, QuadCut):
                path.quad(e.c(), end)
            elif isinstance(e, CubicCut):
                path.quad(e.c1(), e.c2(), end)
            elif isinstance(e, ArcCut):
                path.append(e.arc)
            if previous_settings is not settings and previous_settings is not None:
                if path is not None and len(path) != 0:
                    elements.append(path)
                    path = None
            previous_settings = settings
            last = end
        if path is not None and len(path) != 0:
            elements.append(path)
        return elements

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

    def correct_empty(self, context=None):
        """
        Iterates through backwards deleting any entries that empty.
        """
        if context is None:
            context = self
        for index in range(len(context) - 1, -1, -1):
            c = context[index]
            if not isinstance(c, CutGroup):
                continue
            self.correct_empty(c)
            if len(c) == 0:
                del context[index]

    def extract_closed_groups(self, context=None):
        """
        yields all closed groups within the current cutcode.
        Removing those groups from this cutcode.
        """
        if context is None:
            context = self
        index = len(context) - 1
        while index != -1:
            c = context[index]
            if isinstance(c, CutGroup):
                if c.closed:
                    del context[index]
                    yield c
                index -= 1
                continue
            for s in self.extract_closed_groups(c):
                yield s
            index -= 1

    def permit(self, permit, _list=None):
        if _list is None:
            _list = self.flat()
        for c in _list:
            c.permitted = permit

    def inner_first_cutcode(self):
        ordered = CutCode()
        closed_groups = list(self.extract_closed_groups())
        if len(closed_groups):
            ordered.contains = closed_groups
            ordered.extend(closed_groups)
        ordered.extend(self.flat())
        self.clear()
        for oj in ordered:
            for ok in ordered:
                if oj is ok:
                    continue
                if self.is_inside(ok, oj):
                    if ok.inside is None:
                        ok.inside = list()
                    if oj.contains is None:
                        oj.contains = list()
                    ok.inside.append(oj)
                    oj.contains.append(ok)
        # for j, c in enumerate(ordered):
        #     if c.contains is not None:
        #         for k, q in enumerate(c.contains):
        #             assert q in ordered
        #             assert q is not c
        #     if c.inside is not None:
        #         for m, q in enumerate(c.inside):
        #             assert q in ordered
        #             assert q is not c

        ordered.mode = "constrained"
        return ordered

    def short_travel_cutcode(self, cc):
        """
        Selects cutcode from candidate cutcode permitted, optimizing with greedy/brute for
        shortest distances optimizations.
        """
        curr = cc.start
        if curr is None:
            curr = 0
        else:
            curr = complex(curr[0], curr[1])
        self.permit(True, cc.flat())
        ordered = CutCode()
        while True:
            closest = None
            backwards = False
            distance = float("inf")
            for cut in cc.candidate():
                s = cut.start()
                s = complex(s[0], s[1])
                d = abs(s - curr)
                if d < distance:
                    distance = d
                    backwards = False
                    closest = cut
                if cut.reversible():
                    e = cut.end()
                    e = complex(e[0], e[1])
                    d = abs(e - curr)
                    if d < distance:
                        distance = d
                        backwards = True
                        closest = cut
            if closest is None:
                break
            closest.permitted = False
            c = copy(closest)
            if backwards:
                c.reverse()
            end = c.end()
            curr = complex(end[0], end[1])
            ordered.append(c)
        return ordered

    def inner_selection_cutcode(self, cc):
        """
        Selects cutcode from candidate cutcode permitted but does nothing to optimize byond
        finding a valid solution.
        """
        self.permit(True, cc.flat())
        ordered = CutCode()
        while True:
            c = list(cc.candidate())
            if len(c) == 0:
                break
            ordered.extend(c)
            self.permit(False, ordered.flat())
        return ordered

    def length_travel(self):
        cutcode = list(self.flat())
        distance = 0
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

    def duration_cut(self):
        cutcode = list(self.flat())
        distance = 0
        for i in range(0, len(cutcode)):
            curr = cutcode[i]
            distance += (curr.length() / MILS_PER_MM) / curr.settings.speed
        return distance

    def is_inside(self, inner_path, outer_path):
        """
        Test that path1 is inside path2.
        :param inner_path: inner path
        :param outer_path: outer path
        :return: whether path1 is wholly inside path2.
        """
        if hasattr(inner_path, "path"):
            inner_path = inner_path.path
        if hasattr(outer_path, "path"):
            outer_path = outer_path.path
        if not hasattr(inner_path, "bounding_box"):
            inner_path.bounding_box = Group.union_bbox([inner_path])
        if not hasattr(outer_path, "bounding_box"):
            outer_path.bounding_box = Group.union_bbox([outer_path])

        if outer_path.bounding_box is None:
            return False
        if inner_path.bounding_box is None:
            return False
        if outer_path.bounding_box[0] > inner_path.bounding_box[0]:
            # outer minx > inner minx (is not contained)
            return False
        if outer_path.bounding_box[1] > inner_path.bounding_box[1]:
            # outer miny > inner miny (is not contained)
            return False
        if outer_path.bounding_box[2] < inner_path.bounding_box[2]:
            # outer maxx < inner maxx (is not contained)
            return False
        if outer_path.bounding_box[3] < inner_path.bounding_box[3]:
            # outer maxy < inner maxy (is not contained)
            return False
        if outer_path.bounding_box == inner_path.bounding_box:
            if outer_path == inner_path:  # This is the same object.
                return False
        if not hasattr(outer_path, "vm"):
            outer_path = Polygon(
                [outer_path.point(i / 100.0, error=1e4) for i in range(101)]
            )
            vm = VectorMontonizer()
            vm.add_cluster(outer_path)
            outer_path.vm = vm
        for i in range(101):
            p = inner_path.point(i / 100.0, error=1e4)
            if not outer_path.vm.is_point_inside(p.x, p.y):
                return False
        return True


class LineCut(CutObject):
    def __init__(self, start_point, end_point, settings=None):
        CutObject.__init__(self, start_point, end_point, settings=settings)
        settings.raster_step = 0

    def generator(self):
        start = self.start()
        end = self.end()
        return ZinglPlotter.plot_line(start[0], start[1], end[0], end[1])


class QuadCut(CutObject):
    def __init__(self, start_point, control_point, end_point, settings=None):
        CutObject.__init__(self, start_point, end_point, settings=settings)
        settings.raster_step = 0
        self._control = control_point

    def c(self):
        return self._control

    def length(self):
        return Point.distance(self.start(), self.c()) + Point.distance(
            self.c(), self.end()
        )

    def generator(self):
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
    def __init__(self, start_point, control1, control2, end_point, settings=None):
        CutObject.__init__(self, start_point, end_point, settings=settings)
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


class ArcCut(CutObject):
    def __init__(self, arc, settings=None):
        CutObject.__init__(self, settings=settings)
        settings.raster_step = 0
        self.arc = arc

    def length(self):
        return self.arc.length(error=1e2, min_depth=2)

    def start(self):
        return self.arc.start

    def end(self):
        return self.arc.end

    def reverse(self):
        self.arc = copy(self.arc)
        self.arc.reverse()

    def generator(self):
        return ZinglPlotter.plot_arc(self.arc)


class RasterCut(CutObject):
    def __init__(self, image, settings=None):
        CutObject.__init__(self, settings=settings)
        self.image = image
        step = self.settings.raster_step
        self.step = step
        direction = self.settings.raster_direction
        traverse = 0
        if direction == 0:
            traverse |= X_AXIS
            traverse |= TOP
        elif direction == 1:
            traverse |= X_AXIS
            traverse |= BOTTOM
        elif direction == 2:
            traverse |= Y_AXIS
            traverse |= RIGHT
        elif direction == 3:
            traverse |= Y_AXIS
            traverse |= LEFT
        elif direction == 4:
            traverse |= X_AXIS
            traverse |= TOP
        if self.settings.raster_swing:
            traverse |= UNIDIRECTIONAL

        svgimage = self.image
        image = svgimage.image
        width, height = image.size
        self.width = width
        self.height = height
        mode = image.mode

        if (
            mode not in ("1", "P", "L", "RGB", "RGBA")
            or mode == "P"
            and "transparency" in image.info
        ):
            # Any mode without a filter should get converted.
            image = image.convert("RGBA")
            mode = image.mode
        if mode == "1":

            def image_filter(pixel):
                return (255 - pixel) / 255.0

        elif mode == "P":
            p = image.getpalette()

            def image_filter(pixel):
                v = p[pixel * 3] + p[pixel * 3 + 1] + p[pixel * 3 + 2]
                return 1.0 - (v / 765.0)

        elif mode == "L":

            def image_filter(pixel):
                return (255 - pixel) / 255.0

        elif mode == "RGB":

            def image_filter(pixel):
                return 1.0 - (pixel[0] + pixel[1] + pixel[2]) / 765.0

        elif mode == "RGBA":

            def image_filter(pixel):
                return (
                    (1.0 - (pixel[0] + pixel[1] + pixel[2]) / 765.0) * pixel[3] / 255.0
                )

        else:
            raise ValueError  # this shouldn't happen.
        m = svgimage.transform
        data = image.load()

        overscan = self.settings.overscan
        if overscan is None:
            overscan = 20
        else:
            try:
                overscan = int(overscan)
            except ValueError:
                overscan = 20
        self.overscan = overscan
        tx = m.value_trans_x()
        ty = m.value_trans_y()
        self.plot = RasterPlotter(
            data, width, height, traverse, 0, overscan, tx, ty, step, image_filter
        )

    def reversible(self):
        return False

    def start(self):
        return Point(self.plot.initial_position_in_scene())

    def end(self):
        return Point(self.plot.final_position_in_scene())

    def length(self):
        return (
            self.width * self.height
            + (self.overscan * self.height)
            + (self.height * self.step)
        )

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

    def __init__(self, settings=None):
        CutObject.__init__(self, settings=settings)
        self.plot = []

    def plot(self, plot):
        self.plot.extend(plot)

    def reversible(self):
        return False

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
