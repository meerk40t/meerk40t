"""
Path Offset Module for MeerK40t

This module provides sophisticated path offset (parallel curve) generation for SVG paths,
primarily used for kerf compensation in laser cutting operations.

Key Features:
- Supports offset for lines, arcs, quadratic and cubic Bezier curves
- Handles nested paths (holes) with automatic offset direction inversion
- Advanced intersection detection and loop removal to prevent self-intersecting paths
- Clockwise/counter-clockwise path detection for proper offset direction
- Linearization of curves for improved accuracy
- Segment stitching with miter limit handling
- Support for both radial (arc) and linear connectors

Algorithm Overview:
1. Decompose path into subpaths and detect nesting depth
2. Process each subpath backwards (for easier index management)
3. For each segment, generate offset version by:
   - Lines: Offset using normal vector
   - Arcs: Adjust radius
   - Bezier curves: Use Tiller-Hanson approximation or linearization
4. Stitch offset segments together by:
   - Finding intersections between consecutive segments
   - Detecting and removing loops (forward or backward cuts)
   - Inserting connectors where needed
5. Close subpaths by connecting first and last segments
6. Simplify resulting path using geometric simplification

Offset Direction Convention:
- Positive offset: left/outside for clockwise paths, right/inside for CCW paths
- Negative offset: right/inside for clockwise paths, left/outside for CCW paths
- Nested paths (holes) automatically get inverted offset direction

References:
- Tiller & Hanson: Offsets of Two-Dimensional Profiles (1984)
- Visual reference: https://feirell.github.io/offset-bezier/
"""
from copy import copy
from math import atan2, tau

from meerk40t.core.node.node import Linejoin
from meerk40t.core.units import UNITS_PER_PIXEL, Length
from meerk40t.svgelements import (
    Arc,
    Close,
    CubicBezier,
    Line,
    Move,
    Path,
    Point,
    QuadraticBezier,
)
from meerk40t.core.geomstr import Geomstr

def norm_vector(p1, p2, target_len):
    """
    Calculate normal (perpendicular) vector for line segment offset.
    
    Creates a vector perpendicular to the line from p1 to p2, scaled to the
    specified length. The normal points to the left of the direction vector
    in SVG coordinate space (90 degrees clockwise rotation due to Y-down coords).
    
    Args:
        p1 (Point): Start point of the line segment
        p2 (Point): End point of the line segment
        target_len (float): Desired length of the normal vector (offset distance)
    
    Returns:
        Point: Normal vector with the specified length, perpendicular to p1->p2
        
    Note:
        Returns a zero vector if p1 and p2 are coincident.
        In SVG coords (Y increases down), "left" of vector (dx, dy) is (dy, -dx).
    """
    line_vector = p2 - p1
    # if line_vector.x == 0 and line_vector.y == 0:
    #     return Point(target_len, 0)
    factor = target_len
    # For SVG coords (Y-down), left-hand normal is (dy, -dx) not (-dy, dx)
    normal_vector = Point(line_vector.y, -1 * line_vector.x)
    normlen = abs(normal_vector)
    if normlen != 0:
        factor = target_len / normlen
    normal_vector *= factor
    return normal_vector


def is_clockwise(path, start=0):
    """
    Determine if a path is oriented clockwise or counter-clockwise.
    
    Uses the shoelace formula to calculate the signed area of the polygon
    formed by the path segments. Positive area indicates clockwise orientation.
    
    Args:
        path (Path): SVG path to analyze
        start (int): Starting segment index (default: 0)
    
    Returns:
        bool: True if path is clockwise, False if counter-clockwise
        
    Note:
        Returns True for empty paths as a default.
    """
    def poly_clockwise(poly):
        """
        Returns True if the polygon is clockwise ordered, False if not.
        Uses the shoelace formula for signed area calculation.
        """

        total = (
            poly[-1].x * poly[0].y - poly[0].x * poly[-1].y
        )  # last point to first point
        for i in range(len(poly) - 1):
            total += poly[i].x * poly[i + 1].y - poly[i + 1].x * poly[i].y

        if total > 0:
            # print(f"is_clockwise: Total {total} > 0 -> True (CW)")
            return True
        else:
            # print(f"is_clockwise: Total {total} <= 0 -> False (CCW)")
            return False

    poly = []
    idx = start
    while idx < len(path._segments):
        seg = path._segments[idx]
        if isinstance(seg, (Arc, Line, QuadraticBezier, CubicBezier)):
            if len(poly) == 0:
                poly.append(seg.start)
            poly.append(seg.end)
        else:
            if len(poly) > 0:
                break
        idx += 1
    if len(poly) == 0:
        res = True
    else:
        res = poly_clockwise(poly)
    return res


def linearize_segment(segment, interpolation=500, reduce=True):
    """
    Convert a curve segment into a series of linear approximations.
    
    Samples points along the segment and optionally reduces collinear points
    to minimize the number of line segments while maintaining accuracy.
    
    Args:
        segment: Path segment (Arc, QuadraticBezier, or CubicBezier)
        interpolation (int): Number of interpolation steps (default: 500)
        reduce (bool): Whether to eliminate redundant collinear points (default: True)
    
    Returns:
        list[Point]: Linearized points representing the segment
        
    Note:
        Uses slope tolerance of 0.001 radians for collinearity detection.
    """
    slope_tolerance = 0.001
    s = []
    delta = 1.0 / interpolation
    lastpt = None
    t = 0
    last_slope = None
    while t <= 1:
        appendit = True
        np = segment.point(t)
        if lastpt is not None:
            dx = lastpt.x - np.x
            dy = lastpt.y - np.y
            if abs(dx) < 1e-6 and abs(dy) < 1e-6:
                appendit = False
                # identical points!
            else:
                this_slope = atan2(dy, dx)
                if last_slope is not None:
                    if abs(last_slope - this_slope) < slope_tolerance:
                        # Combine segments, i.e. get rid of mid point
                        this_slope = last_slope
                        appendit = False
                last_slope = this_slope

        if appendit or not reduce:
            s.append(np)
        else:
            s[-1] = np
        t += delta
        lastpt = np
    if s[-1] != segment.end:
        np = Point(segment.end)
        s.append(np)
    # print (f"linearize: {type(segment).__name__}")
    # print (f"Start: ({segment.start.x:.0f}, {segment.start.y:.0f}) - ({s[0].x:.0f}, {s[0].y:.0f})")
    # print (f"End: ({segment.end.x:.0f}, {segment.end.y:.0f}) - ({s[-1].x:.0f}, {s[-1].y:.0f})")
    return s


def offset_point_array(points, offset):
    """
    Generate offset for an array of points representing a polyline.
    
    Creates offset segments for each line segment and handles intersections
    to prevent loops and spikes. Includes retrograde detection to remove
    segments that fold back on themselves.
    
    Args:
        points (list[Point]): Array of points forming a polyline
        offset (float): Offset distance (positive = left, negative = right)
    
    Returns:
        list[Point]: Offset polyline as array of points
        
    Algorithm:
        1. Generate offset segments using normal vectors
        2. Find intersections between consecutive offset segments
        3. Prune retrograde segments (where offset reverses direction)
        4. Limit miter spikes using distance threshold
    """
    if len(points) < 2:
        return []

    class Segment:
        def __init__(self, start, end, orig_start, orig_end):
            self.start = Point(start)
            self.end = Point(end)
            self.orig_start = Point(orig_start)
            self.orig_end = Point(orig_end)
            self.orig_vector = self.orig_end - self.orig_start

    raw_segments = []
    for i in range(len(points) - 1):
        p0 = points[i]
        p1 = points[i + 1]
        nv = norm_vector(p0, p1, offset)
        raw_segments.append(Segment(p0 + nv, p1 + nv, p0, p1))

    if not raw_segments:
        return []

    final_segments = []
    final_segments.append(raw_segments[0])

    for i in range(1, len(raw_segments)):
        next_seg = raw_segments[i]
        pop_count = 0

        while len(final_segments) > 0:
            curr_seg = final_segments[-1]

            # Intersect
            p_i, s, t = intersect_line_segments(
                curr_seg.start, curr_seg.end, next_seg.start, next_seg.end
            )

            if p_i is None:
                # Parallel lines.
                final_segments.append(next_seg)
                break

            # Check for spikes (far intersections)
            limit = max(abs(offset) * 10, 50)
            if curr_seg.end.distance_to(p_i) > limit:
                final_segments.append(next_seg)
                break

            # Check validity for curr_seg
            # The new segment would be curr_seg.start -> p_i
            v_new = p_i - curr_seg.start
            
            # Dot product with original direction
            dot = v_new.x * curr_seg.orig_vector.x + v_new.y * curr_seg.orig_vector.y

            if dot > 0:  # Valid
                if s < 1.0 - 1e-9:
                    # print(f"  Keep intersection: {curr_seg.start} -> {p_i} (Dot: {dot:.4f})")
                    curr_seg.end = Point(p_i)
                    next_seg.start = Point(p_i)
                    final_segments.append(next_seg)
                    break
                else:
                    # next_seg is overshoot/retrograde. Skip it.
                    break
            else:
                # Potential retrograde case. Be conservative to avoid oversimplifying
                # outward offsets on smooth shapes (e.g., circles).
                # Accept intersections when consecutive segments are nearly aligned
                # (small turning angle), or when the intersection lies at a boundary.

                accepted = False
                # Angle between original consecutive segments
                ov1 = curr_seg.orig_vector
                ov2 = next_seg.orig_vector
                len1 = abs(ov1)
                len2 = abs(ov2)
                if len1 > 1e-9 and len2 > 1e-9:
                    cosang = (ov1.x * ov2.x + ov1.y * ov2.y) / (len1 * len2)
                    # If angle < ~60 degrees (cos > 0.5), keep intersection
                    if cosang > 0.5:
                        curr_seg.end = Point(p_i)
                        next_seg.start = Point(p_i)
                        final_segments.append(next_seg)
                        accepted = True
                # Also accept if intersection is effectively at segment boundary
                if not accepted and s is not None and t is not None:
                    if s <= 1e-9 or t >= 1.0 - 1e-9:
                        curr_seg.end = Point(p_i)
                        next_seg.start = Point(p_i)
                        final_segments.append(next_seg)
                        accepted = True

                if accepted:
                    break
                # Otherwise, treat as true retrograde and prune current segment.
                # print(f"  Prune retrograde: {curr_seg.start} -> {p_i} (Dot: {dot:.4f})")
                final_segments.pop()
                pop_count += 1
                # Prevent pathological collapse: if we popped too many times,
                # stop pruning and keep detail by accepting the next segment.
                if pop_count > 5:
                    # Force-append next segment to preserve local detail
                    final_segments.append(next_seg)
                    break

        if len(final_segments) == 0:
            # We popped everything. Restart with next_seg.
            final_segments.append(next_seg)

    # Convert back to points
    result = []
    if final_segments:
        result.append(final_segments[0].start)
        for seg in final_segments:
            # Filter tiny segments in output
            if seg.end.distance_to(result[-1]) > 0.01:
                result.append(seg.end)

    return result


def _offset_polyline_simple(points, offset):
    """
    Simple, stable polyline offset using pairwise intersections of consecutive
    offset segments. This avoids aggressive pruning and preserves detail for
    smooth convex shapes (e.g., arcs/circles).

    Args:
        points (list[Point]): Original polyline points
        offset (float): Offset distance

    Returns:
        list[Point]: Offset polyline points
    """
    if len(points) < 2:
        return []

    # Build offset segments
    off_segs = []
    for i in range(len(points) - 1):
        p0 = points[i]
        p1 = points[i + 1]
        nv = norm_vector(p0, p1, offset)
        s = p0 + nv
        e = p1 + nv
        off_segs.append((s, e))

    result = []
    # Start with first offset point
    result.append(off_segs[0][0])
    # Intersections between consecutive offset segments
    for i in range(len(off_segs) - 1):
        s1, e1 = off_segs[i]
        s2, e2 = off_segs[i + 1]
        p, t, s = intersect_line_segments(s1, e1, s2, e2)
        if p is None:
            # Parallel: use connection point
            p = e1
        result.append(p)
    # End with last offset point
    result.append(off_segs[-1][1])

    # Remove tiny duplicate steps
    cleaned = []
    for pt in result:
        if not cleaned or pt.distance_to(cleaned[-1]) > 1e-6:
            cleaned.append(pt)
    return cleaned


