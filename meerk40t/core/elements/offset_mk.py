"""
This adds console commands that deal with the creation of an offset
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

"""
The following routines deal with the offset of an SVG path at a given distance D.
An offset or parallel curve can easily be established:
    - for a line segment by another line parallel and in distance D:
        Establish the two normals with length D on the end points and
        create the two new endpoints
    - for an arc segment: elongate rx and ry by D
To establish an offset for a quadratic or cubic bezier by another cubic bezier
is not possible so this requires approximation.
An acceptable approximation is proposed by Tiller and Hanson:
    P1 start point
    P2 end point
    C1 control point 1
    C2 control point 2
    You create the offset version of these 3 lines and look for their intersections:
        - offset to (P1 C1)  -> helper 1
        - offset to (C1 C2)  -> helper 2
        - offset to (P2 C2)  -> helper 3
        we establish P1-new
        the intersections between helper 1 and helper 2 is our new control point C1-new
        the intersections between helper 2 and helper 3 is our new control point C2-new



A good visual representation can be seen here:
https://feirell.github.io/offset-bezier/

The algorithm deals with the challenge as follows:
a) It walks through the subpaths of a given path so that we have a continuous curve
b) It looks at the different segment typs and deals with them,
generating a new offseted segment
c) Finally it stitches those segments together, preparing for the simplification
"""


def norm_vector(p1, p2, target_len):
    line_vector = p2 - p1
    # if line_vector.x == 0 and line_vector.y == 0:
    #     return Point(target_len, 0)
    factor = target_len
    normal_vector = Point(-1 * line_vector.y, line_vector.x)
    normlen = abs(normal_vector)
    if normlen != 0:
        factor = target_len / normlen
    normal_vector *= factor
    return normal_vector


def is_clockwise(path, start=0):
    def poly_clockwise(poly):
        """
        returns True if the polygon is clockwise ordered, false if not
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
                # Invalid/Retrograde. Pop curr_seg and try again with previous.
                # print(f"  Prune retrograde: {curr_seg.start} -> {p_i} (Dot: {dot:.4f})")
                final_segments.pop()

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


