from abc import ABC

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
        self.permitted = True

        self.mode = None
        self.inside = None
        self.contains = None
        self.path = None
        self.original_op = None
        self.pass_index = -1

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

    def contains_uncut_objects(self):
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
    CutGroups are group container CutObject. They are used to group objects together such as
    to maintain the relationship between within a closed path object.
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
        """
        Flat list of cut objects with a depth first search.
        """
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
            if c.contains_uncut_objects():
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
        last = None
        path = None
        previous_settings = None
        for e in self:
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