def offset_arc(segment, offset=0, linearize=False, interpolation=500):
    """
    Generate offset for an arc segment.
    
    Args:
        segment (Arc): Arc segment to offset
        offset (float): Offset distance
        linearize (bool): If True, convert to line segments (default: False)
        interpolation (int): Number of interpolation steps for linearization (default: 500)
    
    Returns:
        list: List of offset segments (Arc or Line segments depending on linearize)
        
    Note:
        Currently always linearizes arcs due to implementation limitations.
        Non-linearized version adjusts radius by offset amount.
    """
    if not isinstance(segment, Arc):
        return None
    newsegments = list()
    if linearize:
        s = linearize_segment(segment, interpolation=interpolation, reduce=True)
        # Use a simpler, stable offset for linearized arcs to preserve detail
        # and avoid aggressive pruning that can oversimplify outward offsets.
        s = _offset_polyline_simple(s, offset)
        for idx in range(1, len(s)):
            seg = Line(
                start=Point(s[idx - 1][0], s[idx - 1][1]),
                end=Point(s[idx][0], s[idx][1]),
            )
            seg.origin_type = "offset_arc_linearized"
            newsegments.append(seg)
    else:
        centerpt = Point(segment.center)
        startpt = centerpt.polar_to(
            angle=centerpt.angle_to(segment.start),
            distance=centerpt.distance_to(segment.start) + offset,
        )
        endpt = centerpt.polar_to(
            angle=centerpt.angle_to(segment.end),
            distance=centerpt.distance_to(segment.end) + offset,
        )
        newseg = Arc(
            startpt,
            endpt,
            centerpt,
            #         ccw=ccw,
        )
        newseg.origin_type = "offset_arc"
        newsegments.append(newseg)
    return newsegments


def offset_line(segment, offset=0):
    """
    Generate offset for a line segment.
    
    Creates a parallel line at the specified offset distance using a normal vector.
    The normal points to the left of the line direction.
    
    Args:
        segment (Line): Line segment to offset
        offset (float): Offset distance (positive = left, negative = right)
    
    Returns:
        list[Line]: List containing the single offset line segment
        
    Note:
        Returns a single-element list for API consistency with other offset functions.
    """
    if not isinstance(segment, Line):
        return None
    newseg = copy(segment)
    normal_vector = norm_vector(segment.start, segment.end, offset)
    # print(f"Offset Line: {segment.start} -> {segment.end} | Off={offset} | Norm={normal_vector}")
    newseg.start += normal_vector
    newseg.end += normal_vector
    newseg.origin_type = "offset_line"
    return [newseg]


def offset_quad(segment, offset=0, linearize=False, interpolation=500):
    """
    Generate offset for a quadratic Bezier curve.
    
    Converts the quadratic Bezier to cubic Bezier representation and uses
    cubic offset algorithm.
    
    Args:
        segment (QuadraticBezier): Quadratic Bezier segment to offset
        offset (float): Offset distance
        linearize (bool): If True, convert to line segments (default: False)
        interpolation (int): Number of interpolation steps for linearization (default: 500)
    
    Returns:
        list: List of offset segments (Line or CubicBezier depending on linearize)
    """
    if not isinstance(segment, QuadraticBezier):
        return None
    cubic = CubicBezier(
        start=segment.start,
        control1=segment.start + 2 / 3 * (segment.control - segment.start),
        control2=segment.end + 2 / 3 * (segment.control - segment.end),
        end=segment.end,
    )
    newsegments = offset_cubic(cubic, offset, linearize, interpolation)

    return newsegments


def offset_cubic(segment, offset=0, linearize=False, interpolation=500):
    """
    Generate offset for a cubic Bezier curve using Tiller-Hanson approximation.
    
    True offset curves for Bezier curves cannot be represented exactly as Bezier curves,
    so this uses the Tiller-Hanson approximation algorithm:
    
    Algorithm:
        1. Offset three helper lines:
           - Helper 1: P1 -> C1 (start to first control point)
           - Helper 2: C1 -> C2 (between control points)
           - Helper 3: C2 -> P2 (second control point to end)
        2. Find intersections:
           - Intersection of Helper 1 & 2 = new C1
           - Intersection of Helper 2 & 3 = new C2
        3. Offset start/end points directly to create new P1 and P2
    
    Args:
        segment (CubicBezier): Cubic Bezier segment to offset
        offset (float): Offset distance
        linearize (bool): If True, convert to line segments (default: False)
        interpolation (int): Number of interpolation steps for linearization (default: 500)
    
    Returns:
        list: List of offset segments (Line or CubicBezier depending on linearize)
        
    Limitations:
        This approximation does not handle curves with cusps well. For such curves,
        consider using linearization (linearize=True).
    
    References:
        Tiller & Hanson (1984): "Offsets of Two-Dimensional Profiles"
    """

    if not isinstance(segment, CubicBezier):
        return None
    newsegments = list()
    if linearize:
        s = linearize_segment(segment, interpolation=interpolation, reduce=True)
        # Preserve detail during linearized cubic offsets using a simple, stable polyline offset
        s = _offset_polyline_simple(s, offset)
        for idx in range(1, len(s)):
            seg = Line(
                start=Point(s[idx - 1][0], s[idx - 1][1]),
                end=Point(s[idx][0], s[idx][1]),
            )
            seg.origin_type = "offset_cubic_linearized"
            newsegments.append(seg)
    else:
        newseg = copy(segment)
        if segment.control1 == segment.start:
            p1 = segment.control2
        else:
            p1 = segment.control1
        normal_vector1 = norm_vector(segment.start, p1, offset)
        if segment.control2 == segment.end:
            p1 = segment.control1
        else:
            p1 = segment.control2
        normal_vector2 = norm_vector(p1, segment.end, offset)
        normal_vector3 = norm_vector(segment.control1, segment.control2, offset)

        newseg.start += normal_vector1
        newseg.end += normal_vector2

        v = segment.start + normal_vector1
        w = segment.control1 + normal_vector1
        x = segment.control1 + normal_vector3
        y = segment.control2 + normal_vector3
        intersect, s, t = intersect_line_segments(v, w, x, y)
        if intersect is None:
            # Fallback
            intersect = segment.control1 + 0.5 * (normal_vector1 + normal_vector3)
        newseg.control1 = intersect

        x = segment.control2 + normal_vector2
        y = segment.end + normal_vector2
        v = segment.control1 + normal_vector3
        w = segment.control2 + normal_vector3
        intersect, s, t = intersect_line_segments(v, w, x, y)
        if intersect is None:
            # Fallback
            intersect = segment.control2 + 0.5 * (normal_vector2 + normal_vector3)
        newseg.control2 = intersect
        # print (f"Old: start=({segment.start.x:.0f}, {segment.start.y:.0f}), c1=({segment.control1.x:.0f}, {segment.control1.y:.0f}), c2=({segment.control2.x:.0f}, {segment.control2.y:.0f}), end=({segment.end.x:.0f}, {segment.end.y:.0f})")
        # print (f"New: start=({newsegment.start.x:.0f}, {newsegment.start.y:.0f}), c1=({newsegment.control1.x:.0f}, {newsegment.control1.y:.0f}), c2=({newsegment.control2.x:.0f}, {newsegment.control2.y:.0f}), end=({newsegment.end.x:.0f}, {newsegment.end.y:.0f})")
        newseg.origin_type = "offset_cubic"
        newsegments.append(newseg)
    return newsegments


def intersect_line_segments(w, z, x, y):
    """
    Calculate intersection between two line segments.
    
    Line1 defined by: w + t * (z - w), where t in [0,1] for segment
    Line2 defined by: x + s * (y - x), where s in [0,1] for segment
    
    Args:
        w (Point): Start point of the first line segment
        z (Point): End point of the first line segment
        x (Point): Start point of the second line segment
        y (Point): End point of the second line segment
        
    Returns:
        tuple: (P, t, s) where:
            P (Point): Intersection point, None if lines are parallel
            t (float): Parameter for first line (0-1 means within segment)
            s (float): Parameter for second line (0-1 means within segment)
    """
    a = y.x - x.x
    b = -z.x + w.x
    c = y.y - x.y
    d = -z.y + w.y
    """
    The inverse matrix of
    (a  b)        1       (d  -b)
            = -------- *  (     )
    (c  d)     ad - bc    (-c  a)
    """
    deter = a * d - b * c
    if abs(deter) < 1.0e-8:
        # They don't have an interference
        return None, None, None

    s = 1 / deter * (d * (w.x - x.x) + -b * (w.y - x.y))
    t = 1 / deter * (-c * (w.x - x.x) + a * (w.y - x.y))
    p1 = w + t * (z - w)
    # p2 = x + s * (y - x)
    # print (f"p1 = ({p1.x:.3f}, {p1.y:.3f})")
    # print (f"p2 = ({p2.x:.3f}, {p2.y:.3f})")
    p = p1
    return p, t, s


def get_loop_area(segments, close_pt):
    """
    Calculate the area of a loop formed by segments and a closing point.
    
    Uses the shoelace formula to compute the signed area. Used in determining
    which direction to cut when removing loops during offset operations.
    
    Args:
        segments (list): List of path segments forming the loop
        close_pt (Point): Point to close the loop
    
    Returns:
        float: Absolute area of the loop (always positive)
        
    Note:
        Returns 0.0 if segments list is empty or contains no valid points.
    """
    area = 0.0
    if not segments:
        return 0.0
    
    first_pt = None
    last_pt = None
    
    # Sum segments
    for seg in segments:
        if seg.start is None or seg.end is None:
            continue
        if isinstance(seg, Move):
            continue
        
        if first_pt is None:
            first_pt = seg.start
        
        if last_pt is not None:
            area += (last_pt.x * seg.start.y - seg.start.x * last_pt.y)

        x1, y1 = seg.start.x, seg.start.y
        x2, y2 = seg.end.x, seg.end.y
        area += (x1 * y2 - x2 * y1)
        last_pt = seg.end
    
    if first_pt is None or last_pt is None:
        return 0.0

    # Close the loop to close_pt
    # last -> close_pt
    area += (last_pt.x * close_pt.y - close_pt.x * last_pt.y)
    # close_pt -> first
    area += (close_pt.x * first_pt.y - first_pt.x * close_pt.y)
    
    return abs(area * 0.5)


def is_point_inside_subpath(subpath, point):
    """
    Determine if a point is inside a closed subpath using ray casting algorithm.
    
    Linearizes the subpath and performs ray casting to determine containment.
    Used for detecting nested paths (holes) to apply correct offset direction.
    
    Args:
        subpath: Path segments forming a closed subpath
        point (Point): Point to test for containment
    
    Returns:
        bool: True if point is inside the subpath, False otherwise
        
    Algorithm:
        Cast a horizontal ray from the point to infinity and count how many
        times it crosses the polygon boundary. Odd count = inside, even = outside.
    """
    # Linearize
    poly = []
    for seg in subpath:
        pts = linearize_segment(seg)
        if len(pts) > 0:
            poly.extend(pts[:-1])
    
    # Ray casting
    x, y = point.x, point.y
    n = len(poly)
    inside = False
    if n == 0: return False
    
    p1x, p1y = poly[0].x, poly[0].y
    for i in range(n + 1):
        p2x, p2y = poly[i % n].x, poly[i % n].y
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def offset_path(self, path, offset_value=0):
    """
    High-level wrapper for path offset with simplification.
    
    This method is monkey-patched onto CutOpNode to provide offset functionality.
    It calls path_offset() and applies geometric simplification to the result.
    
    Args:
        self: CutOpNode instance (not used, required for method signature)
        path (Path): Path to offset
        offset_value (float): Offset distance in current units
    
    Returns:
        Path: Offset and simplified path, or original path if offset fails
        
    Note:
        - Inverts offset_value sign for correct behavior
        - Uses linearization for all curves
        - Applies aggressive simplification (tolerance=0.1) for device resolution
    """
    # As this overloads a regular method in a class
    # it needs to have the very same definition (including the class
    # reference self)
    # Radial connectors seem to have issues, so we don't use them for now...
        
    p = path_offset(
        path,
        offset_value=offset_value,
        radial_connector=False,
        linearize=True,
        interpolation=500,
    )
    if p is None:
        return path
    g = Geomstr.svg(p)
    if g.index:
        # We are already at device resolution, so we need to reduce tolerance a lot
        # Standard is 25 tats, so about 1/3 of a mil
        p = g.simplify(tolerance=0.1).as_path()
        p.stroke = path.stroke
        p.fill = path.fill
    return p


