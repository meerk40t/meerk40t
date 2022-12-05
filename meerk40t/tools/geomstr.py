import math

import numpy as np

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

TYPE_LINE = 0
TYPE_QUAD = 1
TYPE_CUBIC = 2
TYPE_ARC = 3
TYPE_POINT = 4

TYPE_RAMP = 0x10
TYPE_VERTEX = 0x79
TYPE_END = 0x80


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


    def polyline(self, points, settings=0):
        """
        Add a series of polyline points
        @param points:
        @param settings:
        @return:
        """
        for i in range(1, len(points)):
            self.line(points[i - 1], points[i], settings=settings)

    def line(self, start, end, settings=0, a=None, b=None):
        """
        Add a line between start and end points at the given settings level

        @param start: complex: start point
        @param end: complex: end point
        @param settings: settings level to assign this particular line.
        @return:
        """
        if a is None:
            a = np.nan
        if b is None:
            b = np.nan
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
            a = np.nan
        if b is None:
            b = np.nan
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

    def arc_radius(self, e):
        line = self.segments[e]
        start = line[0]
        center = self.arc_center(e)
        return abs(start - center)

    def arc_center(self, e):
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

    def segment_point(self, e, t):
        line = self.segments[e]
        if line[2].real == TYPE_LINE:
            point = self._line_point(line, [t])
            return complex(*point)
        elif line[2].real == TYPE_QUAD:
            point = self._quad_point(line, [t])
            return complex(*point)
        elif line[2].real == TYPE_CUBIC:
            point = self._cubic_point(line, [t])
            return complex(*point)

    def _line_point(self, line, positions):
        x0, y0 = line[0].real, line[0].imag
        x1, y1 = line[4].real, line[4].imag
        return np.interp(positions, [0, 1], [x0, x1]), np.interp(
            positions, [0, 1], [y0, y1]
        )

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

    def convex_hull(self, pts):
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
        """Determine the clockwise, linear, or counterclockwise orientation of the given points"""
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
        if isinstance(p, int):
            if p < 0:
                p = self.segments[~p][-1]
            else:
                p = self.segments[p][0]
        dx = math.cos(angle) * r
        dy = math.sin(angle) * r
        return p + complex(dx, dy)

    def reflected(self, p1, p2):
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
            elif segment_type == TYPE_POINT:
                yield start.real, start.imag, settings_index
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
