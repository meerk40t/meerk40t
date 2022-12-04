import math

import numpy as np

from meerk40t.tools.zinglplotter import ZinglPlotter

"""
The idea behind Geometry Strings is to define a common structure that could replace the whole of cutcode and do so in a
way that could be both be faster and more compact for other data structures commonly used throughout Meerk40t. And to
include within that datastructure many common operations that need to be called repeated.

* Some drivers can use direct circular arcs, lines, and others use bezier curves. We should also avoid prematurely
interpolating our data prior to knowing what types of data the driver might want or accept.
* Some drivers can use dwell points, in that, they can go to a particular location and turn the laser on for a period
of time.
* Rasters are converted into a series of tiny steps that are usually either on or off but these are so plentiful that
attempting to render them results in an unusably slow program.
* We should/must optimize our pathing such that we can minimize travel time.
* Some hatch operations result in many disjointed paths. The current objects we have to capture this data requires many
node objects and is very inefficient.

For these reasons we have the geomstr class which uses numpy arrays to define geometric and highly laser-specific
objects, with enough generalization to capture hypothetical additional forms.

Each segment is defined by 5 complex values, these are:

`Start, Control1, Type/Settings, Control2, End`

* Line: Start, NOP, Type=0/Settings, NOP, End
* Quad: Start, C0, Type=1/Settings, C0, End  -- Note C0 is duplicated and identical. But, only one needs to be read.
* Cubic: Start, C0, Type=2/Settings, C1, End
* Arc: Start, C0, Type=3/Settings, C0, End -- Note C0 is duplicated and identical.
* Dwell: Start, NOP, Type=4/Settings, NOP, Start -- Note, Start and End are the same point.
* Wait: NOP, NOP, Type=5/Settings, NOP, NOP, -- Note, Start and End are the same point.
* Ramp: Start, PStart, Type=6/Settings, PEnd, End -- Power ramp line.
* End: NOP, NOP, Type=99/Settings, NOP, NOP -- Structural segment.
* Vertex, NOP, NOP, Type=100/Index, NOP, NOP -- Structural segment.

Note: the Arc is circular-only and defined by 3 points. Start, End, and a single control point. We do not do
elliptical arcs since they are weird/complex and no laser appears to use them.

Additional extensions can be added by expanding the type parameters. Since each set of values is a complex, the points
provide x and y values (real, imag). The type parameter (index 2) provides the settings. The settings object is users'
choice. In the case of Wait, we assume it gives the wait time.

At first glance the structure may seem somewhat unusual but the `Position, Position, Type, Position, Position`
structure serves a utilitarian purpose; all paths are reversible. We can flip this data, to reverse these segments.
The start and end points can swap as well as the control points for the cubic, and arc, or swamp power levels for ramp.
Whereas the types of parameter remains in the same position.

The numpy flip operation can be done over the x and y axis. This provides the list of segments in reverse order while
also reversing all the segments themselves. This is the key to doing 2-opt travel minimization, which is provided in
the code.

---

Ruida has some segments which start at one power and ramp up to a second amount of power. In this case, the reverse of
this needs to attenuate power over that length. In such a case the C0 and C1 places are adapted to set the power.

This class is expected to be able to replace many uses of the Path class as well as all cutcode, permitting all affine
transformations, and serve as a laser-first data structure. These should serve as faster laser-centric path-like code.

Each path's complex2 `.imag` middle part points to a settings index. These are the settings being used to draw this
geometry with whatever device is performing the drawing. So if the laser had frequency or if an embroidery machine had
multi-needles you could refer to the expected thread-color of the segment. If there's only one set of settings all
segments may point to same object. If different settings are used for each segment, these can point to different
segments.

There are two primary structural nodes types. These are END and VERTEX. The END indicates that a particular walk is
finished and that the END of that walk has been reached. A VERTEX indicates that we occupy the same space
as all other VERTEX nodes with that index. No validation will be made to determine if any walks terminating or starting
in the same vertex are coincident. A shape is closed if both the shape starts and ends in the same vertex.

VERTEX also provides us with usable graph topologies. We can consider the difference between a closed and opened path
to be whether both ends terminate in the same vertex. But, we can also have several different geometric strings either
start or end in the same vertex.

Strings can be disjointed, in that the position between one position and the next are not coincident, this implies the
position was moved. Usually this difference in position should be 0.

Structural nodes like VERTEX work on both sides. For example,

Vertex 0
Line A, B
Line B, C
Vertex 1
Line C, D
Line D, E
Vertex 0

The string goes V0, A->B, B->C V1 and the next string goes V1, C->D, D->E, V0. These definitions imply that V0 is
located at points A and E, and for valid geometry probably should be. However, this is merely implied.
We may define another run as V1, Line C->Z.

All strings are reversible. In fact, the reason for the 5 complex structure is so that each segment can reverse with
a np.flip.
"""

