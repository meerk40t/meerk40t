"""
Geomstr objects store aligned arrays of geom primitives. These primitives are line,
quad, cubic, arc, and point. There are a couple additional structural elements
like end, and vertex.

All the geom primitives are stored in an array of with a width of 5 complex
numbers. The complex numbers are often, but not always used as points. This
structure is intended to permit not just efficient storage of all geom objects
and mixtures of those primitives but also to permit efficient reversing
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

Notabene: this module contains some fragments of non-geometric nature, intended
to recreate the logic of cutcode elements, e.g. how often certain segments should
be repeated, whether a function ie transformation should be applied to them etc.
These were introduced by tatarize in late 2023/early 2024 and haven't been completed.
For the time being they aren't understood and might be eliminated in the future
until they have been examined, comprehended and ready to be reintegrated.
This is everything around TYPE_CALL, TYPE_FUNCTION, TYPE_UNTIL
The logic is understood as of now as:
You enclose a couple of regular segments with a start and an end tag:
<TYPE_FUNCTION> ...segments... <TYPE_UNTIL>
Function

"""
import math
import re
from contextlib import contextmanager
from copy import copy

import numpy
import numpy as np

from meerk40t.svgelements import (
    Arc,
    Close,
    CubicBezier,
    Line,
    Matrix,
    Move,
    Path,
    QuadraticBezier,
)
from meerk40t.tools.pmatrix import PMatrix
from meerk40t.tools.zinglplotter import ZinglPlotter

# Note lower nibble is which indexes are positions (except info index)
TYPE_NOP = 0x00 | 0b0000
TYPE_POINT = 0x10 | 0b1001
TYPE_LINE = 0x20 | 0b1001
TYPE_QUAD = 0x30 | 0b1111
TYPE_CUBIC = 0x40 | 0b1111
TYPE_ARC = 0x50 | 0b1111

TYPE_VERTEX = 0x70 | 0b0000
TYPE_END = 0x80 | 0b0000

# Function and Call denote 4 points being the upper-left, upper-right, lower-right,
# lower-left corners all shapes are transformed to match these points, including other call points.
TYPE_FUNCTION = 0x90 | 0b1111  # The two higher level bytes are call label index.
TYPE_UNTIL = (
    0xA0 | 0b0000
)  # The two higher level bytes are the number of times this should be executed before exiting.
TYPE_CALL = 0xB0 | 0b1111  # The two higher level bytes are call label index.
# If until is set to 0xFFFF termination only happens on interrupt.

# A summary of all points that have a special meaning, ie intended for other uses than pure geometry
META_TYPES = (TYPE_NOP, TYPE_FUNCTION, TYPE_VERTEX, TYPE_UNTIL, TYPE_CALL)
NON_GEOMETRY_TYPES = (
    TYPE_NOP,
    TYPE_FUNCTION,
    TYPE_VERTEX,
    TYPE_UNTIL,
    TYPE_CALL,
    TYPE_END,
)


class Polygon:
    def __init__(self, *args):
        self.geomstr = Geomstr()
        self.geomstr.polyline(args)

    def bbox(self, mx=None):
        return self.geomstr.bbox(mx)


def triangle_area(p1, p2, p3):
    """
    calculates the area of a triangle given its vertices
    """
    return (
        abs(p1[0] * (p2[1] - p3[1]) + p2[0] * (p3[1] - p1[1]) + p3[0] * (p1[1] - p2[1]))
        / 2.0
    )


def triangle_areas_from_array(arr):
    """
    take an (N,2) array of points and return an (N,1)
    array of the areas of those triangles, where the first
    and last areas are np.inf

    see triangle_area for algorithm
    """

    result = np.empty((len(arr),), arr.dtype)
    result[0] = np.inf
    result[-1] = np.inf

    p1 = arr[:-2]
    p2 = arr[1:-1]
    p3 = arr[2:]

    # an accumulators to avoid unnecessary intermediate arrays
    accr = result[1:-1]  # Accumulate directly into result
    acc1 = np.empty_like(accr)

    np.subtract(p2[:, 1], p3[:, 1], out=accr)
    np.multiply(p1[:, 0], accr, out=accr)
    np.subtract(p3[:, 1], p1[:, 1], out=acc1)
    np.multiply(p2[:, 0], acc1, out=acc1)
    np.add(acc1, accr, out=accr)
    np.subtract(p1[:, 1], p2[:, 1], out=acc1)
    np.multiply(p3[:, 0], acc1, out=acc1)
    np.add(acc1, accr, out=accr)
    np.abs(accr, out=accr)
    accr /= 2.0
    # Notice: accr was writing into result, so the answer is in there
    return result


# the final value in thresholds is np.inf, which will never be
# the min value.  So, I am safe in "deleting" an index by
# just shifting the array over on top of it


def remove(s, i):
    """
    Quick trick to remove an item from a numpy array without
    creating a new object.  Rather than the array shape changing,
    the final value just gets repeated to fill the space.

    ~3.5x faster than numpy.delete
    """
    s[i:-1] = s[i + 1 :]


def stitcheable_nodes(data, tolerance) -> list:
    out = []
    geoms = []
    # Store all geometries together with an indicator, to which node they belong
    for idx, node in enumerate(data):
        if not hasattr(node, "as_geometry"):
            continue
        for g1 in node.as_geometry().as_contiguous():
            geoms.append((idx, g1))
    if tolerance == 0:
        tolerance = 1e-6
    for idx1, (nodeidx1, g1) in enumerate(geoms):
        for idx2 in range(idx1 + 1, len(geoms)):
            nodeidx2 = geoms[idx2][0]
            g2 = geoms[idx2][1]
            fp1 = g1.first_point
            fp2 = g2.first_point
            lp1 = g1.last_point
            lp2 = g2.last_point
            if (
                abs(lp1 - lp2) <= tolerance
                or abs(lp1 - fp2) <= tolerance
                or abs(fp1 - fp2) <= tolerance
                or abs(fp1 - lp2) <= tolerance
            ):
                if nodeidx1 not in out:
                    out.append(nodeidx1)
                if nodeidx2 not in out:
                    out.append(nodeidx2)
    # print (f"Stitchable nodes: {len(out)}")
    return [data[idx] for idx in out]


def stitch_geometries(geometry_list: list, tolerance: float = 0.0) -> list:
    """
    Stitches geometries within the given tolerance.

    Args:
        geometry_list: List of Geomstr objects to stitch.
        tolerance: Maximum distance between endpoints to consider a stitch.

    Returns:
        List of stitched Geomstr objects, or None if no stitches were made.
    """
    # def coord(point):
    #     return f"{point.real:.2f},{point.imag:.2f}"

    geometries = [g for g in geometry_list if g is not None]
    if not geometries:
        return None
    if tolerance == 0:
        tolerance = 1e-6
    # geometries.sort(key=lambda g: g.first_point)
    anystitches = 1
    pass_count = 0
    # for idx, g in enumerate(geometries):
    #     print (f"{idx}: {g.first_point} -> {g.last_point} ({g.index} segments)")

    while anystitches > 0:
        stitched_geometries = []
        anystitches = 0
        while geometries:
            candidate = geometries.pop(0)
            stitched = False
            for i, target in enumerate(stitched_geometries):
                cand_fp = candidate.first_point
                cand_lp = candidate.last_point
                targ_fp = target.first_point
                targ_lp = target.last_point
                if abs(targ_lp - cand_fp) <= tolerance:
                    # Just append g1 to g2
                    if abs(targ_lp - cand_fp) > 0:
                        target.line(targ_lp, cand_fp)
                    target.append(candidate)
                    stitched_geometries[i] = target
                    stitched = True
                    break
                if abs(targ_fp - cand_lp) <= tolerance:
                    # Insert g1 at the start of g2
                    if abs(targ_fp - cand_lp) > 0:
                        candidate.line(cand_lp, targ_fp)
                    candidate.append(target)
                    stitched_geometries[i] = candidate
                    stitched = True
                    break
                if abs(targ_fp - cand_fp) <= tolerance:
                    # Insert the reverse of g1 at the start
                    candidate.reverse()
                    if abs(targ_fp - cand_fp) > 0:
                        candidate.line(cand_fp, targ_fp)
                    candidate.append(target)
                    stitched_geometries[i] = candidate
                    stitched = True
                    break
                if abs(targ_lp - cand_lp) <= tolerance:
                    if abs(targ_lp - cand_lp) > 0:
                        target.line(targ_lp, cand_lp)
                    candidate.reverse()
                    target.append(candidate)
                    stitched_geometries[i] = target
                    stitched = True
                    break

            if stitched:
                anystitches += 1
            else:
                stitched_geometries.append(candidate)

        # print (f"Stitch pass {pass_count}: {len(stitched_geometries)} geometries, {anystitches} stitches made, org= {len(geometry_list)}, tolerance={tolerance:.2f}")
        if anystitches > 0:
            # Stitches were made, so lets try again
            geometries = list(stitched_geometries)
            pass_count += 1
    # Close any remaining small gaps between start and end points.
    for g in stitched_geometries:
        if 0 < abs(g.last_point - g.first_point) <= tolerance:
            g.line(g.last_point, g.first_point)

    return stitched_geometries


class Simplifier:
    # Copyright (c) 2014 Elliot Hallmark
    # The MIT License (MIT)
    # Permission is hereby granted, free of charge, to any person obtaining a copy
    # of this software and associated documentation files (the "Software"), to deal
    # in the Software without restriction, including without limitation the rights
    # to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    # copies of the Software, and to permit persons to whom the Software is
    # furnished to do so, subject to the following conditions:

    # The above copyright notice and this permission notice shall be included in all
    # copies or substantial portions of the Software.

    # THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    # IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    # FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    # AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    # LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    # OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    # SOFTWARE.

    """
    Implementation of the Visvalingam-Wyatt line simplification algorithm
    Using the implementation from Elliot Hallmark
    https://github.com/fitnr/visvalingamwyatt
        Changes:
        - removed irrelevant (for us) parts
        - added the two PRs #8 and #11

    From the Wiki article https://en.wikipedia.org/wiki/Visvalingam%E2%80%93Whyatt_algorithm
    The Visvalingam–Whyatt algorithm, is an algorithm that decimates a curve composed
    of line segments to a similar curve with fewer points, primarily for usage in
    cartographic generalisation.

    Idea
    Given a polygonal chain (often called a polyline), the algorithm attempts
    to find a similar chain composed of fewer points.

    Points are assigned an importance based on local conditions, and points are
    removed from the least important to most important.

    In Visvalingam's algorithm, the importance is related to the triangular area added by each point.

    Advantages
    The algorithm is easy to understand and explain, but is often competitive with much more complex approaches.
    With the use of a priority queue, the algorithm is performant on large inputs, since the importance of each point can be computed using only its neighbors, and removing a point only requires recomputing the importance of two other points.
    It is simple to generalize to higher dimensions, since the area of the triangle between points has a consistent meaning.

    Disadvantages

    The algorithm does not differentiate between sharp spikes and shallow features, meaning that it will clean up sharp spikes that may be important.
    The algorithm simplifies the entire length of the curve evenly, meaning that curves with high and low detail areas will likely have their fine details eroded.

    """

    def __init__(self, pts):
        """Initialize with points. takes some time to build
        the thresholds but then all threshold filtering later
        is ultra fast"""
        self.pts_in = np.array(pts)
        self.pts = self.pts_in.astype(float)
        self.thresholds = self.build_thresholds()
        self.ordered_thresholds = sorted(self.thresholds, reverse=True)

    def build_thresholds(self):
        """compute the area value of each vertex, which one would
        use to mask an array of points for any threshold value.

        returns a numpy.array (length of pts)  of the areas.
        """
        nmax = len(self.pts)
        real_areas = triangle_areas_from_array(self.pts)
        real_indices = list(range(nmax))

        # destructable copies
        # ARG! areas=real_areas[:] doesn't make a copy!
        areas = np.copy(real_areas)
        i = real_indices[:]

        # pick first point and set up for loop
        min_vert = np.argmin(areas)
        this_area = areas[min_vert]
        #  areas and i are modified for each point finished
        remove(areas, min_vert)  # faster
        # areas = np.delete(areas,min_vert) #slower
        _ = i.pop(min_vert)

        # cntr = 3
        while this_area < np.inf:
            # min_vert was removed from areas and i.
            # Now, adjust the adjacent areas and remove the new min_vert.
            # Now that min_vert was filtered out, min_vert points
            # to the point after the deleted point.

            skip = False  # modified area may be the next minvert

            try:
                right_area = triangle_area(
                    self.pts[i[min_vert - 1]],
                    self.pts[i[min_vert]],
                    self.pts[i[min_vert + 1]],
                )
            except IndexError:
                # trying to update area of endpoint. Don't do it
                pass
            else:
                right_idx = i[min_vert]
                if right_area <= this_area:
                    # even if the point now has a smaller area,
                    # it ultimately is not more significant than
                    # the last point, which needs to be removed
                    # first to justify removing this point.
                    # Though this point is the next most significant
                    right_area = this_area

                    # min_vert refers to the point to the right of
                    # the previous min_vert, so we can leave it
                    # unchanged if it is still the min_vert
                    skip = min_vert

                # update both collections of areas
                real_areas[right_idx] = right_area
                areas[min_vert] = right_area

            if min_vert > 1:
                # can't try/except because 0-1=-1 is a valid index
                left_area = triangle_area(
                    self.pts[i[min_vert - 2]],
                    self.pts[i[min_vert - 1]],
                    self.pts[i[min_vert]],
                )
                if left_area <= this_area:
                    # same justification as above
                    left_area = this_area
                    skip = min_vert - 1
                real_areas[i[min_vert - 1]] = left_area
                areas[min_vert - 1] = left_area

            # only argmin if we have too.
            min_vert = skip or np.argmin(areas)

            _ = i.pop(min_vert)

            this_area = areas[min_vert]
            # areas = np.delete(areas,min_vert) #slower
            remove(areas, min_vert)  # faster

        return real_areas

    def simplify(self, number=None, ratio=None, threshold=None):
        if threshold is not None:
            return self.by_threshold(threshold)

        if number is not None:
            return self.by_number(number)

        ratio = ratio or 0.90
        return self.by_ratio(ratio)

    def by_threshold(self, threshold):
        return self.pts_in[self.thresholds >= threshold]

    def by_number(self, n):
        n = int(n)
        try:
            threshold = self.ordered_thresholds[n]
        except IndexError:
            return self.pts_in

        # return the first n points since by_threshold
        # could return more points if the threshold is the same
        # for some points
        # sort point indices by threshold
        idx = list(range(len(self.pts)))
        sorted_indices = sorted(
            zip(idx, self.thresholds), reverse=True, key=lambda x: x[1]
        )

        # grab first n indices
        sorted_indices = sorted_indices[:n]

        # re-sort by index
        final_indices = sorted([x[0] for x in sorted_indices])

        return self.pts[final_indices]

    def by_ratio(self, r):
        if r <= 0 or r > 1:
            raise ValueError("Ratio must be 0<r<=1. Got {}".format(r))

        return self.by_number(r * len(self.thresholds))


class Clip:
    def __init__(self, shape):
        self.clipping_shape = shape
        self.bounds = shape.bbox()

    def _splits(self, subject, clip):
        """
        Calculate the splits in `subject` by the clip. This should return a list of t positions with the list being
        as long as the number of segments in subject. Finds all intersections between subject and clip and the given
        split positions (of subject) that would make the intersection list non-existant.

        @param subject:
        @param clip:
        @return:
        """
        cminx, cminy, cmaxx, cmaxy = clip.aabb()
        sminx, sminy, smaxx, smaxy = subject.aabb()
        x0, y0 = np.meshgrid(cmaxx, sminx)
        x1, y1 = np.meshgrid(cminx, smaxx)
        x2, y2 = np.meshgrid(cmaxy, sminy)
        x3, y3 = np.meshgrid(cminy, smaxy)

        checks = np.dstack(
            (
                x0 > y0,
                x1 < y1,
                x2 > y2,
                x3 < y3,
            )
        ).all(axis=2)
        splits = [list() for _ in range(len(subject))]
        for s0, s1 in sorted(np.argwhere(checks), key=lambda e: e[0], reverse=True):
            splits[s0].extend(
                [t for t, _ in subject.intersections(int(s0), clip.segments[s1])]
            )
        return splits

    def _splits_brute(self, subject, clip):
        """
        Find the subject clip splits by brute force (for debug testing).

        @param subject:
        @param clip:
        @return:
        """
        splits = [list() for _ in range(len(subject))]
        for s0 in range(len(subject)):
            for s1 in range(len(clip)):
                for t0, t1 in subject.intersections(int(s0), clip.segments[s1]):
                    splits[s0].append(t0)

        return splits

    def inside(self, subject):
        """
        Modifies subject to only contain the segments found inside the given clip.
        @param subject:
        @return:
        """
        clip = self.clipping_shape
        c = Geomstr()
        # Pip currently only works with line segments
        for sp in clip.as_subpaths():
            for segs in sp.as_interpolated_segments(interpolate=100):
                c.polyline(segs)
                c.end()
        sb = Scanbeam(c)

        mid_points = subject.position(slice(subject.index), 0.5)
        r = np.where(sb.points_in_polygon(mid_points))

        subject.segments = subject.segments[r]
        subject.index = len(subject.segments)
        return subject

    def polycut(self, subject, breaks=False):
        """
        Performs polycut on the subject using the preset clipping shape. This only prevents intersections making all
        intersections into divided segments.

        @param subject:
        @param breaks: should the polycut insert overt breaks.
        @return:
        """
        clip = self.clipping_shape
        splits = self._splits(subject, clip)
        # splits2 = self._splits_brute(subject, clip)
        # for q1, q2 in zip(splits, splits2):
        #     assert(q1, q2)

        for s0 in range(len(splits) - 1, -1, -1):
            s = splits[s0]
            if not s:
                continue
            split_lines = list(subject.split(s0, s, breaks=breaks))
            subject.replace(s0, s0, split_lines)
        subject.validate()
        return subject

    def clip(self, subject, split=True):
        """
        Clip algorithm works in 3 steps. First find the splits between the subject and clip and split the subject at
        all positions where it intersects clip. Remove any subject line segment whose midpoint is not found within
        clip.

        @param subject:
        @param split:
        @return:
        """
        if split:
            subject = self.polycut(subject)
        return self.inside(subject)


