from .cubiccut import CubicCut
from .cutgroup import CutGroup
from .dwellcut import DwellCut
from .linecut import LineCut
from .plotcut import PlotCut
from .quadcut import QuadCut
from .rawcut import RawCut
from ...svgelements import Color, Path, Point

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
            # TODO: Settings for different cut objects must be the creating op
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

    def provide_statistics(self, include_start=False):
        result = []
        cutcode = list(self.flat())
        if len(cutcode) == 0:
            item = {
                "type": "",
                "total_distance_travel": 0,
                "total_distance_cut": 0,
                "total_time_extra": 0,
                "total_time_travel": 0,
                "total_time_cut": 0,
                "time_at_start": 0,
                "time_at_end_of_travel": 0,
                "time_at_end_of_burn": 0,
            }
            result.append(item)
            return result
        stop_at = len(cutcode)
        distance_travel = 0
        distance_cut = 0
        extra = 0
        total_duration_cut = 0
        total_duration_travel = 0
        if include_start:
            if self.start is not None:
                distance_travel += abs(
                    complex(*self.start) - complex(*cutcode[0].start)
                )
            else:
                distance_travel += abs(0 - complex(*cutcode[0].start))
        prev_end = 0
        for i in range(0, stop_at):
            duration_of_this_travel = 0
            duration_of_this_burn = 0
            length_of_this_travel = 0
            if i > 0:
                prev = cutcode[i - 1]
                length_of_this_travel = Point.distance(prev.end, curr.start)
                distance_travel += length_of_this_travel

            curr = cutcode[i]
            rapid_speed = self._native_speed(cutcode)
            if rapid_speed is not None:
                total_duration_travel = distance_travel / rapid_speed
                duration_of_this_travel = length_of_this_travel / rapid_speed

            cut_type = type(curr).__name__

            distance_cut += curr.length()
            this_extra = curr.extra()
            extra += this_extra
            native_speed = curr.settings.get("native_speed", curr.speed)
            if native_speed != 0:
                duration_of_this_burn = curr.length() / native_speed
                total_duration_cut += duration_of_this_burn

            end_of_this_travel = prev_end + duration_of_this_travel
            end_of_this_burn = (
                prev_end + duration_of_this_travel + this_extra + duration_of_this_burn
            )
            item = {
                "type": cut_type,
                "total_distance_travel": distance_travel,
                "total_distance_cut": distance_cut,
                "total_time_extra": extra,
                "total_time_travel": total_duration_travel,
                "total_time_cut": total_duration_cut,
                "time_at_start": prev_end,
                "time_at_end_of_travel": end_of_this_travel,
                "time_at_end_of_burn": end_of_this_burn,
            }
            # print (item)
            result.append(item)
            prev_end = total_duration_cut + total_duration_travel + extra

        return result

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
        if stop_at is None or stop_at < 0 or stop_at > len(cutcode):
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
        if stop_at is None or stop_at < 0 or stop_at > len(cutcode):
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
        if stop_at is None or stop_at < 0 or stop_at > len(cutcode):
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
        if stop_at is None or stop_at < 0 or stop_at > len(cutcode):
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
        travel = self.length_travel(stop_at=stop_at)
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