TYPE_LINE = 0
TYPE_QUAD = 1
TYPE_CUBIC = 2
TYPE_ARC = 3
TYPE_DWELL = 4
TYPE_WAIT = 5
TYPE_RAMP = 6
TYPE_END = 99
TYPE_VERTEX = 100


class Scanbeam:
    """
    Accepts a Geomstr operation and performs scanbeam operations.
    """

    def __init__(self, geom):
        self._geom = geom

        self.scanline = -float("inf")

        self._sorted_edge_list = []
        self._edge_index = 0

        self._active_edge_list = []
        self._dirty_actives_sort = False

        self._low = float("inf")
        self._high = -float("inf")

        for i in range(self._geom.index):
            if (self._geom.segments[i][0].imag, self._geom.segments[i][0].real) < (
                self._geom.segments[i][-1].imag,
                self._geom.segments[i][-1].real,
            ):
                self._sorted_edge_list.append((self._geom.segments[i][0], i))
                self._sorted_edge_list.append((self._geom.segments[i][-1], ~i))
            else:
                self._sorted_edge_list.append((self._geom.segments[i][0], ~i))
                self._sorted_edge_list.append((self._geom.segments[i][-1], i))

        def sort_key(e):
            return e[0].imag, e[0].real, ~e[1]

        self._sorted_edge_list.sort(key=sort_key)

        self.increment_scanbeam()

    def scanline_increment(self, delta):
        self.scanline_to(self.scanline + delta)
        return math.isinf(self._low) or math.isinf(self._high)

    def scanline_to(self, scan):
        """
        Move the scanline to the scan position.
        @param scan:
        @return:
        """
        self._dirty_actives_sort = True

        while self._below_scanbeam(scan):
            self.decrement_scanbeam()

        while self._above_scanbeam(scan):
            self.increment_scanbeam()

        self.scanline = scan
        self._sort_actives()

    def x_intercept(self, e):
        return self._geom.x_intercept(e, self.scanline)

    def is_point_inside(self, x, y, tolerance=0):
        """
        Determine if the x/y point is with the segments of a closed shape polygon.

        This assumes that add_polyline added a closed point class.
        @param x: x location of point
        @param y: y location of point
        @param tolerance: wiggle room
        @return:
        """
        self.scanline_to(y)
        for i in range(1, len(self._active_edge_list), 2):
            prior = self._active_edge_list[i - 1]
            after = self._active_edge_list[i]
            if (
                self.x_intercept(prior) - tolerance
                <= x
                <= self.x_intercept(after) + tolerance
            ):
                return True
        return False

    def actives(self):
        """
        Get the active list at the current scanline.

        @return:
        """
        self._sort_actives()
        return self._active_edge_list

    def event_range(self):
        """
        Returns the range of events from the lowest to the highest in y-value.

        @return:
        """
        y_min, index_min = self._sorted_edge_list[0]
        y_max, index_max = self._sorted_edge_list[-1]
        return y_min, y_max

    def _sort_actives(self):
        if not self._dirty_actives_sort:
            return
        self._active_edge_list.sort(key=self.x_intercept)
        self._dirty_actives_sort = False

    def within_scanbeam(self, v):
        """
        Is the value within the current scanbeam?
        @param v:
        @return:
        """

        return not self._below_scanbeam(v) and not self._above_scanbeam(v)

    def _below_scanbeam(self, v):
        """
        Is the value below the current scanbeam?
        @param v:
        @return:
        """
        return v < self._low

    def _above_scanbeam(self, v):
        """
        Is the value above the current scanbeam?

        @param v:
        @return:
        """
        return v > self._high

    def increment_scanbeam(self):
        """
        Increment scanbeam the active edge events.

        @return:
        """
        self._edge_index += 1
        self._low = self._high
        try:
            self._high, sb_index = self._sorted_edge_list[self._edge_index]
            self._high = self._high.imag
        except IndexError:
            self._high = float("inf")

        if self._edge_index > 0:
            sb_value, sb_index = self._sorted_edge_list[self._edge_index - 1]
            if sb_index >= 0:
                self._active_edge_list.append(sb_index)
            else:
                self._active_edge_list.remove(~sb_index)

    def decrement_scanbeam(self):
        """
        Move the scanbeam higher in the events.

        @return:
        """
        # TODO: Not fixed.
        self._edge_index -= 1
        self._high = self._low
        if self._edge_index > 0:
            self._low, sb_index = self._sorted_edge_list[self._edge_index - 1]
            self._low = self._low.imag
            if sb_index > 0:
                self._active_edge_list.append(sb_index)
            else:
                self._active_edge_list.remove(~sb_index)
        else:
            self._low = -float("inf")


