import math

import numpy as np

from meerk40t.tools.zinglplotter import ZinglPlotter

"""
The idea behind numpy laser paths is to define a common structure that could replace the whole of cutcode and do so in a
way that could be both be faster and more compact for other data structures commonly used throughout Meerk40t.

* Some drivers can use direct circular arcs, lines, and others use bezier curves. We should also avoid prematurely
interpolating our data prior to knowing what types of data the driver might want or accept.
* Some drivers accept and use pure step versions of our code. Rather than using lines we would more directly use
individual orthogonal steps.
* Some drivers can use dwell points, in that, they can go to a particular location and turn the laser on for a period
of time.
* Rasters are converted into a series of tiny steps that are usually either on or off but these are so plentiful that
attempting to render them results in an unusably slow program.
* We should/must optimize our pathing such that we can minimize travel time.
* Some hatch operations result in many disjointed paths. The current objects we have to capture this data requires many
node objects and is very inefficient.

For these reasons we have the numpath class which uses numpy arrays to define geometric and highly laser-specific
objects, with enough generalization to capture hypothetical additional forms.

Each segment is defined by 5 complex values, these are:

`Start, Control1, Type/Settings, Control2, End`

* Line: Start, NOP, Type=0, NOP, End
* Quad: Start, C0, Type=1, C0, End  -- Note C0 is duplicated and identical. But, only one needs to be read.
* Cubic: Start, C0, Type=2, C1, End
* Arc: Start, C0, Type=3, C0, End -- Note C0 is duplicated and identical.
* Dwell: Start, NOP, Type=4, NOP, Start -- Note, Start and End are the same point.
* Wait: NOP, NOP, Type=5, NOP, NOP, -- Note, Start and End are the same point.
* Ramp: Start, PStart, Type=6, PEnd, End -- Power ramp line.
* End: NOP, NOP, Type=99, NOP, NOP -- Structural segment.
* Vertex, NOP, NOP, Type=100/Index, NOP, NOP -- Structural segment. 

Note: the Arc is circular only and defined by 3 points. Start, End, and a single control point. It does not do
elliptical arcs since they are weird/complex and no laser appears to use them.

Additional extensions can be added by expanding the type parameters. Since each set of values is a complex, the points
provide x and y values (real, imag). The type parameter (index 2) provides the power, except for Dwell and Wait where
it provides the time.

At first glance the structure may seem somewhat unusual but the `Position, Position, Type, Position, Position`
structure  serves a utilitarian purpose. All paths are reversible. We can flip this data, to reverse these segments.
The start and end points can swap as well as the control points for the cubic, and the power-start and power-end for
Ramp. Whereas the types of parameter remains in the same position.

The numpy flip operation can be done over the x and y axis. This provides the list of segments in reverse order while
also reversing all the segments themselves. This is the key to doing 2-opt travel minimization, which are provided in
the code.

Ruida has some segments which start at one power and ramp up to a second amount of power. In this case, the reverse of
this needs to attenuate power over that length. In such a case the C0 and C1 places are adapted to set the power.

This class is expected to be able to replace many uses of the Path class as well as all cutcode, permitting all affine
transformations, and serve as a laser-first data structure. These should serve as faster laser-centric path-like code.

Each path's imaginary middle part points to a settings index. These are the settings being used to draw this geometry
with whatever device is performing the drawing. So if the laser had frequency or if an embroidery machine had
multi-needles you could refer to the expected thread-color of the segment. If There's only one set of settings all 
segments may point to same object etc.

There are two primary structural nodes types. These are END and VERTEX. The END indicates that a particular walk was
finished and that the END of that walk has been reached. A VERTEX indicates that we occupy the same space
as all other VERTEX nodes with that index, no validation will be made to determine if all strings terminating in the
same vertex are coincident. A shape is closed if both the shape starts and ends a the same vertex.

VERTEX also provides us with usable graph topologies. We can consider the difference between a closed and opened path
whether both ends terminate in the same vertex (assuming no other path strings) use the same vertex.

Segment strings are defined by runs. These are adjacent segments without END or VERTEX. Runs can be disjointed this
implies the position was moved. Usually this difference in position should be 0. Structural nodes like VERTEX work on
both sides. For example, 

Vertex 0
Line A, B
Line B, C
Vertex 1
Line C, D
Line D, E
Vertex 0

The run goes V0, A->B, B->C V1 and a different run goes V1, C->D, D->E, V0. These definitions imply that V0 is located
at points A and E and for valid geometry probably should be. However, this is merely implied. We may define another run
as V1, Line C->Z.

All runs are reversible. In fact, the reason for the 5 complex structure is so that each segment can reverse with
a flip.
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


class Numpath:
    def __init__(self, segments=None):
        if segments is not None:
            self.segments = segments
            self.length = len(self.segments)
            self.capacity = self.length
        else:
            self.length = 0
            self.capacity = 12
            self.segments = np.zeros((self.capacity, 5), dtype="complex")

    def __copy__(self):
        """
        Create a numpath copy.
        @return: Copy of numpath.
        """
        numpath = Numpath()
        numpath.length = self.length
        numpath.capacity = self.capacity
        numpath.segments = np.copy(self.segments)
        return numpath

    def __len__(self):
        """

        @return: length of the numpath (note not the capacity).
        """
        return self.length

    def _ensure_capacity(self, capacity):
        if self.capacity > capacity:
            return
        self.capacity = self.capacity << 1
        new_segments = np.zeros((self.capacity, 5), dtype="complex")
        new_segments[0 : self.length] = self.segments[0 : self.length]
        self.segments = new_segments

    def _trim(self):
        if self.length != self.capacity:
            self.capacity = self.length
            self.segments = self.segments[0 : self.length]

    @property
    def first_point(self):
        """
        First point within the path if said point exists
        @return:
        """
        if self.length:
            return self.segments[0, 0]
        else:
            return None

    def bbox(self, mx=None):
        """
        bounding box of the particular segments.
        @param mx: Conditional matrix operation.
        @return:
        """
        segments = self.segments[: self.length]
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

    def transform(self, mx):
        """
        Affine Transformation by an arbitrary matrix.
        @param mx: Matrix to transform by
        @return:
        """
        for segment in self.segments[0 : self.length]:
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
        self.segments[: self.length, 0] += complex(dx, dy)
        self.segments[: self.length, 4] += complex(dx, dy)
        types = self.segments[: self.length, 2]
        q = np.where(types.astype(int) != TYPE_RAMP)
        self.segments[q, 1] += complex(dx, dy)
        self.segments[q, 3] += complex(dx, dy)

    def uscale(self, scale):
        """
        Uniform scaling operation

        @param scale: uniform scaling factor
        @return:
        """
        self.segments[: self.length, 0] *= scale
        self.segments[: self.length, 4] *= scale
        types = self.segments[: self.length, 2]
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

    def close(self, power=1.0):
        """
        Close the current path if possible. This merely connects the end of the current path to the original point of
        the current path. (After any TYPE_BREAK commands).
        @param power:
        @return:
        """
        if self.length == 0:
            raise ValueError("Empty path cannot close")
        self._ensure_capacity(self.length + 1)
        types = self.segments[: self.length, 2]
        q = np.where(np.real(types) == TYPE_END)[0]
        if len(q):
            last = q[-1] + 1
            if self.length <= last:
                raise ValueError("Empty path cannot close")
        else:
            last = 0
        start_segment = self.segments[last][0]
        end_segment = self.segments[self.length - 1][-1]
        if start_segment != end_segment:
            self.line(end_segment, start_segment, power=power)

    def polyline(self, points, power=1.0):
        """
        Add a series of polyline points
        @param points:
        @param power:
        @return:
        """
        for i in range(1, len(points)):
            self.line(points[i - 1], points[i], power=power)

    def line(self, start, end, power=1.0):
        """
        Add a line between start and end points at the given power level

        @param start: complex: start point
        @param end: complex: end point
        @param power: power level to assign this particular line.
        @return:
        """
        self._ensure_capacity(self.length + 1)
        self.segments[self.length] = (
            start,
            start,
            complex(TYPE_LINE, power),
            end,
            end,
        )
        self.length += 1

    def quad(self, start, control, end, power=1.0):
        """
        Add a quadratic bezier curve.
        @param start: (complex) start point
        @param control: (complex) control point
        @param end: (complex) end point
        @param power: optional power level for the quadratic bezier curve
        @return:
        """
        self._ensure_capacity(self.length + 1)
        self.segments[self.length] = (
            start,
            control,
            complex(TYPE_QUAD, power),
            control,
            end,
        )
        self.length += 1

    def cubic(self, start, control0, control1, end, power=1.0):
        """
        Add in a cubic bezier curve
        @param start: (complex) start point
        @param control0: (complex) first control point
        @param control1: (complex) second control point
        @param end: (complex) end point
        @param power: optional power level for the cubic bezier curve
        @return:
        """
        self._ensure_capacity(self.length + 1)
        self.segments[self.length] = (
            start,
            control0,
            complex(TYPE_CUBIC, power),
            control1,
            end,
        )
        self.length += 1

    def arc(self, start, control, end, power=1.0):
        """
        Add in a circular arc curve
        @param start: (complex) start point
        @param control:(complex) control point
        @param end: (complex) end point
        @param power: optional power level for the arc
        @return:
        """
        self._ensure_capacity(self.length + 1)
        self.segments[self.length] = (
            start,
            control,
            complex(TYPE_ARC, power),
            control,
            end,
        )
        self.length += 1

    def dwell(self, position, time):
        """
        Add in dwell time to fire the laser standing at a particular point.

        @param position: Position at which to fire the laser
        @param time: time in ms to fire the laser
        @return:
        """
        self._ensure_capacity(self.length + 1)
        self.segments[self.length] = (
            position,
            position,
            complex(TYPE_DWELL, time),
            position,
            position,
        )
        self.length += 1

    def wait(self, position, time):
        """
        Add in wait time to stand for the laser
        @param position: Position to wait at
        @param time: time in seconds to wait
        @return:
        """
        self._ensure_capacity(self.length + 1)
        self.segments[self.length] = (
            position,
            position,
            complex(TYPE_WAIT, time),
            position,
            position,
        )
        self.length += 1

    def ramp(self, start, end, power_start=0.0, power_end=1.0):
        """
        Power ramping line.

        @param start: (complex) start point
        @param end: (complex) end point
        @param power_start: starting power
        @param power_end: ending power
        @return:
        """
        self._ensure_capacity(self.length + 1)
        self.segments[self.length] = (
            start,
            power_start,
            complex(TYPE_RAMP, 1),
            power_end,
            end,
        )
        self.length += 1

    def end(self, power=1.0):
        """
        Adds a structural break in the current path. Two structural breaks are assumed to be a new path.
        @param power: Unused power value for break.
        @return:
        """
        self._ensure_capacity(self.length + 1)
        self.segments[self.length] = (
            float("nan"),
            float("nan"),
            complex(TYPE_END, power),
            float("nan"),
            float("nan"),
        )
        self.length += 1

    def as_subpaths(self):
        """
        Generate individual subpaths.

        @return:
        """
        types = self.segments[: self.length, 2]
        q = np.where(types.real == TYPE_END)[0]
        last = 0
        for m in q:
            yield Numpath(self.segments[last:m])
            last = m + 1
        if last != self.length:
            yield Numpath(self.segments[last : self.length])

    def travel_distance(self):
        """
        Calculate the total travel distance for this numpath.
        @return: distance in units for the travel
        """
        # TODO: Update for NOP start/end points
        indexes0 = np.arange(0, self.length - 1)
        indexes1 = indexes0 + 1
        pen_ups = self.segments[indexes0, -1]
        pen_downs = self.segments[indexes1, 0]
        return np.sum(np.abs(pen_ups - pen_downs))

    def two_opt_distance(self, max_passes=None):
        """
        Perform two-opt optimization to minimize travel distances.
        @param max_passes: Max number of passes to attempt
        @return:
        """
        self._trim()
        min_value = -1e-10
        current_pass = 0

        indexes0 = np.arange(0, self.length - 1)
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
            for mid in range(1, self.length - 1):
                idxs = np.arange(mid, self.length - 1)

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
        for segment in self.segments[0 : self.length]:
            start = segment[0]
            c0 = segment[1]
            segpow = segment[2]
            c1 = segment[3]
            end = segment[4]
            segment_type = segpow.real
            power = segpow.imag
            if segment_type == TYPE_LINE:
                for x, y in ZinglPlotter.plot_line(
                    start.real, start.imag, end.real, end.imag
                ):
                    yield x, y, power
            elif segment_type == TYPE_QUAD:
                for x, y in ZinglPlotter.plot_quad_bezier(
                    start.real, start.imag, c0.real, c0.imag, end.real, end.imag
                ):
                    yield x, y, power
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
                    yield x, y, power
            elif segment_type == TYPE_ARC:
                raise NotImplementedError
            elif segment_type == TYPE_DWELL:
                yield start.real, start.imag, 0
                yield start.real, start.imag, -power
            elif segment_type == TYPE_WAIT:
                yield start.real, start.imag, 0
                yield float("nan"), float("nan"), -power
            elif segment_type == TYPE_RAMP:
                pos = list(
                    ZinglPlotter.plot_line(start.real, start.imag, end.real, end.imag)
                )
                power = np.interp(float(c0), float(c1), len(pos))
                for i, p in enumerate(pos):
                    x, y = p
                    yield x, y, power[i]