class Pattern:
    def __init__(self, geomstr=None):
        if geomstr is None:
            geomstr = Geomstr()
        self.geomstr = geomstr
        x0, y0, x1, y1 = geomstr.bbox()
        self.offset_x = x0
        self.offset_y = x0
        self.cell_width = x1 - x0
        self.cell_height = y1 - y0
        self.padding_x = 0
        self.padding_y = 0

    def create_from_pattern(self, pattern, a=None, b=None, *args, **kwargs):
        """
        Write the pattern to the pattern in patterning format.

        @param pattern: generator of pattern format.
        @param a: pattern a value (differs)
        @param b: pattern b value (differs)
        @param args:
        @param kwargs:
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
        self.cell_width, self.cell_height = width, height

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
        cw = self.cell_width
        ch = self.cell_height
        px = self.padding_x
        py = self.padding_y
        if abs(cw + 2 * px) <= 1e-4:
            cols = 1
        else:
            cols = int(((x1 - x0) + cw) / (cw + 2 * px)) + 1
        if abs(ch + 2 * py) <= 1e-4:
            rows = 1
        else:
            rows = int(((y1 - y0) + ch) / (ch + 2 * py)) + 1

        cols = max(1, cols - 2)
        rows = max(1, rows - 2)

        start_value_x = 0
        col = 0
        x_offset = (col + start_value_x) * (cw + 2 * px)
        x = x0 + x_offset
        while x >= x0 - cw and x < x1:
            start_value_x -= 1
            x_offset = (col + start_value_x) * (cw + 2 * px)
            x = x0 + x_offset
            # print (f"X-lower bound: sx={start_value_x}, x={x:.2f}, x0={x0:.2f}, x1={x1:.2f}")

        end_value_x = 0
        col = cols - 1
        x_offset = (col + end_value_x) * (cw + 2 * px)
        x = x0 + x_offset
        while x >= x0 and x < x1:
            end_value_x += 1
            x_offset = (col + end_value_x) * (cw + 2 * px)
            x = x0 + x_offset
            # print (f"X-upper bound: ex={end_value_x}, x={x:.2f}, x0={x0:.2f}, x1={x1:.2f}")

        start_value_y = 0
        row = 0
        y_offset = (row + start_value_y) * (ch + 2 * py)
        y = y0 + y_offset
        while y >= y0 - ch and y < y1:
            start_value_y -= 1
            y_offset = (row + start_value_y) * (ch + 2 * py)
            y = y0 + y_offset
            # print (f"Y-lower bound: sy={start_value_y}, y={y:.2f}, y0={y0:.2f}, y1={y1:.2f}")

        end_value_y = 0
        row = rows - 1
        y_offset = (row + end_value_y) * (ch + 2 * py)
        y = y0 + y_offset
        while y >= y0 and y < y1:
            end_value_y += 1
            y_offset = (row + end_value_y) * (ch + 2 * py)
            y = y0 + y_offset
            # print (f"Y-upper bound: ey={end_value_y}, y={y:.2f}, y0={y0:.2f}, y1={y1:.2f}")

        # print (f"Cols={cols}, s_x={start_value_x}, e_x={end_value_x}")
        # print (f"Rows={rows}, s_y={start_value_y}, e_y={end_value_y}")

        # start_value_x -= 2
        # start_value_y -= 2
        # end_value_x += 1
        # end_value_y += 1

        top_left_x = x0
        # Scale once, translate often
        m = Matrix.scale(cw, ch)
        geom = self.geomstr.as_transformed(m)
        for col in range(start_value_x, cols + end_value_x, 1):
            x_offset = col * (cw + 2 * px)
            x = top_left_x + x_offset

            top_left_y = y0
            for row in range(start_value_y, rows + end_value_y, 1):
                y_offset = row * (ch + 2 * py)
                if col % 2:
                    y_offset += (ch + 2 * py) / 2
                y = top_left_y + y_offset

                g = Geomstr(geom)
                g.translate(x - self.offset_x, y - self.offset_y)
                yield g


class BeamTable:
    def __init__(self, geom):
        self.geometry = geom
        self._nb_events = None
        self._nb_scan = None
        self.intersections = Geomstr()

    def sort_key(self, e):
        return e[0].real, e[0].imag, ~e[1]

    def compute_beam(self):
        ok = self.compute_beam_bo()
        if not ok:
            # print("Failed. Fallback...")
            self.compute_beam_brute()

    def compute_beam_bo(self):
        g = self.geometry
        gs = g.segments
        events = []

        def bisect_events(a, pos, lo=0):
            """
            Brute iterate events to find the correct placement for the required events.
            @param a:
            @param pos:
            @return:
            """
            pos = pos.real, pos.imag
            hi = len(a)
            while lo < hi:
                mid = (lo + hi) // 2
                q = a[mid]
                x = pos[0] - q[0].real
                if x > 1e-8:
                    # x is still greater
                    lo = mid + 1
                    continue
                if x < -1e-8:
                    # x is now less than
                    hi = mid
                    continue
                # x is equal.
                y = pos[1] - q[0].imag
                if y > 1e-8:
                    lo = mid + 1
                    # y is still greater
                    continue
                if y < -1e-8:
                    # y is now less than.
                    hi = mid
                    continue
                # both x and y are equal.
                return mid
            return ~lo

        def get_or_insert_event(x):
            """
            Get event at position, x. Or create event at the given position.

            @param x:
            @return:
            """
            ip1 = bisect_events(events, x)

            if ip1 >= 0:
                evt = events[ip1]
            else:
                evt = (x, [], [], [])
                events.insert(~ip1, evt)
            return evt

        # Add start and end events.
        for i in range(g.index):
            if g._segtype(gs[i]) != TYPE_LINE:
                continue
            event1 = get_or_insert_event(g.segments[i][0])
            event2 = get_or_insert_event(g.segments[i][-1])

            if (gs[i][0].real, gs[i][0].imag) < (gs[i][-1].real, gs[i][-1].imag):
                event1[1].append(i)
                event2[2].append(i)
            else:
                event1[2].append(i)
                event2[1].append(i)

        wh, p, ta, tb = g.brute_line_intersections()
        for w, pos in zip(wh, p):
            event = get_or_insert_event(pos)
            event[3].extend(w)
            self.intersections.point(pos)

        def bisect_yint(a, x, scanline):
            """
            Bisect into the y-intersects of the list (a) to at position x, for scanline value scaneline.
            @param a:
            @param x:
            @param scanline:
            @return:
            """
            value = float(g.y_intercept(x, scanline.real, scanline.imag))
            lo = 0
            hi = len(a)
            while lo < hi:
                mid = (lo + hi) // 2
                x_test = float(g.y_intercept(a[mid], scanline.real, scanline.imag))
                if abs(value - x_test) < 1e-8:
                    x_slope = g.slope(x)
                    if np.isneginf(x_slope):
                        x_slope *= -1
                    t_slope = g.slope(a[mid])
                    if np.isneginf(t_slope):
                        t_slope *= -1
                    if x_slope < t_slope:
                        hi = mid
                    else:
                        lo = mid + 1
                elif value < x_test:
                    hi = mid
                else:
                    lo = mid + 1
            return lo

        checked_swaps = {}

        # def check_intersection(i, q, r, sl):
        #     if (q, r) in checked_swaps:
        #         return
        #     for t1, t2 in g.intersections(q, r):
        #         if t1 in (0, 1) and t2 in (0, 1):
        #             continue
        #         pt_intersect = g.position(q, t1)
        #         if (sl.real, sl.imag) >= (pt_intersect.real, pt_intersect.imag):
        #             continue
        #         checked_swaps[(q, r)] = True
        #         event_intersect = get_or_insert_event(pt_intersect)
        #         event_intersect[1].extend((q, r))
        #         event_intersect[2].extend((q, r))
        #         self.intersections.point(pt_intersect)

        actives = []

        # Store previously active segments
        active_lists = []
        real_events = []
        largest_actives = 0

        i = 0
        while i < len(events):
            event = events[i]
            pt, adds, removes, sorts = event
            try:
                next, _, _, _ = events[i + 1]
            except IndexError:
                next = complex(float("inf"), float("inf"))

            for index in removes:
                try:
                    rp = actives.index(index)
                    del actives[rp]
                except ValueError:
                    # hmm no longer available?!
                    # Not sure what happens here, but we can recreate this error with a welded linetext element
                    # Text= "Wit" and Font="AntPoldCond Bold" (https://www.ffonts.net/AntPoltCond-Bold.font.download)
                    # Reduce the charactergap and you will end up with an attempt to remove a non-existing index.
                    # We cover this, but it will lead then to a degenerate path
                    # Issue # 2595
                    # print(f"Would have crashed for {index}...\n\nAdds={adds}\nRemoves={removes}\nActives={actives}")
                    return False
                # if 0 < rp < len(actives):
                #     check_intersection(i, actives[rp - 1], actives[rp], pt)
            for index in adds:
                ip = bisect_yint(actives, index, pt)
                actives.insert(ip, index)
                # if ip > 0:
                #     check_intersection(i, actives[ip - 1], actives[ip], pt)
                # if ip < len(actives) - 1:
                #     check_intersection(i, actives[ip], actives[ip + 1], pt)
            for index in sorts:
                try:
                    rp = actives.index(index)
                    del actives[rp]
                    ip = bisect_yint(actives, index, pt)
                    actives.insert(ip, index)
                except ValueError:
                    # was removed
                    pass
            i += 1
            if pt == next:
                continue
            if len(actives) > largest_actives:
                largest_actives = len(actives)
            real_events.append(pt)
            active_lists.append(list(actives))
        self._nb_events = real_events
        self._nb_scan = np.zeros((len(active_lists), largest_actives), dtype=int)
        self._nb_scan -= 1
        for i, active in enumerate(active_lists):
            self._nb_scan[i, 0 : len(active)] = active
        return True

    def compute_beam_brute(self):
        g = self.geometry
        gs = g.segments
        events = []
        # Add start and end events.
        for i in range(g.index):
            if g._segtype(gs[i]) != TYPE_LINE:
                continue
            if (gs[i][0].real, gs[i][0].imag) < (gs[i][-1].real, gs[i][-1].imag):
                events.append((g.segments[i][0], i, None))
                events.append((g.segments[i][-1], ~i, None))
            else:
                events.append((g.segments[i][0], ~i, None))
                events.append((g.segments[i][-1], i, None))

        wh, p, ta, tb = g.brute_line_intersections()
        for w, pos in zip(wh, p):
            events.append((pos, 0, w))
            self.intersections.point(pos)

        # Sort start, end, intersections events.
        events.sort(key=self.sort_key)

        # Store currently active segments.
        actives = []

        # scanline = None
        def bisect_yint(a, x, scanline):
            x = float(g.y_intercept(x, scanline.real, scanline.imag))
            lo = 0
            hi = len(a)
            while lo < hi:
                mid = (lo + hi) // 2
                if x < float(g.y_intercept(a[mid], scanline.real, scanline.imag)):
                    hi = mid
                else:
                    lo = mid + 1
            return lo

        # Store previously active segments
        active_lists = []
        real_events = []

        largest_actives = 0

        for i in range(len(events)):
            event = events[i]
            pt, index, swap = event

            try:
                next, _, _ = events[i + 1]
                scanline = (pt + next) / 2
            except IndexError:
                next = complex(float("inf"), float("inf"))
                scanline = next

            if swap is not None:
                s1 = actives.index(swap[0])
                s2 = actives.index(swap[1])
                actives[s1], actives[s2] = actives[s2], actives[s1]
            elif index >= 0:
                ip = bisect_yint(actives, index, scanline)
                actives.insert(ip, index)
            else:
                remove_index = actives.index(~index)
                del actives[remove_index]

            if pt != next:
                if len(actives) > largest_actives:
                    largest_actives = len(actives)
                # actives.sort(key=y_ints)
                real_events.append(pt)
                active_lists.append(list(actives))

        self._nb_events = real_events
        self._nb_scan = np.zeros((len(active_lists), largest_actives), dtype=int)
        self._nb_scan -= 1
        for i, active in enumerate(active_lists):
            self._nb_scan[i, 0 : len(active)] = active

    def points_in_polygon(self, e):
        if self._nb_scan is None:
            self.compute_beam()

        idx = np.searchsorted(self._nb_events, e)
        actives = self._nb_scan[idx - 1]
        line = self.geometry.segments[actives]
        a = line[..., 0]
        b = line[..., -1]
        a = np.where(actives == -1, np.nan + np.nan * 1j, a)
        b = np.where(actives == -1, np.nan + np.nan * 1j, b)

        old_np_seterr = np.seterr(invalid="ignore", divide="ignore")
        try:
            # If vertical slope is undefined. All y-ints are at y since y0=y1
            m = (b.real - a.real) / (b.imag - a.imag)
            x0 = a.real - (m * a.imag)
            xs = np.reshape(np.repeat(np.real(e), x0.shape[1]), x0.shape)
            y_intercepts = np.where(~np.isinf(m), (xs - x0) / m, a.imag)
        finally:
            np.seterr(**old_np_seterr)
        ys = np.reshape(np.repeat(np.imag(e), x0.shape[1]), x0.shape)
        results = np.sum(y_intercepts <= ys, axis=1)
        results %= 2
        return results

    def actives_at(self, value):
        if self._nb_scan is None:
            self.compute_beam()
        idx = np.searchsorted(self._nb_events, value)
        actives = self._nb_scan[idx - 1]
        aw = np.argwhere(actives != -1)[:, 0]
        return actives[aw]

    def combine(self):
        """
        Returns all lines sliced at the events and merged.
        @return:
        """
        if self._nb_scan is None:
            self.compute_beam()
        g = Geomstr()
        actives = self._nb_scan[:-1]
        from_vals = self._nb_events[:-1]
        to_vals = self._nb_events[1:]
        y_start = self.geometry.y_intercept(
            actives, np.real(from_vals), np.imag(from_vals)
        )
        y_end = self.geometry.y_intercept(actives, np.real(to_vals), np.imag(to_vals))
        from_vals = np.reshape(np.repeat(from_vals, y_start.shape[1]), y_start.shape)
        to_vals = np.reshape(np.repeat(to_vals, y_end.shape[1]), y_end.shape)
        starts = np.ravel(np.real(from_vals) + y_start * 1j)
        ends = np.ravel(np.real(to_vals) + y_end * 1j)

        filter = np.dstack((starts != ends, ~np.isnan(starts))).all(axis=2)[0]
        starts = starts[filter]
        ends = ends[filter]
        count = starts.shape[0]
        segments = np.dstack(
            (starts, [0] * count, [TYPE_LINE] * count, [0] * count, ends)
        )[0]
        g.append_lines(segments)
        return g

    def union(self, *args):
        return self.cag("union", *args)

    def intersection(self, *args):
        return self.cag("intersection", *args)

    def xor(self, *args):
        return self.cag("xor", *args)

    def difference(self, *args):
        return self.cag("difference", *args)

    def cag(self, cag_op, *args):
        if self.geometry.index == 0:
            return Geomstr()
        if self._nb_scan is None:
            self.compute_beam()
        g = Geomstr()
        actives = self._nb_scan[:-1]
        lines = self.geometry.segments[actives][..., 2]
        cc = None
        for v in args:
            s = np.dstack((np.imag(lines) == v, actives != -1)).all(axis=2)
            qq = np.cumsum(s, axis=1) % 2
            if cc is None:
                cc = qq
            else:
                if cag_op == "union":
                    cc = cc | qq
                elif cag_op == "intersection":
                    cc = cc & qq
                elif cag_op == "xor":
                    cc = cc ^ qq
                elif cag_op == "difference":
                    cc = ~cc | qq
                elif cag_op == "eq":
                    cc = cc == qq
        yy = np.pad(cc, ((0, 0), (1, 0)), constant_values=0)
        hh = np.diff(yy, axis=1)
        from_vals = self._nb_events[:-1]
        to_vals = self._nb_events[1:]
        y_start = self.geometry.y_intercept(
            actives, np.real(from_vals), np.imag(from_vals)
        )
        y_end = self.geometry.y_intercept(actives, np.real(to_vals), np.imag(to_vals))
        from_vals = np.reshape(np.repeat(from_vals, y_start.shape[1]), y_start.shape)
        to_vals = np.reshape(np.repeat(to_vals, y_end.shape[1]), y_end.shape)
        starts = np.ravel(np.real(from_vals) + y_start * 1j)
        ends = np.ravel(np.real(to_vals) + y_end * 1j)
        hravel = np.ravel(hh)

        filter = np.dstack((starts != ends, ~np.isnan(starts), hravel != 0)).all(
            axis=2
        )[0]
        starts = starts[filter]
        ends = ends[filter]
        count = starts.shape[0]
        segments = np.dstack(
            (starts, [0] * count, [TYPE_LINE] * count, [0] * count, ends)
        )[0]
        g.append_lines(segments)
        return g


class Scanbeam:
    """
    Accepts a Geomstr operation and performs scanbeam operations.
    """

    def __init__(self, geom):
        self._geom = geom

        self.scanline = -float("inf")

        self._sorted_edge_list = []
        self._edge_index_of_high = -1

        self._active_edge_list = []
        self._dirty_actives_sort = False

        self._low = float("inf")
        self._high = -float("inf")

        self.valid_low = self._low
        self.valid_high = self._high

        for i in range(self._geom.index):
            if self._geom._segtype(self._geom.segments[i]) != TYPE_LINE:
                continue
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

        self._nb_events = None
        self._nb_scan = None

    def compute_beam(self):
        actives = []
        largest_actives = 0
        events = []
        while self._high != float("inf"):
            if self._high != self._low:
                if len(self.actives()) > largest_actives:
                    largest_actives = len(self.actives())
                actives.append(list(self.actives()))
                events.append(self._high)
            self.increment_scanbeam()
        actives.append([])
        self._nb_events = events
        self._nb_scan = np.zeros((len(actives), largest_actives), dtype=int)
        self._nb_scan -= 1
        for i, active in enumerate(actives):
            self._nb_scan[i, 0 : len(active)] = active

    def points_in_polygon(self, e):
        if self._nb_scan is None:
            self.compute_beam()
        idx = np.searchsorted(self._nb_events, np.imag(e))
        actives = self._nb_scan[idx]
        line = self._geom.segments[actives]
        a = line[..., 0]
        a = np.where(actives == -1, np.nan + np.nan * 1j, a)
        b = line[..., -1]
        b = np.where(actives == -1, np.nan + np.nan * 1j, b)

        old_np_seterr = np.seterr(invalid="ignore", divide="ignore")
        try:
            # If horizontal slope is undefined. But, all x-ints are at x since x0=x1
            m = (b.imag - a.imag) / (b.real - a.real)
            y0 = a.imag - (m * a.real)
            ys = np.reshape(np.repeat(np.imag(e), y0.shape[1]), y0.shape)
            x_intercepts = np.where(~np.isinf(m), (ys - y0) / m, a.real)
        finally:
            np.seterr(**old_np_seterr)
        xs = np.reshape(np.repeat(np.real(e), y0.shape[1]), y0.shape)
        results = np.sum(x_intercepts <= xs, axis=1)
        results %= 2
        return results

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
        @param tolerance: wiggle room, in favor of inside
        @return:
        """
        if tolerance == 0:
            tolerance == 1e-6
        self.scanline_to(y)
        for i in range(1, len(self._active_edge_list), 2):
            prior = self._active_edge_list[i - 1]
            after = self._active_edge_list[i]
            p_i = self.x_intercept(prior) - tolerance
            a_i = self.x_intercept(after) + tolerance
            if p_i <= x <= a_i:
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
        if not self._sorted_edge_list:
            return self._low, self._low
        y_min, index_min = self._sorted_edge_list[0]
        y_max, index_max = self._sorted_edge_list[-1]
        return y_min.imag, y_max.imag

    def current_is_valid_range(self):
        return self.valid_high >= self.scanline >= self.valid_low

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
        leading_edge = self._edge_index_of_high
        if leading_edge >= 0:
            sb_value, sb_index = self._sorted_edge_list[leading_edge]
            if sb_index >= 0:
                self._active_edge_list.append(sb_index)
            else:
                self._active_edge_list.remove(~sb_index)

        self._edge_index_of_high += 1
        self._low = self._high
        if self._edge_index_of_high < len(self._sorted_edge_list):
            self._high, sb_index = self._sorted_edge_list[self._edge_index_of_high]
            self._high = self._high.imag
        else:
            self._high = float("inf")

    def decrement_scanbeam(self):
        """
        Decrement scanbeam the active edge events.

        @return:
        """
        leading_edge = self._edge_index_of_high - 1
        if leading_edge < len(self._sorted_edge_list):
            sb_value, sb_index = self._sorted_edge_list[leading_edge]
            if sb_index >= 0:
                self._active_edge_list.remove(sb_index)
            else:
                self._active_edge_list.append(~sb_index)

        self._edge_index_of_high -= 1
        self._high = self._low
        if self._edge_index_of_high > 0:
            self._low, sb_index = self._sorted_edge_list[self._edge_index_of_high - 1]
            self._low = self._low.imag
        else:
            self._low = float("-inf")