class Geomstr:
    """
    Geometry String Class
    """

    def __init__(self, segments=None):
        if segments is not None:
            self.index = len(segments)
            self.capacity = self.index
            self.segments = segments
        else:
            self.index = 0
            self.capacity = 12
            self.segments = np.zeros((self.capacity, 5), dtype="complex")

        self._settings = dict()

    def __copy__(self):
        """
        Create a geomstr copy.

        @return: Copy of geomstr.
        """
        geomstr = Geomstr()
        geomstr.index = self.index
        geomstr.capacity = self.capacity
        geomstr.segments = np.copy(self.segments)
        return geomstr

    def __len__(self):
        """
        @return: length of the geomstr (note not the capacity).
        """
        return self.index

    def merge(self, other):
        """
        Merge other geomstr with this geomstr. Intersections meet at vertices.
        @param other:
        @return:
        """
        intersections = self.find_intersections(other)
        bisectors = {}

        for xi, yi, s, t, idx in intersections:
            bis = bisectors.get(s)
            if bis is None:
                bis = []
                bisectors[s] = bis
            bis.append((xi, yi, s, t, idx))
        original = self.segments
        total = self.index + other.index + len(intersections) * 4 + 1
        new_segments = np.zeros((total, 5), dtype="complex")

        itx = 0
        itx = self._bisect_segments(bisectors, original, self.index, new_segments, itx)
        new_segments[itx] = (
            np.nan,
            np.nan,
            complex(TYPE_END, -1),
            np.nan,
            np.nan,
        )
        itx += 1

        bisectors = {}
        for xi, yi, s, t, idx in intersections:
            bis = bisectors.get(t)
            if bis is None:
                bis = []
                bisectors[t] = bis
            bis.append((xi, yi, t, s, idx))
        original = other.segments
        itx = self._bisect_segments(bisectors, original, other.index, new_segments, itx)
        self.segments = new_segments
        self.index = itx
        self.capacity = new_segments.shape[0]
        return self

    def _bisect_segments(self, bisectors, original, index, new_segments, itx):
        def bisector_sort(e):
            """Sort by edge index, and distance from start."""
            return e[2], abs(complex(e[0], e[1]) - original[e[2], 0])

        for seg in range(index):
            bisector = bisectors.get(seg)
            if bisector is None:
                # Not bisected, copy over.
                new_segments[itx] = original[seg]
                itx += 1
                continue
            bisector.sort(key=bisector_sort)

            start = original[seg, 0]
            settype = original[seg, 2]
            for xi, yi, si, ti, idx in bisector:
                end = complex(xi, yi)

                new_segments[itx] = (
                    start,
                    start,
                    settype,
                    end,
                    end,
                )
                itx += 1

                new_segments[itx] = (
                    np.nan,
                    np.nan,
                    complex(TYPE_VERTEX, idx),
                    np.nan,
                    np.nan,
                )
                itx += 1

                start = end
            end = original[seg, -1]
            new_segments[itx] = (
                start,
                start,
                settype,
                end,
                end,
            )
            itx += 1
        return itx

    def find_intersections(self, other):
        """
        Finds intersections between line types through brute force.

        @param other:
        @return:
        """
        idx = 0
        intersections = []
        for s in range(self.index):
            if int(self.segments[s, 2].real) & 0xFF != TYPE_LINE:
                continue
            for t in range(other.index):
                if int(other.segments[t, 2].real) & 0xFF != TYPE_LINE:
                    continue
                intersect = Geomstr.line_intersect(
                    self.segments[s, 0].real,
                    self.segments[s, 0].imag,
                    self.segments[s, -1].real,
                    self.segments[s, -1].imag,
                    other.segments[t, 0].real,
                    other.segments[t, 0].imag,
                    other.segments[t, -1].real,
                    other.segments[t, -1].imag,
                )
                if not intersect:
                    continue
                xi, yi = intersect
                intersections.append((xi, yi, s, t, idx))
                idx += 1
        return intersections

    def _ensure_capacity(self, capacity):
        if self.capacity > capacity:
            return
        self.capacity = self.capacity << 1
        new_segments = np.zeros((self.capacity, 5), dtype="complex")
        new_segments[0 : self.index] = self.segments[0 : self.index]
        self.segments = new_segments

    def _trim(self):
        if self.index != self.capacity:
            self.capacity = self.index
            self.segments = self.segments[0 : self.index]

    def settings(self, key, settings):
        """
        Set settings object for given key.

        @param key:
        @param settings:
        @return:
        """
        self._settings[key] = settings

    @property
    def first_point(self):
        """
        First point within the path if said point exists
        @return:
        """
        if self.index:
            return self.segments[0, 0]
        else:
            return None

    def bbox(self, mx=None):
        """
        bounding box of the particular segments.
        @param mx: Conditional matrix operation.
        @return:
        """
        segments = self.segments[: self.index]
        nans = np.isnan(segments[:, 0])
        firsts = segments[~nans, 0]
        nans = np.isnan(segments[:, 4])
        lasts = segments[~nans, 4]
        max_x = max(
            np.max(np.real(firsts)),
            np.max(np.real(lasts)),
        )
        min_x = min(
            np.min(np.real(firsts)),
            np.min(np.real(lasts)),
        )
        max_y = max(
            np.max(np.imag(firsts)),
            np.max(np.imag(lasts)),
        )
        min_y = min(
            np.min(np.imag(firsts)),
            np.min(np.imag(lasts)),
        )
        if mx is not None:
            min_x, min_y = (
                min_x * mx.a + min_y * mx.c + 1 * mx.e,
                min_x * mx.b + min_y * mx.d + 1 * mx.f,
            )
            max_x, max_y = (
                max_x * mx.a + max_y * mx.c + 1 * mx.e,
                max_x * mx.b + max_y * mx.d + 1 * mx.f,
            )
        return min_x, min_y, max_x, max_y

    def segment_bbox(self, e):
        line = self.segments[e]
        if line[2].real == TYPE_LINE:
            return (
                min(line[0].real, line[-1].real),
                min(line[0].imag, line[-1].imag),
                max(line[0].real, line[-1].real),
                max(line[0].imag, line[-1].imag),
            )
        elif line[2].real == TYPE_QUAD:
            local_extremizers = list(self._quad_local_extremes(0, line))
            extreme_points = self._quad_point(line, local_extremizers)
            local_extrema = extreme_points[0]
            xmin = min(local_extrema)
            xmax = max(local_extrema)

            local_extremizers = list(self._quad_local_extremes(1, line))
            extreme_points = self._quad_point(line, local_extremizers)
            local_extrema = extreme_points[1]
            ymin = min(local_extrema)
            ymax = max(local_extrema)

            return xmin, ymin, xmax, ymax
        elif line[2].real == TYPE_CUBIC:
            local_extremizers = list(self._cubic_local_extremes(0, line))
            extreme_points = self._cubic_point(line, local_extremizers)
            local_extrema = extreme_points[0]
            xmin = min(local_extrema)
            xmax = max(local_extrema)

            local_extremizers = list(self._cubic_local_extremes(1, line))
            extreme_points = self._cubic_point(line, local_extremizers)
            local_extrema = extreme_points[1]
            ymin = min(local_extrema)
            ymax = max(local_extrema)

            return xmin, ymin, xmax, ymax

    def _quad_point(self, line, positions):
        """Calculate the x,y position at a certain position of the path. `pos` may be a
        float or a NumPy array."""

        x0, y0 = line[0].real, line[0].imag
        x1, y1 = line[1].real, line[1].imag
        # line[3] is identical to line[1]
        x2, y2 = line[4].real, line[4].imag

        def _compute_point(position):
            # compute factors
            n_pos = 1 - position
            pos_2 = position * position
            n_pos_2 = n_pos * n_pos
            n_pos_pos = n_pos * position

            return (
                n_pos_2 * x0 + 2 * n_pos_pos * x1 + pos_2 * x2,
                n_pos_2 * y0 + 2 * n_pos_pos * y1 + pos_2 * y2,
            )

        return _compute_point(np.array(positions))

    def _quad_local_extremes(self, v, e):
        yield 0
        yield 1
        if v == 0:
            a = e[0].real, e[1].real, e[4].real
        else:
            a = e[0].imag, e[1].imag, e[4].imag

        n = a[0] - a[1]
        d = a[0] - 2 * a[1] + a[2]
        if d != 0:
            t = n / float(d)
            if 0 < t < 1:
                yield t
        else:
            yield 0.5

    def _cubic_point(self, line, positions):
        x0, y0 = line[0].real, line[0].imag
        x1, y1 = line[1].real, line[1].imag
        x2, y2 = line[3].real, line[3].imag
        x3, y3 = line[4].real, line[4].imag

        def _compute_point(position):
            # compute factors
            pos_3 = position * position * position
            n_pos = 1 - position
            n_pos_3 = n_pos * n_pos * n_pos
            pos_2_n_pos = position * position * n_pos
            n_pos_2_pos = n_pos * n_pos * position
            return (
                n_pos_3 * x0 + 3 * (n_pos_2_pos * x1 + pos_2_n_pos * x2) + pos_3 * x3,
                n_pos_3 * y0 + 3 * (n_pos_2_pos * y1 + pos_2_n_pos * y2) + pos_3 * y3,
            )

        return _compute_point(np.array(positions))

    def _cubic_local_extremes(self, v, e):
        """
        returns the extreme t values for a cubic bezier curve, with a non-zero denom
        """
        yield 0
        yield 1
        if v == 0:
            a = e[0].real, e[1].real, e[3].real, e[4].real
        else:
            a = e[0].imag, e[1].imag, e[3].imag, e[4].imag

        denom = a[0] - 3 * a[1] + 3 * a[2] - a[3]
        if abs(denom) >= 1e-12:
            delta = (
                a[1] * a[1] - (a[0] + a[1]) * a[2] + a[2] * a[2] + (a[0] - a[1]) * a[3]
            )
            if delta >= 0:  # otherwise no local extrema
                sqdelta = math.sqrt(delta)
                tau = a[0] - 2 * a[1] + a[2]
                r1 = (tau + sqdelta) / denom
                r2 = (tau - sqdelta) / denom
                if 0 < r1 < 1:
                    yield r1
                if 0 < r2 < 1:
                    yield r2
        else:
            yield 0.5

    def segment_slope(self, e):
        line = self.segments[e]
        a = line[0]
        b = line[-1]
        if b.real - a.real == 0:
            return float("inf")
        return (b.imag - a.imag) / (b.real - a.real)

    def segment_intercept(self, e):
        line = self.segments[e]
        a = line[0]
        b = line[-1]
        if b.real - a.real == 0:
            return float("inf")
        im = (b.imag - a.imag) / (b.real - a.real)
        return a.imag - (im * a.real)

    def segment_end_with_min_y(self, e):
        line = self.segments[e]
        a = line[0]
        b = line[-1]
        if a.imag < b.imag:
            return a
        else:
            return b

    def segment_end_with_max_y(self, e):
        line = self.segments[e]
        a = line[0]
        b = line[-1]
        if a.imag > b.imag:
            return a
        else:
            return b

    def x_intercept(self, e, y):
        m = self.segment_slope(e)
        b = self.segment_intercept(e)
        if math.isnan(m) or math.isinf(m):
            low = self.segment_end_with_min_y(e)
            return low.real
        return (y - b) / m

    def transform(self, mx):
        """
        Affine Transformation by an arbitrary matrix.
        @param mx: Matrix to transform by
        @return:
        """
        for segment in self.segments[0 : self.index]:
            start = segment[0]
            c0 = segment[1]
            segpow = segment[2]
            c1 = segment[3]
            end = segment[4]

            start = complex(
                start.real * mx.a + start.imag * mx.c + 1 * mx.e,
                start.real * mx.b + start.imag * mx.d + 1 * mx.f,
            )
            end = complex(
                end.real * mx.a + end.imag * mx.c + 1 * mx.e,
                end.real * mx.b + end.imag * mx.d + 1 * mx.f,
            )
            if segpow.real != TYPE_RAMP:
                c0 = complex(
                    c0.real * mx.a + c0.imag * mx.c + 1 * mx.e,
                    c0.real * mx.b + c0.imag * mx.d + 1 * mx.f,
                )
                c1 = complex(
                    c1.real * mx.a + c1.imag * mx.c + 1 * mx.e,
                    c1.real * mx.b + c1.imag * mx.d + 1 * mx.f,
                )
            segment[:] = start, c0, segpow, c1, end

    def translate(self, dx, dy):
        """
        Translate the location within the path.

        @param dx: change in x
        @param dy: change in y
        @return:
        """
        self.segments[: self.index, 0] += complex(dx, dy)
        self.segments[: self.index, 4] += complex(dx, dy)
        types = self.segments[: self.index, 2]
        q = np.where(types.astype(int) != TYPE_RAMP)
        self.segments[q, 1] += complex(dx, dy)
        self.segments[q, 3] += complex(dx, dy)

    def uscale(self, scale):
        """
        Uniform scaling operation

        @param scale: uniform scaling factor
        @return:
        """
        self.segments[: self.index, 0] *= scale
        self.segments[: self.index, 4] *= scale
        types = self.segments[: self.index, 2]
        q = np.where(types.real != TYPE_RAMP)
        self.segments[q, 1] *= scale
        self.segments[q, 3] *= scale

    def rotate(self, angle):
        """
        Rotate segments around the origin.
        @param angle: angle in radians
        @return:
        """
        rotation = complex(math.cos(angle), math.sin(angle))
        self.uscale(rotation)

    def close(self, settings=0):
        """
        Close the current path if possible. This merely connects the end of the current path to the original point of
        the current path. (After any TYPE_BREAK commands).

        @param settings:
        @return:
        """
        if self.index == 0:
            raise ValueError("Empty path cannot close")
        self._ensure_capacity(self.index + 1)
        types = self.segments[: self.index, 2]
        q = np.where(np.real(types) == TYPE_END)[0]
        if len(q):
            last = q[-1] + 1
            if self.index <= last:
                raise ValueError("Empty path cannot close")
        else:
            last = 0
        start_segment = self.segments[last][0]
        end_segment = self.segments[self.index - 1][-1]
        if start_segment != end_segment:
            self.line(end_segment, start_segment, settings=settings)

    def polyline(self, points, settings=0):
        """
        Add a series of polyline points
        @param points:
        @param settings:
        @return:
        """
        for i in range(1, len(points)):
            self.line(points[i - 1], points[i], settings=settings)

    def line(self, start, end, settings=0):
        """
        Add a line between start and end points at the given settings level

        @param start: complex: start point
        @param end: complex: end point
        @param settings: settings level to assign this particular line.
        @return:
        """
        self._ensure_capacity(self.index + 1)
        self.segments[self.index] = (
            start,
            start,
            complex(TYPE_LINE, settings),
            end,
            end,
        )
        self.index += 1

    def quad(self, start, control, end, settings=0):
        """
        Add a quadratic bezier curve.
        @param start: (complex) start point
        @param control: (complex) control point
        @param end: (complex) end point
        @param settings: optional settings level for the quadratic bezier curve
        @return:
        """
        self._ensure_capacity(self.index + 1)
        self.segments[self.index] = (
            start,
            control,
            complex(TYPE_QUAD, settings),
            control,
            end,
        )
        self.index += 1

    def cubic(self, start, control0, control1, end, settings=0):
        """
        Add in a cubic bezier curve
        @param start: (complex) start point
        @param control0: (complex) first control point
        @param control1: (complex) second control point
        @param end: (complex) end point
        @param settings: optional settings level for the cubic bezier curve
        @return:
        """
        self._ensure_capacity(self.index + 1)
        self.segments[self.index] = (
            start,
            control0,
            complex(TYPE_CUBIC, settings),
            control1,
            end,
        )
        self.index += 1

    def arc(self, start, control, end, settings=0):
        """
        Add in a circular arc curve
        @param start: (complex) start point
        @param control:(complex) control point
        @param end: (complex) end point
        @param settings: optional settings level for the arc
        @return:
        """
        self._ensure_capacity(self.index + 1)
        self.segments[self.index] = (
            start,
            control,
            complex(TYPE_ARC, settings),
            control,
            end,
        )
        self.index += 1

    def dwell(self, position, time):
        """
        Add in dwell time to fire the laser standing at a particular point.

        @param position: Position at which to fire the laser
        @param time: time in ms to fire the laser
        @return:
        """
        self._ensure_capacity(self.index + 1)
        self.segments[self.index] = (
            position,
            position,
            complex(TYPE_DWELL, time),
            position,
            position,
        )
        self.index += 1

    def wait(self, position, time):
        """
        Add in wait time to stand for the laser
        @param position: Position to wait at
        @param time: time in seconds to wait
        @return:
        """
        self._ensure_capacity(self.index + 1)
        self.segments[self.index] = (
            position,
            position,
            complex(TYPE_WAIT, time),
            position,
            position,
        )
        self.index += 1

    def ramp(self, start, end, settings_start=0.0, settings_end=0):
        """
        settings ramping line.

        @param start: (complex) start point
        @param end: (complex) end point
        @param settings_start: starting settings
        @param settings_end: ending settings
        @return:
        """
        self._ensure_capacity(self.index + 1)
        self.segments[self.index] = (
            start,
            settings_start,
            complex(TYPE_RAMP, 1),
            settings_end,
            end,
        )
        self.index += 1

    def end(self, settings=0):
        """
        Adds a structural break in the current path. Two structural breaks are assumed to be a new path.
        @param settings: Unused settings value for break.
        @return:
        """
        self._ensure_capacity(self.index + 1)
        self.segments[self.index] = (
            np.nan,
            np.nan,
            complex(TYPE_END, settings),
            np.nan,
            np.nan,
        )
        self.index += 1

    def vertex(self, vertex=0):
        """
        Adds a structural break in the current path. Two structural breaks are assumed to be a new path.
        @param settings: Unused settings value for break.
        @return:
        """
        self._ensure_capacity(self.index + 1)
        self.segments[self.index] = (
            np.nan,
            np.nan,
            complex(TYPE_VERTEX, vertex),
            np.nan,
            np.nan,
        )
        self.index += 1

    def length(self):
        indexes0 = np.arange(0, self.index)
        pen_downs = self.segments[indexes0, 0]
        pen_ups = self.segments[indexes0, -1]
        return np.sum(np.abs(pen_ups - pen_downs))

    def travel_distance(self):
        """
        Calculate the total travel distance for this geomstr.
        @return: distance in units for the travel
        """
        # TODO: Update for NOP start/end points
        indexes0 = np.arange(0, self.index - 1)
        indexes1 = indexes0 + 1
        pen_ups = self.segments[indexes0, -1]
        pen_downs = self.segments[indexes1, 0]
        return np.sum(np.abs(pen_ups - pen_downs))

    def as_subpaths(self):
        """
        Generate individual subpaths.

        @return:
        """
        types = self.segments[: self.index, 2]
        q = np.where(types.real == TYPE_END)[0]
        last = 0
        for m in q:
            yield Geomstr(self.segments[last:m])
            last = m + 1
        if last != self.index:
            yield Geomstr(self.segments[last : self.index])

    def two_opt_distance(self, max_passes=None):
        """
        Perform two-opt optimization to minimize travel distances.
        @param max_passes: Max number of passes to attempt
        @return:
        """
        self._trim()
        min_value = -1e-10
        current_pass = 0

        indexes0 = np.arange(0, self.index - 1)
        indexes1 = indexes0 + 1

        segments = self.segments
        improved = True
        while improved:
            improved = False

            first = segments[0][0]
            pen_ups = segments[indexes0, -1]
            pen_downs = segments[indexes1, 0]

            delta = np.abs(first - pen_downs) - np.abs(pen_ups - pen_downs)
            index = int(np.argmin(delta))
            if delta[index] < min_value:
                segments[: index + 1] = np.flip(
                    segments[: index + 1], (0, 1)
                )  # top to bottom, and right to left flips.
                improved = True
            for mid in range(1, self.index - 1):
                idxs = np.arange(mid, self.index - 1)

                mid_source = segments[mid - 1, -1]
                mid_dest = segments[mid, 0]
                pen_ups = segments[idxs, -1]
                pen_downs = segments[idxs + 1, 0]
                delta = (
                    np.abs(mid_source - pen_ups)
                    + np.abs(mid_dest - pen_downs)
                    - np.abs(pen_ups - pen_downs)
                    - np.abs(mid_source - mid_dest)
                )
                index = int(np.argmin(delta))
                if delta[index] < min_value:
                    segments[mid : mid + index + 1] = np.flip(
                        segments[mid : mid + index + 1], (0, 1)
                    )
                    improved = True

            last = segments[-1, -1]
            pen_ups = segments[indexes0, -1]
            pen_downs = segments[indexes1, 0]

            delta = np.abs(pen_ups - last) - np.abs(pen_ups - pen_downs)
            index = int(np.argmin(delta))
            if delta[index] < min_value:
                segments[index + 1 :] = np.flip(
                    segments[index + 1 :], (0, 1)
                )  # top to bottom, and right to left flips.
                improved = True
            if max_passes and current_pass >= max_passes:
                break
            current_pass += 1

    def generator(self):
        """
        Generate plotter code. This should generate individual x, y, power levels for each type of segment.
        The wait and dwell segments generate x, y, with a negative power (consisting of the wait time)
        @return:
        """
        for segment in self.segments[0 : self.index]:
            start = segment[0]
            c0 = segment[1]
            segpow = segment[2]
            c1 = segment[3]
            end = segment[4]
            segment_type = segpow.real
            settings_index = segpow.imag
            if segment_type == TYPE_LINE:
                for x, y in ZinglPlotter.plot_line(
                    start.real, start.imag, end.real, end.imag
                ):
                    yield x, y, settings_index
            elif segment_type == TYPE_QUAD:
                for x, y in ZinglPlotter.plot_quad_bezier(
                    start.real, start.imag, c0.real, c0.imag, end.real, end.imag
                ):
                    yield x, y, settings_index
            elif segment_type == TYPE_CUBIC:
                for x, y in ZinglPlotter.plot_cubic_bezier(
                    start.real,
                    start.imag,
                    c0.real,
                    c0.imag,
                    c1.real,
                    c1.imag,
                    end.real,
                    end.imag,
                ):
                    yield x, y, settings_index
            elif segment_type == TYPE_ARC:
                raise NotImplementedError
            elif segment_type == TYPE_DWELL:
                yield start.real, start.imag, 0
                yield start.real, start.imag, -settings_index
            elif segment_type == TYPE_WAIT:
                yield start.real, start.imag, 0
                yield float("nan"), float("nan"), -settings_index
            elif segment_type == TYPE_RAMP:
                pos = list(
                    ZinglPlotter.plot_line(start.real, start.imag, end.real, end.imag)
                )
                settings_index = np.interp(float(c0), float(c1), len(pos))
                for i, p in enumerate(pos):
                    x, y = p
                    yield x, y, settings_index[i]

    @staticmethod
    def line_intersect(x1, y1, x2, y2, x3, y3, x4, y4):
        denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
        if denom == 0:
            return None  # Parallel.
        ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
        ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom
        if 0.0 <= ua <= 1.0 and 0.0 <= ub <= 1.0:
            return (x1 + ua * (x2 - x1)), (y1 + ua * (y2 - y1))
        return None
