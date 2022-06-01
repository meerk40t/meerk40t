import math

import numpy as np

from meerk40t.tools.zinglplotter import ZinglPlotter

"""
The idea behind numpy laser paths is to define a common structure that could replace the whole of cutcode and do so
in a way that could be both be faster and more compact for other data structures commonly used throughout meerk40t.

* Some drivers can use direct circular arcs, lines, and bezier curves. We should also avoid prematurely interpolating
our data prior to knowing what types of data the driver might want or accept.
* Some drivers accept and use pure step versions of our code. Rather than using lines we would more directly use 
individual orthogonal steps.
* Some drivers can and do use dwell points in that they can go to a particular location and turn the laser on for a
period of time.
* Rasters are converted into a series of tiny steps that are either on or off but are so plentiful that attempting to
render them results in an unusably slow program.
* We should/must optimize our pathing such that we can minimize travel time.
* Some hatch operations result in many disjointed paths similar to what we get with rasters. The current selection of
objects to capture this data requires many node objects and is considerably lengthy.

For these reasons, I am introducing the numpath class which uses numpy to define these geometric objects, as well as
some highly laser specific ones, with enough generalization to capture considerable other forms.

Each segment consists of 5 complex values, these are:
Start, Control1, Type/Power, Control2, End

Every type of geometric connection is defined by these elements:
* Line: Start, NOP, Type=0, NOP, End
* Quad: Start, C0, Type=1, C0, End -- Note C0 is duplicated and identical, only one needs to be read.
* Cubic: Start, C0, Type=2, C1, End
* Arc: Start, C0, Type=3, C0, End -- Note C0 is duplicated and identical (circular)
* Dwell: Start, NOP, Type=4/Time, NOP, Start -- Note, Start and End are the same point.

Note: the Arc is defined by 3 points. Start, end, and a single control point, this is a circular-arc only and does
not do elliptical arcs since they are weird/complex and no laser appears to use them.

Additional extensions can be added by expanding the type parameters. Since each set of values is a complex, the points
provide x and y values. The type parameter provides the power, except for Dwell where it provides the time for the 
dwell.

At first glance the structure may seem somewhat unusual but the `Position, Position, type, Position, Position` structure 
serves a utilitarian purpose. All paths are reversible. To do this we apply a flip of these parameters. The start and
end points swap as well as the control points for the cubic. Whereas the type parameter remains in the same position.
If we want to reverse any number of segments the numpy flip operation can be done over the x and y axis. This provides
the list of segments in reverse order while also reversing all the segments themselves.

There are a few laser segments which may not be in principle reversible. For example, Ruida has some segments which
start at one power and ramp up to a second amount of power. In this case, the reverse of this should attenuate power
over that length rather than ramp it up. In such cases the C0 and C1 places could be adapted to set the power, and
a flip would attenuate the power in the other direction. This wouldn't work for a segment that would need to do both,
for example a power-ramping cubic-bezier segments. But, the same rules apply for any geometric segments, they should
be written such that the reversed-form is the reverse of that segment.

This class is expected to be able to replace many uses of the Path class as well as all cutcode.
"""

TYPE_LINE = 0
TYPE_QUAD = 1
TYPE_CUBIC = 2
TYPE_ARC = 3
TYPE_DWELL = 4
TYPE_WAIT = 5
TYPE_RAMP = 6


class Numpath:
    def __init__(self):
        self.length = 0
        self.capacity = 12
        self.segments = np.zeros((self.capacity, 5), dtype="complex")

    def __copy__(self):
        numpath = Numpath()
        numpath.length = self.length
        numpath.capacity = self.capacity
        numpath.segments = np.copy(self.segments)
        return numpath

    def bbox(self):
        max_value = max(np.max(self.segments[:self.length, 0]), np.max(self.segments[:self.length, 4]))
        min_value = max(np.min(self.segments[:self.length, 0]), np.min(self.segments[:self.length, 4]))
        return min_value.real, min_value.imag, max_value.real, max_value.imag

    def translate(self, dx, dy):
        self.segments[:self.length, 0] += complex(dx, dy)
        self.segments[:self.length, 4] += complex(dx, dy)
        types = self.segments[:self.length, 2]
        q = np.where(types.astype(int) != TYPE_RAMP)
        self.segments[q, 1] += complex(dx, dy)
        self.segments[q, 3] += complex(dx, dy)

    def uscale(self, scale):
        self.segments[:self.length, 0] *= scale
        self.segments[:self.length, 4] *= scale
        types = self.segments[:self.length, 2]
        q = np.where(types.astype(int) != TYPE_RAMP)
        self.segments[q, 1] *= scale
        self.segments[q, 3] *= scale

    def rotate(self, angle):
        rotation = complex(math.cos(angle), math.sin(angle))
        self.uscale(rotation)

    def transform(self, mx):
        for segment in self.segments[0: self.length]:
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

    @property
    def first_point(self):
        if self.length:
            return self.segments[0,0]
        else:
            return None

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

    def add_polyline(self, lines, power=1.0):
        for i in range(1, len(lines)):
            self.add_line(lines[i-1], lines[i], power=power)

    def add_line(self, start, end, power=1.0):
        self._ensure_capacity(self.length + 1)
        self.segments[self.length] = (
            start,
            start,
            complex(TYPE_LINE, power),
            end,
            end,
        )
        self.length += 1

    def add_quad(self, start, control, end, power=1.0):
        self._ensure_capacity(self.length + 1)
        self.segments[self.length] = (
            start,
            control,
            complex(TYPE_QUAD, power),
            control,
            end,
        )
        self.length += 1

    def add_cubic(self, start, control0, control1, end, power=1.0):
        self._ensure_capacity(self.length + 1)
        self.segments[self.length] = (
            start,
            control0,
            complex(TYPE_CUBIC, power),
            control1,
            end,
        )
        self.length += 1

    def add_arc(self, start, control, end, power=1.0):
        self._ensure_capacity(self.length + 1)
        self.segments[self.length] = (
            start,
            control,
            complex(TYPE_ARC, power),
            control,
            end,
        )
        self.length += 1

    def add_dwell(self, position, time=1.0):
        self._ensure_capacity(self.length + 1)
        self.segments[self.length] = (
            position,
            position,
            complex(TYPE_DWELL, time),
            position,
            position,
        )
        self.length += 1

    def add_wait(self, position, time=1.0):
        self._ensure_capacity(self.length + 1)
        self.segments[self.length] = (
            position,
            position,
            complex(TYPE_WAIT, time),
            position,
            position,
        )
        self.length += 1

    def add_ramp(self, start, end, power_start=0.0, power_end=1.0):
        self._ensure_capacity(self.length + 1)
        self.segments[self.length] = (
            start,
            power_start,
            complex(TYPE_RAMP, 1),
            power_end,
            end,
        )
        self.length += 1

    def travel_distance(self):
        indexes0 = np.arange(0, self.length - 1)
        indexes1 = indexes0 + 1
        pen_ups = self.segments[indexes0, -1]
        pen_downs = self.segments[indexes1, 0]
        return np.sum(np.abs(pen_ups - pen_downs))

    def two_opt_distance(self, max_passes=None):
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
                yield float('nan'), float('nan'), -power
            elif segment_type == TYPE_RAMP:
                pos = list(
                    ZinglPlotter.plot_line(start.real, start.imag, end.real, end.imag)
                )
                power = np.interp(float(c0), float(c1), len(pos))
                for i, p in enumerate(pos):
                    x, y = p
                    yield x, y, power[i]
