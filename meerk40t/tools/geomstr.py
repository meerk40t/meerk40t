import math
from copy import copy

import numpy as np

from meerk40t.svgelements import Matrix
from meerk40t.tools.zinglplotter import ZinglPlotter

"""
Geomstr objects store aligned arrays of geom primitives. These primitives are line,
quad, cubic, arc, and point. There are a couple additional structural elements
like end, and vertex. 

All the geom primitives are stored in an array of with a width of 5 complex
numbers. The complex numbers are often, but not always used as points. This
structure is intended to permit not just efficient storage of all geom objects
and mixtures of those  primitives but also to permit efficient reversing
with the use of flips.

The center complex number stores the geom type and a reference point to the
associated settings information. This is usually going to be a dictionary
but objects would work equally well.

Adjacent geoms are part of a run. It's assumed that most geometry accessing 
this data is going travel in a path through each of these points. Disjointed
geoms are considered to be implicit moves. For example:

line (0+0j, 0+50j)
line (50+0j, 50+50j)

is not a connected run, but two disjointed lines. This implies that we moved
between these lines, in fact, we assume that geometry will always travel
from one geom to the next. Except for a structural end type geom. That overtly
declares that no geometry objects should imply any additional links.

A vertex geom does not have an associated set of settings (or a position)
but rather the .imag component of the center complex gives the vertex index.
Any vertex with the same index is the same vertex regardless where it occurs
in the geometry. This means that if a run occurs such that it starts and
ends with vertex #1, this is explicitly a closed path, or rather implicitly
circular, it could still be disjointed. This also means that multiple
different runs or even individual geoms can connect to the same vertex,
creating a graph topography.

All the non-structural geoms have index 0 and index 4 the complex representation
of the start and end points of the geom. The quad and arcs store the same
control point in index 1 and 3. And the cubic stores the first and second
control points in 1 and 3. Point and line may store arbitrary information
in indexes 1 and 3. All geoms store descriptive info in index 2. This means
that reversing geoms and even reversing run of geoms can always be done
with np.flip() calls.

The arc geom is circular and the parameterization is three points, the start,
end and control. If the start and end points are coincident, the control point
is not merely on the arc but is also the furthest point on the arc, located
2*radius distances from the start and end points, the entire geom effectively
denotes a clockwise circle. Note: given that this is degenerate, flipping does
not properly give a counterclockwise circle. If the three points are all
collinear this is effectively a line. If all three points are coincident
this is effectively a point.
"""

# Note lower nibble is which indexes are positions (except info index)
TYPE_NOP = 0 | 0b000
TYPE_POINT = 0x10 | 0b1001
TYPE_LINE = 0x20 | 0b1001
TYPE_QUAD = 0x30 | 0b1111
TYPE_CUBIC = 0x40 | 0b1111
TYPE_ARC = 0x50 | 0b1111

TYPE_VERTEX = 0x70 | 0b0000
TYPE_END = 0x80 | 0b0000


class Pattern:
    def __init__(self, geomstr=None):
        if geomstr is None:
            geomstr = Geomstr()
        self.geomstr = geomstr
        x0, y0, x1, y1 = geomstr.geometry.bbox()
        self.offset_x = x0
        self.offset_y = x0
        self.cell_width = x1-x0
        self.cell_height = y1-y0
        self.padding_x = 0
        self.padding_y = 0

    def create_from_pattern(self, pattern, a=None, b=None, *args, **kwargs):
        """
        Write the pattern to the pattern in patterning format.

        @param pattern: generator of pattern format.
        @return:
        """
        self.offset_x = 0
        self.offset_y = 0
        self.cell_width = 1
        self.cell_height = 1

        path = self.geomstr
        path.clear()
        current = 0j

        for entry in pattern(a, b, *args, **kwargs):
            key = entry[0].lower()
            if key == "m":
                current = complex(entry[1], entry[2])
            elif key == "h":
                endpoint = complex(current.real + entry[1], current.imag)
                path.line(current, endpoint)
                current = endpoint
            elif key == "v":
                endpoint = complex(current.real, current.imag + entry[1])
                path.line(current, endpoint)
                current = endpoint
            elif key == "l":
                # Line to...
                endpoint = complex(entry[1], entry[2])
                path.line(current, endpoint)
                current = endpoint
            elif key == "a":
                control = complex(entry[1], entry[2])
                endpoint = complex(entry[3], entry[4])
                path.arc(current, control, endpoint)
                current = endpoint
            elif key == "c":
                control1 = complex(entry[1], entry[2])
                control2 = complex(entry[3], entry[4])
                endpoint = complex(entry[5], entry[6])
                path.cubic(current, control1, control2, endpoint)
                current = endpoint
            elif key == "q":
                control1 = complex(entry[1], entry[2])
                endpoint = complex(entry[3], entry[4])
                path.quad(current, control1, endpoint)
                current = endpoint
            else:
                raise ValueError("Unrecognized Pattern Element")

    def set_cell_dims_percent(self, percent_x, percent_y):
        # I dunno
        pass

    def set_cell_dims(self, width, height):
        self.cell_width, self.cell_width = width, height

    def set_cell_padding(self, pad_x, pad_y):
        self.padding_x, self.padding_y = pad_x, pad_y

    def generate(self, x0, y0, x1, y1):
        """
        Generates a geomstr pattern between x0, y0, x1 and y1. The pattern may exceed
        the given bounds. It is guaranteed, however, to include all the required pattern
        copies within space given.

        @param x0:
        @param y0:
        @param x1:
        @param y1:
        @return:
        """
        cwidth = self.cell_width
        cheight = self.cell_height
        padding_x = self.padding_x
        padding_y = self.padding_y

        #  Determine rows and columns of cuts to create
        #  will round down so add 1 and trim later
        if cwidth + 2 * padding_x == 0:
            columns = 1
        else:
            columns = int(((x1 - x0) + cwidth)/ (cwidth + (2 * padding_x))) + 1
        if cheight + 2 * padding_y == 0:
            rows = 1
        else:
            rows = int(((y1 - y0) + cheight)/ (cheight + (2 * padding_y))) + 1

        extend_patterns = False

        if extend_patterns:
            start_value = -2
            end_value = 1
            off_x = -1 * (cwidth / 2)
        else:
            columns = max(1, columns - 2)
            rows = max(1, rows - 2)
            start_value = 0
            end_value = 0
            off_x = 0

        for c in range(start_value, columns + end_value, 1):
            top_left_x = x0 + off_x
            x_offset = c * (cwidth + (2 * padding_x))
            x_current = top_left_x + x_offset
            for row in range(start_value, rows + end_value, 1):
                top_left_y = y0
                y_offset = row * (cheight + (2 * padding_y)) + (
                        (cheight + (2 * padding_y)) / 2
                ) * (c % 2)
                y_current = top_left_y + y_offset

                if x_current < x1 and y_current < y1:
                    # Don't call draw if outside of hinge area
                    m = Matrix.translate(x_current - self.offset_x, y_current - self.offset_y)
                    m *= Matrix.scale(self.cell_height, self.cell_height)
                    yield self.geomstr.as_transformed(m)


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