def path_offset(
    path, offset_value=0, radial_connector=False, linearize=True, interpolation=500
):
    """
    Generate offset (parallel) path for an SVG path with advanced features.
    
    Main offset algorithm supporting nested paths, loop removal, and intersection
    handling. Processes subpaths independently and handles nesting automatically.
    
    Args:
        path (Path): SVG path to offset
        offset_value (float): Offset distance (positive = expand for CW, shrink for CCW)
        radial_connector (bool): Use arc connectors instead of lines (default: False)
        linearize (bool): Convert curves to lines for processing (default: True)
        interpolation (int): Number of interpolation steps for linearization (default: 500)
    
    Returns:
        Path: Offset path with all subpaths processed
        
    Algorithm:
        1. Detect nesting depth of all subpaths using point-in-polygon tests
        2. Invert offset for nested paths (odd depth = holes)
        3. For each subpath:
           a. Process segments backwards (easier index management)
           b. Generate offset version of each segment
           c. Stitch segments together, handling intersections
           d. Remove loops using area heuristics
           e. Close the subpath
        4. Combine all offset subpaths into result
    
    Key Features:
        - Automatic hole detection and correct offset direction
        - Loop removal with forward/backward cut decision
        - Miter limit to prevent extreme spikes
        - Retrograde segment detection and removal
        - Global join optimization for corners
        - Backtracking artifact prevention
    
    Constants:
        MINIMAL_LEN (float): Minimum segment length threshold (5 units)
    """
    MINIMAL_LEN = 5
    # print (f"Path Offset: Offset={offset_value}, Radial={radial_connector}, Linearize={linearize}, Interp={interpolation}")
    # if isinstance(path, Path):
    #     print (f"Path: {path.d()}")

    def stitch_segments_at_index(
        offset, stitchpath, seg1_end, orgintersect, radial=False, closed=False, limit=None
    ):
        """
        Stitch two consecutive offset segments together, handling gaps and intersections.
        
        This is the core stitching function that connects offset segments by:
        - Finding intersections between segments
        - Detecting and removing loops (self-intersections)
        - Inserting connector segments where needed
        - Applying miter limits to prevent spikes
        
        Args:
            offset (float): Offset distance for reference
            stitchpath (Path): Path being constructed with offset segments
            seg1_end (int): Index of the left segment to stitch
            orgintersect (Point): Original intersection point before offset
            radial (bool): Use arc connectors instead of lines (default: False)
            closed (bool): Whether this is a closed path (default: False)
            limit (int): Maximum segment index to scan for intersections (default: None)
        
        Returns:
            tuple: (point_added, deleted_from_start, deleted_tail, deleted_loop)
                - point_added (int): Number of connector segments added (1, 0, or negative)
                - deleted_from_start (int): Segments deleted from path start
                - deleted_tail (int): Segments deleted from path end
                - deleted_loop (int): Segments deleted in middle (loop removal)
        
        Algorithm:
            1. Identify seg1 (left) and seg2 (right) segments
            2. Scan for intersections with subsequent segments (backwards for furthest)
            3. If intersection found:
               a. Decide cut direction using area heuristic (forward vs backward)
               b. Remove intervening segments
               c. Adjust segment endpoints to intersection point
            4. If no intersection and gap exists:
               a. Insert connector segment (line or arc)
               b. Check for backtracking artifacts and fix
        
        Special Cases:
            - Parallel segments: Detect inverted U-turns using cross products
            - Consecutive segments: Apply miter limit check
            - Global joins: Connect to predecessor segment when appropriate
            - Wrapped segments: Handle closed path wraparound
        """
        point_added = 0
        deleted_from_start = 0
        deleted_tail = 0
        deleted_loop = 0
        left_end = seg1_end
        lp = len(stitchpath)
        cw_global = is_clockwise(stitchpath)
        right_start = left_end + 1
        wrapped = False
        if right_start >= lp:
            if not closed:
                return point_added, deleted_from_start, deleted_tail, deleted_loop
            # Look for the first segment
            right_start = right_start % lp
            wrapped = True
            while not isinstance(
                stitchpath._segments[right_start],
                (Arc, Line, QuadraticBezier, CubicBezier),
            ):
                right_start += 1
            
            # If we wrapped to a segment that is before our current processing point (left_end),
            # it means we are trying to stitch with an unprocessed (Original) segment.
            # We must NOT do this. We should leave the gap and let the First segment 
            # (when processed later/earlier?) handle the stitch with us, or let close_subpath handle it.
            # Note: We iterate backwards, so segments < left_end are unprocessed.
            if right_start < left_end:
                 # print(f"Wrapped but right_start {right_start} < left_end {left_end}. Aborting stitch.")
                 return point_added, deleted_from_start, deleted_tail, deleted_loop

        seg1 = stitchpath._segments[left_end]
        seg2 = stitchpath._segments[right_start]

        #  print (f"Stitch {left_end}: {type(seg1).__name__}, {right_start}: {type(seg2).__name__} - max={len(stitchpath._segments)}")
        if isinstance(seg1, Close):
            # Close will be dealt with differently...
            return point_added, deleted_from_start, deleted_tail, deleted_loop
        if isinstance(seg1, Move):
            seg1.end = Point(seg2.start)
            return point_added, deleted_from_start, deleted_tail, deleted_loop

        if isinstance(seg1, Line):
            needs_connector = True
            # Check for intersections with subsequent segments
            # We iterate backwards to find the furthest intersection (largest loop removal)
            best_p = None
            best_idx = -1

            # Let's scan all subsequent segments that are Lines
            scan_end = len(stitchpath._segments) - 1
            if limit is not None and limit < scan_end:
                scan_end = limit
            
            # Identify predecessor index
            pred_idx = left_end - 1
            while pred_idx >= 0 and isinstance(stitchpath._segments[pred_idx], Move):
                pred_idx -= 1
            if pred_idx < 0 and closed:
                pred_idx = len(stitchpath._segments) - 1
                while pred_idx > left_end and isinstance(stitchpath._segments[pred_idx], Move):
                     pred_idx -= 1
            
            # print(f"Stitch {left_end}: pred_idx={pred_idx}, len={len(stitchpath._segments)}")


            # Precompute seg1 bbox
            s1_x1 = min(seg1.start.x, seg1.end.x)
            s1_x2 = max(seg1.start.x, seg1.end.x)
            s1_y1 = min(seg1.start.y, seg1.end.y)
            s1_y2 = max(seg1.start.y, seg1.end.y)

            for k in range(scan_end, right_start - 1, -1):
                if k == left_end:
                    continue
                if k == pred_idx:
                    # Global Join (Predecessor)
                    seg_k = stitchpath._segments[k]
                    # seg1 is curr. seg_k is pred.
                    # We want to join seg_k.end to seg1.start.
                    p_g, s_g, t_g = intersect_line_segments(
                        Point(seg1.start), Point(seg1.end),
                        Point(seg_k.start), Point(seg_k.end)
                    )
                    if p_g is not None:
                         d1 = seg1.start.distance_to(p_g)
                         d2 = seg_k.end.distance_to(p_g)
                         limit_dist = abs(offset) * 4 if abs(offset) > 1e-6 else 1000
                         # print(f"Global Join Check: {left_end} vs {k}. d1={d1}, d2={d2}, limit={limit_dist}")
                         if d1 < limit_dist and d2 < limit_dist:
                             # Check for inversion
                             v1 = seg1.end - seg1.start
                             vk = seg_k.end - seg_k.start
                             v1_new = seg1.end - p_g
                             vk_new = p_g - seg_k.start
                             
                             dot1 = v1.x * v1_new.x + v1.y * v1_new.y
                             dotk = vk.x * vk_new.x + vk.y * vk_new.y
                             
                             # print(f"Global Join Inversion: dot1={dot1}, dotk={dotk}")
                             
                             if dot1 > 0 and dotk > 0:
                                     # print(f"Global Join Applied: {left_end} vs {k} at {p_g}")
                                     seg1.start = Point(p_g)
                                     seg_k.end = Point(p_g)
                    continue
                seg_k = stitchpath._segments[k]
                if isinstance(seg_k, Line):
                    # Bbox check
                    if min(seg_k.start.x, seg_k.end.x) > s1_x2: continue
                    if max(seg_k.start.x, seg_k.end.x) < s1_x1: continue
                    if min(seg_k.start.y, seg_k.end.y) > s1_y2: continue
                    if max(seg_k.start.y, seg_k.end.y) < s1_y1: continue

                    # Check for parallel swap (Inverted U-turn)
                    v1 = seg1.end - seg1.start
                    vk = seg_k.end - seg_k.start
                    
                    len1 = abs(v1)
                    lenk = abs(vk)
                    
                    # Check if parallel and opposite
                    # We use normalized cross product (sin(angle)) to be scale-independent
                    if len1 > 1e-9 and lenk > 1e-9:
                        cross = v1.x * vk.y - v1.y * vk.x
                        dot = v1.x * vk.x + v1.y * vk.y
                        sin_angle = cross / (len1 * lenk)
                        cos_angle = dot / (len1 * lenk)
                        
                        if abs(sin_angle) < 1e-3 and cos_angle < 0:
                            # Check for Inversion using Cross Product of connection
                            v_conn = seg_k.start - seg1.end
                            turn_cross = v1.x * v_conn.y - v1.y * v_conn.x
                            
                            is_inverted = False
                            if cw_global: # CW Shape
                                # Expect CW Turn (Positive Cross). If Negative, Inverted.
                                if turn_cross < -1e-6:
                                    is_inverted = True
                            else: # CCW Shape
                                # Expect CCW Turn (Negative Cross). If Positive, Inverted.
                                if turn_cross > 1e-6:
                                    is_inverted = True
                            
                            # Check for Collinear Overlap (Spike)
                            if abs(turn_cross) < 1e-6:
                                # Collinear connection. Check if backtracking.
                                dot_conn = v1.x * v_conn.x + v1.y * v_conn.y
                                if dot_conn < 0:
                                    is_inverted = True
                            
                            if is_inverted:
                                # Swapped! Use midpoint of outer ends
                                best_p = Point((seg1.start.x + seg_k.end.x)/2, (seg1.start.y + seg_k.end.y)/2)
                                best_idx = k
                                break

                    p, s, t = intersect_line_segments(
                        Point(seg1.start),
                        Point(seg1.end),
                        Point(seg_k.start),
                        Point(seg_k.end),
                    )
                    if p is not None:
                        # Check if intersection is within segments
                        # We use a small tolerance for floating point errors
                        if -1e-5 <= s <= 1.0 + 1e-5 and -1e-5 <= t <= 1.0 + 1e-5:
                            # Check Miter Limit for consecutive segments
                            if k == left_end + 1:
                                d = seg1.end.distance_to(p)
                                limit_dist = abs(offset) * 10
                                if d > limit_dist:
                                    # Exceeds miter limit, ignore this intersection
                                    # This will cause a fallback to inserting a connector
                                    continue

                            # print(f"Intersection found between {left_end} and {k}: s={s}, t={t}")
                            best_p = p
                            best_idx = k
                            break  # Found the furthest intersection
                        elif k == left_end + 1:
                            # Consecutive segment - check if we can close the gap/overlap
                            # This handles Miter joins and missed overlaps
                            d1 = seg1.end.distance_to(p)
                            d2 = seg_k.start.distance_to(p)
                            # Allow extension up to a limit (e.g. 10x offset or fixed amount)
                            limit_dist = abs(offset) * 4 if abs(offset) > 1e-6 else 1000
                            # Check for inversion
                            # seg1.end becomes p.
                            # seg_k.start becomes p.
                            
                            # Original vectors
                            v1 = seg1.end - seg1.start
                            vk = seg_k.end - seg_k.start
                            
                            # New vectors
                            v1_new = p - seg1.start
                            vk_new = seg_k.end - p
                            
                            # Check dot products
                            if (v1.x * v1_new.x + v1.y * v1_new.y) > 0 and \
                               (vk.x * vk_new.x + vk.y * vk_new.y) > 0:
                                seg1.end = Point(p)
                                seg_k.start = Point(p)
                                needs_connector = False

            if best_p is not None:
                # We found a valid intersection
                
                # Determine which way to cut
                cut_forward = True
                if closed and best_idx > right_start:
                    # Calculate Area Heuristic
                    # Forward Loop Area
                    area_forward = get_loop_area(stitchpath._segments[right_start:best_idx], best_p)
                    
                    # Backward Loop Area
                    # Construct backward loop segments
                    seg2_part = Line(best_p, seg2.end)
                    seg1_part = Line(seg1.start, best_p)
                    
                    # Note: stitchpath[:left_end] excludes left_end.
                    backward_segments = [seg2_part] + stitchpath._segments[best_idx+1:] + stitchpath._segments[:left_end] + [seg1_part]
                    
                    area_backward = get_loop_area(backward_segments, best_p)
                    
                    if area_forward > area_backward:
                        cut_forward = False
                    else:
                        pass
                elif wrapped:
                    # Fallback if not closed but wrapped (shouldn't happen if logic is correct)
                    len_forward = best_idx - right_start
                    len_backward = left_end - best_idx
                    if len_backward < len_forward:
                        cut_forward = False
                
                if cut_forward:
                    if best_idx > right_start:
                        # Remove segments from right_start to best_idx - 1
                        count = best_idx - right_start
                        del stitchpath._segments[right_start:best_idx]
                        point_added -= count
                        if wrapped:
                            deleted_from_start = count
                        # Update best_idx (it shifted)
                        best_idx = right_start
                    
                    seg2 = stitchpath._segments[
                        best_idx
                    ]  # This is the segment we intersected with

                    seg1.end = Point(best_p)
                    seg2.start = Point(best_p)
                    if best_idx > 0 and isinstance(
                        stitchpath._segments[best_idx - 1], Move
                    ):
                        stitchpath._segments[best_idx - 1].end = Point(best_p)

                    needs_connector = False
                else:
                    # Backward cut
                    seg2 = stitchpath._segments[best_idx]
                    
                    if wrapped and right_start == 0:
                         # This is the local wrap case (loop at end)
                         # We want to keep the "wrap" loop: P->B (tail of seg1) ... C->P (head of seg2)
                         # Remove segments from best_idx (tail) to left_end (head)
                         
                         # Update seg2 (C->D becomes C->P)
                         seg2.end = Point(best_p)
                         
                         # Update seg1 (A->B becomes P->B)
                         seg1.start = Point(best_p)
                         
                         # Remove segments between seg2 and seg1 (inclusive of tails/heads we don't want?)
                         # We kept head of seg2 and tail of seg1.
                         # We remove tail of seg2 (handled by update) and head of seg1 (handled by update).
                         # We remove segments strictly between best_idx and left_end.
                         
                         if left_end > best_idx + 1:
                             count = left_end - (best_idx + 1)
                             del stitchpath._segments[best_idx + 1 : left_end]
                             deleted_loop = count
                             point_added -= count
                         
                         # Note: We don't delete seg1 or seg2, just modified them.
                         # But wait, if we modified them, we effectively removed the "loop" part?
                         # No, we removed the "Main" part.
                         # The "Main" part was D...A.
                         # D was end of seg2. A was start of seg1.
                         # We removed D...A.
                         
                    else:
                         # Global backward cut (removing start and end)
                         # We want to keep P->B (tail of seg1) ... C->P (head of seg2)
                         # Actually we keep right_start ... best_idx
                         
                         # 1. Update seg2 (C->D becomes C->P)
                         seg2.end = Point(best_p)
                         
                         # 2. Update start of kept chain
                         stitchpath._segments[right_start].start = Point(best_p)
                         
                         # 3. Remove end: best_idx + 1 ... end
                         count_end = lp - (best_idx + 1)
                         if count_end > 0:
                             del stitchpath._segments[best_idx + 1:]
                             deleted_tail = count_end
                             point_added -= count_end
                         
                         # 4. Remove start: 0 ... right_start
                         count_start = right_start
                         if count_start > 0:
                             start_del = 0
                             if len(stitchpath._segments) > 0 and isinstance(stitchpath._segments[0], Move):
                                 start_del = 1
                                 # We preserve the Move, so we must update its end point to match the new start
                                 stitchpath._segments[0].end = Point(best_p)
                             
                             if count_start > start_del:
                                 del stitchpath._segments[start_del:count_start]
                                 count_del = count_start - start_del
                                 point_added -= count_del
                                 deleted_from_start = count_del
                    
                    return point_added, deleted_from_start, deleted_tail, deleted_loop

            elif isinstance(seg2, Line):
                p, s, t = intersect_line_segments(
                    Point(seg1.start),
                    Point(seg1.end),
                    Point(seg2.start),
                    Point(seg2.end),
                )
                if p is not None:
                    # We have an intersection
                    if -1e-9 <= s <= 1.0 + 1e-9 and -1e-9 <= t <= 1.0 + 1e-9:
                        # We shorten the segments accordingly.
                        seg1.end = Point(p)
                        seg2.start = Point(p)
                        if right_start > 0 and isinstance(
                            stitchpath._segments[right_start - 1], Move
                        ):
                            stitchpath._segments[right_start - 1].end = Point(p)
                        needs_connector = False
                        # print ("Used internal intersect")
                    elif not radial:
                        # is the intersection too far away for our purposes?
                        odist = orgintersect.distance_to(p)
                        if odist > abs(offset) * 4:
                            needs_connector = True
                        elif t > 1.0 + 1e-9:
                            # seg2 is overshadowed (t > 1). Remove it.
                            del stitchpath._segments[right_start]
                            
                            rec_point_added = -1
                            rec_deleted_start = 0
                            new_left_end = left_end
                            new_limit = limit
                            
                            if right_start == 0:
                                rec_point_added = 0
                                rec_deleted_start = 1
                                new_left_end = left_end - 1
                            
                            if new_limit is not None:
                                new_limit -= 1

                            # Recurse to stitch seg1 to the new neighbor
                            p_a, d_s, d_t, d_l = stitch_segments_at_index(
                                offset, stitchpath, new_left_end, orgintersect, radial, closed, new_limit
                            )
                            return point_added + rec_point_added + p_a, deleted_from_start + rec_deleted_start + d_s, deleted_tail + d_t, deleted_loop + d_l
                        elif s < -1e-9:
                            # seg1 is overshadowed (s < 0). 
                            # Remove it.
                            del stitchpath._segments[left_end]
                            
                            if left_end == 0:
                                return point_added, deleted_from_start + 1, deleted_tail, deleted_loop
                            else:
                                return point_added - 1, deleted_from_start, deleted_tail, deleted_loop
                        else:
                            seg1.end = Point(p)
                            seg2.start = Point(p)
                            if right_start > 0 and isinstance(
                                stitchpath._segments[right_start - 1], Move
                            ):
                                stitchpath._segments[right_start - 1].end = Point(p)
                            needs_connector = False
                            # print ("Used external intersect")
            elif isinstance(seg1, Move):
                needs_connector = False
        else:  # Arc, Quad and Cubic Bezier
            needs_connector = True
            if isinstance(seg2, Line):
                needs_connector = True
            elif isinstance(seg2, Move):
                needs_connector = False

        if needs_connector and seg1.end != seg2.start:
            """
            There is a fundamental challenge to this naiive implementation:
            if the offset gets bigger you will get intersections of previous segments
            which will effectively defeat it. You will end up with connection lines
            reaching back creating a loop. Right now there's no real good way
            to deal with it:
            a) if it would be just the effort to create an offset of your path you
            can apply an intersection algorithm like Bentley-Ottman to identify
            intersections and remove them (or even simpler just use the
            Point.convex_hull method in svgelements).
            *BUT*
            b) this might defeat the initial purpose of the routine to get some kerf
            compensation. So you are effectively eliminating cutlines from your design
            which may not be what you want.

            So we try to avoid that by just looking at two consecutive path segments
            as these were by definition continuous.
            """

            if radial:
                # print ("Inserted an arc")
                # Let's check whether the distance of these points is smaller
                # than the radius

                angle = seg1.end.angle_to(seg1.start) - seg1.end.angle_to(seg2.start)
                while angle < 0:
                    angle += tau
                while angle > tau:
                    angle -= tau
                # print (f"Angle: {angle:.2f} ({angle / tau * 360.0:.1f})")
                startpt = Point(seg1.end)
                endpt = Point(seg2.start)

                if angle >= tau / 2:
                    ccw = True
                else:
                    ccw = False
                # print ("Generate connect-arc")
                connect_seg = Arc(
                    start=startpt, end=endpt, center=Point(orgintersect), ccw=ccw
                )
                clen = connect_seg.length(error=1e-2)
                # print (f"Ratio: {clen / abs(tau * offset):.2f}")
                if clen > abs(tau * offset / 2):
                    # That seems strange...
                    connect_seg = Line(startpt, endpt)
            else:
                # print ("Inserted a Line")
                connect_seg = Line(Point(seg1.end), Point(seg2.start))
                
                # Check for backtracking (Z-shape artifact)
                # This happens when segments cross but we missed the intersection
                # or they are parallel and overlapping.
                v1 = seg1.end - seg1.start
                vc = connect_seg.end - connect_seg.start
                
                if abs(v1) > 1e-9 and abs(vc) > 1e-9:
                    dot1 = v1.x * vc.x + v1.y * vc.y
                    # print(f"Connector check: dot1={dot1}, v1={v1}, vc={vc}")
                    # If dot product is negative, the connector goes backwards relative to seg1
                    if dot1 < 0:
                        # Check if it's a sharp turn (e.g. > 90 degrees)
                        # If dot < 0, it means angle > 90.
                        # This is likely an artifact for inside corners that failed to intersect.
                        # For outside corners, the connector should always go forward (dot > 0).
                        
                        # Likely an artifact. 
                        # Try to find a better stitch point (midpoint of overlap)
                        # Project seg2.start onto seg1 line
                        # Or just use midpoint of the connector
                        mid = Point((seg1.end.x + seg2.start.x)/2, (seg1.end.y + seg2.start.y)/2)
                        seg1.end = Point(mid)
                        seg2.start = Point(mid)
                        connect_seg = None
                        needs_connector = False
                        # No segment added, point_added remains unchanged
                
            if connect_seg is not None:
                connect_seg.origin_type = "stitch_connector"
                stitchpath._segments.insert(left_end + 1, connect_seg)
                point_added = 1
        elif needs_connector:
            # print ("Need connector but end points were identical")
            pass
        else:
            # print ("No connector needed")
            pass
        return point_added, deleted_from_start, deleted_tail, deleted_loop

    def close_subpath(radial, sub_path, firstidx, lastidx, offset, orgintersect):
        """
        Close a subpath by connecting the last segment to the first segment.
        
        Handles the final connection needed to close offset paths. Attempts to
        find intersection between first and last segments, or inserts connector.
        
        Args:
            radial (bool): Use arc connectors instead of lines
            sub_path (Path): Subpath to close
            firstidx (int): Index of first valid segment
            lastidx (int): Index of last valid segment
            offset (float): Offset distance for reference
            orgintersect (Point): Original corner point before offset
        
        Algorithm:
            1. Find first and last valid segments
            2. Check if they intersect:
               a. If intersection within both segments: adjust endpoints
               b. If intersection beyond segments: insert connector
            3. Use radial connector if requested and gap is small
            4. Fall back to line connector if needed
        """
        # from time import perf_counter
        seg1 = None
        seg2 = None
        very_first = None
        very_last = None
        # t_start = perf_counter()
        idx = firstidx
        while idx < len(sub_path._segments) and very_first is None:
            seg = sub_path._segments[idx]
            if seg.start is not None:
                very_first = Point(seg.start)
                seg1 = seg
                break
            idx += 1
        idx = lastidx
        while idx >= 0 and very_last is None:
            seg = sub_path._segments[idx]
            if seg.end is not None:
                seg2 = seg
                very_last = Point(seg.end)
                break
            idx -= 1
        if very_first is None or very_last is None:
            return
        # print (f"{perf_counter()-t_start:.3f} Found first and last")
        seglen = very_first.distance_to(very_last)
        if seglen > MINIMAL_LEN:
            p, s, t = intersect_line_segments(
                Point(seg1.start),
                Point(seg1.end),
                Point(seg2.start),
                Point(seg2.end),
            )
            if p is not None:
                # We have an intersection and shorten the segments accordingly.
                d = orgintersect.distance_to(p)
                # print(f"CloseSubpath: s={s}, t={t}, d={d}, offset={offset}")
                if 0 <= s <= 1 and 0 <= t <= 1:
                    seg1.start = Point(p)
                    seg2.end = Point(p)
                    # print (f"{perf_counter()-t_start:.3f} Close subpath by adjusting inner lines, d={d:.2f} vs. offs={offset:.2f}")
                elif d >= abs(offset) and seglen > abs(offset):
                    if radial:
                        # print (f"{perf_counter()-t_start:.3f} Insert an arc")
                        # Let's check whether the distance of these points is smaller
                        # than the radius

                        angle = seg1.end.angle_to(seg1.start) - seg1.end.angle_to(
                            seg2.start
                        )
                        while angle < 0:
                            angle += tau
                        while angle > tau:
                            angle -= tau
                        # print (f"{perf_counter()-t_start:.3f} Angle: {angle:.2f} ({angle / tau * 360.0:.1f})")
                        startpt = Point(seg2.end)
                        endpt = Point(seg1.start)

                        if angle >= tau / 2:
                            ccw = True
                        else:
                            ccw = False
                        # print (f"{perf_counter()-t_start:.3f} Generate connect-arc")
                        # print (f"{perf_counter()-t_start:.3f} s={startpt}, e={endpt}, c={orgintersect}, ccw={ccw}")
                        segment = Arc(
                            start=startpt,
                            end=endpt,
                            center=Point(orgintersect),
                            ccw=ccw,
                        )
                        # print (f"{perf_counter()-t_start:.3f} Now calculating length")
                        clen = segment.length(error=1e-2)
                        # print (f"{perf_counter()-t_start:.3f} Ratio: {clen / abs(tau * offset):.2f}")
                        if clen > abs(tau * offset / 2):
                            # That seems strange...
                            segment = Line(startpt, endpt)
                        segment.origin_type = "close_segment"
                        # print(f"{perf_counter()-t_start:.3f} Inserting segment at {lastidx + 1}...")
                        sub_path._segments.insert(lastidx + 1, segment)
                        # print(f"{perf_counter()-t_start:.3f} Done.")

                    else:
                        p = orgintersect.polar_to(
                            angle=orgintersect.angle_to(p),
                            distance=abs(offset),
                        )
                        segment = Line(p, seg1.start)
                        segment.origin_type = "close_segment_interim_1"
                        sub_path._segments.insert(lastidx + 1, segment)
                        segment = Line(seg2.end, p)
                        segment.origin_type = "close_segment_interim_2"
                        sub_path._segments.insert(lastidx + 1, segment)
                        # sub_path._segments.insert(firstidx, segment)
                        # print (f"Close subpath with interim pt, d={d:.2f} vs. offs={offset:.2f}")
                else:
                    seg1.start = Point(p)
                    seg2.end = Point(p)
                    # print (f"Close subpath by adjusting lines, d={d:.2f} vs. offs={offset:.2f}")
            else:
                segment = Line(very_last, very_first)
                sub_path._segments.insert(lastidx + 1, segment)
                # print ("Fallback case, just create  line")

    # Main path_offset algorithm begins here
    
    results = []
    
    # Phase 1: Detect nested paths (holes) for automatic offset direction inversion
    # ============================================================================
    # Collect all subpaths and determine their nesting depth by testing if their
    # first point is contained in any other subpath. Odd nesting depth indicates
    # a hole, which requires inverted offset direction.
    # 
    # Example: Outer rectangle with inner rectangular hole
    #   - Outer path: depth 0 (not inside anything)
    #   - Inner path: depth 1 (inside outer) -> offset inverted
    # 
    # This ensures that "expand" operation shrinks holes (thickens material)
    # and "shrink" operation expands holes (thins material).
    
    subpaths = list(path.as_subpaths())
    depths = [0] * len(subpaths)
    
    # Determine nesting depths using point-in-polygon tests
    # Note: Assumes subpaths are well-separated and non-intersecting
    for i in range(len(subpaths)):
        # Find a valid point on subpath i
        pt = None
        for seg in subpaths[i]:
            if isinstance(seg, (Line, Arc, QuadraticBezier, CubicBezier)):
                pt = seg.start
                break
        if pt is None: continue
        
        for j in range(len(subpaths)):
            if i == j: continue
            if is_point_inside_subpath(subpaths[j], pt):
                depths[i] += 1

    spct = 0
    for i, subpath in enumerate(subpaths):
        spct += 1
        # print (f"Subpath {spct}")
        p = Path([copy(seg) for seg in subpath])
        if not linearize:
            # p.approximate_arcs_with_cubics()
            pass
        offset = offset_value
        if depths[i] % 2 == 1:
            offset = -1 * offset
            
        # # No offset bigger than half the path size, otherwise stuff will get crazy
        # if offset > 0:
        #     bb = p.bbox()
        #     offset = min(offset, bb[2] - bb[0])
        #     offset = min(offset, bb[3] - bb[1])
        is_closed = False
        # Remember the complete subshape (could be multiple segements due to linearization)
        last_point = None
        first_point = None
        is_closed = False
        helper1 = None
        helper2 = None
        idx = len(p._segments) - 1
        while idx >= 0:
            if idx >= len(p._segments):
                idx = len(p._segments) - 1
                if idx < 0:
                    break
            segment = p._segments[idx]
            # print (f"Deal with seg {idx}: {type(segment).__name__} - {first_point}, {last_point}, {is_closed}")
            if isinstance(segment, Close):
                # Let's add a line and replace the closed segment by this new segment
                # Look for the last two valid segments
                last_point = None
                first_point = None
                pt_last = None
                pt_first = None
                idx1 = idx - 1
                while idx1 >= 0:
                    if isinstance(
                        p._segments[idx1], (Arc, Line, QuadraticBezier, CubicBezier)
                    ):
                        pt_last = Point(p._segments[idx1].end)
                        break
                    idx1 -= 1
                idx1 -= 1
                while idx1 >= 0:
                    if isinstance(
                        p._segments[idx1], (Arc, Line, QuadraticBezier, CubicBezier)
                    ):
                        pt_first = Point(p._segments[idx1].start)
                    else:
                        break
                    idx1 -= 1
                if pt_last is not None and pt_first is not None:
                    segment = Line(pt_last, pt_first)
                    p._segments[idx] = segment
                    last_point = idx
                    is_closed = True
                    cw = is_clockwise(p, max(0, idx1))
                    if not cw:
                        offset = -1 * offset
                else:
                    # Invalid close?! Remove it
                    p._segments.pop(idx)
                    if last_point is not None:
                        last_point -= 1
                    idx -= 1
                    continue
            elif isinstance(segment, Move):
                # print(f"Move handler: last={last_point}, first={first_point}, closed={is_closed}")
                if last_point is not None and first_point is not None and is_closed:
                    seglen = p._segments[first_point].start.distance_to(
                        p._segments[last_point].end
                    )
                    if seglen > MINIMAL_LEN:
                        close_subpath(
                            radial_connector,
                            p,
                            first_point,
                            last_point,
                            offset,
                            helper2,
                        )
                last_point = None
                first_point = None
            if segment.start is not None and segment.end is not None:
                seglen = segment.start.distance_to(segment.end)
                if seglen < MINIMAL_LEN:
                    # print (f"Skipped: {seglen}")
                    p._segments.pop(idx)
                    if last_point is not None:
                        last_point -= 1
                    idx -= 1
                    continue
                first_point = idx
                if last_point is None:
                    last_point = idx
                    # print(f"Init last_point={last_point}")
                    is_closed = False
                    # offset = offset_value # Do not reset offset here, it might have been adjusted by depth
                    # We need to establish if this is a closed path and if it goes counterclockwise
                    # Let establish the range and check whether this is closed
                    idx1 = last_point - 1
                    fpt = None
                    while idx1 >= 0:
                        seg = p._segments[idx1]
                        if isinstance(seg, (Line, Arc, QuadraticBezier, CubicBezier)):
                            fpt = seg.start
                        idx1 -= 1
                    if fpt is not None and segment.end.distance_to(fpt) < MINIMAL_LEN:
                        is_closed = True
                        cw = is_clockwise(p, max(0, idx1))
                        if not cw:
                            offset = -1 * offset
                        # print ("Seems to be closed!")
                # print (f"Regular point: {idx}, {type(segment).__name__}, {first_point}, {last_point}, {is_closed}")
            if idx == 0:
                # print(f"Processing index 0: {type(segment).__name__}, last={last_point}, first={first_point}, closed={is_closed}")
                pass
            helper1 = Point(p._segments[idx].end)
            helper2 = Point(p._segments[idx].start)
            left_end = idx
            # print (f"Segment to deal with: {type(segment).__name__}")
            newsegment = None
            if isinstance(segment, Arc):
                arclinearize = linearize
                # Arc is not working, so we always linearize
                arclinearize = True
                newsegment = offset_arc(segment, offset, arclinearize, interpolation)
            elif isinstance(segment, QuadraticBezier):
                newsegment = offset_quad(segment, offset, linearize, interpolation)
            elif isinstance(segment, CubicBezier):
                newsegment = offset_cubic(segment, offset, linearize, interpolation)
            elif isinstance(segment, Line):
                newsegment = offset_line(segment, offset)
            
            if newsegment is not None:
                if len(newsegment) == 0:
                    idx -= 1
                    continue
                
                # print(f"Idx {idx}: newsegment len={len(newsegment)}")
                
                # Insert segments
                p._segments[idx] = newsegment[0]
                for nidx in range(len(newsegment) - 1, 0, -1):  # All but the first
                    p._segments.insert(idx + 1, newsegment[nidx])
                
                # Stitch loop
                cnt = len(newsegment)
                curr = idx + cnt - 1
                
                # Update last_point for the inserted segments
                if last_point is not None:
                    last_point += cnt - 1
                    # print(f"Updated last_point (insert)={last_point}")

                while curr >= idx:
                    if len(p._segments) == 0:
                        break
                    h1 = helper1 if curr == idx + cnt - 1 else Point(p._segments[curr].end)
                    # print(f"Before Stitch {curr}: len={len(p._segments)}")
                    stitched, deleted_start, deleted_tail, deleted_loop = stitch_segments_at_index(
                        offset, p, curr, h1, radial=radial_connector, closed=is_closed, limit=last_point
                    )
                    
                    if last_point is not None:
                        last_point += stitched
                        # if stitched != 0: print(f"Updated last_point (stitched)={last_point}")
                    
                    if deleted_start > 0:
                        idx -= deleted_start
                        curr -= deleted_start
                        if idx < 0:
                            idx = 0
                        if first_point is not None:
                            first_point -= deleted_start
                            if first_point < 0: first_point = 0
                            if first_point == 0 and len(p._segments) > 1 and isinstance(p._segments[0], Move):
                                first_point = 1
                        # if last_point is not None:
                        #     last_point -= deleted_start
                            # print(f"Updated last_point (del_start)={last_point}")

                    if deleted_loop > 0:
                        # We deleted segments between best_idx and curr
                        # deleted_loop = curr - (best_idx + 1)
                        # start_deleted = best_idx + 1 = curr - deleted_loop
                        start_deleted = curr - deleted_loop
                        if idx >= start_deleted:
                            idx = start_deleted
                            if first_point is not None:
                                first_point = idx
                        curr -= deleted_loop

                    if deleted_tail > 0:
                        # if last_point is not None:
                        #     last_point -= deleted_tail
                            # print(f"Updated last_point (del_tail)={last_point}")
                        if curr >= len(p._segments):
                            curr = len(p._segments)
                    
                    curr -= 1
                
                idx -= 1
                # print(f"End of loop iter: idx={idx}, last={last_point}, closed={is_closed}")
                continue

            # Fallback (should not be reached with current types)
            left_end = idx
            stitched, deleted_start, deleted_tail, deleted_loop = stitch_segments_at_index(
                offset, p, left_end, helper1, radial=radial_connector, closed=is_closed, limit=last_point
            )
            if last_point is not None:
                last_point += stitched
            
            if deleted_tail > 0:
                pass
                # if last_point is not None:
                #     last_point -= deleted_tail
                # idx = left_end - deleted_tail + 1 # ?

            idx -= 1
            if deleted_start > 0:
                idx -= deleted_start
                if first_point is not None:
                    first_point -= deleted_start
                    if first_point < 0:
                        first_point = 0
                # if last_point is not None:
                #     last_point -= deleted_start

            if deleted_loop > 0:
                # Should not happen for Move segments usually?
                # But if it does, we need to handle it.
                curr = left_end
                start_deleted = curr - deleted_loop
                if idx >= start_deleted:
                    idx = start_deleted - 1
                    if first_point is not None:
                        first_point = idx


        if last_point is not None and first_point is not None and is_closed:
            # print(f"Attempting to close subpath: first={first_point}, last={last_point}, len={len(p._segments)}")
            if 0 <= first_point < len(p._segments) and 0 <= last_point < len(p._segments):
                start_pt = p._segments[first_point].start
                end_pt = p._segments[last_point].end
                if start_pt is not None and end_pt is not None:
                    seglen = start_pt.distance_to(end_pt)
                    # print(f"Gap distance: {seglen}")
                    if seglen > MINIMAL_LEN:
                        close_subpath(
                            radial_connector, p, first_point, last_point, offset, helper2
                        )
        else:
            # print(f"Not closing: last={last_point}, first={first_point}, closed={is_closed}")
            pass

        results.append(p)

    if len(results) == 0:
        # Strange, should never happen
        return path
    result = results[0]
    for idx in range(1, len(results)):
        result += results[idx]
    # result.approximate_arcs_with_cubics()
    return result