def offset_arc(segment, offset=0, linearize=False, interpolation=500):
    if not isinstance(segment, Arc):
        return None
    newsegments = list()
    if linearize:
        s = linearize_segment(segment, interpolation=interpolation, reduce=True)
        s = offset_point_array(s, offset)
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
    To establish an offset for a quadratic or cubic bezier by another cubic bezier
    is not possible so this requires approximation.
    An acceptable approximation is proposed by Tiller and Hanson:
        P1 start point
        P2 end point
        C1 control point 1
        C2 control point 2
        You create the offset version of these 3 lines and look for their intersections:
        - offset to (P1 C1)  -> helper 1
        - offset to (C1 C2)  -> helper 2
        - offset to (P2 C2)  -> helper 3
        we establish P1-new
        the intersections between helper 1 and helper 2 is our new control point C1-new
        the intersections between helper 2 and helper 3 is our new control point C2-new

        Beware, this has limitations! It's not dealing well with curves that have cusps
    """

    if not isinstance(segment, CubicBezier):
        return None
    newsegments = list()
    if linearize:
        s = linearize_segment(segment, interpolation=interpolation, reduce=True)
        s = offset_point_array(s, offset)
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
    We establish the intersection between two lines given by
    line1 = (w, z), line2 = (x, y)
    We define the first line by the equation w + s * (z - w)
    We define the second line by the equation x + t * (y - x)
    We give back the intersection and the values for s and t
    out of these two equations at the intersection point.
    Notabene: if the intersection is on the two line segments
    then s and t need to be between 0 and 1.

    Args:
        w (Point): Start point of the first line segment
        z (Point): End point of the second line segment
        x (Point): Start point of the first line segment
        y (Point): End point of the second line segment
    Returns three values: P, s, t
        P: Point of intersection, None if the two lines have no intersection
        S: Value for s in P = w + s * (z - w)
        T: Value for t in P = x + t * (y - x)

        ( w1 )     ( z1 - w1 )    ( x1 )     ( y1 - x1 )
        (    ) + t (         )  = (    ) + s (         )
        ( w2 )     ( z2 - w2 )    ( y1 )     ( y2 - x2 )

        ( w1 - x1 )     ( y1 - x1 )     ( z1 - w1 )
        (         ) = s (         ) - t (         )
        ( w2 - x2 )     ( y2 - x2 )     ( z2 - w2 )

        ( w1 - x1 )    ( y1 - x1   -z1 + w1 ) ( s )
        (         ) =  (                    ) (   )
        ( w2 - x2 )    ( y2 - x2   -z2 + w2 ) ( t )

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
    return p, s, t


def offset_path(self, path, offset_value=0):
    # As this oveloading a regular method in a class
    # it needs to have the very same definition (including the class
    # reference self)
    # Radial connectors seem to have issues, so we don't use them for now...
    p = path_offset(
        path,
        offset_value=-offset_value,
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
    MINIMAL_LEN = 5
    print (f"Path Offset: Offset={offset_value}, Radial={radial_connector}, Linearize={linearize}, Interp={interpolation}")
    if isinstance(path, Path):
        print (f"Path: {path.d()}")

    def stitch_segments_at_index(
        offset, stitchpath, seg1_end, orgintersect, radial=False, closed=False, limit=None
    ):
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
                    continue
                seg_k = stitchpath._segments[k]
                if isinstance(seg_k, Line):
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

                    # Bbox check
                    if min(seg_k.start.x, seg_k.end.x) > s1_x2: continue
                    if max(seg_k.start.x, seg_k.end.x) < s1_x1: continue
                    if min(seg_k.start.y, seg_k.end.y) > s1_y2: continue
                    if max(seg_k.start.y, seg_k.end.y) < s1_y1: continue

                    p, s, t = intersect_line_segments(
                        Point(seg1.start),
                        Point(seg1.end),
                        Point(seg_k.start),
                        Point(seg_k.end),
                    )
                    if p is not None:
                        # Check if intersection is within segments
                        # We use a small tolerance for floating point errors
                        if -1e-9 <= s <= 1.0 + 1e-9 and -1e-9 <= t <= 1.0 + 1e-9:
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
                    else:
                        # Check for parallel swap (Inverted U-turn)
                        v1 = seg1.end - seg1.start
                        vk = seg_k.end - seg_k.start
                        # Check if parallel and opposite
                        cross = v1.x * vk.y - v1.y * vk.x
                        dot = v1.x * vk.x + v1.y * vk.y
                        
                        if abs(cross) < 1e-3 and dot < 0:
                             print(f"Parallel Check {left_end} vs {k}: cross={cross}, dot={dot}")
                        
                        if abs(cross) < 1e-6 and dot < 0:
                             len1 = abs(v1)
                             if len1 > 1e-9:
                                 n1 = Point(-v1.y / len1, v1.x / len1)
                                 v_conn = seg_k.start - seg1.end
                                 proj = v_conn.x * n1.x + v_conn.y * n1.y
                                 
                                 print(f"Parallel Swap Check: proj={proj}")
                                 
                                 # If proj < 0, they are swapped
                                 if proj < -1e-4:
                                     # Swapped! Use midpoint of outer ends
                                     print(f"Swapped! Fixing U-turn.")
                                     best_p = Point((seg1.start.x + seg_k.end.x)/2, (seg1.start.y + seg_k.end.y)/2)
                                     best_idx = k
                                     break

            if best_p is not None:
                # We found a valid intersection
                
                # Determine which way to cut
                cut_forward = True
                if closed:
                    # Check if we should keep the "inner" loop (forward cut) or "outer" loop (backward cut)
                    # Forward cut removes: right_start ... best_idx - 1
                    len_forward = best_idx - right_start
                    
                    # Backward cut removes: best_idx ... end AND start ... right_start - 1
                    # Note: if wrapped, right_start is already modulo'd, but here we use linear indices
                    # If wrapped locally (right_start < left_end), len_forward calculation might be negative?
                    # No, best_idx comes from loop range(scan_end, right_start - 1, -1).
                    # If wrapped, right_start is 0. best_idx >= 0.
                    # So len_forward is positive.
                    
                    # Backward length:
                    len_backward = (lp - best_idx) + right_start
                    
                    # If wrapped locally, right_start is 0.
                    # len_backward = lp - best_idx.
                    # len_forward = best_idx.
                    # This matches the wrapped heuristic.
                    
                    if len_forward > len_backward:
                        cut_forward = False
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
                             
                             # print(f"Global backward cut: count_start={count_start}, start_del={start_del}")
                             if count_start > start_del:
                                 del stitchpath._segments[start_del:count_start]
                                 point_added -= (count_start - start_del)
                                 deleted_from_start = (count_start - start_del)
                                 deleted_from_start = count_start - start_del
                                 point_added -= (count_start - start_del)
                    
                    return point_added, deleted_from_start, deleted_tail, deleted_loop
                    
                    return point_added, deleted_from_start, deleted_from_end

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
                            # Recurse to stitch seg1 to the new neighbor
                            p_a, d_s, d_t, d_l = stitch_segments_at_index(
                                offset, stitchpath, left_end, orgintersect, radial, closed, limit
                            )
                            return point_added - 1 + p_a, deleted_from_start + d_s, deleted_tail + d_t, deleted_loop + d_l
                        elif s < -1e-9:
                            # seg1 is overshadowed (s < 0). 
                            # Remove it.
                            del stitchpath._segments[left_end]
                            return point_added, deleted_from_start + 1, deleted_tail, deleted_loop
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
                    print(f"Connector check: dot1={dot1}, v1={v1}, vc={vc}")
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
                        point_added = 0
                
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

    # def dis(pt):
    #     if pt is None:
    #         return "None"
    #     else:
    #         return f"({pt.x:.0f}, {pt.y:.0f})"

    results = []
    # This needs to be a continuous path
    spct = 0
    for subpath in path.as_subpaths():
        spct += 1
        print (f"Subpath {spct}")
        p = Path(subpath)
        if not linearize:
            # p.approximate_arcs_with_cubics()
            pass
        offset = offset_value
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
                        offset = -1 * offset_value
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
                    offset = offset_value
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
                            offset = -1 * offset_value
                        # print ("Seems to be closed!")
                # print (f"Regular point: {idx}, {type(segment).__name__}, {first_point}, {last_point}, {is_closed}")
            if idx == 0:
                # print(f"Processing index 0: {type(segment).__name__}, last={last_point}, first={first_point}, closed={is_closed}")
                pass
            helper1 = Point(p._segments[idx].end)
            helper2 = Point(p._segments[idx].start)
            left_end = idx
            print (f"Segment to deal with: {type(segment).__name__}")
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
                    # print(f"After Stitch {curr}: len={len(p._segments)}")
                    
                    if last_point is not None:
                        last_point += stitched
                        # if stitched != 0: print(f"Updated last_point (stitched)={last_point}")
                    
                    if deleted_start > 0:
                        # idx -= deleted_start
                        # curr -= deleted_start
                        if idx < 0:
                            idx = 0
                        if first_point is not None:
                            first_point -= deleted_start
                            if first_point < 0: first_point = 0
                            if first_point == 0 and len(p._segments) > 1 and isinstance(p._segments[0], Move):
                                first_point = 1
                        if last_point is not None:
                            last_point -= deleted_start
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
                        if last_point is not None:
                            last_point -= deleted_tail
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
                if last_point is not None:
                    last_point -= deleted_tail
                # idx = left_end - deleted_tail + 1 # ?

            idx -= 1
            if deleted_start > 0:
                idx -= deleted_start
                if first_point is not None:
                    first_point -= deleted_start
                    if first_point < 0:
                        first_point = 0
                if last_point is not None:
                    last_point -= deleted_start

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
                ll = Length(offset)
                # Invert for right behaviour
                offset = -1.0 * float(ll)
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
            post.append(classify_new(data_out))
            self.signal("refresh_scene", "Scene")
        return "elements", data_out

    # --------------------------- END COMMANDS ------------------------------