class MergeGraph:
    def __init__(self, geomstr):
        self.geomstr = geomstr

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
        return self.geomstr

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
            if self.geomstr._segtype(segments[s]) != TYPE_LINE:
                continue
            for t in range(other.index):
                if self.geomstr._segtype(other.segments[t]) != TYPE_LINE:
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


class Geomstr:
    """
    Geometry String Class
    """

    def __init__(self, segments=None):
        self._settings = dict()
        if segments is not None:
            if isinstance(segments, Geomstr):
                self._settings.update(segments._settings)
                self.index = segments.index
                segments = segments.segments
            else:
                # Given raw segments, index is equal to count
                self.index = len(segments)
            self.segments = copy(segments)
            self.capacity = len(segments)
        else:
            self.index = 0
            self.capacity = 12
            self.segments = np.zeros((self.capacity, 5), dtype="complex")

    def __str__(self):
        return f"Geomstr({self.index} segments)"

    def __repr__(self):
        return f"Geomstr({repr(self.segments[:self.index])})"

    def __eq__(self, other):
        if not isinstance(other, Geomstr):
            return False
        if other.index != self.index:
            return False

        m = self.segments[: self.index] == other.segments[: other.index]
        return m.all()

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

    def __iter__(self):
        return self.segments

    def __bool__(self):
        return bool(self.index != 0)

    @staticmethod
    def _segtype(info):
        # Index 2 of a segment does contain the segment-type in the lower nibble of the number
        return int(info[2].real) & 0xFF

    def debug_me(self):
        # Provides information about the Geometry.
        def cplx_info(num):
            return f"({num.real:.0f}, {num.imag:.0f})"

        print(f"Segments: {self.index}")
        for idx, seg in enumerate(self.segments[: self.index]):
            start = seg[0]
            c1 = seg[1]
            seg_type = int(seg[2].real)
            pure_seg_type = self._segtype(seg)
            c2 = seg[3]
            end = seg[4]
            seg_info = self.segment_type(idx)
            if pure_seg_type not in NON_GEOMETRY_TYPES:
                seg_info += f", Start: {cplx_info(start)}, End: {cplx_info(end)}"
            if pure_seg_type == TYPE_QUAD:
                seg_info += f", C: {cplx_info(c1)}"
            elif pure_seg_type == TYPE_CUBIC:
                seg_info += f", C1: {cplx_info(c1)}, C2: {cplx_info(c2)}"
            elif pure_seg_type == TYPE_ARC:
                seg_info += f", C1: {cplx_info(c1)}, C2: {cplx_info(c2)}"
            elif pure_seg_type == TYPE_UNTIL:
                loop_count = seg_type >> 8
                seg_info += f", loops: {loop_count}"
            elif pure_seg_type == TYPE_FUNCTION:
                defining_function = seg_type >> 8
                seg_info += f", function: {defining_function}"
            elif pure_seg_type == TYPE_CALL:
                executing_function = seg_type >> 8
                seg_info += f", function: {executing_function}"

            print(seg_info)
        svg = self.as_path()
        print(f"Path-equivalent: {svg.d()}")

    @classmethod
    def turtle(cls, turtle, n=4, d=1.0):
        PATTERN_COMMAWSP = r"[ ,\t\n\x09\x0A\x0C\x0D]+"
        PATTERN_FLOAT = r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?"
        num_parse = [
            ("DIST", r"[dD]" + PATTERN_FLOAT),
            ("N", "n" + PATTERN_FLOAT),
            ("COMMAND", r"[FfBb]"),
            ("TURN", r"[\+\-LR]"),
            ("SKIP", PATTERN_COMMAWSP),
        ]
        num_re = re.compile("|".join("(?P<%s>%s)" % pair for pair in num_parse))
        current_pt = 0j
        direction = 0
        turn = math.tau / n
        g = cls()
        pos = 0
        limit = len(turtle)
        while pos < limit:
            match = num_re.match(turtle, pos)
            if match is None:
                break  # No more matches.
            kind = match.lastgroup
            pos = match.end()
            if kind == "SKIP":
                continue
            elif kind == "COMMAND":
                c = match.group()
                if c == "F":
                    next_pt = Geomstr.polar(None, current_pt, direction, d)
                    g.line(current_pt, next_pt, 0, a=0, b=0)
                    current_pt = next_pt
                elif c == "f":
                    next_pt = Geomstr.polar(None, current_pt, direction, d)
                    g.line(current_pt, next_pt, 0, a=2, b=2)
                    current_pt = next_pt
                elif c == "B":
                    next_pt = Geomstr.polar(None, current_pt, direction, d)
                    g.line(current_pt, next_pt, 0, a=1, b=1)
                    current_pt = next_pt
                elif c == "b":
                    next_pt = Geomstr.polar(None, current_pt, direction, d)
                    g.line(current_pt, next_pt, 0, a=3, b=3)
                    current_pt = next_pt
            elif kind == "TURN":
                c = match.group()
                if c in ("+", "R"):
                    direction += turn
                elif c in ("-", "L"):
                    direction -= turn
            elif kind == "DIST":
                value = match.group()
                d = float(value[1:])
                c = value[0]
                if c == "D":
                    d = math.sqrt(d)
            elif kind == "N":
                value = match.group()
                n = int(float(value[1:]))
                turn = math.tau / n
        return g

    @classmethod
    def svg(cls, path_d):
        obj = cls()
        if isinstance(path_d, str):
            try:
                path = Path(path_d)
            except ValueError:
                # Invalid or empty path
                return obj
        else:
            path = path_d
        last_point = None
        for seg in path:
            if isinstance(seg, Move):
                # If the move destination is identical to destination of the
                # last point then we need to introduce a subpath break
                if (
                    last_point is not None
                    and last_point.x == seg.end.x
                    and last_point.y == seg.end.y
                ):
                    # This is a deliberate subpath break
                    obj.end()
            elif (
                isinstance(seg, (Line, Close))
                and seg.start is not None
                and seg.end is not None
            ):
                obj.line(complex(seg.start), complex(seg.end))
            elif (
                isinstance(seg, QuadraticBezier)
                and seg.start is not None
                and seg.end is not None
                and seg.control is not None
            ):
                obj.quad(complex(seg.start), complex(seg.control), complex(seg.end))
            elif (
                isinstance(seg, CubicBezier)
                and seg.start is not None
                and seg.end is not None
                and seg.control1 is not None
                and seg.control2 is not None
            ):
                obj.cubic(
                    complex(seg.start),
                    complex(seg.control1),
                    complex(seg.control2),
                    complex(seg.end),
                )
            elif isinstance(seg, Arc) and seg.start is not None and seg.end is not None:
                if seg.is_circular():
                    obj.arc(
                        complex(seg.start), complex(seg.point(0.5)), complex(seg.end)
                    )
                else:
                    quads = seg.as_quad_curves(4)
                    for q in quads:
                        obj.quad(complex(q.start), complex(q.control), complex(q.end))
            last_point = seg.end
        return obj

    @classmethod
    def image(cls, pil_image, invert=False, vertical=False, bidirectional=True):
        g = cls()
        if pil_image.mode != "1":
            pil_image = pil_image.convert("1")
        im = np.array(pil_image)
        if not invert:
            # Invert is default, Black == 0 (False), White == 255 (True)
            im = ~im

        if vertical:
            im = np.swapaxes(im, 0, 1)

        a = np.pad(im, ((0, 0), (0, 1)), constant_values=0)
        b = np.pad(im, ((0, 0), (1, 0)), constant_values=0)
        starts = a & ~b
        ends = ~a & b
        sx, sy = np.nonzero(starts)
        ex, ey = np.nonzero(ends)
        if vertical:
            starts = sx + sy * 1j
            ends = ex + ey * 1j
        else:
            starts = sy + sx * 1j
            ends = ey + ex * 1j
        count = len(ex)
        segments = np.dstack(
            (starts, [0] * count, [TYPE_LINE] * count, [0] * count, ends)
        )[0]
        if bidirectional:
            Geomstr.bidirectional(segments, vertical=vertical)
        g.append_lines(segments)
        return g

    @staticmethod
    def bidirectional(segments, vertical=False):
        swap_start = 0
        last_row = -1
        rows = 0
        for i in range(len(segments) + 1):
            try:
                s, c1, info, c2, e = segments[i]
                if vertical:
                    current_row = s.imag
                else:
                    current_row = s.real
            except IndexError:
                current_row = -1
            if current_row == last_row:
                continue
            # Start of a new row.
            last_row = current_row
            rows += 1
            if rows % 2 == 0:
                segments[swap_start:i] = np.flip(segments[swap_start:i], (0, 1))
            swap_start = i
        return segments

    @classmethod
    def lines(cls, *points, settings=0):
        path = cls()
        if not points:
            return path
        first_point = points[0]
        if isinstance(first_point, (float, int)):
            if len(points) < 2:
                return path
            points = list(zip(*[iter(points)] * 2))
            first_point = points[0]
        if isinstance(first_point, numpy.ndarray):
            points = list(first_point)
            first_point = points[0]
        if isinstance(first_point, (list, tuple, numpy.ndarray)):
            points = [None if pts is None else pts[0] + pts[1] * 1j for pts in points]
            first_point = points[0]
        if isinstance(first_point, complex):
            on = False
            for i in range(1, len(points)):
                if points[i - 1] is not None and points[i] is not None:
                    on = True
                    path.line(points[i - 1], points[i], settings=settings)
                else:
                    if on:
                        path.end(settings=settings)
                    on = False
        return path

    @classmethod
    def ellipse(cls, rx, ry, cx, cy, rotation=0, slices=12):
        obj = cls()
        obj.arc_as_cubics(
            0,
            math.tau,
            rx=rx,
            ry=ry,
            cx=cx,
            cy=cy,
            rotation=rotation,
            slices=slices,
        )
        return obj

    @classmethod
    def circle(cls, r, cx, cy, slices=4):
        rx = r
        ry = r

        def point_at_t(t):
            return complex(cx + rx * math.cos(t), cy + ry * math.sin(t))

        obj = cls()
        step_size = math.tau / slices

        t_start = 0
        t_end = step_size
        for i in range(slices):
            obj.arc(
                point_at_t(t_start),
                point_at_t((t_start + t_end) / 2),
                point_at_t(t_end),
            )
            t_start = t_end
            t_end += step_size
        return obj

    @classmethod
    def rect(cls, x, y, width, height, rx=0, ry=0, settings=0):
        path = cls()
        if rx < 0 < width or ry < 0 < height:
            rx = abs(rx)
            ry = abs(ry)
        if rx == ry == 0:
            (path.line(complex(x, y), complex(x + width, y), settings=settings),)
            (
                path.line(
                    complex(x + width, y),
                    complex(x + width, y + height),
                    settings=settings,
                ),
            )
            (
                path.line(
                    complex(x + width, y + height),
                    complex(x, y + height),
                    settings=settings,
                ),
            )
            (path.line(complex(x, y + height), complex(x, y), settings=settings),)
        else:
            offset = 1 - (1.0 / math.sqrt(2))
            path.line(complex(x + rx, y), complex(x + width - rx, y), settings=settings)
            path.arc(
                complex(x + width - rx, y),
                complex(x + width - rx * offset, y + ry * offset),
                complex(x + width, y + ry),
                settings=settings,
            )
            path.line(
                complex(x + width, y + ry),
                complex(x + width, y + height - ry),
                settings=settings,
            )
            path.arc(
                complex(x + width, y + height - ry),
                complex(x + width - rx * offset, y + height - ry * offset),
                complex(x + width - rx, y + height),
                settings=settings,
            )
            path.line(
                complex(x + width - rx, y + height),
                complex(x + rx, y + height),
                settings=settings,
            )
            path.arc(
                complex(x + rx, y + height),
                complex(x + rx * offset, y + height - ry * offset),
                complex(x, y + height - ry),
                settings=settings,
            )
            path.line(
                complex(x, y + height - ry), complex(x, y + ry), settings=settings
            )
            path.arc(
                complex(x, y + ry),
                complex(x + rx * offset, y + ry * offset),
                complex(x + rx, y),
                settings=settings,
            )
            path.close()
            # path.line(complex(x + rx, y), complex(x + rx, y), settings=settings)
        return path

    @classmethod
    def hull(cls, geom, distance=50):
        ipts = list(geom.as_equal_interpolated_points(distance=distance))
        pts = list(Geomstr.convex_hull(None, ipts))
        if pts:
            pts.append(pts[0])
        return Geomstr.lines(*pts)

    @classmethod
    def regular_polygon(
        cls,
        number_of_vertex,
        point_center=0j,
        radius=0,
        radius_inner=0,
        alt_seq=1,
        density=1,
        start_angle=0,
    ):
        if number_of_vertex < 2:
            return cls()
        if alt_seq == 0 and radius_inner != 0:
            alt_seq = 1
        # Do we have to consider the radius value as the length of one corner?
        # if side_length:
        #     # Let's recalculate the radius then...
        #     # d_oc = s * csc( pi / n)
        #     radius = 0.5 * radius / math.sin(math.pi / number_of_vertex)
        # if inscribed and side_length is None:
        #     # Inscribed requires side_length be undefined.
        #     # You have as well provided the --side_length parameter, this takes precedence, so --inscribed is ignored
        #     radius = radius / math.cos(math.pi / number_of_vertex)

        if alt_seq < 1:
            radius_inner = radius

        i_angle = start_angle
        delta_angle = math.tau / number_of_vertex
        pts = []
        for j in range(number_of_vertex):
            r = radius if j % (2 * alt_seq) < alt_seq else radius_inner
            current = point_center + r * complex(math.cos(i_angle), math.sin(i_angle))
            i_angle += delta_angle
            pts.append(current)

        # Close the path
        pts.append(pts[0])
        if density <= 1 or number_of_vertex > density:
            return Geomstr.lines(*pts)

        # Process star-like qualities.
        star_points = [pts[0]]
        for i in range(number_of_vertex):
            idx = (density * i) % number_of_vertex
            star_points.append(pts[idx])
        star_points.append(star_points[0])
        return Geomstr.lines(*star_points)

    @classmethod
    def hatch(cls, outer, angle, distance):
        """
        Create a hatch geometry from an outer shape, an angle (in radians) and distance (in units).
        @param outer:
        @param angle:
        @param distance:
        @return:
        """
        outlines = outer.segmented()
        path = outlines
        path.rotate(angle)
        vm = Scanbeam(path)
        y_min, y_max = vm.event_range()
        vm.valid_low = y_min - distance
        vm.valid_high = y_max + distance
        vm.scanline_to(vm.valid_low)

        forward = True
        geometry = cls()
        if np.isinf(y_max):
            return geometry
        if distance == 0:
            return geometry
        while vm.current_is_valid_range():
            vm.scanline_to(vm.scanline + distance)
            y = vm.scanline
            actives = vm.actives()

            r = range(1, len(actives), 2) if forward else range(len(actives) - 1, 0, -2)
            for i in r:
                left_segment = actives[i - 1]
                right_segment = actives[i]
                left_segment_x = vm.x_intercept(left_segment)
                right_segment_x = vm.x_intercept(right_segment)
                if forward:
                    geometry.line(
                        complex(left_segment_x, y), complex(right_segment_x, y)
                    )
                else:
                    geometry.line(
                        complex(right_segment_x, y), complex(left_segment_x, y)
                    )
                geometry.end()
            forward = not forward
        geometry.rotate(-angle)
        return geometry

    @classmethod
    def wobble(cls, algorithm, outer, radius, interval, speed, unit_factor=1):
        from meerk40t.fill.fills import Wobble

        w = Wobble(algorithm, radius=radius, speed=speed, interval=interval)
        w.unit_factor = unit_factor
        w.total_length = outer.length()

        geometry = cls()
        for segments in outer.as_interpolated_segments(interpolate=50):
            points = []
            last = None
            for pt in segments:
                if last is not None:
                    for wx, wy in w(last.real, last.imag, pt.real, pt.imag):
                        if wx is None:
                            if len(points):
                                geometry.append(Geomstr.lines(*points))
                                geometry.end()
                            points = []
                        else:
                            points.append(complex(wx, wy))
                last = pt
            if (
                w.may_close_path
                and len(segments) > 1
                and abs(segments[0] - segments[-1]) < 1e-5
                and len(points) > 0
            ):
                if abs(points[0] - points[-1]) >= 1e-5:
                    points.append(points[0])
            geometry.append(Geomstr.lines(*points))
        return geometry

    @classmethod
    def wobble_slowtooth(cls, outer, radius, interval, speed):
        from meerk40t.fill.fills import slowtooth as algorithm

        return cls.wobble(algorithm, outer, radius, interval, speed)

    @classmethod
    def wobble_gear(cls, outer, radius, interval, speed):
        from meerk40t.fill.fills import gear as algorithm

        return cls.wobble(algorithm, outer, radius, interval, speed)

    @classmethod
    def wobble_jigsaw(cls, outer, radius, interval, speed):
        from meerk40t.fill.fills import jigsaw as algorithm

        return cls.wobble(algorithm, outer, radius, interval, speed)

    @classmethod
    def wobble_sawtooth(cls, outer, radius, interval, speed):
        from meerk40t.fill.fills import sawtooth as algorithm

        return cls.wobble(algorithm, outer, radius, interval, speed)

    @classmethod
    def wobble_sinewave(cls, outer, radius, interval, speed):
        from meerk40t.fill.fills import sinewave as algorithm

        return cls.wobble(algorithm, outer, radius, interval, speed)

    @classmethod
    def wobble_circle_left(cls, outer, radius, interval, speed):
        from meerk40t.fill.fills import circle_left as algorithm

        return cls.wobble(algorithm, outer, radius, interval, speed)

    @classmethod
    def wobble_circle_right(cls, outer, radius, interval, speed):
        from meerk40t.fill.fills import circle_right as algorithm

        return cls.wobble(algorithm, outer, radius, interval, speed)

    @classmethod
    def wobble_circle(cls, outer, radius, interval, speed):
        from meerk40t.fill.fills import circle as algorithm

        return cls.wobble(algorithm, outer, radius, interval, speed)

    @classmethod
    def wobble_meander_1(cls, outer, radius, interval, speed):
        from meerk40t.fill.fills import meander_1 as algorithm

        return cls.wobble(algorithm, outer, radius, interval, speed)

    @classmethod
    def wobble_meander_2(cls, outer, radius, interval, speed):
        from meerk40t.fill.fills import meander_2 as algorithm

        return cls.wobble(algorithm, outer, radius, interval, speed)

    @classmethod
    def wobble_meander_3(cls, outer, radius, interval, speed):
        from meerk40t.fill.fills import meander_3 as algorithm

        return cls.wobble(algorithm, outer, radius, interval, speed)

    @classmethod
    def wobble_dash(cls, outer, dashlength, interval, irrelevant, unit_factor=1):
        from meerk40t.fill.fills import dashed_line as algorithm

        return cls.wobble(
            algorithm,
            outer,
            dashlength,
            interval * unit_factor,
            irrelevant,
            unit_factor=unit_factor,
        )

    @classmethod
    def wobble_tab(cls, outer, tablength, interval, tabpositions, unit_factor=1):
        from meerk40t.fill.fills import tabbed_path as algorithm

        return cls.wobble(
            algorithm,
            outer,
            tablength,
            interval * unit_factor,
            tabpositions,
            unit_factor=unit_factor,
        )

    @classmethod
    def from_float_segments(cls, float_segments):
        sa = np.ndarray((len(float_segments), 5, 2))
        sa[:] = float_segments
        float_segments = sa[..., 0] + 1j * sa[..., 1]
        return cls(float_segments)

    def as_float_segments(self):
        return [
            (
                (start.real, start.imag),
                (c1.real, c1.imag),
                (info.real, info.imag),
                (c2.real, c2.imag),
                (end.real, end.imag),
            )
            for start, c1, info, c2, end in self.segments[: self.index]
        ]

    def flag_settings(self, flag=None, start=0, end=None):
        if end is None:
            end = self.index
        for i in range(start, end):
            info = self.segments[i][2]
            if flag is None:
                self.segments[i][2] = complex(info.real, i)
            else:
                self.segments[i][2] = complex(info.real, flag)

    def copies(self, n):
        segs = self.segments[: self.index]
        self.segments = np.vstack([segs] * n)
        self.capacity = len(self.segments)
        self.index = self.capacity

    def as_contiguous_segments(self, start_pos=0, end_pos=None):
        """
        Interpolated segments gives interpolated points as a generator of lists.

        At points of disjoint, the list is yielded.
        @param end_pos:
        @param start_pos:
        """
        segments = list()
        for point in self.as_contiguous_points(start_pos=start_pos, end_pos=end_pos):
            if isinstance(point, tuple):
                point, settings = point
                if segments:
                    yield segments, settings
                    segments = list()
            else:
                segments.append(point)

    def as_contiguous_points(self, start_pos=0, end_pos=None):
        """
        Yields points between the given positions where the lines are connected and the settings are the same.
        Gaps are caused by settings being unequal, segment_type changing, or disjointed segments.
        Gaps yield a None, followed by a setting value.

        @param start_pos: position to start
        @param end_pos:  position to end.
        @return:
        """
        if end_pos is None:
            end_pos = self.index
        at_start = True
        end = None
        settings = None
        for e in self.segments[start_pos:end_pos]:
            seg_type = self._segtype(e)
            set_type = int(e[2].imag)
            if seg_type in META_TYPES:
                continue
            start = e[0]
            if not at_start and (set_type != settings or abs(start - end) > 1e-8):
                # Start point does not equal previous end point, or settings changed
                yield None, settings
                at_start = True
                if seg_type == TYPE_END:
                    # End segments, flag new start but should not be returned.
                    continue
            end = e[4]
            settings = set_type
            if at_start:
                yield start
                at_start = False
            if seg_type == TYPE_END:
                at_start = True
                continue
            yield end
        yield None, settings

    def as_points(self):
        at_start = True
        for seg in self.segments[: self.index]:
            start = seg[0]
            end = seg[4]
            segtype = self._segtype(seg)
            if segtype in NON_GEOMETRY_TYPES:
                continue
            if at_start:
                yield start
            yield end
            at_start = False

    def as_equal_interpolated_segments(self, distance=100):
        """
        Interpolated segments gives interpolated points as a generator of lists.

        At points of disjoint, the list is yielded.
        @param distance:
        @return:
        """
        segments = list()
        for point in self.as_equal_interpolated_points(distance=distance):
            if point is None:
                if segments:
                    yield segments
                    segments = list()
            else:
                segments.append(point)
        if segments:
            yield segments

    def as_equal_interpolated_points(self, distance=100, expand_lines=False):
        """
        Regardless of specified distance this will always give the start and end points of each node within the
        geometry. It will not duplicate the nodes if the start of one is the end of another. If the start and end
        values do not line up, it will yield a None value to denote there is a broken path.

        @param distance:
        @return:
        """

        at_start = True
        end = None
        for e in self.segments[: self.index]:
            seg_type = self._segtype(e)
            if seg_type in META_TYPES:
                continue
            start = e[0]
            if end != start and not at_start:
                # Start point does not equal previous end point.
                yield None
                at_start = True
            end = e[4]
            if at_start:
                if seg_type == TYPE_END:
                    # End segments, flag new start but should not be returned.
                    continue
                yield start
                at_start = False

            if seg_type == TYPE_END:
                at_start = True
                continue
            elif seg_type == TYPE_LINE:
                if expand_lines:
                    ts = np.linspace(0, 1, 1000)
                    pts = self._line_position(e, ts)
                    distances = np.abs(pts[:-1] - pts[1:])
                    distances = np.cumsum(distances)
                    max_distance = distances[-1]
                    dist_values = np.linspace(
                        0,
                        max_distance,
                        int(np.ceil(max_distance / distance)),
                        endpoint=False,
                    )[1:]
                    near_t = np.searchsorted(distances, dist_values, side="right")
                    pts = pts[near_t]
                    yield from pts
            elif seg_type == TYPE_QUAD:
                ts = np.linspace(0, 1, 1000)
                pts = self._quad_position(e, ts)
                distances = np.abs(pts[:-1] - pts[1:])
                distances = np.cumsum(distances)
                max_distance = distances[-1]
                dist_values = np.linspace(
                    0,
                    max_distance,
                    int(np.ceil(max_distance / distance)),
                    endpoint=False,
                )[1:]
                near_t = np.searchsorted(distances, dist_values, side="right")
                pts = pts[near_t]
                yield from pts
            elif seg_type == TYPE_CUBIC:
                ts = np.linspace(0, 1, 1000)
                pts = self._cubic_position(e, ts)
                distances = np.abs(pts[:-1] - pts[1:])
                distances = np.cumsum(distances)
                max_distance = distances[-1]
                dist_values = np.linspace(
                    0,
                    max_distance,
                    int(np.ceil(max_distance / distance)),
                    endpoint=False,
                )[1:]
                near_t = np.searchsorted(distances, dist_values, side="right")
                pts = pts[near_t]
                yield from pts
            elif seg_type == TYPE_ARC:
                ts = np.linspace(0, 1, 1000)
                pts = self._arc_position(e, ts)
                distances = np.abs(pts[:-1] - pts[1:])
                distances = np.cumsum(distances)
                max_distance = distances[-1]
                dist_values = np.linspace(
                    0,
                    max_distance,
                    int(np.ceil(max_distance / distance)),
                    endpoint=False,
                )[1:]
                near_t = np.searchsorted(distances, dist_values, side="right")
                pts = pts[near_t]
                yield from pts
            yield end

    def as_interpolated_segments(self, interpolate=100):
        """
        Interpolated segments gives interpolated points as a generator of lists.

        At points of disjoint, the list is yielded.
        @param interpolate:
        @return:
        """
        segments = list()
        for point in self.as_interpolated_points(interpolate=interpolate):
            if point is None:
                if segments:
                    yield segments
                    segments = list()
            else:
                segments.append(point)
        if segments:
            yield segments

    def as_interpolated_points(self, interpolate=100):
        """
        Interpolated points gives all the points for the geomstr data. The arc, quad, and cubic are interpolated.

        Non-connected data yields a None object.

        Points are not connected to either side.

        @param interpolate:
        @return:
        """
        at_start = True
        end = None
        for e in self.segments[: self.index]:
            seg_type = self._segtype(e)
            if seg_type in META_TYPES:
                continue
            start = e[0]
            if end != start and not at_start:
                # Start point does not equal previous end point.
                yield None
                at_start = True
                if seg_type == TYPE_END:
                    # End segments, flag new start but should not be returned.
                    continue
            end = e[4]
            # Multiple consecutive ends or an end at start ?
            if at_start and seg_type == TYPE_END:
                continue
            if at_start:
                yield start
            at_start = False
            if seg_type == TYPE_LINE:
                yield end
                continue
            if seg_type == TYPE_QUAD:
                quads = self._quad_position(e, np.linspace(0, 1, interpolate))
                yield from quads[1:]
            elif seg_type == TYPE_CUBIC:
                cubics = self._cubic_position(e, np.linspace(0, 1, interpolate))
                yield from cubics[1:]
            elif seg_type == TYPE_ARC:
                arcs = self._arc_position(e, np.linspace(0, 1, interpolate))
                yield from arcs[1:]
            elif seg_type == TYPE_END:
                at_start = True

    def segmented(self, distance=50):
        return Geomstr.lines(*self.as_equal_interpolated_points(distance=distance))

    def _ensure_capacity(self, capacity):
        if self.capacity > capacity:
            return
        self.capacity = max(self.capacity << 1, capacity)
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

    def allocate_at_position(self, e, space=1):
        """
        Creates space within the array, at position e.

        If space is negative this will delete space.
        @param e:
        @param space:
        @return:
        """
        self._ensure_capacity(self.index + space)
        self.segments[e + space : self.index + space] = self.segments[e : self.index]
        self.index += space

    def replace(self, e0, e1, lines):
        space = len(lines) - (e1 - e0) - 1
        self.allocate_at_position(e1, space)
        if len(lines):
            self.segments[e0 : e0 + len(lines)] = lines

    def insert(self, e, lines):
        space = len(lines)
        self.allocate_at_position(e, space)
        self.segments[e : e + space] = lines

    def append_segment(self, start, control, info, control2, end):
        self._ensure_capacity(self.index + 1)
        self.segments[self.index] = (start, control, info, control2, end)
        self.index += 1

    def append_lines(self, lines):
        self._ensure_capacity(self.index + len(lines))
        self.segments[self.index : self.index + len(lines)] = lines
        self.index += len(lines)

    def append(self, other, end=True):
        self._ensure_capacity(self.index + other.index + 1)
        if self.index != 0 and end:
            self.end()
        self.segments[self.index : self.index + other.index] = other.segments[
            : other.index
        ]
        self.index += other.index

    def validate(self):
        infos = self.segments[: self.index, 2]

        starts = self.segments[: self.index, 0]
        q = np.where(np.real(infos).astype(int) & 0b1000)
        assert not np.any(np.isnan(starts[q]))

        ends = self.segments[: self.index, 4]
        q = np.where(np.real(infos).astype(int) & 0b0001)
        assert not np.any(np.isnan(ends[q]))

        c1 = self.segments[: self.index, 1]
        q = np.where(np.real(infos).astype(int) & 0b0100)
        assert not np.any(np.isnan(c1[q]))

        c2 = self.segments[: self.index, 3]
        q = np.where(np.real(infos).astype(int) & 0b0010)
        assert not np.any(np.isnan(c2[q]))

    #######################
    # Geometric Primitives
    #######################

    def line(self, start, end, settings=0, a=None, b=None):
        """
        Add a line between start and end points at the given settings level

        @param start: complex: start point
        @param end: complex: end point
        @param settings: settings level to assign this particular line.
        @param a: unused control1 value
        @param b: unused control2 value
        @return:
        """
        if a is None:
            a = 0
        if b is None:
            b = 0
        self.append_segment(
            start,
            a,
            complex(TYPE_LINE, settings),
            b,
            end,
        )

    def quad(self, start, control, end, settings=0):
        """
        Add a quadratic bezier curve.
        @param start: (complex) start point
        @param control: (complex) control point
        @param end: (complex) end point
        @param settings: optional settings level for the quadratic bezier curve
        @return:
        """
        self.append_segment(
            start,
            control,
            complex(TYPE_QUAD, settings),
            control,
            end,
        )

    def cubic(self, start, control0, control1, end, settings=0):
        """
        Add in a cubic Bézier curve
        @param start: (complex) start point
        @param control0: (complex) first control point
        @param control1: (complex) second control point
        @param end: (complex) end point
        @param settings: optional settings level for the cubic Bézier curve
        @return:
        """
        self.append_segment(
            start,
            control0,
            complex(TYPE_CUBIC, settings),
            control1,
            end,
        )

    def arc(self, start, control, end, settings=0):
        """
        Add in a circular arc curve
        @param start: (complex) start point
        @param control:(complex) control point
        @param end: (complex) end point
        @param settings: optional settings level for the arc
        @return:
        """
        self.append_segment(
            start,
            control,
            complex(TYPE_ARC, settings),
            control,
            end,
        )

    def point(self, position, settings=0, a=None, b=None):
        """
        Add in point 1D geometry object.

        @param position: Position at which add point
        @param settings: optional settings level for the point
        @param a: unused control1 value
        @param b: unused control2 value
        @return:
        """
        if a is None:
            a = 0
        if b is None:
            b = 0
        self.append_segment(
            position,
            a,
            complex(TYPE_POINT, settings),
            b,
            position,
        )

    def end(self, settings=0):
        """
        Adds a structural break in the current path. Two structural breaks are assumed to be a new path.
        @param settings: Unused settings value for break.
        @return:
        """
        if self.index and self._segtype(self.segments[self.index - 1]) == TYPE_END:
            # No two consecutive ends
            return
        self.append_segment(
            np.nan,
            np.nan,
            complex(TYPE_END, settings),
            np.nan,
            np.nan,
        )

    def vertex(self, vertex=0):
        """
        Add a vertex, a vertex is assumed to be the same point always. Any run that hits a
        vertex is said to have hit a graph-node. If there are two vertexes there is a loop
        if there's more than segments that goto a vertex that is a graph.
        @param vertex: Vertex index of vertex being added
        @return:
        """
        self.append_segment(
            np.nan,
            np.nan,
            complex(TYPE_VERTEX, vertex),
            np.nan,
            np.nan,
        )

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

    @contextmanager
    def function(self, function_index=None, placement=None, settings=0, loops=0):
        if function_index is None:
            if hasattr(self, "_function"):
                self._function += 1
            else:
                self._function = 1
            function_index = self._function
        g = Geomstr()
        yield g
        if not g:
            # Nothing was added to function.
            return

        self._ensure_capacity(self.index + 2 + len(g))
        if placement is None:
            nx, ny, mx, my = g.bbox()
            placement = (
                complex(nx, ny),
                complex(mx, ny),
                complex(mx, my),
                complex(nx, my),
            )

        self.segments[self.index] = (
            placement[0],
            placement[1],
            complex(TYPE_FUNCTION | (function_index << 8), settings),
            placement[2],
            placement[3],
        )
        self.index += 1
        self.append(g, end=False)
        self.segments[self.index] = (
            0,
            0,
            complex(TYPE_UNTIL | (loops << 8), settings),
            0,
            0,
        )
        self.index += 1

    def call(self, function_index, placement=None, settings=0):
        self._ensure_capacity(self.index + 1)
        if placement is None:
            self.segments[self.index] = (
                np.nan,
                np.nan,
                complex(TYPE_CALL | (function_index << 8), settings),
                np.nan,
                np.nan,
            )
        else:
            self.segments[self.index] = (
                placement[0],
                placement[1],
                complex(TYPE_CALL | (function_index << 8), settings),
                placement[2],
                placement[3],
            )
        self.index += 1

    def is_closed(self):
        if self.index == 0:
            return True
        # Even if the last and first segment stitch to each other,
        # they could still belong to different subpaths!
        # So a geomstr that has more than one subpath will not be considered closed!
        for p in self.segments[: self.index]:
            if self._segtype(p) == TYPE_END:
                return False
        return abs(self.segments[0][0] - self.segments[self.index - 1][-1]) < 1e-5

    #######################
    # Geometric Helpers
    #######################

    def arc_as_quads(
        self, start_t, end_t, rx, ry, cx, cy, rotation=0, slices=None, settings=0
    ):
        """
        Creates a rotated elliptical arc using quads. This is a helper for creating a more complex arc-like shape from
        out of approximate quads.

        @param start_t: start_t for the arc
        @param end_t: end_t for the arc
        @param rx: rx of the ellipse
        @param ry: ry of the ellipse
        @param cx: center_x of the ellipse
        @param cy: center_y of the ellipse
        @param rotation: rotation of the ellipse
        @param slices: number of quads to use in the approximation.
        @param settings: index of settings for these segments
        @return:
        """
        sweep = start_t - end_t
        if slices is None:
            # A full ellipse can be properly represented with 12 slices - we err on the side of caution here...
            slices = int(1.5 * 12 * sweep / math.tau)
            slices = max(2, slices)
        t_slice = sweep / float(slices)
        alpha_mid = (4.0 - math.cos(t_slice)) / 3.0
        current_t = start_t
        theta = rotation

        cos_theta = math.cos(theta)
        sin_theta = math.sin(theta)
        a = rx
        b = ry

        def point_at_t(t, alpha=1.0):
            cos_t = math.cos(t)
            sin_t = math.sin(t)
            px = cx + alpha * (a * cos_t * cos_theta - b * sin_t * sin_theta)
            py = cy + alpha * (a * cos_t * sin_theta + b * sin_t * cos_theta)
            return complex(px, py)

        p_start = point_at_t(current_t)

        for i in range(0, slices):
            next_t = current_t + t_slice
            mid_t = (next_t + current_t) / 2

            if i == slices - 1:
                next_t = end_t
            # Calculate p_end.
            p_end = point_at_t(next_t)

            # Calculate p_mid
            p_mid = point_at_t(mid_t, alpha_mid)

            self.quad(p_start, p_mid, p_end, settings=settings)
            p_start = p_end
            current_t = next_t

    def arc_as_cubics(
        self, start_t, end_t, rx, ry, cx, cy, rotation=0, slices=None, settings=0
    ):
        """
        Creates a rotated elliptical arc using quads. This is a helper for creating a more complex arc-like shape from
        out of approximate quads.

        @param start_t: start_t for the arc
        @param end_t: end_t for the arc
        @param rx: rx of the ellipse
        @param ry: ry of the ellipse
        @param cx: center_x of the ellipse
        @param cy: center_y of the ellipse
        @param rotation: rotation of the ellipse
        @param slices: number of quads to use in the approximation.
        @param settings: index of settings for these segments

        @return:
        """
        sweep = end_t - start_t
        if slices is None:
            # A full ellipse can be properly represented with 12 slices - we err on the side of caution here...
            slices = int(1.5 * 12 * sweep / math.tau)
            slices = max(2, slices)
        t_slice = sweep / float(slices)
        alpha = (
            math.sin(t_slice)
            * (math.sqrt(4 + 3 * pow(math.tan(t_slice / 2.0), 2)) - 1)
            / 3.0
        )

        theta = rotation
        current_t = start_t
        cos_theta = math.cos(theta)
        sin_theta = math.sin(theta)

        def point_at_t(t, alpha=1.0):
            cos_t = math.cos(t)
            sin_t = math.sin(t)
            px = cx + alpha * (rx * cos_t * cos_theta - ry * sin_t * sin_theta)
            py = cy + alpha * (rx * cos_t * sin_theta + ry * sin_t * cos_theta)
            return complex(px, py)

        p_start = point_at_t(current_t)

        for i in range(0, slices):
            next_t = current_t + t_slice
            if i == slices - 1:
                next_t = end_t

            cos_start_t = math.cos(current_t)
            sin_start_t = math.sin(current_t)

            ePrimen1x = -rx * cos_theta * sin_start_t - ry * sin_theta * cos_start_t
            ePrimen1y = -rx * sin_theta * sin_start_t + ry * cos_theta * cos_start_t

            cos_end_t = math.cos(next_t)
            sin_end_t = math.sin(next_t)

            p2En2x = cx + rx * cos_end_t * cos_theta - ry * sin_end_t * sin_theta
            p2En2y = cy + rx * cos_end_t * sin_theta + ry * sin_end_t * cos_theta
            p_end = complex(p2En2x, p2En2y)

            ePrimen2x = -rx * cos_theta * sin_end_t - ry * sin_theta * cos_end_t
            ePrimen2y = -rx * sin_theta * sin_end_t + ry * cos_theta * cos_end_t

            p_c1 = complex(
                p_start.real + alpha * ePrimen1x, p_start.imag + alpha * ePrimen1y
            )
            p_c2 = complex(
                p_end.real - alpha * ePrimen2x, p_end.imag - alpha * ePrimen2y
            )
            self.cubic(p_start, p_c1, p_c2, p_end)
            p_start = p_end
            current_t = next_t

    def polyline(self, points, settings=0):
        """
        Add a series of polyline points
        @param points:
        @param settings:
        @return:
        """
        for i in range(1, len(points)):
            self.line(points[i - 1], points[i], settings=settings)

    def reverse(self):
        """
        Reverses geomstr paths. Flipping each segment and the order of the segments.

        This results in a contiguous path going back to front.

        @return: None
        """
        self.segments[: self.index] = np.flip(self.segments[: self.index], (0, 1))

    @staticmethod
    def fit_to_points(replacement, p1, p2, flags=0):
        r = Geomstr(replacement)
        if flags:
            if flags & 0b01:
                # Flip x (reverse order)
                r.reverse()
            if flags & 0b10:
                # Flip y (top-to-bottom)
                r.transform(Matrix.scale(1, -1))
            geoms = r.segments
            infos = np.real(geoms[:, 2]).astype(int)
            q = np.where(infos == TYPE_LINE)
            c1 = np.real(geoms[q][:, 1]).astype(int) ^ (flags & 0b11)
            c2 = np.real(geoms[q][:, 3]).astype(int) ^ (flags & 0b11)
            r.segments[q, 1] = c1
            r.segments[q, 3] = c2
        # Get r points.
        first_point = r.first_point
        last_point = r.last_point

        # Map first point to 0.
        r.translate(-first_point.real, -first_point.imag)

        # Scale distance first->last to distance of p1,p2
        scaled = abs(p1 - p2) / abs(first_point - last_point)
        r.uscale(scaled)

        # rotate angle first->last to the angle of p1-P2
        delta_angle = Geomstr.angle(None, p1, p2) - Geomstr.angle(
            None, first_point, last_point
        )
        r.rotate(delta_angle)

        # Map 0 to position of p1
        r.translate(p1.real, p1.imag)
        return r

    def divide(self, other):
        """
        Divide the current closed point shape by the other.

        This should probably use the other part doing to splitting to create a proper divide. So if cut with a bezier
        we would get a bezier segment making the connection on both sides of the shape.

        @param other:
        @return:
        """
        closed = self.is_closed()
        c = Clip(other)
        polycut = c.polycut(self, breaks=True)

        geoms = list()
        g = Geomstr()
        geoms.append(g)
        for e in polycut.segments[: self.index]:
            if self._segtype(e) == TYPE_END:
                g = Geomstr()
                geoms.append(g)
            else:
                g.append_lines([e])
        if closed and len(geoms) >= 2:
            first = geoms[0]
            last = geoms[-1]
            del geoms[-1]
            first.insert(0, last.segments[: last.index])
        return geoms

    def round_corners(self, amount=0.2):
        """
        Round segment corners.

        @return:
        """
        for i in range(self.index - 1, 0, -1):
            previous = self.segments[i - 1]
            current = self.segments[i]
            start0, control0, info0, control20, end0 = previous
            start1, control1, info1, control21, end1 = current
            if (
                self._segtype(previous) != TYPE_LINE
                or self._segtype(current) != TYPE_LINE
            ):
                continue
            towards0 = Geomstr.towards(None, start0, end0, 1 - amount)
            towards1 = Geomstr.towards(None, start1, end1, amount)
            self.segments[i - 1][4] = towards0
            self.segments[i][0] = towards1
            self.insert(i, [[towards0, control0, info0, control20, towards1]])

    def bezier_corners(self, amount=0.2):
        """
        Round segment corners.

        @return:
        """
        for i in range(self.index - 1, 0, -1):
            previous = self.segments[i - 1]
            current = self.segments[i]
            start0, control0, info0, control20, end0 = previous
            start1, control1, info1, control21, end1 = current
            if (
                self._segtype(previous) != TYPE_LINE
                or self._segtype(current) != TYPE_LINE
            ):
                continue
            towards0 = Geomstr.towards(None, start0, end0, 1 - amount)
            towards1 = Geomstr.towards(None, start1, end1, amount)
            self.segments[i - 1][4] = towards0
            self.segments[i][0] = towards1
            self.insert(i, [[towards0, end0, TYPE_QUAD, start1, towards1]])

    def fractal(self, replacement):
        """
        Perform line-segment fractal replacement according to the ventrella system.

        http://www.fractalcurves.com/

        Only line segments will be replaced. The start and end points of the geomstr data will
        be scaled to the correct size and inserted to replace the current line segments.

        These replacements come in 4 flavors according to the values of extra info values of 'a'. If we perform
        horizontal swaps the positions of a and b will be swapped as well, so `a` and `b` should probably equal each
        other. The values are [0-3], straight/flat, straight/flipped, backwards/flat, backwards/flipped.

        The replacement data will be applied to every line segment, other segment types will not be affected. The
        scale distance and angle will be solely based on the start-and-end points of the replacement non-contiguous
        parts will also be replaced in situ.

        @param replacement: geomstr replacement data for each line segment.
        @return:
        """
        for i in range(self.index - 1, -1, -1):
            segment = self.segments[i]
            start, control, info, control2, end = segment
            if self._segtype(segment) != TYPE_LINE:
                continue
            fit = Geomstr.fit_to_points(
                replacement, start, end, flags=int(np.real(control))
            )
            self.replace(i, i, fit.segments[: fit.index])

    #######################
    # Query Properties
    #######################
    def segment_type(self, e=None, line=None):
        if line is None:
            line = self.segments[e]

        infor = self._segtype(line)
        if infor == TYPE_LINE:
            return "line"
        if infor == TYPE_QUAD:
            return "quad"
        if infor == TYPE_CUBIC:
            return "cubic"
        if infor == TYPE_ARC:
            return "arc"
        if infor == TYPE_POINT:
            return "point"
        if infor == TYPE_VERTEX:
            return "vertex"
        if infor == TYPE_END:
            return "end"
        if infor == TYPE_NOP:
            return "nop"
        if infor == TYPE_FUNCTION:
            return "function"
        if infor == TYPE_UNTIL:
            return "until"
        if infor == TYPE_CALL:
            return "call"

    @property
    def first_point(self):
        """
        First point within the path if said point exists
        @return:
        """
        for i in range(self.index):
            segment = self.segments[i]
            if int(segment[2].real) & 0b1000:
                return segment[0]
        return None

    @property
    def last_point(self):
        """
        Last point within the path if said point exists

        @return:
        """
        for i in range(self.index - 1, -1, -1):
            segment = self.segments[i]
            if int(segment[2].real) & 0b0001:
                return segment[4]
        return None

    #######################
    # Universal Functions
    #######################

    def aabb(self):
        """
        Calculate the per-segment `Axis Aligned Bounding Box` of each individual segment

        @return:
        """
        c = self.segments[: self.index]
        infos = np.real(c[:, 2]).astype(int)

        xs = np.dstack(
            (
                np.real(c[:, 0]),
                np.real(c[:, 4]),
                np.where(infos & 0b0100, np.real(c[:, 1]), np.real(c[:, 0])),
                np.where(infos & 0b0010, np.real(c[:, 3]), np.real(c[:, 4])),
            )
        )
        ys = np.dstack(
            (
                np.imag(c[:, 0]),
                np.imag(c[:, 4]),
                np.where(infos & 0b0100, np.imag(c[:, 1]), np.imag(c[:, 0])),
                np.where(infos & 0b0010, np.imag(c[:, 3]), np.imag(c[:, 4])),
            )
        )
        return xs.min(axis=2), ys.min(axis=2), xs.max(axis=2), ys.max(axis=2)

    def bbox(self, mx=None, e=None):
        """
        Get the bounds of the given geom primitive

        @param mx:
        @param e:
        @return:
        """
        if e is None:
            segments = self.segments
            index = self.index
            bounds = self.bbox(mx=mx, e=segments[0:index])
            min_x, min_y, max_x, max_y = bounds
            min_x = min_x[np.where(~np.isnan(min_x))]
            min_y = min_y[np.where(~np.isnan(min_y))]
            max_x = max_x[np.where(~np.isnan(max_x))]
            max_y = max_y[np.where(~np.isnan(max_y))]
            if len(min_x) == 0:
                return np.nan, np.nan, np.nan, np.nan
            return np.min(min_x), np.min(min_y), np.max(max_x), np.max(max_y)
        if isinstance(e, np.ndarray):
            bboxes = np.zeros((4, len(e)), dtype=float)
            for i, line in enumerate(e):
                bboxes[:, i] = self._bbox_segment(line)
            return bboxes
        line = self.segments[e]
        return self._bbox_segment(line)

    def _bbox_segment(self, line):
        segtype = self._segtype(line)
        if segtype == TYPE_LINE:
            return (
                min(line[0].real, line[-1].real),
                min(line[0].imag, line[-1].imag),
                max(line[0].real, line[-1].real),
                max(line[0].imag, line[-1].imag),
            )
        elif segtype == TYPE_QUAD:
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
        elif segtype == TYPE_CUBIC:
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
        elif segtype == TYPE_ARC:
            local_extremizers = list(self._arc_local_extremes(0, line))
            extreme_points = self._arc_position(line, local_extremizers)
            local_extrema = extreme_points.real
            xmin = min(local_extrema)
            xmax = max(local_extrema)

            local_extremizers = list(self._arc_local_extremes(1, line))
            extreme_points = self._arc_position(line, local_extremizers)
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
        if isinstance(e, int):
            line = self.segments[e]
            segtype = self._segtype(line)
            if segtype == TYPE_LINE:
                point = self._line_position(line, [t])
                return complex(*point)
            if segtype == TYPE_QUAD:
                point = self._quad_position(line, [t])
                return complex(*point)
            if segtype == TYPE_CUBIC:
                point = self._cubic_position(line, [t])
                return complex(*point)
            if segtype == TYPE_ARC:
                point = self._arc_position(line, [t])
                return complex(*point)
            return
        geoms = self.segments[e]
        results = np.zeros(geoms.shape[0], dtype="complex")
        results[:] = complex(np.nan, np.nan)

        infos = np.real(geoms[:, 2]).astype(int)
        q = np.where(infos == TYPE_LINE)
        pts = self._line_position(geoms[q], [t])
        results[q] = pts
        q = np.where(infos == TYPE_QUAD)
        pts = self._quad_position(geoms[q], [t])
        results[q] = pts
        q = np.where(infos == TYPE_CUBIC)
        pts = self._cubic_position(geoms[q], [t])
        results[q] = pts
        q = np.where(infos == TYPE_ARC)
        pts = self._arc_position(geoms[q], [t])
        results[q] = pts
        q = np.where(infos == TYPE_POINT)
        pts = self._line_position(geoms[q], [t])
        results[q] = pts
        return results

    def _line_position(self, line, positions):
        if len(line.shape) != 1:
            # If there's 2d to this, then axis 1 is lines.
            return self.towards(line[:, 0], line[:, -1], positions[0])
        x0, y0 = line[0].real, line[0].imag
        x1, y1 = line[-1].real, line[-1].imag
        return (
            np.interp(positions, [0, 1], [x0, x1])
            + np.interp(positions, [0, 1], [y0, y1]) * 1j
        )

    def _quad_position(self, line, positions):
        """Calculate the x,y position at a certain position of the path. `pos` may be a
        float or a NumPy array."""
        if len(line.shape) != 1:
            # 2d means axis 1 is lines:
            position = positions[0]
            n_pos = 1 - position
            pos_2 = position * position
            n_pos_2 = n_pos * n_pos
            n_pos_pos = n_pos * position
            x0, y0 = line[:, 0].real, line[:, 0].imag
            x1, y1 = line[:, 1].real, line[:, 1].imag
            x2, y2 = line[:, -1].real, line[:, -1].imag
            return (n_pos_2 * x0 + 2 * n_pos_pos * x1 + pos_2 * x2) + (
                n_pos_2 * y0 + 2 * n_pos_pos * y1 + pos_2 * y2
            ) * 1j
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
        if len(line.shape) != 1:
            # 2d means axis 1 is lines:
            position = positions[0]
            pos_3 = position * position * position
            n_pos = 1 - position
            n_pos_3 = n_pos * n_pos * n_pos
            pos_2_n_pos = position * position * n_pos
            n_pos_2_pos = n_pos * n_pos * position
            x0, y0 = line[:, 0].real, line[:, 0].imag
            x1, y1 = line[:, 1].real, line[:, 1].imag
            x2, y2 = line[:, 3].real, line[:, 3].imag
            x3, y3 = line[:, -1].real, line[:, -1].imag
            return (
                n_pos_3 * x0 + 3 * (n_pos_2_pos * x1 + pos_2_n_pos * x2) + pos_3 * x3
            ) + (
                n_pos_3 * y0 + 3 * (n_pos_2_pos * y1 + pos_2_n_pos * y2) + pos_3 * y3
            ) * 1j

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
        if len(line.shape) != 1:
            # 2d means axis 1 is lines:
            results = np.zeros(line.shape[0], dtype=complex)
            for i, _line in enumerate(line):
                results[i] = self._arc_position(line, positions)
            return results
        start, control, info, control2, end = line

        xy = np.empty((len(positions), 2), dtype=float)
        center = self.arc_center(line=line)
        theta = self.angle(center, start)
        sweep = self.arc_sweep(line=line, center=center)

        if start == end and sweep == 0:
            xy[:, 0], xy[:, 1] = start
        else:
            positions = np.array(positions)
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

    def _arc_local_extremes(self, v, e):
        """
        returns the extreme t values for an arc curve
        """
        yield 0.0
        yield 1.0

        start, control, info, control2, end = e
        t = np.array([float(k) * math.tau / 4.0 for k in range(-4 + v, 5, 2)])

        center = self.arc_center(line=e)
        start_t = self.angle(center, start)
        sweep = self.arc_sweep(line=e, center=center)
        candidates = t - start_t
        candidates /= sweep
        q = np.dstack(
            (
                0.0 < candidates,
                1.0 > candidates,
            )
        ).all(axis=2)
        yield from candidates[q[0]]

    def length(self, e=None):
        """
        Returns the length of geom e.

        @param e:
        @return:
        """
        if e is None:
            total = 0
            for i in range(self.index):
                total += self.length(i)
            return total

        line = self.segments[e]
        start, control1, info, control2, end = line
        segtype = self._segtype(line)
        if segtype in NON_GEOMETRY_TYPES:
            return 0
        if segtype == TYPE_POINT:
            return 0
        if segtype == TYPE_LINE:
            return abs(start - end)
        if segtype == TYPE_QUAD:
            a = start - 2 * control1 + end
            b = 2 * (control1 - start)
            # For an explanation of this case, see
            # http://www.malczak.info/blog/quadratic-bezier-curve-length/
            A = 4 * (a.real * a.real + a.imag * a.imag)
            B = 4 * (a.real * b.real + a.imag * b.imag)
            C = b.real * b.real + b.imag * b.imag

            Sabc = 2 * math.sqrt(A + B + C)
            A2 = math.sqrt(A)
            A32 = 2 * A * A2
            C2 = 2 * math.sqrt(C)
            if abs(A2) <= 1e-11:
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
            BA = B / A2
            return (
                A32 * Sabc
                + A2 * B * (Sabc - C2)
                + (4 * C * A - B * B) * math.log((2 * A2 + BA + Sabc) / (BA + C2))
            ) / (4 * A32)
        if segtype == TYPE_CUBIC:
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
        if segtype == TYPE_ARC:
            """The length of an elliptical arc segment requires numerical
            integration, and in that case it's simpler to just do a geometric
            approximation, as for cubic Bézier curves.
            """
            positions = self._arc_position(line, np.linspace(0, 1))
            q = np.arange(0, len(positions) - 1)
            pen_downs = positions[q]  # values 0-49
            pen_ups = positions[q + 1]  # values 1-50
            res = np.sum(np.abs(pen_ups - pen_downs))
            # print (f"Calculated for an arc: {res}")
            return res

        # print (f"And now I have no idea how to deal with type {info.real}")
        return 0

    def area(self, density=None):
        """
        Gives the area of a particular geometry.

        @param density: the interpolation density
        @return:
        """
        if density is None:
            density = 100
        area = 0
        for poly in self.as_interpolated_segments(interpolate=density):
            p_array = np.array(poly)
            original = len(p_array)
            indexes0 = np.arange(0, original - 1)
            indexes1 = indexes0 + 1
            starts = p_array[indexes0]
            ends = p_array[indexes1]
            # use the numpy multiplication of all columns with n-1 of the previous
            area_xy = np.sum(np.real(ends) * np.imag(starts))
            area_yx = np.sum(np.imag(ends) * np.real(starts))
            area += 0.5 * abs(area_xy - area_yx)
        return area

    def _cubic_length_via_quad(self, line):
        """
        If we have scipy.integrate available, use quad from that to solve this.

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

    def split(self, e, t, breaks=False):
        """
        Splits individual geom e at position t [0-1]

        @param e:
        @param t: position(s) to split at (numpy ok)
        @param breaks: include breaks/ends between contours
        @return:
        """
        line = self.segments[e]
        start, control, info, control2, end = line
        segtype = self._segtype(line)
        if segtype == TYPE_LINE:
            try:
                if len(t):
                    # If this is an array the cuts must be in order.
                    t = np.sort(t)
            except TypeError:
                pass
            mid = self.towards(start, end, t)
            if isinstance(mid, complex):
                yield start, control, info, control2, mid
                if breaks:
                    yield mid, mid, complex(TYPE_END, info.imag), mid, mid
                yield mid, control, info, control2, end
            else:
                # Mid is an array of complexes
                yield start, control, info, control2, mid[0]
                for i in range(1, len(mid)):
                    if breaks:
                        yield (
                            mid[i - 1],
                            mid[i - 1],
                            complex(TYPE_END, info.imag),
                            mid[i - 1],
                            mid[i - 1],
                        )
                    yield mid[i - 1], control, info, control2, mid[i]
                if breaks:
                    yield mid[-1], 0, complex(TYPE_END, info.imag), 0, mid[-1]
                yield mid[-1], control, info, control2, end
        if segtype == TYPE_QUAD:
            yield from self._split_quad(e, t, breaks=breaks)
        if segtype == TYPE_CUBIC:
            yield from self._split_cubic(e, t, breaks=breaks)

    def _split_quad(self, e, t, breaks):
        """
        Performs deCasteljau's algorithm unrolled.
        """
        if (
            not isinstance(e, (np.ndarray, tuple, list))
            or len(e) == 0
            or not isinstance(e[0], complex)
        ):
            e = self.segments[e]
        if isinstance(t, (np.ndarray, tuple, list)):
            if len(t) == 1:
                t = t[0]
            else:
                t = np.sort(t)
                last = 0.0
                for t0 in sorted(t):
                    # Thanks tiger.
                    splits = list(
                        self._split_quad(e, (t0 - last) / (1 - last), breaks=breaks)
                    )
                    last = t0
                    yield splits[0]
                    e = splits[1]
                yield e
                return
        start, control, info, control2, end = e
        r1_0 = t * (control - start) + start
        r1_1 = t * (end - control) + control
        r2 = t * (r1_1 - r1_0) + r1_0
        yield start, r1_0, info, r1_0, r2
        # yield r2, 0, complex(TYPE_END, info.imag), 0, r2
        yield r2, r1_1, info, r1_1, end

    def _split_cubic(self, e, t, breaks=False):
        if (
            not isinstance(e, (np.ndarray, tuple, list))
            or len(e) == 0
            or not isinstance(e[0], complex)
        ):
            e = self.segments[e]
        if isinstance(t, (np.ndarray, tuple, list)):
            if len(t) == 1:
                t = t[0]
            else:
                t = np.sort(t)
                last = 0.0
                for t0 in sorted(t):
                    splits = list(
                        self._split_cubic(e, (t0 - last) / (1 - last), breaks=breaks)
                    )
                    last = t0
                    yield splits[0]
                    e = splits[1]
                yield e
                return
        start, control, info, control2, end = e
        r1_0 = t * (control - start) + start
        r1_1 = t * (control2 - control) + control
        r1_2 = t * (end - control2) + control2
        r2_0 = t * (r1_1 - r1_0) + r1_0
        r2_1 = t * (r1_2 - r1_1) + r1_1
        r3 = t * (r2_1 - r2_0) + r2_0
        yield start, r1_0, info, r2_0, r3
        # yield r3, 0, complex(TYPE_END, info.imag), 0, r3
        yield r3, r2_1, info, r1_2, end

    def normal(self, e, t):
        """
        return the unit-normal (right hand rule) vector to this at t.

        @param e:
        @param t:
        @return:
        """
        return -1j * self.tangent(e, t)

    def tangent(self, e, t):
        """
        returns the tangent vector of the geom at t (centered at origin).

        @param e:
        @param t:
        @return:
        """
        start, control1, info, control2, end = self.segments[e]
        segtype = self._segtype(self.segments[e])
        if segtype == TYPE_LINE:
            dseg = end - start
            return dseg / abs(dseg)

        if segtype in (TYPE_QUAD, TYPE_CUBIC):
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

        if segtype == TYPE_ARC:
            dseg = self.derivative(e, t)
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
        segtype = self._segtype(self.segments[e])
        if segtype == TYPE_LINE:
            return 0
        if segtype in (TYPE_QUAD, TYPE_CUBIC, TYPE_ARC):
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
        segtype = self._segtype(line)
        if segtype == TYPE_CUBIC:
            return np.poly1d(self._cubic_coeffs(line))
        if segtype == TYPE_QUAD:
            return np.poly1d(self._quad_coeffs(line))
        if segtype == TYPE_LINE:
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
        segtype = self._segtype(line)

        if segtype == TYPE_LINE:
            if n == 1:
                return end - start
            return 0

        if segtype == TYPE_QUAD:
            if n == 1:
                return 2 * ((control - start) * (1 - t) + (end - control) * t)
            elif n == 2:
                return 2 * (end - 2 * control + start)
            return 0

        if segtype == TYPE_CUBIC:
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
        if segtype == TYPE_ARC:
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

    def intersections(self, e, other):
        line1 = self.segments[e] if isinstance(e, int) else e
        line2 = self.segments[other] if isinstance(other, int) else other
        segtype1 = self._segtype(line1)
        segtype2 = self._segtype(line2)
        start, control1, info, control2, end = line1
        ostart, ocontrol1, oinfo, ocontrol2, oend = line2
        if segtype1 in (TYPE_LINE, TYPE_QUAD, TYPE_CUBIC) and segtype2 in (
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
        if segtype1 in NON_GEOMETRY_TYPES:
            return
        if segtype2 in NON_GEOMETRY_TYPES:
            return
        if segtype1 == TYPE_LINE:
            if segtype2 == TYPE_LINE:
                yield from self._line_line_intersections(line1, line2)
                return
        #     if oinfo.real == TYPE_QUAD:
        #         yield from self._line_quad_intersections(line1, line2)
        #         return
        #     if oinfo.real == TYPE_CUBIC:
        #         yield from self._line_cubic_intersections(line1, line2)
        #         return
        #
        # if info.real == TYPE_QUAD:
        #     if oinfo.real == TYPE_LINE:
        #         yield from self._line_quad_intersections(line2, line1)
        #         return
        #
        # if info.real == TYPE_CUBIC:
        #     if oinfo.real == TYPE_LINE:
        #         yield from self._line_cubic_intersections(line2, line1)
        #         return
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
        segtype1 = self._segtype(segment1)
        segtype2 = self._segtype(segment2)

        fun1 = self._get_segment_function(segtype1)
        fun2 = self._get_segment_function(segtype2)
        if fun1 is None or fun2 is None:
            return  # Only shapes can intersect. We don't do point x point.
        yield from self._find_intersections_intercept(segment1, segment2, fun1, fun2)

    def _find_intersections_intercept(
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
            # Zoomed min+segment intersected.
            # Fractional guess within intersected segment
            at_guess = ta[0] + (hit[1] + ta_hit[i]) * step_a
            bt_guess = tb[0] + (hit[0] + tb_hit[i]) * step_b

            if depth == enhancements:
                # We've enhanced as best as we can, yield the current + segment t-value to our answer
                yield at_guess, bt_guess
            else:
                yield from self._find_intersections_intercept(
                    segment1,
                    segment2,
                    fun1,
                    fun2,
                    ta=(at_guess - step_a / 2, at_guess + step_a / 2, at_guess),
                    tb=(bt_guess - step_b / 2, bt_guess + step_b / 2, bt_guess),
                    samples=enhance_samples,
                    depth=depth + 1,
                    enhancements=enhancements,
                    enhance_samples=enhance_samples,
                )

    def _find_intersections_kross(
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

        p0 = j[:-1]
        d0 = j[1:] - j[:-1]
        p1 = k[:-1]
        d1 = k[1:] - k[:-1]

        ap0, ap1 = np.meshgrid(p0, p1)
        ad0, ad1 = np.meshgrid(d0, d1)
        e = ap1 - ap0
        ex = np.real(e)
        ey = np.imag(e)
        d0x = np.real(ad0)
        d0y = np.imag(ad0)
        d1x = np.real(ad1)
        d1y = np.imag(ad1)

        kross = (d0x * d1y) - (d0y * d1x)
        # sqkross = kross * kross
        # sqLen0 = np.real(ad0) * np.real(ad0) + np.imag(ad0) * np.imag(ad0)
        # sqLen1 = np.real(ad1) * np.real(ad1) + np.imag(ad1) * np.imag(ad1)
        s = ((ex * d1y) - (ey * d1x)) / kross
        t = ((ex * d0y) - (ey * d0x)) / kross
        hits = np.dstack(
            (
                # sqkross > 0.01 * sqLen0 * sqLen1,
                s >= 0,
                s <= 1,
                t >= 0,
                t <= 1,
            )
        ).all(axis=2)
        where_hit = np.argwhere(hits)

        # pos = ap0[hits] + s[hits] * ad0[hits]
        if len(where_hit) != 1 and step_a < 1e-10:
            # We're hits are becoming unstable give last best value.
            if ta[2] is not None and tb[2] is not None:
                yield ta[2], tb[2]
            return

        # Calculate the t values for the intersections
        ta_hit = s[hits]
        tb_hit = t[hits]

        for i, hit in enumerate(where_hit):
            # Zoomed min+segment intersected.
            # Fractional guess within intersected segment
            at_guess = ta[0] + (hit[1] + ta_hit[i]) * step_a
            bt_guess = tb[0] + (hit[0] + tb_hit[i]) * step_b

            if depth == enhancements:
                # We've enhanced as best as we can, yield the current + segment t-value to our answer
                yield at_guess, bt_guess
            else:
                yield from self._find_intersections_kross(
                    segment1,
                    segment2,
                    fun1,
                    fun2,
                    ta=(at_guess - step_a / 2, at_guess + step_a / 2, at_guess),
                    tb=(bt_guess - step_b / 2, bt_guess + step_b / 2, bt_guess),
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

    def brute_line_intersections(self):
        """
        Brute line intersections finds all the intersections of all the lines in the geomstr with brute force.

        @return: intersection-indexes, position, t-values
        """
        geoms = self.segments[: self.index]
        infos = np.real(geoms[:, 2]).astype(int)
        q = np.where(infos == TYPE_LINE)
        starts = geoms[q][:, 0]
        ends = geoms[q][:, -1]
        lines = np.dstack((starts, ends))[0]
        x, y = np.triu_indices(len(starts), 1)
        j = lines[x]
        k = lines[y]
        a1 = j[:, 0]
        ax1 = np.real(a1)
        ay1 = np.imag(a1)
        b1 = k[:, 0]
        bx1 = np.real(b1)
        by1 = np.imag(b1)
        a2 = j[:, 1]
        ax2 = np.real(a2)
        ay2 = np.imag(a2)
        b2 = k[:, 1]
        bx2 = np.real(b2)
        by2 = np.imag(b2)

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
        )
        hits = hits.all(axis=2)[0]

        where_hits = np.dstack((x[hits], y[hits]))[0]
        ta_hit = qa[hits] / denom[hits]
        tb_hit = qb[hits] / denom[hits]

        x_vals = ax1[hits] + ta_hit * (ax2[hits] - ax1[hits])
        y_vals = ay1[hits] + ta_hit * (ay2[hits] - ay1[hits])
        wh = q[0][where_hits]
        return wh, x_vals + y_vals * 1j, ta_hit, tb_hit

    #######################
    # Geom Transformations
    #######################

    def transform(self, mx, e=None):
        """
        Affine Transformation by an arbitrary matrix.
        @param mx: Matrix to transform by
        @param e: index, line values
        @return:
        """
        if e is not None:
            geoms = self.segments[e]

            geoms[0] = (
                np.real(geoms[0]) * mx.a + np.imag(geoms[0]) * mx.c + 1 * mx.e
            ) + (np.real(geoms[0]) * mx.b + np.imag(geoms[0]) * mx.d + 1 * mx.f) * 1j
            geoms[4] = (
                np.real(geoms[4]) * mx.a + np.imag(geoms[4]) * mx.c + 1 * mx.e
            ) + (np.real(geoms[4]) * mx.b + np.imag(geoms[4]) * mx.d + 1 * mx.f) * 1j

            infos = geoms[2]
            q = np.where(infos.astype(int) & 0b0110)
            geoms = self.segments[q]

            geoms[1] = (
                np.real(geoms[1]) * mx.a + np.imag(geoms[1]) * mx.c + 1 * mx.e
            ) + (np.real(geoms[1]) * mx.b + np.imag(geoms[1]) * mx.d + 1 * mx.f) * 1j
            geoms[3] = (
                np.real(geoms[3]) * mx.a + np.imag(geoms[3]) * mx.c + 1 * mx.e
            ) + (np.real(geoms[3]) * mx.b + np.imag(geoms[3]) * mx.d + 1 * mx.f) * 1j
            return
        segments = self.segments
        index = self.index
        starts = segments[:index, 0]
        reals = starts.real * mx.a + starts.imag * mx.c + 1 * mx.e
        imags = starts.real * mx.b + starts.imag * mx.d + 1 * mx.f
        segments[:index, 0] = reals + 1j * imags
        ends = segments[:index, 4]
        reals = ends.real * mx.a + ends.imag * mx.c + 1 * mx.e
        imags = ends.real * mx.b + ends.imag * mx.d + 1 * mx.f
        segments[:index, 4] = reals + 1j * imags

        infos = segments[:index, 2]
        q = np.where(np.real(infos).astype(int) & 0b0110)

        c0s = segments[q, 1]
        reals = c0s.real * mx.a + c0s.imag * mx.c + 1 * mx.e
        imags = c0s.real * mx.b + c0s.imag * mx.d + 1 * mx.f
        segments[q, 1] = reals + 1j * imags
        c1s = segments[q, 3]
        reals = c1s.real * mx.a + c1s.imag * mx.c + 1 * mx.e
        imags = c1s.real * mx.b + c1s.imag * mx.d + 1 * mx.f
        segments[q, 3] = reals + 1j * imags

    def transform3x3(self, mx, e=None):
        """
        Perspective Transformation by an arbitrary 3x3 matrix.
        @param mx: Matrix to transform by (3x3)
        @param e: index, line values
        @return:
        """
        if e is None:
            i0 = 0
            i1 = self.index
            e = self.segments[i0:i1]

        def value(x, y):
            m = mx.mx
            count = len(x)
            pts = np.vstack((x, y, np.ones(count)))
            result = np.dot(m, pts)
            return result[0] / result[2] + 1j * result[1] / result[2]

        starts = e[..., 0]
        e[..., 0] = value(starts.real, starts.imag)

        ends = e[..., 4]
        e[..., 4] = value(ends.real, ends.imag)

        infos = e[..., 2]
        q = np.where(np.real(infos).astype(int) & 0b0110)[0]

        c0s = e[q, 1]
        e[q, 1] = value(c0s.real, c0s.imag)

        c1s = e[q, 3]
        e[q, 3] = value(c1s.real, c1s.imag)

    def translate(self, dx, dy, e=None):
        """
        Translate the location within the path.

        @param dx: change in x
        @param dy: change in y
        @param e: index, line values
        @return:
        """
        if e is None:
            segments = self.segments
            index = self.index
            segments[:index, 0] += complex(dx, dy)
            segments[:index, 4] += complex(dx, dy)
            infos = segments[:index, 2]
            q = np.where(np.real(infos).astype(int) & 0b0110)
            segments[q, 1] += complex(dx, dy)
            segments[q, 3] += complex(dx, dy)
            return
        geoms = self.segments[e]
        offset = complex(dx, dy)
        geoms[0] += offset
        geoms[4] += offset
        infos = geoms[2]
        q = np.where(infos.astype(int) & 0b0110)
        geoms = self.segments[q]
        geoms[1] += offset
        geoms[3] += offset

    def uscale(self, scale, e=None):
        """
        Uniform scaling operation

        @param scale: uniform scaling factor
        @param e: index, line values
        @return:
        """
        if e is None:
            segments = self.segments
            index = self.index
            segments[:index, 0] *= scale
            segments[:index, 4] *= scale
            infos = segments[:index, 2]
            q = np.where(np.real(infos).astype(int) & 0b0110)
            segments[q, 1] *= scale
            segments[q, 3] *= scale
            return
        geoms = self.segments[e]
        geoms[0] *= scale
        geoms[4] *= scale

        infos = geoms[2]
        q = np.where(infos.astype(int) & 0b0110)
        geoms = self.segments[q]
        geoms[1] *= scale
        geoms[3] *= scale

    def rotate(self, angle, e=None):
        """
        Rotate segments around the origin.
        @param angle: angle in radians
        @param e: index, line values
        @return:
        """
        rotation = complex(math.cos(angle), math.sin(angle))
        self.uscale(rotation, e=e)

    def as_transformed(self, mx):
        g = copy(self)
        g.transform(mx)
        return g

    #######################
    # Arc Functions
    #######################

    def arc_radius(self, e=None, line=None):
        if line is None:
            line = self.segments[e]
        start = line[0]
        center = Geomstr.arc_center(self, line=line)
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
        if sweep < 0:
            # sweep is the now the positive value from start to reach end going clockwise.
            sweep += math.tau
        if self.orientation(start, control, end) != "cw":
            # sweep is the negative value from start to reach end going counter-clockwise
            return sweep - math.tau
        return sweep

    def arc_t_at_point(self, point, e=None, line=None, center=None):
        if line is None:
            line = self.segments[e]
        start, control, info, control2, end = line
        if center is None:
            center = self.arc_center(line=line)
        start_t = self.angle(center, start)
        sweep = self.arc_sweep(line=line, center=center)
        angle_at_point = self.angle(center, point) - start_t

        w = np.where(angle_at_point < 0)
        angle_at_point[w] += math.tau  # ranged 0, tau
        t_at_point = angle_at_point / sweep

        return t_at_point

    #######################
    # Point/Endpoint Functions
    #######################

    def convex_hull(self, pts):
        """
        Generate points of the convex hull around the given points.

        If a point refers to a non-point with differing start/end values then
        ~index refers to the endpoint and index refers to the start point.

        Also accepts complex number coordinates, as well as (x,y) coordinate, instead of geom endpoint.

        @param pts:

        @return:
        Uses a fast quickhull implementation found here: https://gist.github.com/marmakoide/549d925fa55b4d24dad9a0dedc33ae11
        Quickhull algorithm: https://en.wikipedia.org/wiki/Quickhull
        """

        def process(S, P, a, b):
            signed_dist = np.cross(S[P] - S[a], S[b] - S[a])
            K = [i for s, i in zip(signed_dist, P) if s > 0 and i != a and i != b]

            if len(K) == 0:
                return (a, b)

            c = max(zip(signed_dist, P))[1]
            return process(S, K, a, c)[:-1] + process(S, K, c, b)

        def quickhull_2d(S: np.ndarray) -> np.ndarray:
            a, b = np.argmin(S[:, 0]), np.argmax(S[:, 0])
            max_index = np.argmax(S[:, 0])
            # max_element = S[max_index]
            return (
                process(S, np.arange(S.shape[0]), a, max_index)[:-1]
                + process(S, np.arange(S.shape[0]), max_index, a)[:-1]
            )

        if len(pts) == 0:
            return
        points = []
        for i in range(len(pts)):
            p = pts[i]
            if p is None or (isinstance(p, complex) and np.isnan(p.real)):
                continue
            if isinstance(p, int):
                if p < 0:
                    p = self.segments[~p][-1]
                else:
                    p = self.segments[p][0]
            if isinstance(p, complex):
                points.append((p.real, p.imag))
            else:
                points.append(p)

        c_points = np.array(points)
        hull = quickhull_2d(c_points)
        if hull:
            res_pts = c_points[np.array(hull)]
            for p in res_pts:
                yield complex(p[0], p[1])

    def _convex_hull_original(self, pts):
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
            if p is None or np.isnan(p.real):
                continue
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
        # I think tats math is wrong, so here's my orientation calculation
        # but that will let multiple unit tests fail
        # val = (q.real - p.real) * (r.imag - p.imag) - (q.imag - p.imag) * (r.real - p.real)

        val = (q.imag - p.imag) * (r.real - q.real) - (q.real - p.real) * (
            r.imag - q.imag
        )
        if val == 0:
            return "linear"
        elif val > 0:
            return "ccw"
        else:
            return "cw"

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
        return np.arctan2(d.imag, d.real)

    def towards(self, p1, p2, amount):
        """
        Position from p1 towards p2 by amount.

        If p1 or p2 refers to a non-point with differing start/end values then
        ~index refers to the endpoint and index refers to the start point.

        Also accepts complex number coordinates, instead of geom endpoint.

        @param p1:
        @param p2:
        @param amount: value (numpy array accepted)
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

    def near(self, p, distance):
        """
        Find the points in the geometry which are within distance units of p.

        @param p:
        @param distance:
        @return:
        """
        geoms = self.segments[: self.index]
        infos = geoms[:, 2]
        a = np.real(infos).astype(int) & 0b1000 != 0
        b = np.real(infos).astype(int) & 0b0100 != 0
        c = np.real(infos).astype(int) | 0b1111 == 0  # False
        d = np.real(infos).astype(int) & 0b0010 != 0
        e = np.real(infos).astype(int) & 0b0001 != 0
        v = np.dstack((a, b, c, d, e))[0]
        q = abs(geoms - p) <= distance
        return np.argwhere(q & v)

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
        if len(line.shape) == 2:
            a = line[:, 0]
            b = line[:, -1]
        else:
            a = line[0]
            b = line[-1]
        old_np_seterr = np.seterr(invalid="ignore", divide="ignore")
        try:
            m = (b.imag - a.imag) / (b.real - a.real)
        finally:
            np.seterr(**old_np_seterr)
        return m

    def y_at_axis(self, e):
        """
        y_intercept of the lines (e) at x-axis (x=0)

        @param e:
        @return:
        """
        line = self.segments[e]
        if len(line.shape) == 2:
            a = line[:, 0]
            b = line[:, -1]
        else:
            a = line[0]
            b = line[-1]
        old_np_seterr = np.seterr(invalid="ignore", divide="ignore")
        try:
            im = (b.imag - a.imag) / (b.real - a.real)
            return a.imag - (im * a.real)
        finally:
            np.seterr(**old_np_seterr)

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

    def x_intercept(self, e, y, default=np.nan):
        """
        Gives the x_intercept of a line at a specific value of y.

        @param e: Segment line numbers to solve.
        @param y: y value at which to find corresponding x value.
        @param default: default value if answer is otherwise undefined.
        @return:
        """
        line = self.segments[e]
        a = line[..., 0]
        b = line[..., -1]
        old_np_seterr = np.seterr(invalid="ignore", divide="ignore")
        try:
            # If horizontal slope is undefined. But, all x-ints are at x since x0=x1
            m = (b.imag - a.imag) / (b.real - a.real)
            y0 = a.imag - (m * a.real)
            pts = np.where(~np.isinf(m), (y - y0) / m, np.real(a))
            pts[m == 0] = default
            return pts
        finally:
            np.seterr(**old_np_seterr)

    def y_intercept(self, e, x, default=np.nan):
        """
        Gives the y_intercept of a line at a specific value of x, if undefined returns default.

        @param e: Segment line numbers to solve.
        @param x: x value at which to find corresponding y values.
        @param default: default value if answer is otherwise undefined.
        @return:
        """
        line = self.segments[e]
        a = line[..., 0]
        b = line[..., -1]
        old_np_seterr = np.seterr(invalid="ignore", divide="ignore")
        try:
            # If vertical slope is undefined. But, all y-ints are at y since y0=y1
            m = (b.real - a.real) / (b.imag - a.imag)
            x0 = a.real - (m * a.imag)
            if len(x0.shape) >= 2:
                x = np.reshape(np.repeat(x, x0.shape[1]), x0.shape)
                default = np.reshape(np.repeat(default, x0.shape[1]), x0.shape)
            pts = np.where(~np.isinf(m), (x - x0) / m, np.imag(a))
            pts = np.where(m == 0, default, pts)
            # pts[m == 0] = default
            return pts
        finally:
            np.seterr(**old_np_seterr)

    #######################
    # Geometry Window Functions
    #######################

    def as_path(self):
        _open = True
        path = Path()
        for p in self.segments[: self.index]:
            s, c0, i, c1, e = p
            segtype = self._segtype(p)
            if segtype == TYPE_END:
                _open = True
                continue

            if _open or len(path) == 0 or path.current_point != s:
                path.move(s)
                _open = False
            if segtype == TYPE_LINE:
                path.line(e)
            elif segtype == TYPE_QUAD:
                path.quad(c0, e)
            elif segtype == TYPE_CUBIC:
                path.cubic(c0, c1, e)
            elif segtype == TYPE_ARC:
                path.append(Arc(start=s, control=c0, end=e))
                # path.arc(start=s, control=c0, end=e)
            elif segtype == TYPE_POINT:
                path.move(s)
                path.closed()
        return path

    # def as_contiguous_org(self):
    #     segments = self.segments
    #     index = self.index
    #     # infos = segments[:index, 2]
    #
    #     original = self.index
    #     indexes0 = np.arange(0, original - 1)
    #     indexes1 = indexes0 + 1
    #
    #     pen_ups = segments[indexes0, -1]
    #     pen_downs = segments[indexes1, 0]
    #
    #     q = np.where(pen_ups != pen_downs)[0]
    #     last = 0
    #     for m in q:
    #         if m != last:
    #             yield Geomstr(self.segments[last:m+1])
    #         last = m + 1
    #     if last != self.index:
    #         yield Geomstr(self.segments[last: self.index])

    def as_contiguous(self):
        """
        Generate individual subpaths of contiguous segments

        @return:
        """
        last = 0
        for idx, seg in enumerate(self.segments[: self.index]):
            segtype = self._segtype(seg)
            if segtype == TYPE_END:
                yield Geomstr(self.segments[last:idx])
                last = idx + 1
            elif idx > 0:
                # are the start and endpositions different?
                if self.segments[idx, 0] != self.segments[idx - 1, -1]:
                    yield Geomstr(self.segments[last:idx])
                    last = idx
        if last != self.index:
            yield Geomstr(self.segments[last : self.index])

    def ensure_proper_subpaths(self):
        """
        Will look at interrupted segments that don't have an 'end' between them
        and inserts one if necessary
        """
        idx = 1
        while idx < self.index:
            seg1 = self.segments[idx]
            segtype1 = self._segtype(seg1)
            seg2 = self.segments[idx - 1]
            segtype2 = self._segtype(seg2)
            if segtype1 in META_TYPES or segtype2 in META_TYPES:
                continue
            if segtype1 != TYPE_END and segtype2 != TYPE_END and seg1[0] != seg2[-1]:
                # This is a non-contiguous segment
                end_segment = (
                    np.nan,
                    np.nan,
                    complex(TYPE_END, 0),
                    np.nan,
                    np.nan,
                )
                # print (f"inserted an end at #{idx}")
                self.insert(idx, end_segment)
            idx += 1
        # And at last: we don't need an TYPE_END as very last segment
        if self.index:
            seg1 = self.segments[self.index - 1]
            if self._segtype(seg1) == TYPE_END:
                self.index -= 1

    def as_subpaths(self):
        """
        Generate individual subpaths.

        @return:
        """
        types = self.segments[: self.index, 2]
        q = np.where(types.real == TYPE_END)[0]
        last = 0
        for m in q:
            if m != last:
                yield Geomstr(self.segments[last:m])
            last = m + 1
        if last != self.index:
            yield Geomstr(self.segments[last : self.index])

    def render(self, buffer=10, scale=1):
        sb = Scanbeam(self)
        nx, ny, mx, my = self.bbox()
        px, py = np.mgrid[
            nx - buffer : mx + buffer : scale, ny - buffer : my + buffer : scale
        ]
        ppx = px + 1j * py
        pxs = ppx.ravel()
        data = sb.points_in_polygon(pxs)

        from PIL import Image

        size = ppx.shape[::-1]
        databytes = np.packbits(data)
        return Image.frombytes(mode="1", size=size, data=databytes)

    def draw(self, draw, offset_x, offset_y):
        """
        Though not a requirement, this draws with the given ImageDraw api found in Pillow.

        Currently only works with lines.
        @param draw: draw object
        @param offset_x: x offset
        @param offset_y: y offset
        @return:
        """
        types = self.segments[: self.index, 2]
        q = np.where(types.real == TYPE_LINE)
        for line in self.segments[q]:
            start, control1, info, control2, end = line
            draw.line(
                (
                    int(start.real) - offset_x,
                    int(start.imag) - offset_y,
                    int(end.real) - offset_x,
                    int(end.imag) - offset_y,
                ),
                fill="black",
            )

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

    def simplify(self, tolerance=25, inplace=False):
        """
        Simplifies polyline sections of a geomstr by applying the Ramer-Douglas-Peucker algorithm.
        https://en.wikipedia.org/wiki/Ramer%E2%80%93Douglas%E2%80%93Peucker_algorithm

        Tolerance is the maximum distance a point might have from a line to still be considered
        collinear.
        - a value of about 25 would reduce the effective resolution to about 1/1000 mm
        - a value of 65 to about 1 mil = 1/1000 inch
        """

        def _compute_distances(points, start, end):
            """Compute the distances between all points and the line defined by start and end.

            :param points: Points to compute distance for.
            :param start: Starting point of the line
            :param end: End point of the line

            :return: Points distance to the line.
            """
            line = end - start
            line_length = np.linalg.norm(line)
            if line_length == 0:
                return np.linalg.norm(points - start, axis=-1)
            if line.size == 2:
                return abs(np.cross(line, start - points)) / line_length  # 2D case
            return (
                abs(np.linalg.norm(np.cross(line, start - points), axis=-1))
                / line_length
            )  # 3D case

        def _mask(points, epsilon: float):
            stack = [[0, len(points) - 1]]
            indices = np.ones(len(points), dtype=bool)

            while stack:
                start_index, last_index = stack.pop()

                local_points = points[indices][start_index + 1 : last_index]
                if len(local_points) == 0:
                    continue
                distances = _compute_distances(
                    local_points, points[start_index], points[last_index]
                )
                dist_max = max(distances)
                index_max = start_index + 1 + np.argmax(distances)

                if dist_max > epsilon:
                    stack.append([start_index, index_max])
                    stack.append([index_max, last_index])
                else:
                    indices[start_index + 1 : last_index] = False
            return indices

        def _rdp(points, epsilon: float):
            mask = _mask(points, epsilon)
            return points[mask]

        geoms = self.segments[: self.index]
        infos = np.real(geoms[:, 2]).astype(int)
        q = infos == TYPE_LINE
        a = np.pad(q, (0, 1), constant_values=False)
        b = np.pad(q, (1, 0), constant_values=False)
        starts = a & ~b
        ends = ~a & b
        start_pos = np.nonzero(starts)[0]
        end_pos = np.nonzero(ends)[0]
        if inplace:
            newgeometry = self
        else:
            newgeometry = Geomstr(self)
        for s, e in zip(reversed(start_pos), reversed(end_pos)):
            replace = Geomstr()
            for to_simplify, settings in self.as_contiguous_segments(s, e):
                points = [
                    (x, y) for x, y in zip(np.real(to_simplify), np.imag(to_simplify))
                ]
                simplified = _rdp(np.array(points), tolerance)
                c_simp = simplified[:, 0] + simplified[:, 1] * 1j
                replace.append(Geomstr.lines(c_simp, settings=settings))
            newsegs = replace.segments[: replace.index]
            newgeometry.replace(s, e - 1, newsegs)
        return newgeometry

    #######################
    # Global Functions
    #######################

    def raw_length(self):
        """
        Determines the raw length of the geoms. Where length is taken as the distance
        from start to end (ignoring any curving), real length could be greater than this
        but never less.

        @return:
        """
        segments = self.segments
        index = self.index
        infos = segments[:index, 2]
        q = np.where(np.real(infos).astype(int) & 0b1001)
        pen_downs = segments[q, 0]
        pen_ups = segments[q, -1]
        return np.sum(np.abs(pen_ups - pen_downs))

    def travel_distance(self):
        """
        Calculate the total travel distance for this geomstr.
        @return: distance in units for the travel
        """
        segments = self.segments
        index = self.index
        infos = segments[:index, 2]
        q = np.where(np.real(infos).astype(int) & 0b1001)
        valid_segments = segments[q]

        indexes0 = np.arange(0, len(valid_segments) - 1)
        indexes1 = indexes0 + 1
        pen_ups = valid_segments[indexes0, -1]
        pen_downs = valid_segments[indexes1, 0]
        return np.sum(np.abs(pen_ups - pen_downs))

    def remove_0_length(self):
        """
        Determines the raw length of the geoms, drops any segments which are 0 distance.

        @return:
        """
        segments = self.segments
        index = self.index
        infos = segments[:index, 2]
        pen_downs = segments[:index, 0]
        pen_ups = segments[:index, -1]
        v = np.dstack(
            ((np.real(infos).astype(int) & 0b1001), np.abs(pen_ups - pen_downs) == 0)
        ).all(axis=2)[0]
        w = np.argwhere(~v)[..., 0]
        self.segments = self.segments[w, :]
        self.index = len(self.segments)

    def greedy_distance(self, pt: complex = 0j, flips=True):
        """
        Perform greedy optimization to minimize travel distances.

        @return:
        """
        infos = self.segments[: self.index, 2]
        q = np.where(np.real(infos).astype(int) & 0b1001)[0]
        for mid in range(0, len(q)):
            idxs = q[mid:]
            p1 = idxs[0]
            pen_downs = self.segments[idxs, 0]
            down_dists = np.abs(pen_downs - pt)
            down_distance = np.argmin(down_dists)
            if not flips:
                # Flipping is not allowed.
                if down_distance == 0:
                    continue
                p2 = idxs[down_distance]
                c = copy(self.segments[p2])
                self.segments[p2] = self.segments[p1]
                self.segments[p1] = c
                pt = c[-1]
                continue
            pen_ups = self.segments[idxs, -1]
            up_dists = np.abs(pen_ups - pt)
            up_distance = np.argmin(up_dists)
            if down_dists[down_distance] <= up_dists[up_distance]:
                if down_distance == 0:
                    continue
                p2 = idxs[down_distance]
                c = copy(self.segments[p2])
            else:
                if up_distance == 0:
                    self.segments[p1] = self.segments[p1, ::-1]
                    continue
                p2 = idxs[up_distance]
                c = copy(self.segments[p2, ::-1])
            self.segments[p2] = self.segments[p1]
            self.segments[p1] = c
            pt = c[-1]

    def two_opt_distance(
        self, max_passes=None, chunk=0, auto_stop_threshold=None, feedback=None
    ):
        """
        Perform two-opt optimization to minimize travel distances.
        @param max_passes: Max number of passes to attempt
        @param chunk: Chunk check value
        @param auto_stop_threshold percentage value of needed gain in every pass
        @return:
        """
        self._trim()
        segments = self.segments
        max_index = self.index

        min_value = -1e-10
        current_pass = 0

        indexes0 = np.arange(0, max_index - 1)
        indexes1 = indexes0 + 1

        improved = True
        first_travel = self.travel_distance()
        last_travel = first_travel
        threshold_value = (
            None
            if auto_stop_threshold is None
            else auto_stop_threshold / 100.0 * last_travel
        )
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
            for mid in range(1, max_index - 1):
                mid_max = max_index - 1
                if chunk:
                    mid_max = min(mid_max, mid + chunk)
                idxs = indexes0[mid:mid_max]

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
            this_travel = self.travel_distance()
            dt = last_travel - this_travel
            dt_total = first_travel - this_travel
            if feedback:
                msg = f"Pass {current_pass + 1}: saved {dt / first_travel * 100:.1f}%, total: {dt_total / first_travel * 100:.1f}%"
                feedback(msg)
            if max_passes and current_pass >= max_passes:
                break
            if threshold_value:
                if dt <= threshold_value:
                    break
                last_travel = this_travel
            current_pass += 1

    #######################
    # Spooler Functions
    #######################

    def generator(self):
        """
        Generate plotter code. This should generate individual x, y, power levels for each type of segment.
        The wait and dwell segments generate x, y, with a negative power (consisting of the wait time)
        @return:
        """
        segments = self.segments
        index = self.index

        for segment in segments[0:index]:
            start = segment[0]
            c0 = segment[1]
            segpow = segment[2]
            c1 = segment[3]
            end = segment[4]
            segment_type = self._segtype(segment)
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

    def generate(self):
        yield "geometry", self

    def as_lines(self, lines=None, function_dict=None):
        if lines is None:
            lines = self.segments[: self.index]
        if function_dict is None:
            function_dict = dict()
        default_dict = dict()
        defining_function = 0
        function_start = 0
        for index, line in enumerate(lines):
            start, c1, info, c2, end = line

            segment_type = int(info.real)
            pure_segment_type = self._segtype(line)
            if defining_function > 0:
                if pure_segment_type != TYPE_UNTIL:
                    continue
                loop_count = segment_type >> 8
                function_dict[defining_function] = (function_start, index, loop_count)
                defining_function = 0
                continue
            if pure_segment_type == TYPE_LINE:
                segment_type = "line"
            elif pure_segment_type == TYPE_QUAD:
                segment_type = "quad"
            elif pure_segment_type == TYPE_CUBIC:
                segment_type = "cubic"
            elif pure_segment_type == TYPE_ARC:
                segment_type = "arc"
            elif pure_segment_type == TYPE_POINT:
                segment_type = "point"
            elif pure_segment_type == TYPE_END:
                segment_type = "end"
            elif pure_segment_type == TYPE_NOP:
                # Nop should be skipped.
                continue
            elif pure_segment_type == TYPE_VERTEX:
                # Vertex should be skipped.
                continue
            elif pure_segment_type == TYPE_FUNCTION:
                defining_function = segment_type >> 8
                function_start = index
                continue
            elif pure_segment_type == TYPE_CALL:
                executing_function = segment_type >> 8
                fun_start, fun_end, loops = function_dict[executing_function]

                subroutine = copy(self.segments[fun_start + 1 : fun_end])
                f = self.segments[fun_start]
                if not np.isnan(start):
                    mx = PMatrix.map(f[0], f[1], f[3], f[4], start, c1, c2, end)
                    Geomstr.transform3x3(None, mx, subroutine)
                for loop in range(loops + 1):
                    yield from self.as_lines(subroutine, function_dict=function_dict)
                continue

            sets = self._settings.get(info.imag, default_dict)
            yield segment_type, start, c1, c2, end, sets

    def simplify_geometry(self, number=None, ratio=None, threshold=None):
        geom = self
        final = Geomstr()
        for subgeom in geom.as_subpaths():
            newgeom = Geomstr()
            points = list()
            closed = subgeom.is_closed()

            def processpts():
                if len(points) == 0:
                    return
                simplifier = Simplifier(points)
                """
                # Simplify by percentage of points to keep
                simplifier.simplify(ratio=0.5)

                # Simplify by giving number of points to keep
                simplifier.simplify(number=1000)

                # Simplify by giving an area threshold (in the units of the data)
                simplifier.simplify(threshold=0.01)
                """
                if number is not None:
                    newpoints = simplifier.simplify(number=number)
                elif ratio is not None:
                    newpoints = simplifier.simplify(ratio=ratio)
                elif threshold is not None:
                    newpoints = simplifier.simplify(threshold=threshold)
                else:
                    raise ValueError(
                        "You need to provide at least one parameter for simplify_geomstr"
                    )
                newgeom.append(Geomstr.lines(newpoints))
                points.clear()

            for segment in subgeom.segments[: subgeom.index]:
                start, control, info, control2, end = segment
                segtype = subgeom._segtype(segment)
                if segtype == TYPE_LINE:
                    if len(points) == 0:
                        points.append((start.real, start.imag))
                    points.append((end.real, end.imag))
                elif segtype == TYPE_END:
                    if len(points):
                        processpts()
                    newgeom.append_segment(start, control, info, control2, end)
                else:
                    if len(points):
                        processpts()
                    newgeom.append_segment(start, control, info, control2, end)
            if len(points):
                processpts()
            if closed and newgeom.index > 0:
                newgeom.close()
            final.append(newgeom)
        return final