def path_offset_simple(path, offset_value=0, interpolation=20, miter_limit=None, cleanup_window=100):
    """Simplified path offset (performance-oriented).

    Provides a lightweight alternative to `path_offset` without complex loop
    removal, retrograde pruning, or multi-pass heuristics. Intended for fast
    outward/inward expansion of single, simple closed paths (rectangles,
    polygons, linearized curves).

    Semantics: Positive offset expands clockwise paths and shrinks
    counter-clockwise paths (matching full algorithm semantics).

    Args:
        path (Path): Source path (should be closed).
        offset_value (float): Requested offset distance.
        interpolation (int): Uniform subdivision per segment (0 for adaptive).
        miter_limit (float): Max miter length factor (None=auto: 4 outward, 2.5 inward).
        cleanup_window (int): Recent edge window for self-intersection checks (default 100).

    Returns:
        Path | None: Offset path or None if degenerate.
    """
    try:
        from meerk40t.svgelements import Path, Move, Line, Point
    except Exception:
        return None

    import os  # For debug flags
    if path is None or len(path) == 0:
        return None

    # Adaptive sampling helpers
    def _seg_length(seg):
        try:
            return seg.length()
        except Exception:
            # Fallback rough length
            s = getattr(seg, "start", None)
            e = getattr(seg, "end", None)
            if s is None or e is None:
                return 0.0
            dx = e.x - s.x
            dy = e.y - s.y
            return (dx * dx + dy * dy) ** 0.5

    def _adaptive_samples(seg, base_step, max_samples=200):
        L = _seg_length(seg)
        if L == 0:
            return 1
        # Curvature-based refinement: sample more densely for curves
        k = int(max(4, min(max_samples, L / base_step)))  # Minimum 4 samples per segment
        # If segment has curvature (arc/quad/cubic), use angle-based splitting heuristic
        if hasattr(seg, 'point') and hasattr(seg, 'derivative'):
            try:
                # Sample at thirds and check angle change
                d0 = seg.derivative(0.0)
                d1 = seg.derivative(0.5)
                d2 = seg.derivative(1.0)
                # Rough angle heuristic: if derivative changes significantly, boost samples
                def _angle(dx, dy):
                    import math
                    return math.atan2(dy, dx)
                a0 = _angle(d0.x, d0.y) if d0 else 0
                a1 = _angle(d1.x, d1.y) if d1 else 0
                a2 = _angle(d2.x, d2.y) if d2 else 0
                # Normalize angle differences to [-pi, pi]
                import math
                def _norm_angle(a):
                    while a > math.pi: a -= 2*math.pi
                    while a < -math.pi: a += 2*math.pi
                    return a
                delta1 = abs(_norm_angle(a1 - a0))
                delta2 = abs(_norm_angle(a2 - a1))
                max_delta = max(delta1, delta2)
                # If angle change per half-segment > 0.15 rad (~8.5 deg), increase samples
                if max_delta > 0.15:
                    k = int(k * (1 + max_delta / 0.15))
                    k = min(k, max_samples)
            except Exception:
                pass
        return k

    def _sample_segment(seg, k):
        """Sample segment including both start and end points"""
        points = []
        s = getattr(seg, "start", None)
        if s is not None:
            points.append(s)
        if hasattr(seg, "point") and k > 1:
            for i in range(1, k):
                t = i / k
                try:
                    p = seg.point(t)
                except Exception:
                    p = None
                if p is not None:
                    points.append(p)
        # Always include the endpoint
        e = getattr(seg, "end", None)
        if e is not None:
            points.append(e)
        return points

    # Base step scales with offset magnitude and overall shape size
    try:
        bx0, by0, bx1, by1 = path.bbox()
        diag = ((bx1 - bx0) ** 2 + (by1 - by0) ** 2) ** 0.5
    except Exception:
        diag = 100.0
    base_step = max(5.0, min(diag / 200.0, max(5.0, abs(offset_value) / 2.0)))

    # Collect polyline points with adaptive sampling per segment
    # Track which points are segment boundaries (original control points)
    pts = []
    seg_boundary_map = {}  # index -> (seg_idx, is_start, is_end, seg)
    
    for seg_idx, seg in enumerate(path):
        # Skip zero-length segments (degenerate)
        seg_len = _seg_length(seg)
        if seg_len < 1e-6:  # Threshold for considering segment degenerate
            continue
        
        if interpolation and interpolation > 1:
            k = interpolation
        else:
            k = _adaptive_samples(seg, base_step)
        sampled = _sample_segment(seg, k)
        
        if not sampled:
            continue
        
        # Mark first point as segment start boundary
        start_idx = len(pts)
        seg_boundary_map[start_idx] = (seg_idx, True, False, seg)
        
        # Add first point or skip if duplicate of previous segment's endpoint
        if len(pts) == 0 or sampled[0] != pts[-1]:
            pts.append(sampled[0])
        else:
            # Junction point - update mapping to indicate it's also start of this segment
            start_idx = len(pts) - 1
            seg_boundary_map[start_idx] = (seg_idx, True, True, seg)  # Both end and start
        
        # Add intermediate points
        pts.extend(sampled[1:-1])
        
        # Add endpoint and mark as segment end boundary
        if sampled[-1] != sampled[0]:  # Avoid duplicate if segment is a point
            pts.append(sampled[-1])
            seg_boundary_map[len(pts) - 1] = (seg_idx, False, True, seg)
    
    # For closed paths, ensure last point equals first point, or remove duplicate
    # Use a small margin to treat nearly-equal endpoints as duplicates
    if len(pts) > 1:
        p_first = pts[0]
        p_last = pts[-1]
        # Compute distance between endpoints
        dx = (p_last.x - p_first.x) if hasattr(p_first, 'x') else (p_last[0] - p_first[0])
        dy = (p_last.y - p_first.y) if hasattr(p_first, 'y') else (p_last[1] - p_first[1])
        d2 = dx * dx + dy * dy
        # Margin scales modestly with base_step to be robust across sizes
        eps = (base_step * 1e-3)
        if d2 <= eps * eps:
            # Last point is (nearly) duplicate of first - remove it
            pts = pts[:-1]
    
    if len(pts) < 3:
        return None

    # Optional secondary uniform interpolation to densify long straight segments
    if interpolation and interpolation > 1:
        refined = []
        for i in range(len(pts) - 1):
            p0 = pts[i]
            p1 = pts[i + 1]
            refined.append(p0)
            dx = p1.x - p0.x
            dy = p1.y - p0.y
            for j in range(1, interpolation):
                t = j / interpolation
                refined.append(p0 + (dx * t, dy * t))
        refined.append(pts[-1])
        pts = refined

    # Determine orientation directly from points (shoelace) to avoid segment start edge cases.
    def _poly_clockwise(points):
        total = points[-1].x * points[0].y - points[0].x * points[-1].y
        for i in range(len(points) - 1):
            total += points[i].x * points[i + 1].y - points[i + 1].x * points[i].y
        return total > 0
    cw = _poly_clockwise(pts)
    effective_offset = offset_value if cw else -offset_value
    if effective_offset == 0:
        return Path(path)  # Shallow copy; no change.

    # Auto-adjust miter_limit: tighter for inward (shrink) offsets to reduce spikes
    if miter_limit is None:
        miter_limit = 2.5 if effective_offset < 0 else 4.0

    # Edge normals (SVG Y-down left-hand normal => outward for CW)
    edges = []
    normals = []
    for i in range(len(pts)):
        p0 = pts[i]
        p1 = pts[(i + 1) % len(pts)]  # Wrap around to close the polygon
        dx = p1.x - p0.x
        dy = p1.y - p0.y
        edges.append((dx, dy))
        nx = dy
        ny = -dx
        length = (nx * nx + ny * ny) ** 0.5
        if length != 0:
            scale = effective_offset / length
            nx *= scale
            ny *= scale
        normals.append((nx, ny))

    def intersect_lines(p, d, q, e):
        """Find intersection of two lines: p+t*d and q+u*e"""
        cross = d[0] * e[1] - d[1] * e[0]
        if abs(cross) < 1e-9:
            return None
        qmpx = q[0] - p[0]
        qmpy = q[1] - p[1]
        t = (qmpx * e[1] - qmpy * e[0]) / cross
        return (p[0] + t * d[0], p[1] + t * d[1])

    # Generate offset points using miter joins with intersection search
    out_pts = []
    n = len(pts)
    search_radius = 3  # Reduced from 10 - only look at nearby edges to prevent distant intersections
    
    # Helper: compute tangent for a segment at start/end
    def _seg_tangent(seg, at_start=True):
        try:
            d = seg.derivative(0.0 if at_start else 1.0)
            if d is not None and hasattr(d, "x") and hasattr(d, "y"):
                return (d.x, d.y)
        except Exception:
            pass
        return None

    for i in range(n):
        p_curr = pts[i]
        
        # Junction handling: if this sampled index is a segment boundary, prefer true tangents
        if i in seg_boundary_map:
            seg_idx, is_start, is_end, seg = seg_boundary_map[i]
            # Use outgoing tangent at a start, incoming tangent at an end
            if is_start:
                t_out = _seg_tangent(seg, at_start=True)
                if t_out and (t_out[0]**2 + t_out[1]**2) > 1e-6:  # Require substantial tangent
                    L = (t_out[0]**2 + t_out[1]**2) ** 0.5
                    # Ensure edge is at least base_step magnitude
                    if L * base_step > 1e-3:
                        edges[i] = (t_out[0] / L * base_step, t_out[1] / L * base_step)
            if is_end:
                t_in = _seg_tangent(seg, at_start=False)
                if t_in and (t_in[0]**2 + t_in[1]**2) > 1e-6:  # Require substantial tangent
                    prev_i = (i - 1) % n
                    L = (t_in[0]**2 + t_in[1]**2) ** 0.5
                    # Ensure edge is at least base_step magnitude
                    if L * base_step > 1e-3:
                        edges[prev_i] = (t_in[0] / L * base_step, t_in[1] / L * base_step)

        # Search backward for a substantial incoming edge
        # Increased threshold to skip over clusters of tiny over-sampled edges
        best_prev_idx = (i - 1) % n
        best_prev_len = (edges[best_prev_idx][0]**2 + edges[best_prev_idx][1]**2) ** 0.5
        min_acceptable_len = base_step * 0.5  # At least half the sampling step
        for k in range(2, min(search_radius, n)):
            idx = (i - k) % n
            edge_len = (edges[idx][0]**2 + edges[idx][1]**2) ** 0.5
            # Require significantly longer edge AND above minimum threshold
            if edge_len > max(best_prev_len * 2.0, min_acceptable_len):
                best_prev_idx = idx
                best_prev_len = edge_len
                break
        
        # Search forward for a substantial outgoing edge
        best_next_idx = i
        best_next_len = (edges[best_next_idx][0]**2 + edges[best_next_idx][1]**2) ** 0.5
        for k in range(1, min(search_radius, n)):
            idx = (i + k) % n
            edge_len = (edges[idx][0]**2 + edges[idx][1]**2) ** 0.5
            # Require significantly longer edge AND above minimum threshold
            if edge_len > max(best_next_len * 2.0, min_acceptable_len):
                best_next_idx = idx
                best_next_len = edge_len
                break
        
        # Get the start points of the offset edges we're intersecting
        p_prev_start_idx = best_prev_idx
        p_next_start_idx = best_next_idx
        
        offset_prev_start = (pts[p_prev_start_idx].x + normals[best_prev_idx][0], 
                            pts[p_prev_start_idx].y + normals[best_prev_idx][1])
        offset_next_start = (pts[p_next_start_idx].x + normals[best_next_idx][0], 
                            pts[p_next_start_idx].y + normals[best_next_idx][1])
        
        edge_prev = edges[best_prev_idx]
        edge_next = edges[best_next_idx]
        
        # Try to find intersection of the two offset edges
        intersection = intersect_lines(offset_prev_start, edge_prev, offset_next_start, edge_next)
        
        if intersection is not None:
            # Check if intersection is reasonable (miter limit)
            dist_to_intersection = ((intersection[0] - p_curr.x)**2 + (intersection[1] - p_curr.y)**2) ** 0.5
            max_miter_dist = abs(effective_offset) * miter_limit

            # Junction-aware bevel: if we're at a segment boundary with a sharp turn, prefer bevel
            use_bevel = False
            sb = seg_boundary_map.get(i)
            if sb is not None:
                # Compute angle between normals; large angle -> bevel
                import math
                n_prev = normals[(i - 1) % n]
                n_next = normals[i]
                dot = n_prev[0] * n_next[0] + n_prev[1] * n_next[1]
                len_prev = (n_prev[0]**2 + n_prev[1]**2) ** 0.5
                len_next = (n_next[0]**2 + n_next[1]**2) ** 0.5
                if len_prev > 1e-9 and len_next > 1e-9:
                    cosang = max(-1.0, min(1.0, dot / (len_prev * len_next)))
                    ang = math.acos(cosang)
                    # Threshold ~60 degrees; above this, bevel is visually safer
                    if ang > (math.pi / 3):
                        use_bevel = True

            if not use_bevel and dist_to_intersection <= max_miter_dist:
                # Avoid stacking duplicates at exact junctions
                if not out_pts or intersection != out_pts[-1]:
                    out_pts.append(intersection)
            else:
                # Miter limit exceeded or sharp junction - use bevel join
                n_prev = normals[(i - 1) % n]
                n_next = normals[i]
                avg_nx = (n_prev[0] + n_next[0]) * 0.5
                avg_ny = (n_prev[1] + n_next[1]) * 0.5
                ptb = (p_curr.x + avg_nx, p_curr.y + avg_ny)
                if not out_pts or ptb != out_pts[-1]:
                    out_pts.append(ptb)
        else:
            # Parallel edges - use simple offset
            # At junctions, enforce a minimum edge length to avoid micro-steps
            n_curr = normals[i]
            # Minimum move ~ 0.5 * base_step to avoid tiny sawtooth
            import math
            move_len = (n_curr[0]**2 + n_curr[1]**2) ** 0.5
            scale = 1.0
            if seg_boundary_map.get(i) is not None and move_len < (0.5 * base_step):
                if move_len > 1e-12:
                    scale = (0.5 * base_step) / move_len
            pto = (p_curr.x + n_curr[0] * scale, p_curr.y + n_curr[1] * scale)
            if not out_pts or pto != out_pts[-1]:
                out_pts.append(pto)

    if len(out_pts) < 3:
        return None

    # Fast self-intersection cleanup (spike/loop removal)
    # Stack-based approach: when the new edge intersects a prior edge (non-adjacent),
    # truncate the polygon to the intersection point to remove the loop.
    def _bbox(a, b):
        x0 = a[0] if isinstance(a, tuple) else a.x
        y0 = a[1] if isinstance(a, tuple) else a.y
        x1 = b[0] if isinstance(b, tuple) else b.x
        y1 = b[1] if isinstance(b, tuple) else b.y
        return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))

    def _segments_intersect(p1, p2, q1, q2):
        x1, y1 = (p1[0], p1[1]) if isinstance(p1, tuple) else (p1.x, p1.y)
        x2, y2 = (p2[0], p2[1]) if isinstance(p2, tuple) else (p2.x, p2.y)
        x3, y3 = (q1[0], q1[1]) if isinstance(q1, tuple) else (q1.x, q1.y)
        x4, y4 = (q2[0], q2[1]) if isinstance(q2, tuple) else (q2.x, q2.y)
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(den) < 1e-9:
            return None
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
        u = ((x1 - x3) * (y1 - y2) - (y1 - y3) * (x1 - x2)) / den
        if t < 0 or t > 1 or u < 0 or u > 1:
            return None
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))

    cleaned = []
    window = cleanup_window  # check last N edges for performance
    max_spike_len = abs(effective_offset) * 2.0  # reject spikes longer than 2x offset
    for pt in out_pts:
        # Skip None points
        if pt is None:
            continue
            
        if not cleaned:
            cleaned.append(pt)
            continue
        # Candidate new edge from cleaned[-1] to pt
        p1 = cleaned[-1]
        p2 = pt
        
        # Validate edge length - reject edges much longer than offset distance
        dx = (p2[0] if isinstance(p2, tuple) else p2.x) - (p1[0] if isinstance(p1, tuple) else p1.x)
        dy = (p2[1] if isinstance(p2, tuple) else p2.y) - (p1[1] if isinstance(p1, tuple) else p1.y)
        edge_len = (dx * dx + dy * dy) ** 0.5
        
        # For large offsets, be more aggressive: skip edges > 3x offset
        # For small offsets, use 5x to avoid over-filtering
        threshold_multiplier = 3.0 if abs(effective_offset) > 1000 else 5.0
        if edge_len > max_spike_len * threshold_multiplier:
            continue
        
        cb1 = _bbox(p1, p2)
        # Check intersection against prior edges in window
        truncated = False
        start_idx = max(0, len(cleaned) - window)
        for j in range(start_idx, len(cleaned) - 2):
            q1 = cleaned[j]
            q2 = cleaned[j + 1]
            # Skip adjacent edge check
            if q2 == p1 or q1 == p1:
                continue
            qb = _bbox(q1, q2)
            # Coarse BB test
            if cb1[0] > qb[2] or cb1[2] < qb[0] or cb1[1] > qb[3] or cb1[3] < qb[1]:
                continue
            inter = _segments_intersect(p1, p2, q1, q2)
            if inter is not None:
                # Validate intersection doesn't create extreme jump
                ix, iy = inter
                dist_to_inter = ((ix - (p1[0] if isinstance(p1, tuple) else p1.x))**2 + 
                                (iy - (p1[1] if isinstance(p1, tuple) else p1.y))**2) ** 0.5
                if dist_to_inter < max_spike_len * 2.0:
                    # Truncate cleaned to j+1 and replace endpoint with intersection
                    cleaned = cleaned[: j + 1]
                    cleaned.append(inter)
                    truncated = True
                    break
        if not truncated:
            cleaned.append(pt)

    out_pts = cleaned

    # Final validation - ensure no None values and remove duplicate consecutive points
    clean_pts = []
    prev_pt = None
    for pt in out_pts:
        if pt is None:
            continue
        # Check if duplicate of previous
        if prev_pt is not None:
            px = prev_pt[0] if isinstance(prev_pt, tuple) else prev_pt.x
            py = prev_pt[1] if isinstance(prev_pt, tuple) else prev_pt.y
            cx = pt[0] if isinstance(pt, tuple) else pt.x
            cy = pt[1] if isinstance(pt, tuple) else pt.y
            # Skip if identical to previous point (within tiny epsilon)
            if abs(cx - px) < 1e-6 and abs(cy - py) < 1e-6:
                continue
        clean_pts.append(pt)
        prev_pt = pt
    
    out_pts = clean_pts
    if len(out_pts) < 3:
        return None
    
    # Segment intersection helper (used for self-intersection detection)
    def _seg_intersect(p1, p2, q1, q2):
        x1 = p1[0] if isinstance(p1, tuple) else p1.x
        y1 = p1[1] if isinstance(p1, tuple) else p1.y
        x2 = p2[0] if isinstance(p2, tuple) else p2.x
        y2 = p2[1] if isinstance(p2, tuple) else p2.y
        x3 = q1[0] if isinstance(q1, tuple) else q1.x
        y3 = q1[1] if isinstance(q1, tuple) else q1.y
        x4 = q2[0] if isinstance(q2, tuple) else q2.x
        y4 = q2[1] if isinstance(q2, tuple) else q2.y
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(den) < 1e-9:
            return None
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
        u = ((x1 - x3) * (y1 - y2) - (y1 - y3) * (x1 - x2)) / den
        if t < 0 or t > 1 or u < 0 or u > 1:
            return None
        ix = x1 + t * (x2 - x1)
        iy = y1 + t * (y2 - y1)
        return (ix, iy)
    
    # Global closure trimming: detect mid-array self-intersection forming wrap-around
    # Efficient strided scan across far-apart segment pairs; trim to intersection.
    def _seg_intersect(p1, p2, q1, q2):
        x1 = p1[0] if isinstance(p1, tuple) else p1.x
        y1 = p1[1] if isinstance(p1, tuple) else p1.y
        x2 = p2[0] if isinstance(p2, tuple) else p2.x
        y2 = p2[1] if isinstance(p2, tuple) else p2.y
        x3 = q1[0] if isinstance(q1, tuple) else q1.x
        y3 = q1[1] if isinstance(q1, tuple) else q1.y
        x4 = q2[0] if isinstance(q2, tuple) else q2.x
        y4 = q2[1] if isinstance(q2, tuple) else q2.y
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(den) < 1e-9:
            return None
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
        u = ((x1 - x3) * (y1 - y2) - (y1 - y3) * (x1 - x2)) / den
        if t < 0 or t > 1 or u < 0 or u > 1:
            return None
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))

    # Global self-intersection cleanup: detect large loops dynamically
    # Scan for non-adjacent segments that intersect, indicating a wrap-around
    if len(out_pts) > 200 and not os.environ.get('OFFSET_SKIP_TRIM'):
        npts = len(out_pts)
        if os.environ.get('OFFSET_DEBUG'):
            print(f"[DEBUG] Pre-trim: {npts} points")
        
        # Dynamic detection: look for large-gap intersections across the path
        # Use chunk-based spatial hashing for efficiency
        # Iteratively remove loops until no more found
        max_passes = 10
        for _ in range(max_passes):
            npts = len(out_pts)
            if npts < 3:
                break
                
            best = None
            best_gap = 0
            min_gap = 2  # Minimum separation to consider (catch small loops)
            
            # Divide path into chunks
            chunk_size = 50
            chunks = []
            for i in range(0, npts - 1, chunk_size):
                end = min(i + chunk_size + 1, npts)
                pts_slice = out_pts[i:end]
                xs = [p[0] if isinstance(p, tuple) else p.x for p in pts_slice]
                ys = [p[1] if isinstance(p, tuple) else p.y for p in pts_slice]
                bbox = (min(xs), min(ys), max(xs), max(ys))
                chunks.append({'bbox': bbox, 'start': i, 'end': end-1})

            def _bbox_intersect(b1, b2):
                return not (b1[2] < b2[0] or b1[0] > b2[2] or b1[3] < b2[1] or b1[1] > b2[3])

            # Check chunk pairs
            for i in range(len(chunks)):
                c1 = chunks[i]
                
                for j in range(i, len(chunks)):
                    c2 = chunks[j]
                    if not _bbox_intersect(c1['bbox'], c2['bbox']):
                        continue
                    
                    # Detailed check for segments in intersecting chunks
                    for k in range(c1['start'], c1['end']):
                        a1 = out_pts[k]
                        a2 = out_pts[k+1]
                        
                        for m in range(c2['start'], c2['end']):
                            # Ensure gap constraint
                            if m <= k + min_gap:
                                continue
                                
                            b1 = out_pts[m]
                            b2 = out_pts[m+1]
                            
                            inter = _seg_intersect(a1, a2, b1, b2)
                            if inter:
                                gap = m - k
                                # Ignore closure intersections (start/end meeting)
                                # Adjacent segments at closure are 0 and npts-2 (gap = npts-2)
                                if gap >= npts - 2:
                                    continue
                                    
                                if gap > best_gap:
                                    best_gap = gap
                                    best = (k, m, inter)
            
            # If intersection found, handle it
            if best is not None and best_gap > min_gap:
                i, j, inter = best
                if os.environ.get('OFFSET_DEBUG'):
                    print(f"[DEBUG] Found self-intersection at indices {i} and {j}, gap={best_gap}")
                
                # Heuristic: if the loop is larger than half the path, it's likely the main body
                # (e.g. closure intersection). Keep the loop, discard tails.
                # Otherwise, it's an artifact loop. Remove the loop, keep tails.
                if best_gap > npts / 2:
                    # Keep the loop i...j
                    # Path: inter -> (i+1...j) -> inter
                    # We construct it as [inter] + out_pts[i+1:j+1] + [inter]
                    new_pts = [inter]
                    new_pts.extend(out_pts[i+1:j+1])
                    new_pts.append(inter)
                    out_pts = new_pts
                    if os.environ.get('OFFSET_DEBUG'):
                        print(f"[DEBUG] Kept loop (main body), new len={len(out_pts)}")
                else:
                    # Remove the loop i...j
                    # Path: (0...i) -> inter -> (j+1...N)
                    new_pts = out_pts[:i+1]
                    new_pts.append(inter)
                    new_pts.extend(out_pts[j+1:])
                    out_pts = new_pts
                    if os.environ.get('OFFSET_DEBUG'):
                        print(f"[DEBUG] Removed loop (artifact), new len={len(out_pts)}")
            else:
                # No more intersections
                break
    
    if len(out_pts) < 3:
        return None

    # Post-slice leading point cleanup:
    # If the first edge is extremely short or the angle at the first vertex
    # indicates a near reversal, drop the first point.
    # For negative offsets, also check for oversized edges at closure that indicate artifacts.
    def _edge_len(a, b):
        ax = a[0] if isinstance(a, tuple) else a.x
        ay = a[1] if isinstance(a, tuple) else a.y
        bx = b[0] if isinstance(b, tuple) else b.x
        by = b[1] if isinstance(b, tuple) else b.y
        dx = bx - ax
        dy = by - ay
        return (dx * dx + dy * dy) ** 0.5

    def _angle_deg(p0, p1, p2):
        x0 = p0[0] if isinstance(p0, tuple) else p0.x
        y0 = p0[1] if isinstance(p0, tuple) else p0.y
        x1 = p1[0] if isinstance(p1, tuple) else p1.x
        y1 = p1[1] if isinstance(p1, tuple) else p1.y
        x2 = p2[0] if isinstance(p2, tuple) else p2.x
        y2 = p2[1] if isinstance(p2, tuple) else p2.y
        dx1 = x1 - x0
        dy1 = y1 - y0
        dx2 = x2 - x1
        dy2 = y2 - y1
        l1 = (dx1 * dx1 + dy1 * dy1) ** 0.5
        l2 = (dx2 * dx2 + dy2 * dy2) ** 0.5
        if l1 < 1e-9 or l2 < 1e-9:
            return 0.0
        dot = (dx1 * dx2 + dy1 * dy2) / (l1 * l2)
        if dot < -1.0:
            dot = -1.0
        elif dot > 1.0:
            dot = 1.0
        import math
        return math.degrees(math.acos(dot))
    
    # For negative offsets, trim oversized edges at start/end (closure artifacts)
    if effective_offset < 0 and len(out_pts) >= 5:
        # Use median edge length as reference for "normal" edges
        edge_lengths = []
        for i in range(min(20, len(out_pts) - 1)):
            if i < 3 or i >= len(out_pts) - 3:
                continue  # Skip first/last 3 edges
            edge_lengths.append(_edge_len(out_pts[i], out_pts[i + 1]))
        
        if edge_lengths:
            edge_lengths.sort()
            median_edge = edge_lengths[len(edge_lengths) // 2]
            # Threshold: 3x median edge length (catches artifacts while preserving valid geometry)
            max_normal_edge = max(median_edge * 3.0, abs(effective_offset) * 0.3)
        else:
            max_normal_edge = abs(effective_offset) * 0.5
        
        # Check and trim leading oversized edges
        while len(out_pts) >= 3:
            first_edge = _edge_len(out_pts[0], out_pts[1])
            if first_edge > max_normal_edge:
                out_pts = out_pts[1:]  # Drop first point
            else:
                break
        
        # Check and trim trailing oversized edges
        while len(out_pts) >= 3:
            last_edge = _edge_len(out_pts[-2], out_pts[-1])
            if last_edge > max_normal_edge:
                out_pts = out_pts[:-1]  # Drop last point
            else:
                break

    if len(out_pts) < 3:
        return None

    # Check for remaining stub artifacts
    if len(out_pts) >= 3:
        first_edge = _edge_len(out_pts[0], out_pts[1])
        # Compute a reference edge length from the next edge
        ref_edge = _edge_len(out_pts[1], out_pts[2])
        # Angle at the first vertex
        ang = _angle_deg(out_pts[0], out_pts[1], out_pts[2])
        # Absolute epsilon based on offset magnitude (and a minimum)
        abs_eps = max(1.0, abs(effective_offset) * 0.005)
        # Conditions to drop the leading point:
        # - First edge is an absolute tiny stub (first_edge < abs_eps)
        # - OR first edge is much shorter than the next (likely a stub)
        # - OR angle suggests near reversal (> 170°)
        if first_edge < abs_eps or (ref_edge > 0 and first_edge < ref_edge * 0.2) or ang > 170.0:
            out_pts = out_pts[1:]
    
    if len(out_pts) < 3:
        return None

    # Compute proper closing junction before building segments
    # Check if we need to close the path with a junction point
    first_pt = out_pts[0]
    last_pt = out_pts[-1]
    x0 = first_pt[0] if isinstance(first_pt, tuple) else first_pt.x
    y0 = first_pt[1] if isinstance(first_pt, tuple) else first_pt.y
    x_last = last_pt[0] if isinstance(last_pt, tuple) else last_pt.x
    y_last = last_pt[1] if isinstance(last_pt, tuple) else last_pt.y
    dist_to_first = ((x_last - x0)**2 + (y_last - y0)**2) ** 0.5
    
    # Track if we computed a closing junction
    closing_junction = None
    
    close_threshold = max(abs(effective_offset) * 0.01, base_step * 0.1)
    if dist_to_first > close_threshold:
        # Compute proper junction intersection for closing the path
        # We need to intersect the offset edges extending from the last and first points
        
        if len(out_pts) >= 3 and len(pts) >= 3:
            # Get the original points and edges for the closing junction
            n_pts = len(pts)
            
            # Last offset edge: starts at last offset point, extends along the edge 
            # between second-to-last and last original points
            last_orig_idx = n_pts - 1
            prev_orig_idx = n_pts - 2
            
            # Direction of last edge (from prev to last original point)
            last_edge_dir = edges[prev_orig_idx]  # edges[i] is from pts[i] to pts[i+1]
            
            # Start point of last offset edge: last offset point
            offset_last_start = (x_last, y_last)
            
            # First offset edge: starts at first offset point, extends along the edge
            # between first and second original points  
            first_edge_dir = edges[0]  # edges[0] is from pts[0] to pts[1]
            
            # Start point of first offset edge: first offset point
            offset_first_start = (x0, y0)
            
            # Find intersection of the two offset edges
            junction = intersect_lines(offset_last_start, last_edge_dir, 
                                     offset_first_start, first_edge_dir)
            
            if junction is not None:
                # Check if junction is reasonable (miter limit)
                dist_last = ((junction[0] - x_last)**2 + (junction[1] - y_last)**2) ** 0.5
                dist_first = ((junction[0] - x0)**2 + (junction[1] - y0)**2) ** 0.5
                max_miter_dist = abs(effective_offset) * miter_limit
                
                if dist_last <= max_miter_dist and dist_first <= max_miter_dist:
                    # Use the junction point - replace the last point with it
                    out_pts[-1] = junction
                else:
                    # Miter limit exceeded - use bevel (average of normals)
                    # Get normals for the closing junction
                    last_normal = normals[prev_orig_idx]
                    first_normal = normals[0]
                    avg_nx = (last_normal[0] + first_normal[0]) * 0.5
                    avg_ny = (last_normal[1] + first_normal[1]) * 0.5
                    
                    # Bevel point at the midpoint between last and first points
                    mid_x = (x_last + x0) * 0.5
                    mid_y = (y_last + y0) * 0.5
                    bevel_pt = (mid_x + avg_nx, mid_y + avg_ny)
                    out_pts[-1] = bevel_pt  # Replace last point with bevel
            # If no intersection found (parallel edges), the path closes naturally

    # Build path segments with explicit start/end points
    first_pt = out_pts[0]
    x0 = first_pt[0] if isinstance(first_pt, tuple) else first_pt.x
    y0 = first_pt[1] if isinstance(first_pt, tuple) else first_pt.y
    first = Point(x0, y0)
    
    segs = [Move(first)]
    
    # Create line segments for all consecutive points
    n = len(out_pts)
    for i in range(n - 1):
        curr_pt = out_pts[i]
        next_pt = out_pts[i + 1]
        x_curr = curr_pt[0] if isinstance(curr_pt, tuple) else curr_pt.x
        y_curr = curr_pt[1] if isinstance(curr_pt, tuple) else curr_pt.y
        x_next = next_pt[0] if isinstance(next_pt, tuple) else next_pt.x
        y_next = next_pt[1] if isinstance(next_pt, tuple) else next_pt.y
        segs.append(Line(start=Point(x_curr, y_curr), end=Point(x_next, y_next)))
    
    # Final closing segment back to start
    last_pt = out_pts[-1]
    x_last = last_pt[0] if isinstance(last_pt, tuple) else last_pt.x
    y_last = last_pt[1] if isinstance(last_pt, tuple) else last_pt.y
    
    # Direct closing segment from last point (which may be a junction) to first point
    segs.append(Line(start=Point(x_last, y_last), end=first))
    
    return Path(*segs)


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "postboot":
        init_commands(kernel)


def init_commands(kernel):
    self = kernel.elements

    _ = kernel.translation

    classify_new = self.post_classify
    # We are patching the class responsible for Cut nodes in general,
    # so that any new instance of this class will be able to use the
    # new functionality.
    # Notabene: this may be overloaded by another routine (like from pyclipr)
    # at a later time.
    from meerk40t.core.node.op_cut import CutOpNode
    print ("Changing CutOpNode.offset_routine to internal")
    CutOpNode.offset_routine = offset_path
    kernel.add_capability("offset_routine", "Internal")

    @self.console_argument(
        "offset",
        type=str,
        help=_(
            "offset to line mm (positive values to left/outside, negative values to right/inside)"
        ),
    )
    @self.console_option(
        "radial", "r", action="store_true", type=bool, help=_("radial connector")
    )
    @self.console_option(
        "native",
        "n",
        action="store_true",
        type=bool,
        help=_("native path offset (use at you own risk)"),
    )
    @self.console_option(
        "interpolation", "i", type=int, help=_("interpolation points per segment")
    )
    @self.console_command(
        ("offset2", "offset"),
        help=_("create an offset path for any of the given elements, old algorithm"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_offset_path(
        command,
        channel,
        _,
        offset=None,
        radial=None,
        native=False,
        interpolation=None,
        data=None,
        post=None,
        **kwargs,
    ):
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No elements selected"))
            return "elements", data
        if native:
            linearize = False
        else:
            linearize = True
        if interpolation is None:
            interpolation = 500
        if offset is None:
            offset = 0
        else:
            try:
                offset = float(Length(offset))
            except ValueError:
                offset = 0
        if radial is None:
            radial = False
        data_out = list()
        for node in data:
            if hasattr(node, "as_path"):
                p = abs(node.as_path())
            else:
                bb = node.bounds
                if bb is None:
                    # Node has no bounds or space, therefore no offset outline.
                    return "elements", data_out
                p = Geomstr.rect(
                    x=bb[0], y=bb[1], width=bb[2] - bb[0], height=bb[3] - bb[1]
                ).as_path()

            node_path = path_offset(
                p,
                offset,
                radial_connector=radial,
                linearize=linearize,
                interpolation=interpolation,
            )
            if node_path is None or len(node_path) == 0:
                continue
            node_path.validate_connections()
            with self.node_lock:
                newnode = self.elem_branch.add(
                    path=node_path, type="elem path", stroke=node.stroke
                )
            newnode.stroke_width = UNITS_PER_PIXEL
            newnode.linejoin = Linejoin.JOIN_ROUND
            newnode.label = (
                f"Offset of {node.id if node.label is None else node.display_label()}"
            )
            data_out.append(newnode)

        # Newly created! Classification needed?
        if len(data_out) > 0:
            # Skip classification for simple offset to avoid overhead and classification side-effects.
            self.signal("refresh_scene", "Scene")
        return "elements", data_out

    # --------------------------- END COMMANDS ------------------------------
    # Simplified variant using path_offset_simple
    @self.console_argument(
        "offset",
        type=str,
        help=_(
            "offset distance (positive expands CW path, negative shrinks)"
        ),
    )
    @self.console_option(
        "interpolation", "i", type=int, help=_("uniform interpolation per segment (simple)")
    )
    @self.console_option(
        "miterlimit", "m", type=float, help=_("maximum miter length factor (auto if omitted)")
    )
    @self.console_option(
        "window", "w", type=int, help=_("self-intersection check window (default 100)")
    )
    @self.console_command(
        ("offsetsimple", "offset_simple"),
        help=_("create an offset path using simplified fast algorithm"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_offset_path_simple(
        command,
        channel,
        _,
        offset=None,
        interpolation=None,
        miterlimit=None,
        window=None,
        data=None,
        post=None,
        **kwargs,
    ):
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No elements selected"))
            return "elements", data
        if interpolation is None:
            interpolation = 0
        if window is None:
            window = 100
        if offset is None:
            offset = 0
        else:
            try:
                offset = float(Length(offset))
            except ValueError:
                offset = 0
        data_out = []
        for node in data:
            if hasattr(node, "as_path"):
                p = abs(node.as_path())
            else:
                bb = node.bounds
                if bb is None:
                    continue
                p = Geomstr.rect(
                    x=bb[0], y=bb[1], width=bb[2] - bb[0], height=bb[3] - bb[1]
                ).as_path()
            new_path = path_offset_simple(p, offset_value=offset, interpolation=interpolation, miter_limit=miterlimit, cleanup_window=window)
            if new_path is None or len(new_path) == 0:
                continue
            new_path.validate_connections()
            with self.node_lock:
                newnode = self.elem_branch.add(
                    path=new_path, type="elem path", stroke=node.stroke
                )
            newnode.stroke_width = UNITS_PER_PIXEL
            newnode.linejoin = Linejoin.JOIN_ROUND
            newnode.label = f"Simple Offset of {node.id if node.label is None else node.display_label()}"
            data_out.append(newnode)
        if len(data_out) > 0:
            post.append(classify_new(data_out))
            self.signal("refresh_scene", "Scene")
        return "elements", data_out