class Geometry:
    """
    Total geomstr functions
    """

    def __init__(self, geomstr):
        self.geomstr = geomstr

    @property
    def segments(self):
        return self.geomstr.segments

    @property
    def index(self):
        return self.geomstr.index

    @property
    def capacity(self):
        return self.geomstr.capacity

    def transform(self, mx):
        """
        Affine Transformation by an arbitrary matrix.
        @param mx: Matrix to transform by
        @return:
        """
        segments = self.geomstr.segments
        index = self.geomstr.index
        starts = segments[:index, 0]
        reals = starts.real * mx.a + starts.imag * mx.c + 1 * mx.e
        imags = starts.real * mx.b + starts.imag * mx.d + 1 * mx.f
        segments[:index, 0] = reals + 1j * imags
        ends = segments[:index, 4]
        reals = ends.real * mx.a + ends.imag * mx.c + 1 * mx.e
        imags = ends.real * mx.b + ends.imag * mx.d + 1 * mx.f
        segments[:index, 4] = reals + 1j * imags

        infos = segments[:index, 2]
        q = np.where(infos.astype(int) & 0b0110)

        c0s = segments[q, 1]
        reals = c0s.real * mx.a + c0s.imag * mx.c + 1 * mx.e
        imags = c0s.real * mx.b + c0s.imag * mx.d + 1 * mx.f
        segments[q, 1] = reals + 1j * imags
        c1s = segments[q, 3]
        reals = c1s.real * mx.a + c1s.imag * mx.c + 1 * mx.e
        imags = c1s.real * mx.b + c1s.imag * mx.d + 1 * mx.f
        segments[q, 3] = reals + 1j * imags

    def translate(self, dx, dy):
        """
        Translate the location within the path.

        @param dx: change in x
        @param dy: change in y
        @return:
        """
        segments = self.geomstr.segments
        index = self.geomstr.index
        segments[:index, 0] += complex(dx, dy)
        segments[:index, 4] += complex(dx, dy)
        infos = segments[:index, 2]
        q = np.where(infos.astype(int) & 0b0110)
        segments[q, 1] += complex(dx, dy)
        segments[q, 3] += complex(dx, dy)

    def uscale(self, scale):
        """
        Uniform scaling operation

        @param scale: uniform scaling factor
        @return:
        """
        segments = self.geomstr.segments
        index = self.geomstr.index
        segments[:index, 0] *= scale
        segments[:index, 4] *= scale
        infos = segments[:index, 2]
        q = np.where(infos.astype(int) & 0b0110)
        segments[q, 1] *= scale
        segments[q, 3] *= scale

    def rotate(self, angle):
        """
        Rotate segments around the origin.
        @param angle: angle in radians
        @return:
        """
        rotation = complex(math.cos(angle), math.sin(angle))
        self.uscale(rotation)

    def bbox(self, mx=None):
        """
        bounding box of the particular segments.
        @param mx: Conditional matrix operation.
        @return:
        """
        # TODO: Doesn't account for mx
        segments = self.geomstr.segments
        index = self.geomstr.index
        min_x, min_y, max_x, max_y = self.geomstr.bbox(segments[0:index])
        if len(min_x) == 0:
            return np.nan, np.nan, np.nan, np.nan
        return np.min(min_x), np.min(min_y), np.max(max_x), np.max(max_y)

    def raw_length(self):
        """
        Determines the raw length of the geoms. Where length is taken as the distance
        from start to end (ignoring any curving), real length would be greater than this
        but never less.

        @return:
        """
        segments = self.geomstr.segments
        index = self.geomstr.index
        infos = segments[:index, 2]
        q = np.where(infos.astype(int) & 0b1001)
        pen_downs = segments[q, 0]
        pen_ups = segments[q, -1]
        return np.sum(np.abs(pen_ups - pen_downs))

    def travel_distance(self):
        """
        Calculate the total travel distance for this geomstr.
        @return: distance in units for the travel
        """
        segments = self.geomstr.segments
        index = self.geomstr.index
        infos = segments[:index, 2]
        q = np.where(infos.astype(int) & 0b1001)
        valid_segments = segments[q]

        indexes0 = np.arange(0, len(valid_segments) - 1)
        indexes1 = indexes0 + 1
        pen_ups = valid_segments[indexes0, -1]
        pen_downs = valid_segments[indexes1, 0]
        return np.sum(np.abs(pen_ups - pen_downs))

    def two_opt_distance(self, max_passes=None):
        """
        Perform two-opt optimization to minimize travel distances.
        @param max_passes: Max number of passes to attempt
        @return:
        """
        self.geomstr._trim()
        segments = self.geomstr.segments
        original = self.geomstr.index

        min_value = -1e-10
        current_pass = 0

        indexes0 = np.arange(0, original - 1)
        indexes1 = indexes0 + 1

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
            for mid in range(1, original - 1):
                idxs = np.arange(mid, original - 1)

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

    def merge(self, other):
        """
        Merge other geomstr with this geomstr. Intersections meet at vertices.
        @param other:
        @return:
        """
        segments = self.geomstr.segments
        index = self.geomstr.index

        intersections = self.find_intersections(other)
        bisectors = {}

        for xi, yi, s, t, idx in intersections:
            bis = bisectors.get(s)
            if bis is None:
                bis = []
                bisectors[s] = bis
            bis.append((xi, yi, s, t, idx))
        original = segments
        total = index + other.index + len(intersections) * 4 + 1
        new_segments = np.zeros((total, 5), dtype="complex")

        itx = 0
        itx = self._bisect_segments(bisectors, original, index, new_segments, itx)
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
        self.geomstr.segments = new_segments
        self.geomstr.index = itx
        self.geomstr.capacity = new_segments.shape[0]
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
        segments = self.geomstr.segments
        index = self.geomstr.index
        idx = 0
        intersections = []
        for s in range(index):
            if int(segments[s, 2].real) & 0xFF != TYPE_LINE:
                continue
            for t in range(other.index):
                if int(other.segments[t, 2].real) & 0xFF != TYPE_LINE:
                    continue
                intersect = Geomstr.line_intersect(
                    segments[s, 0].real,
                    segments[s, 0].imag,
                    segments[s, -1].real,
                    segments[s, -1].imag,
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

    def generator(self):
        """
        Generate plotter code. This should generate individual x, y, power levels for each type of segment.
        The wait and dwell segments generate x, y, with a negative power (consisting of the wait time)
        @return:
        """
        segments = self.geomstr.segments
        index = self.geomstr.index

        for segment in segments[0:index]:
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
            elif segment_type == TYPE_POINT:
                yield start.real, start.imag, settings_index
            # elif segment_type == TYPE_RAMP:
            #     pos = list(
            #         ZinglPlotter.plot_line(start.real, start.imag, end.real, end.imag)
            #     )
            #     settings_index = np.interp(float(c0), float(c1), len(pos))
            #     for i, p in enumerate(pos):
            #         x, y = p
            #         yield x, y, settings_index[i]


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

    def __str__(self):
        return f"Geomstr({self.index} segments)"

    def __repr__(self):
        return f"Geomstr({repr(self.segments[:self.index])})"

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

    @property
    def geometry(self):
        """
        return geometry class for the geomstr object.
        """
        return Geometry(self)

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

    def clear(self):
        self.index = 0

    #######################
    # Geometric Primatives
    #######################

    def line(self, start, end, settings=0, a=None, b=None):
        """
        Add a line between start and end points at the given settings level

        @param start: complex: start point
        @param end: complex: end point
        @param settings: settings level to assign this particular line.
        @return:
        """
        if a is None:
            a = 0
        if b is None:
            b = 0
        self._ensure_capacity(self.index + 1)
        self.segments[self.index] = (
            start,
            a,
            complex(TYPE_LINE, settings),
            b,
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

    def point(self, position, settings=0, a=None, b=None):
        """
        Add in point 1D geometry object.

        @param position: Position at which add point
        @param settings: optional settings level for the point
        @return:
        """
        if a is None:
            a = 0
        if b is None:
            b = 0
        self._ensure_capacity(self.index + 1)
        self.segments[self.index] = (
            position,
            a,
            complex(TYPE_POINT, settings),
            b,
            position,
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
        Add a vertex, a vertex is assumed to be the same point always. Any run that hits a
        vertex is said to have hit a graph-node. If there are two vertexes there is a loop
        if there's more than segments that goto a vertex that is a graph.
        @param vertex: Vertex index of vertex being added
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

    #######################
    # Geometric Helpers
    #######################

    def polyline(self, points, settings=0):
        """
        Add a series of polyline points
        @param points:
        @param settings:
        @return:
        """
        for i in range(1, len(points)):
            self.line(points[i - 1], points[i], settings=settings)

    #######################
    # Query Properties
    #######################
    def segment_type(self, e=None, line=None):
        if line is None:
            line = self.segments[e]

        infor = line[2].real
        if infor == TYPE_LINE:
            return "line"
        if infor == TYPE_QUAD:
            return "quad"
        if infor == TYPE_CUBIC:
            return "cubic"
        if infor == TYPE_ARC:
            return "arc"
        if infor == TYPE_POINT:
            return "arc"
        if infor == TYPE_VERTEX:
            return "vertex"
        if infor == TYPE_END:
            return "end"
        if infor == TYPE_NOP:
            return "nop"

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

    # def deCasteljau(self, control_points, returnArray, t):
    #     """
    #      Performs deCasteljau's algorithm for a bezier curve defined by the given control points.
    #
    #      A cubic for example requires four points. So it should get an array of 8 values
    #
    #      @param control_points (x,y) coord list of the Bezier curve.
    #      @param returnArray    Array to store the solved points. (can be null)
    #      @param t              Amount through the curve we are looking at.
    #      @return returnArray
    #     """
    #     returnArray = deCasteljauEnsureCapacity(returnArray, control_points.length / 2);
    #     System.arraycopy(control_points, 0, returnArray, 0, control_points.length);
    #     return deCasteljau(returnArray, control_points.length / 2, t);
    #
    # def deCasteljau(self, array, length, t):
    #     """
    #     Performs deCasteljau's algorithm for a bezier curve defined by the given control points.
    #
    #     A cubic for example requires four points. So it should get an array of 8 values
    #     @param array  (x,y) coord list of the Bezier curve, with needed interpolation space.
    #     @param length Length of curve in points. 2 = Line, 3 = Quad 4 = Cubic, 5 = Quintic...
    #     @param t      Amount through the curve we are looking at.
    #     @return returnArray
    #     """
    #     m = length * 2;
    #     index = m; # start after the control points.
    #     skip = m - 2; # skip if first compare is the last control position.
    #     array = deCasteljauEnsureCapacity(array, length);
    #     for i in range(0, len(array)-2, 2):
    #         if i == skip:
    #             m = m - 2
    #             skip += m
    #             continue
    #         array[index] = (float) ((t * (array[i + 2] - array[i])) + array[i])
    #         index += 1
    #         array[index] = (float) ((t * (array[i + 3] - array[i + 1])) + array[i + 1])
    #         index += 1
    #     return array
    #
    #
    # def deCasteljauDivide(self, controlPoints, order, t):
    #     """
    #      Given controlpoints and the order, this function returns the subdivided curve and
    #      the relevant data are the first (order + order - 1) datum. Additional space will have
    #      been created and returned as working space for making the relevant curve.
    #
    #      Given 1, 2, 3 it will build
    #        6
    #       4 5
    #      1 2 3
    #
    #      * And reorder that to return, 1 4 6 7 3.
    #      * [0, midpoint] are one curve.
    #      * [midpoint,end] are another curve.
    #      * <p>
    #      * Both curves reuse the midpoint.
    #      * <p>
    #      * UNTESTED!
    #      *
    #      * @param controlPoints at least order control points must be valid.
    #      * @param order         the cardinality of the curve.
    #      * @param t             the amount through that curve.
    #      * @return controlPoints or modified controlPoints object
    #      */
    #      """
    #     controlPoints = deCasteljau(controlPoints, order, t);
    #     size = order + order - 1;
    #     midpoint = order
    #     width = order
    #     r = 1
    #     for w in range(size):
    #         if r == midpoint:
    #             width = order - 1
    #             r = width
    #         else:
    #             r += width
    #             width -= 1
    #             controlPoints[(w << 1)] = controlPoints[(r << 1)];
    #             controlPoints[(w << 1) + 1] = controlPoints[(r << 1) + 1];
    #     # reverse the second half values.
    #     m = (size + midpoint) / 2
    #     i = midpoint * 2
    #     s = size * 2
    #     while  i < m:
    #         swapPoints(controlPoints, i, s)
    #         i += 2
    #         s -= 2
    #     return controlPoints;
    #
    # def deCasteljauEnsureCapacity(self, array, order):
    #     sizeRequired = order * (order + 1)  # equation converts to 2-float 1-position format.
    #     if array is None:
    #         return [0.0] * sizeRequired
    #     if sizeRequired > len(array):
    #         # insure capacity
    #         array.extend([0.0] * (sizeRequired - len(array)))
    #     return array

    #######################
    # Universal Functions
    #######################

    def bbox(self, e):
        """
        Get the bounds of the given geom primitive

        @param e:
        @return:
        """
        if isinstance(e, np.ndarray):
            bboxes = np.zeros((4, len(e)), dtype=float)
            for i in range(len(e)):
                bboxes[:, i] = self.bbox(i)
            return bboxes
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
            extreme_points = self._quad_position(line, local_extremizers)
            local_extrema = extreme_points.real
            xmin = min(local_extrema)
            xmax = max(local_extrema)

            local_extremizers = list(self._quad_local_extremes(1, line))
            extreme_points = self._quad_position(line, local_extremizers)
            local_extrema = extreme_points.imag
            ymin = min(local_extrema)
            ymax = max(local_extrema)

            return xmin, ymin, xmax, ymax
        elif line[2].real == TYPE_CUBIC:
            local_extremizers = list(self._cubic_local_extremes(0, line))
            extreme_points = self._cubic_position(line, local_extremizers)
            local_extrema = extreme_points.real
            xmin = min(local_extrema)
            xmax = max(local_extrema)

            local_extremizers = list(self._cubic_local_extremes(1, line))
            extreme_points = self._cubic_position(line, local_extremizers)
            local_extrema = extreme_points.imag
            ymin = min(local_extrema)
            ymax = max(local_extrema)

            return xmin, ymin, xmax, ymax

    def position(self, e, t):
        """
        Get the position t [0-1] within the geom.

        @param e:
        @param t:
        @return:
        """
        line = self.segments[e]
        if line[2].real == TYPE_LINE:
            point = self._line_position(line, [t])
            return complex(*point)
        elif line[2].real == TYPE_QUAD:
            point = self._quad_position(line, [t])
            return complex(*point)
        elif line[2].real == TYPE_CUBIC:
            point = self._cubic_position(line, [t])
            return complex(*point)
        if line[2].real == TYPE_ARC:
            point = self._arc_position(line, [t])

    def _line_position(self, line, positions):
        x0, y0 = line[0].real, line[0].imag
        x1, y1 = line[4].real, line[4].imag
        return (
            np.interp(positions, [0, 1], [x0, x1])
            + np.interp(positions, [0, 1], [y0, y1]) * 1j
        )

    def _quad_position(self, line, positions):
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

            return (n_pos_2 * x0 + 2 * n_pos_pos * x1 + pos_2 * x2) + (
                n_pos_2 * y0 + 2 * n_pos_pos * y1 + pos_2 * y2
            ) * 1j

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

    def _cubic_position(self, line, positions):
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
                n_pos_3 * x0 + 3 * (n_pos_2_pos * x1 + pos_2_n_pos * x2) + pos_3 * x3
            ) + (
                n_pos_3 * y0 + 3 * (n_pos_2_pos * y1 + pos_2_n_pos * y2) + pos_3 * y3
            ) * 1j

        return _compute_point(np.array(positions))

    def _cubic_local_extremes(self, v, e):
        """
        returns the extreme t values for a cubic Bézier curve, with a non-zero denom
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

    def _arc_position(self, line, positions):
        start, control, info, control2, end = line

        xy = np.empty((len(positions), 2), dtype=float)
        center = self.arc_center(line=line)
        theta = self.angle(center, start)
        sweep = self.arc_sweep(line=line, center=center)

        if start == end and sweep == 0:
            xy[:, 0], xy[:, 1] = start
        else:
            t = theta + positions * sweep
            r = abs(center - start)

            cx = center.real
            cy = center.imag
            cos_t = np.cos(t)
            sin_t = np.sin(t)
            xy[:, 0] = cx + r * cos_t
            xy[:, 1] = cy + r * sin_t

            # ensure clean endings
            xy[positions == 0, :] = list([start.real, start.imag])
            xy[positions == 1, :] = list([end.real, end.imag])

        return xy[:, 0] + xy[:, 1] * 1j

    def length(self, e):
        """
        Returns the length of geom e.

        @param e:
        @return:
        """
        line = self.segments[e]
        start, control1, info, control2, end = line
        if info.real == TYPE_LINE:
            return abs(start - end)
        if info.real == TYPE_QUAD:
            a = start - 2 * control1 + end
            b = 2 * (control1 - start)
            try:
                # For an explanation of this case, see
                # http://www.malczak.info/blog/quadratic-bezier-curve-length/
                A = 4 * (a.real * a.real + a.imag * a.imag)
                B = 4 * (a.real * b.real + a.imag * b.imag)
                C = b.real * b.real + b.imag * b.imag

                Sabc = 2 * math.sqrt(A + B + C)
                A2 = math.sqrt(A)
                A32 = 2 * A * A2
                C2 = 2 * math.sqrt(C)
                BA = B / A2

                s = (
                    A32 * Sabc
                    + A2 * B * (Sabc - C2)
                    + (4 * C * A - B * B) * math.log((2 * A2 + BA + Sabc) / (BA + C2))
                ) / (4 * A32)
            except (ZeroDivisionError, ValueError):
                # a_dot_b = a.real * b.real + a.imag * b.imag
                if abs(a) < 1e-10:
                    s = abs(b)
                else:
                    k = abs(b) / abs(a)
                    if k >= 2:
                        s = abs(b) - abs(a)
                    else:
                        s = abs(a) * (k * k / 2 - k + 1)
            return s
        if info.real == TYPE_CUBIC:
            try:
                return self._cubic_length_via_quad(line)
            except:
                # Absolute fallback
                pass
            positions = self._cubic_position(line, np.linspace(0, 1))
            q = np.arange(0, len(positions) - 1)
            pen_downs = positions[q]  # values 0-49
            pen_ups = positions[q + 1]  # values 1-50
            return np.sum(np.abs(pen_ups - pen_downs))

    def _cubic_length_via_quad(self, line):
        """
        If we have scipy.integrate availible, use quad from that to solve this.

        @param line:
        @return:
        """
        from scipy.integrate import quad

        start, control1, info, control2, end = line

        p0 = start
        p1 = control1
        p2 = control2
        p3 = end

        def _abs_derivative(t):
            return abs(
                3 * (p1 - p0) * (1 - t) ** 2
                + 6 * (p2 - p1) * (1 - t) * t
                + 3 * (p3 - p2) * t**2
            )

        return quad(_abs_derivative, 0.0, 1.0, epsabs=1e-12, limit=1000)[0]

    def split(self, e, t):
        """
        Splits individual geom e at position t [0-1]

        @param e:
        @param t:
        @return:
        """
        raise NotImplementedError

    def normal(self, e, t):
        """
        return the unit-normal (right hand rule) vector to this at t.

        @param e:
        @param t:
        @return:
        """
        return -1j * self.tangent(t)

    def tangent(self, e, t):
        """
        returns the tangent vector of the geom at t (centered at origin).

        @param e:
        @param t:
        @return:
        """
        start, control1, info, control2, end = self.segments[e]

        if info.real == TYPE_LINE:
            dseg = end - start
            return dseg / abs(dseg)

        if info.real in (TYPE_QUAD, TYPE_CUBIC):
            dseg = self.derivative(e, t)

            # Note: dseg might be numpy value, use np.seterr(invalid='raise')
            try:
                unit_tangent = dseg / abs(dseg)
            except (ZeroDivisionError, FloatingPointError):
                # This may be a removable singularity, if so we just need to compute
                # the limit.
                # Note: limit{{dseg / abs(dseg)} = sqrt(limit{dseg**2 / abs(dseg)**2})
                dseg_poly = self.poly(e).deriv()
                dseg_abs_squared_poly = (
                    self._real(dseg_poly) ** 2 + self._imag(dseg_poly) ** 2
                )
                try:
                    unit_tangent = np.sqrt(
                        self._rational_limit(dseg_poly**2, dseg_abs_squared_poly, t)
                    )
                except ValueError:
                    bef = self.poly(e).deriv()(t - 1e-4)
                    aft = self.poly(e).deriv()(t + 1e-4)
                    mes = (
                        f"Unit tangent appears to not be well-defined at t = {t},\n"
                        f"seg.poly().deriv()(t - 1e-4) = {bef}\n"
                        f"seg.poly().deriv()(t + 1e-4) = {aft}"
                    )
                    raise ValueError(mes)
            return unit_tangent

        if info.real == TYPE_ARC:
            dseg = self.derivative(t)
            return dseg / abs(dseg)

    def _rational_limit(self, f, g, t0):
        """Computes the limit of the rational function (f/g)(t)
        as t approaches t0."""
        assert isinstance(f, np.poly1d) and isinstance(g, np.poly1d)
        assert g != np.poly1d([0])
        if g(t0) != 0:
            return f(t0) / g(t0)
        elif f(t0) == 0:
            return self._rational_limit(f.deriv(), g.deriv(), t0)
        else:
            raise ValueError("Limit does not exist.")

    def _real(self, z):
        try:
            return np.poly1d(z.coeffs.real)
        except AttributeError:
            return z.real

    def _imag(self, z):
        try:
            return np.poly1d(z.coeffs.imag)
        except AttributeError:
            return z.imag

    def curvature(self, e, t):
        """
        returns the curvature of the geom at t

        @param e:
        @param t:
        @return:
        """
        start, control1, info, control2, end = self.segments[e]
        if info.real == TYPE_LINE:
            return 0
        if info.real in (TYPE_QUAD, TYPE_CUBIC, TYPE_ARC):
            dz = self.derivative(e, t)
            ddz = self.derivative(e, t, n=2)
            dx, dy = dz.real, dz.imag
            ddx, ddy = ddz.real, ddz.imag
            old_np_seterr = np.seterr(invalid="raise")
            try:
                kappa = abs(dx * ddy - dy * ddx) / math.sqrt(dx * dx + dy * dy) ** 3
            except (ZeroDivisionError, FloatingPointError):
                # tangent vector is zero at t, use polytools to find limit
                p = self.poly(e)
                dp = p.deriv()
                ddp = dp.deriv()
                dx, dy = self._real(dp), self._imag(dp)
                ddx, ddy = self._real(ddp), self._imag(ddp)
                f2 = (dx * ddy - dy * ddx) ** 2
                g2 = (dx * dx + dy * dy) ** 3
                lim2 = self._rational_limit(f2, g2, t)
                if lim2 < 0:  # impossible, must be numerical error
                    return 0
                kappa = np.sqrt(lim2)
            finally:
                np.seterr(**old_np_seterr)
            return kappa

    def _line_coeffs(self, p):
        return [p[4] - p[0], p[0]]

    def _quad_coeffs(self, p):
        return p[0] - 2 * p[1] + p[4], 2 * (p[1] - p[0]), p[0]

    def _cubic_coeffs(self, p):
        return (
            -p[0] + 3 * (p[1] - p[3]) + p[4],
            3 * (p[0] - 2 * p[1] + p[3]),
            3 * (-p[0] + p[1]),
            p[0],
        )

    def poly(self, e):
        """
        Returns segment as polynomial object

        @param e:
        @return:
        """
        line = self.segments[e]
        if line[2].real == TYPE_CUBIC:
            return np.poly1d(self._cubic_coeffs(line))
        if line[2].real == TYPE_QUAD:
            return np.poly1d(self._quad_coeffs(line))
        if line[2].real == TYPE_LINE:
            return np.poly1d(self._line_coeffs(line))

    def derivative(self, e, t, n=1):
        """
        return the nth dervative of the segment e at position t

        @param e:
        @param t:
        @param n:
        @return:
        """
        line = self.segments[e]
        start, control, info, control2, end = line

        if info.real == TYPE_LINE:
            if n == 1:
                return end - start
            return 0

        if info.real == TYPE_QUAD:
            if n == 1:
                return 2 * ((control - start) * (1 - t) + (end - control) * t)
            elif n == 2:
                return 2 * (end - 2 * control + start)
            return 0

        if info.real == TYPE_CUBIC:
            if n == 1:
                return (
                    3 * (control - start) * (1 - t) ** 2
                    + 6 * (control2 - control) * (1 - t) * t
                    + 3 * (end - control2) * t**2
                )
            elif n == 2:
                return 6 * (
                    (1 - t) * (control2 - 2 * control + start)
                    + t * (end - 2 * control2 + control)
                )
            elif n == 3:
                return 6 * (end - 3 * (control2 - control) - start)
            return 0
        if info.real == TYPE_ARC:
            # Delta is angular distance of the arc.
            # Theta is the angle between x-axis and start_point
            center = self.arc_center(e)
            theta = self.angle(center, start)
            sweep = self.arc_sweep(e, center=center)
            angle = theta + t * sweep
            r = abs(center - start)
            k = (sweep * math.tau / 360) ** n  # ((d/dt)angle)**n

            if n % 4 == 0 and n > 0:
                return r * math.cos(angle) + 1j * (r * math.sin(angle))
            elif n % 4 == 1:
                return k * (-r * math.sin(angle) + 1j * (r * math.cos(angle)))
            elif n % 4 == 2:
                return k * (-r * math.cos(angle) + 1j * (-r * math.sin(angle)))
            elif n % 4 == 3:
                return k * (r * math.sin(angle) + 1j * (-r * math.cos(angle)))
            else:
                raise ValueError("n should be a positive integer.")

    def intersections(self, e, other_seg):
        line1 = self.segments[e]
        line2 = self.segments[other_seg]
        start, control1, info, control2, end = line1
        ostart, ocontrol1, oinfo, ocontrol2, oend = line2
        if info.real in (TYPE_LINE, TYPE_QUAD, TYPE_CUBIC) and oinfo.real in (
            TYPE_LINE,
            TYPE_QUAD,
            TYPE_CUBIC,
        ):
            # Fast fail
            if int(info.real) & 0b0110:
                sa = start.real, control1.real, control2.real, end.real
                sb = start.imag, control1.imag, control2.imag, end.imag
            else:
                sa = start.real, end.real
                sb = start.imag, end.imag
            if int(oinfo.real) & 0b0110:
                oa = ostart.real, ocontrol1.real, ocontrol2.real, oend.real
                ob = ostart.imag, ocontrol1.imag, ocontrol2.imag, oend.imag
            else:
                oa = start.real, end.real
                ob = start.imag, end.imag
            if (
                min(oa) > max(sa)
                or max(oa) < min(sa)
                or min(ob) > max(sb)
                or max(ob) < min(sb)
            ):
                return  # There can't be any intersections
        if info.real == TYPE_POINT:
            return
        if oinfo.real == TYPE_POINT:
            return
        if info.real == TYPE_LINE:
            if oinfo.real == TYPE_LINE:
                yield from self._line_line_intersections(line1, line2)
                return
            if oinfo.real == TYPE_QUAD:
                yield from self._line_quad_intersections(line1, line2)
                return
            if oinfo.real == TYPE_CUBIC:
                yield from self._line_cubic_intersections(line1, line2)
                return

        if info.real == TYPE_QUAD:
            if oinfo.real == TYPE_LINE:
                yield from self._line_quad_intersections(line2, line1)
                return

        if info.real == TYPE_CUBIC:
            if oinfo.real == TYPE_LINE:
                yield from self._line_cubic_intersections(line2, line1)
                return
        yield from self._find_intersections(line1, line2)

    def _line_line_intersections(self, line1, line2):
        start, control1, info, control2, end = line1
        ostart, ocontrol1, oinfo, ocontrol2, oend = line2

        a = (start.real, end.real)
        b = (start.imag, end.imag)
        c = (ostart.real, oend.real)
        d = (ostart.imag, oend.imag)
        denom = (a[1] - a[0]) * (d[0] - d[1]) - (b[1] - b[0]) * (c[0] - c[1])
        if np.isclose(denom, 0):
            return
        t1 = (
            c[0] * (b[0] - d[1]) - c[1] * (b[0] - d[0]) - a[0] * (d[0] - d[1])
        ) / denom
        t2 = (
            -(a[1] * (b[0] - d[0]) - a[0] * (b[1] - d[0]) - c[0] * (b[0] - b[1]))
            / denom
        )
        if 0 <= t1 <= 1 and 0 <= t2 <= 1:
            yield t1, t2

    def _polyroots(self, p, realroots=False, condition=lambda r: True):
        """
        Returns the roots of a polynomial with coefficients given in p.
          p[0] * x**n + p[1] * x**(n-1) + ... + p[n-1]*x + p[n]
        INPUT:
        p - Rank-1 array-like object of polynomial coefficients.
        realroots - a boolean.  If true, only real roots will be returned  and the
            condition function can be written assuming all roots are real.
        condition - a boolean-valued function.  Only roots satisfying this will be
            returned.  If realroots==True, these conditions should assume the roots
            are real.
        OUTPUT:
        A list containing the roots of the polynomial.
        NOTE:  This uses np.isclose and np.roots"""
        from itertools import combinations

        roots = np.roots(p)
        if realroots:
            roots = [r.real for r in roots if np.isclose(r.imag, 0)]
        roots = [r for r in roots if condition(r)]

        duplicates = []
        for idx, (r1, r2) in enumerate(combinations(roots, 2)):
            if np.isclose(r1, r2):
                duplicates.append(idx)
        return [r for idx, r in enumerate(roots) if idx not in duplicates]

    def _line_quad_intersections(self, line, bezier):
        line = line[0], line[4]
        bezier = bezier[0], bezier[1], bezier[4]
        # First let's shift the complex plane so that line starts at the origin

        shifted_bezier = [z - line[0] for z in bezier]
        shifted_line_end = line[1] - line[0]
        line_length = abs(shifted_line_end)

        # Now let's rotate the complex plane so that line falls on the x-axis
        rotation_matrix = line_length / shifted_line_end
        transformed_bezier = [rotation_matrix * z for z in shifted_bezier]

        # Now all intersections should be roots of the imaginary component of
        # the transformed bezier
        transformed_bezier_imag = [p.imag for p in transformed_bezier]
        p = transformed_bezier_imag
        # Quad coeffs
        coeffs_y = (p[0] - 2 * p[1] + p[2], 2 * (p[1] - p[0]), p[0])
        # returns real roots 0 <= r <= 1
        roots_y = list(
            self._polyroots(
                coeffs_y, realroots=True, condition=lambda tval: 0 <= tval <= 1
            )
        )

        transformed_bezier_real = [p.real for p in transformed_bezier]
        p = transformed_bezier_real
        for bez_t in set(roots_y):
            # Quad xvalues
            xval = p[0] + bez_t * (2 * (p[1] - p[0]) + bez_t * (p[0] - 2 * p[1] + p[2]))
            if 0 <= xval <= line_length:
                line_t = xval / line_length
                yield bez_t, line_t

    def _line_cubic_intersections(self, line, bezier):
        line = line[0], line[4]
        bezier = bezier[0], bezier[1], bezier[3], bezier[4]
        # First let's shift the complex plane so that line starts at the origin

        shifted_bezier = [z - line[0] for z in bezier]
        shifted_line_end = line[1] - line[0]
        line_length = abs(shifted_line_end)

        # Now let's rotate the complex plane so that line falls on the x-axis
        rotation_matrix = line_length / shifted_line_end
        transformed_bezier = [rotation_matrix * z for z in shifted_bezier]

        # Now all intersections should be roots of the imaginary component of
        # the transformed bezier
        transformed_bezier_imag = [p.imag for p in transformed_bezier]
        p = transformed_bezier_imag
        # Cubic coeffs
        coeffs_y = (
            -p[0] + 3 * (p[1] - p[2]) + p[3],
            3 * (p[0] - 2 * p[1] + p[2]),
            3 * (p[1] - p[0]),
            p[0],
        )
        # returns real roots 0 <= r <= 1
        roots_y = list(
            self._polyroots(
                coeffs_y, realroots=True, condition=lambda tval: 0 <= tval <= 1
            )
        )
        transformed_bezier_real = [p.real for p in transformed_bezier]

        for bez_t in set(roots_y):
            # Cubic xvalue
            xval = p[0] + bez_t * (
                3 * (p[1] - p[0])
                + bez_t
                * (
                    3 * (p[0] + p[2])
                    - 6 * p[1]
                    + bez_t * (-p[0] + 3 * (p[1] - p[2]) + p[3])
                )
            )
            if 0 <= xval <= line_length:
                line_t = xval / line_length
                yield bez_t, line_t

    def _get_segment_function(self, infor):
        if infor == TYPE_LINE:
            return self._line_position
        if infor == TYPE_QUAD:
            return self._quad_position
        if infor == TYPE_CUBIC:
            return self._cubic_position
        if infor == TYPE_ARC:
            return self._arc_position

    def _find_intersections(self, segment1, segment2):
        fun1 = self._get_segment_function(segment1[2].real)
        fun2 = self._get_segment_function(segment2[2].real)
        yield from self._find_intersections_main(segment1, segment2, fun1, fun2)

    def _find_intersections_main(
        self,
        segment1,
        segment2,
        fun1,
        fun2,
        samples=50,
        ta=(0.0, 1.0, None),
        tb=(0.0, 1.0, None),
        depth=0,
        enhancements=2,
        enhance_samples=50,
    ):
        """
        Calculate intersections by linearized polyline intersections with enhancements.
        We calculate probable intersections by linearizing our segment into `sample` polylines
        we then find those intersecting segments and the range of t where those intersections
        could have occurred and then subdivide those segments in a series of enhancements to
        find their intersections with increased precision.

        This code is fast, but it could fail by both finding a rare phantom intersection (if there
        is a low or no enhancements) or by failing to find a real intersection. Because the polylines
        approximation did not intersect in the base case.

        At a resolution of about 1e-15 the intersection calculations become unstable and intersection
        candidates can duplicate or become lost. We terminate at that point and give the last best
        guess.

        :param segment1:
        :param segment2:
        :param samples:
        :param ta:
        :param tb:
        :param depth:
        :param enhancements:
        :param enhance_samples:
        :return:
        """
        assert samples >= 2
        a = np.linspace(ta[0], ta[1], num=samples)
        b = np.linspace(tb[0], tb[1], num=samples)
        step_a = a[1] - a[0]
        step_b = b[1] - b[0]
        j = fun1(segment1, a)
        k = fun2(segment2, b)

        ax1, bx1 = np.meshgrid(np.real(j[:-1]), np.real(k[:-1]))
        ax2, bx2 = np.meshgrid(np.real(j[1:]), np.real(k[1:]))
        ay1, by1 = np.meshgrid(np.imag(j[:-1]), np.imag(k[:-1]))
        ay2, by2 = np.meshgrid(np.imag(j[1:]), np.imag(k[1:]))

        denom = (by2 - by1) * (ax2 - ax1) - (bx2 - bx1) * (ay2 - ay1)
        qa = (bx2 - bx1) * (ay1 - by1) - (by2 - by1) * (ax1 - bx1)
        qb = (ax2 - ax1) * (ay1 - by1) - (ay2 - ay1) * (ax1 - bx1)
        hits = np.dstack(
            (
                denom != 0,  # Cannot be parallel.
                np.sign(denom) == np.sign(qa),  # D and Qa must have same sign.
                np.sign(denom) == np.sign(qb),  # D and Qb must have same sign.
                abs(denom) >= abs(qa),  # D >= Qa (else not between 0 - 1)
                abs(denom) >= abs(qb),  # D >= Qb (else not between 0 - 1)
            )
        ).all(axis=2)
        where_hit = np.argwhere(hits)
        if len(where_hit) != 1 and step_a < 1e-10:
            # We're hits are becoming unstable give last best value.
            if ta[2] is not None and tb[2] is not None:
                yield ta[2], tb[2]
            return

        # Calculate the t values for the intersections
        ta_hit = qa[hits] / denom[hits]
        tb_hit = qb[hits] / denom[hits]

        for i, hit in enumerate(where_hit):

            at = ta[0] + float(hit[1]) * step_a  # Zoomed min+segment intersected.
            bt = tb[0] + float(hit[0]) * step_b
            # Fractional guess within intersected segment
            a_fractional = ta_hit[i] * step_a
            b_fractional = tb_hit[i] * step_b
            if depth == enhancements:
                # We've enhanced as best as we can, yield the current + segment t-value to our answer
                yield at + a_fractional, bt + b_fractional
            else:
                yield from self._find_intersections_main(
                    segment1,
                    segment2,
                    fun1,
                    fun2,
                    ta=(at, at + step_a, at + a_fractional),
                    tb=(bt, bt + step_b, bt + b_fractional),
                    samples=enhance_samples,
                    depth=depth + 1,
                    enhancements=enhancements,
                    enhance_samples=enhance_samples,
                )

    def _find_polyline_intersections(self, a, b):
        """
        Find all intersections between complex-array polylines a and b

        @param a:
        @param b:
        @return:
        """
        old_np_seterr = np.seterr(divide="ignore", invalid="ignore")
        try:
            ax1, bx1 = np.meshgrid(np.real(a[:-1]), np.real(b[:-1]))
            ax2, bx2 = np.meshgrid(np.real(a[1:]), np.real(b[1:]))
            ay1, by1 = np.meshgrid(np.imag(a[:-1]), np.imag(b[:-1]))
            ay2, by2 = np.meshgrid(np.imag(a[1:]), np.imag(b[1:]))

            # Note if denom is zero these are parallel lines.
            denom = (by2 - by1) * (ax2 - ax1) - (bx2 - bx1) * (ay2 - ay1)

            ua = ((bx2 - bx1) * (ay1 - by1) - (by2 - by1) * (ax1 - bx1)) / denom
            ub = ((ax2 - ax1) * (ay1 - by1) - (ay2 - ay1) * (ax1 - bx1)) / denom
            hit = np.dstack((0.0 <= ua, ua <= 1.0, 0.0 <= ub, ub <= 1.0)).all(axis=2)
            ax1 = ax1[hit]
            ay1 = ay1[hit]
            x_vals = ax1 + ua[hit] * (ax2[hit] - ax1)
            y_vals = ay1 + ua[hit] * (ay2[hit] - ay1)
            return x_vals + y_vals * 1j
        finally:
            np.seterr(**old_np_seterr)

    #######################
    # Geom Tranformations
    #######################

    def transform(self, e, mx):
        """
        Affine Transformation by an arbitrary matrix.

        @param e: line to transform
        @param mx: Matrix to transform by
        @return:
        """
        geoms = self.segments[e]

        geoms[0] = (np.real(geoms[0]) * mx.a + np.imag(geoms[0]) * mx.c + 1 * mx.e) + (
            np.real(geoms[0]) * mx.b + np.imag(geoms[0]) * mx.d + 1 * mx.f
        ) * 1j
        geoms[4] = (np.real(geoms[4]) * mx.a + np.imag(geoms[4]) * mx.c + 1 * mx.e) + (
            np.real(geoms[4]) * mx.b + np.imag(geoms[4]) * mx.d + 1 * mx.f
        ) * 1j

        infos = geoms[2]
        q = np.where(infos.astype(int) & 0b0110)
        geoms = self.segments[q]

        geoms[1] = (np.real(geoms[1]) * mx.a + np.imag(geoms[1]) * mx.c + 1 * mx.e) + (
            np.real(geoms[1]) * mx.b + np.imag(geoms[1]) * mx.d + 1 * mx.f
        ) * 1j
        geoms[3] = (np.real(geoms[3]) * mx.a + np.imag(geoms[3]) * mx.c + 1 * mx.e) + (
            np.real(geoms[3]) * mx.b + np.imag(geoms[3]) * mx.d + 1 * mx.f
        ) * 1j

    def translate(self, e, dx, dy):
        """
        Translate the location within the path.

        @param dx: change in x
        @param dy: change in y
        @return:
        """
        geoms = self.segments[e]
        offset = complex(dx, dy)
        geoms[0] += offset
        geoms[4] += offset
        infos = geoms[2]
        q = np.where(infos.astype(int) & 0b0110)
        geoms = self.segments[q]
        geoms[1] += offset
        geoms[3] += offset

    def uscale(self, e, scale):
        """
        Uniform scaling operation

        @param scale: uniform scaling factor
        @return:
        """
        geoms = self.segments[e]
        geoms[0] *= scale
        geoms[4] *= scale

        infos = geoms[2]
        q = np.where(infos.astype(int) & 0b0110)
        geoms = self.segments[q]
        geoms[1] *= scale
        geoms[3] *= scale

    def rotate(self, e, angle):
        """
        Rotate segments around the origin.
        @param angle: angle in radians
        @return:
        """
        rotation = complex(math.cos(angle), math.sin(angle))
        self.uscale(e, rotation)

    def as_transformed(self, mx):
        g = copy(self)
        g.geometry.transform(mx)
        return g

    #######################
    # Arc Functions
    #######################

    def arc_radius(self, e):
        line = self.segments[e]
        start = line[0]
        center = self.arc_center(e)
        return abs(start - center)

    def arc_center(self, e=None, line=None):
        if line is None:
            line = self.segments[e]
        start = line[0]
        control = line[1]
        end = line[4]

        delta_a = control - start
        delta_b = end - control
        ab_mid = (start + control) / 2.0
        bc_mid = (control + end) / 2.0
        if start == end:
            return ab_mid

        if abs(delta_a.real) > 1e-12:
            slope_a = delta_a.imag / delta_a.real
        else:
            slope_a = np.inf

        if abs(delta_b.real) > 1e-12:
            slope_b = delta_b.imag / delta_b.real
        else:
            slope_b = np.inf

        if abs(delta_a.imag) < 1e-12:  # slope_a == 0
            cx = ab_mid.real
            if abs(delta_b.real) < 1e-12:  # slope_b == inf
                return complex(cx, bc_mid.imag)
            if abs(slope_b) > 1e-12:
                return complex(cx, bc_mid.imag + (bc_mid.real - cx) / slope_b)
            return complex(cx, np.inf)
        elif abs(delta_b.imag) < 1e-12:  # slope_b == 0
            cx = bc_mid.real
            if abs(delta_a.imag) < 1e-12:  # slope_a == inf
                return complex(cx, ab_mid.imag)
            return complex(cx, ab_mid.imag + (ab_mid.real - cx) / slope_a)
        elif abs(delta_a.real) < 1e-12:  # slope_a == inf
            cy = ab_mid.imag
            return complex(slope_b * (bc_mid.imag - cy) + bc_mid.real, cy)
        elif abs(delta_b.real) < 1e-12:  # slope_b == inf
            cy = bc_mid.imag
            return complex(slope_a * (ab_mid.imag - cy) + ab_mid.real, cy)
        elif abs(slope_a - slope_b) < 1e-12:
            return ab_mid
        cx = (
            slope_a * slope_b * (ab_mid.imag - bc_mid.imag)
            - slope_a * bc_mid.real
            + slope_b * ab_mid.real
        ) / (slope_b - slope_a)
        cy = ab_mid.imag - (cx - ab_mid.real) / slope_a
        return complex(cx, cy)

    def arc_sweep(self, e=None, line=None, center=None):
        if line is None:
            line = self.segments[e]
        start, control, info, control2, end = line
        if start == end:
            # If start and end are coincident then our sweep is a full cw circle
            return math.tau
        if center is None:
            center = self.arc_center(e)
        start_t = self.angle(center, start)
        end_t = self.angle(center, end)
        sweep = end_t - start_t
        if self.orientation(start, control, end) == "cw":
            return sweep + math.tau
        return sweep

    #######################
    # Point/Endpoint Functions
    #######################

    def convex_hull(self, pts):
        """
        Generate points of the convex hull around the given points.

        If a point refers to a non-point with differing start/end values then
        ~index refers to the endpoint and index refers to the start point.

        Also accepts complex number coordinates, instead of geom endpoint.

        @param pts:
        @return:
        """
        if len(pts) == 0:
            return
        points = []
        for i in range(len(pts)):
            p = pts[i]
            if isinstance(p, int):
                if p < 0:
                    p = self.segments[~p][-1]
                else:
                    p = self.segments[p][0]
            points.append(p)
        points = sorted(set(points), key=lambda p: p.real)
        first_point_on_hull = points[0]
        point_on_hull = first_point_on_hull
        while True:
            yield point_on_hull
            endpoint = point_on_hull
            for t in points:
                if (
                    point_on_hull is endpoint
                    or Geomstr.orientation(None, point_on_hull, t, endpoint) == "ccw"
                ):
                    endpoint = t
            point_on_hull = endpoint
            if first_point_on_hull is point_on_hull:
                break

    def orientation(self, p, q, r):
        """
        Determine the clockwise, linear, or counterclockwise orientation of the given
        points.

        If p, q, r refers to a non-point with differing start/end values then
        ~index refers to the endpoint and index refers to the start point.

        Also accepts complex number coordinates, instead of geom endpoint.
        """
        if isinstance(p, int):
            if p < 0:
                p = self.segments[~p][-1]
            else:
                p = self.segments[p][0]
        if isinstance(q, int):
            if q < 0:
                q = self.segments[~q][-1]
            else:
                q = self.segments[q][0]
        if isinstance(r, int):
            if r < 0:
                r = self.segments[~r][-1]
            else:
                r = self.segments[r][0]
        val = (q.imag - p.imag) * (r.real - q.real) - (q.real - p.real) * (
            r.imag - q.imag
        )
        if val == 0:
            return "linear"
        elif val > 0:
            return "cw"
        else:
            return "ccw"

    def polar(self, p, angle, r):
        """
        polar position from p at angle and distance r.

        If p refers to a non-point with differing start/end values then ~index
        refers to the endpoint and index refers to the start point.

        Also accepts complex number coordinates, instead of geom endpoint.

        @param p:
        @param angle:
        @param r:
        @return:
        """
        if isinstance(p, int):
            if p < 0:
                p = self.segments[~p][-1]
            else:
                p = self.segments[p][0]
        dx = math.cos(angle) * r
        dy = math.sin(angle) * r
        return p + complex(dx, dy)

    def reflected(self, p1, p2):
        """
        p1 reflected across p2

        If p1 or p2 refers to a non-point with differing start/end values then
        ~index refers to the endpoint and index refers to the start point.

        Also accepts complex number coordinates, instead of geom endpoint.

        @param p1:
        @param p2:
        @return:
        """
        if isinstance(p1, int):
            if p1 < 0:
                p1 = self.segments[~p1][-1]
            else:
                p1 = self.segments[p1][0]
        if isinstance(p2, int):
            if p2 < 0:
                p2 = self.segments[~p2][-1]
            else:
                p2 = self.segments[p2][0]
        return p2 + (p2 - p1)

    def angle(self, p1, p2):
        """
        Angle from p1 to p2

        If p1 or p2 refers to a non-point with differing start/end values then
        ~index refers to the endpoint and index refers to the start point.

        Also accepts complex number coordinates, instead of geom endpoint.

        @param p1:
        @param p2:
        @return:
        """
        if isinstance(p1, int):
            if p1 < 0:
                p1 = self.segments[~p1][-1]
            else:
                p1 = self.segments[p1][0]
        if isinstance(p2, int):
            if p2 < 0:
                p2 = self.segments[~p2][-1]
            else:
                p2 = self.segments[p2][0]
        d = p2 - p1
        return math.atan2(d.imag, d.real)

    def towards(self, p1, p2, amount):
        """
        Position from p1 towards p2 by amount.

        If p1 or p2 refers to a non-point with differing start/end values then
        ~index refers to the endpoint and index refers to the start point.

        Also accepts complex number coordinates, instead of geom endpoint.

        @param p1:
        @param p2:
        @param amount:
        @return:
        """
        if isinstance(p1, int):
            if p1 < 0:
                p1 = self.segments[~p1][-1]
            else:
                p1 = self.segments[p1][0]
        if isinstance(p2, int):
            if p2 < 0:
                p2 = self.segments[~p2][-1]
            else:
                p2 = self.segments[p2][0]
        return amount * (p2 - p1) + p1

    def distance(self, p1, p2):
        """
        Distance between points.
        If p1 or p2 refers to a non-point with differing start/end values then
        ~index refers to the endpoint and index refers to the start point.

        Also accepts complex number coordinates, instead of geom endpoint.

        @param p1:
        @param p2:
        @return:
        """
        if isinstance(p1, int):
            if p1 < 0:
                p1 = self.segments[~p1][-1]
            else:
                p1 = self.segments[p1][0]
        if isinstance(p2, int):
            if p2 < 0:
                p2 = self.segments[~p2][-1]
            else:
                p2 = self.segments[p2][0]
        return abs(p1 - p2)

    #######################
    # Line-Like Functions
    #######################

    def slope(self, e):
        """
        Slope of line between start and end points.

        @param e:
        @return:
        """
        line = self.segments[e]
        a = line[0]
        b = line[-1]
        if b.real - a.real == 0:
            return float("inf")
        return (b.imag - a.imag) / (b.real - a.real)

    def y_intercept(self, e):
        """
        y_intercept value between start and end points.

        @param e:
        @return:
        """
        line = self.segments[e]
        a = line[0]
        b = line[-1]
        if b.real - a.real == 0:
            return float("inf")
        im = (b.imag - a.imag) / (b.real - a.real)
        return a.imag - (im * a.real)

    def endpoint_min_y(self, e):
        """
        returns which endpoint has a larger value for y.

        @param e:
        @return:
        """
        line = self.segments[e]
        a = line[0]
        b = line[-1]
        if a.imag < b.imag:
            return a
        else:
            return b

    def endpoint_max_y(self, e):
        """
        returns which endpoint has a smaller value for y.

        @param e:
        @return:
        """
        line = self.segments[e]
        a = line[0]
        b = line[-1]
        if a.imag > b.imag:
            return a
        else:
            return b

    def endpoint_min_x(self, e):
        """
        returns which endpoint has a larger value for x.

        @param e:
        @return:
        """
        line = self.segments[e]
        a = line[0]
        b = line[-1]
        if a.real < b.real:
            return a
        else:
            return b

    def endpoint_max_x(self, e):
        """
        returns which endpoint has a smaller value for x.

        @param e:
        @return:
        """
        line = self.segments[e]
        a = line[0]
        b = line[-1]
        if a.real > b.real:
            return a
        else:
            return b

    def x_intercept(self, e, y):
        """
        Gives the x_intercept of a line at a specific value of y.

        @param e:
        @param y:
        @return:
        """
        m = self.slope(e)
        b = self.y_intercept(e)
        if math.isnan(m) or math.isinf(m):
            low = self.endpoint_min_y(e)
            return low.real
        return (y - b) / m

    #######################
    # Geometry Window Functions
    #######################

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
