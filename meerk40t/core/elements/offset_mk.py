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
from meerk40t.tools.geomstr import Geomstr

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

        if total <= 0:
            return True
        else:
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
    result = list()
    p0 = None
    for idx, p1 in enumerate(points):
        if idx > 0:
            nv = norm_vector(p0, p1, offset)
            result.append(p0 + nv)
            result.append(p1 + nv)
        p0 = Point(p1)
    for idx in range(3, len(result)):
        w = result[idx - 3]
        z = result[idx - 2]
        x = result[idx - 1]
        y = result[idx]
        p_i, s, t = intersect_line_segments(w, z, x, y)
        if p_i is None:
            continue
        result[idx - 2] = Point(p_i)
        result[idx - 1] = Point(p_i)
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
        newsegments.append(newseg)
    return newsegments


def offset_line(segment, offset=0):
    if not isinstance(segment, Line):
        return None
    newseg = copy(segment)
    normal_vector = norm_vector(segment.start, segment.end, offset)
    newseg.start += normal_vector
    newseg.end += normal_vector
    # print (f"Old= ({segment.start.x:.0f}, {segment.start.y:.0f})-({segment.end.x:.0f}, {segment.end.y:.0f})")
    # print (f"New= ({newsegment.start.x:.0f}, {newsegment.start.y:.0f})-({newsegment.end.x:.0f}, {newsegment.end.y:.0f})")
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
    p = path_offset(
        path,
        offset_value=-offset_value,
        radial_connector=True,
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

    def stitch_segments_at_index(
        offset, stitchpath, seg1_end, orgintersect, radial=False, closed=False
    ):
        point_added = 0
        left_end = seg1_end
        lp = len(stitchpath)
        right_start = left_end + 1
        if right_start >= lp:
            if not closed:
                return point_added
            # Look for the first segment
            right_start = right_start % lp
            while not isinstance(
                stitchpath._segments[right_start],
                (Arc, Line, QuadraticBezier, CubicBezier),
            ):
                right_start += 1
        seg1 = stitchpath._segments[left_end]
        seg2 = stitchpath._segments[right_start]

        #  print (f"Stitch {left_end}: {type(seg1).__name__}, {right_start}: {type(seg2).__name__} - max={len(stitchpath._segments)}")
        if isinstance(seg1, Close):
            # Close will be dealt with differently...
            return point_added
        if isinstance(seg1, Move):
            seg1.end = Point(seg2.start)
            return point_added

        if isinstance(seg1, Line):
            needs_connector = True
            if isinstance(seg2, Line):
                p, s, t = intersect_line_segments(
                    Point(seg1.start),
                    Point(seg1.end),
                    Point(seg2.start),
                    Point(seg2.end),
                )
                if p is not None:
                    # We have an intersection
                    if 0 <= abs(s) <= 1 and 0 <= abs(t) <= 1:
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
                        if odist > abs(offset):
                            angle = orgintersect.angle_to(p)
                            p = orgintersect.polar_to(angle, abs(offset))

                            newseg1 = Line(seg1.end, p)
                            newseg2 = Line(p, seg2.start)
                            stitchpath._segments.insert(left_end + 1, newseg2)
                            stitchpath._segments.insert(left_end + 1, newseg1)
                            point_added = 2
                            needs_connector = False
                            # print ("Used shortened external intersect")
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
            stitchpath._segments.insert(left_end + 1, connect_seg)
            point_added = 1
        elif needs_connector:
            # print ("Need connector but end points were identical")
            pass
        else:
            # print ("No connector needed")
            pass
        return point_added

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
                if 0 <= abs(s) <= 1 and 0 <= abs(t) <= 1:
                    seg1.start = Point(p)
                    seg2.end = Point(p)
                    # print (f"{perf_counter()-t_start:.3f} Close subpath by adjusting inner lines, d={d:.2f} vs. offs={offset:.2f}")
                elif d >= abs(offset):
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
                        # print(f"{perf_counter()-t_start:.3f} Inserting segment at {lastidx + 1}...")
                        sub_path._segments.insert(lastidx + 1, segment)
                        # print(f"{perf_counter()-t_start:.3f} Done.")

                    else:
                        p = orgintersect.polar_to(
                            angle=orgintersect.angle_to(p),
                            distance=abs(offset),
                        )
                        segment = Line(p, seg1.start)
                        sub_path._segments.insert(lastidx + 1, segment)
                        segment = Line(seg2.end, p)
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
        # print (f"Subpath {spct}")
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
        # Let's check the first and last valid point. If they are identical
        # we consider this to be a closed path even if it has no closed indicator.
        # firstp_start = None
        # lastp = None
        idx = 0
        while (idx < len(p)) and not isinstance(
            p._segments[idx], (Arc, Line, QuadraticBezier, CubicBezier)
        ):
            idx += 1
        firstp_start = Point(p._segments[idx].start)
        idx = len(p._segments) - 1
        while idx >= 0 and not isinstance(
            p._segments[idx], (Arc, Line, QuadraticBezier, CubicBezier)
        ):
            idx -= 1
        lastp = Point(p._segments[idx].end)
        if firstp_start.distance_to(lastp) < 1e-3:
            is_closed = True
            # print ("Seems to be closed!")
        # We need to establish if this is a closed path and if the first segment goes counterclockwise
        cw = False
        if not is_closed:
            for idx in range(len(p._segments) - 1, -1, -1):
                if isinstance(p._segments[idx], Close):
                    is_closed = True
                    break
        if is_closed:
            cw = is_clockwise(p, 0)
            if cw:
                offset = -1 * offset_value
        # print (f"Subpath: closed={is_closed}, clockwise={cw}")
        # Remember the complete subshape (could be multiple segements due to linearization)
        last_point = None
        first_point = None
        is_closed = False
        helper1 = None
        helper2 = None
        for idx in range(len(p._segments) - 1, -1, -1):
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
                    if cw:
                        offset = -1 * offset_value
                else:
                    # Invalid close?! Remove it
                    p._segments.pop(idx)
                    if last_point is not None:
                        last_point -= 1
                    continue
            elif isinstance(segment, Move):
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
                    continue
                first_point = idx
                if last_point is None:
                    last_point = idx
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
                        if cw:
                            offset = -1 * offset_value
                        # print ("Seems to be closed!")
                # print (f"Regular point: {idx}, {type(segment).__name__}, {first_point}, {last_point}, {is_closed}")
            helper1 = Point(p._segments[idx].end)
            helper2 = Point(p._segments[idx].start)
            left_end = idx
            #  print (f"Segment to deal with: {type(segment).__name__}")
            if isinstance(segment, Arc):
                arclinearize = linearize
                # Arc is not working, so we always linearize
                arclinearize = True
                newsegment = offset_arc(segment, offset, arclinearize, interpolation)
                if newsegment is None or len(newsegment) == 0:
                    continue
                left_end = idx - 1 + len(newsegment)
                last_point += len(newsegment) - 1
                p._segments[idx] = newsegment[0]
                for nidx in range(len(newsegment) - 1, 0, -1):  # All but the first
                    p._segments.insert(idx + 1, newsegment[nidx])
            elif isinstance(segment, QuadraticBezier):
                newsegment = offset_quad(segment, offset, linearize, interpolation)
                if newsegment is None or len(newsegment) == 0:
                    continue
                left_end = idx - 1 + len(newsegment)
                last_point += len(newsegment) - 1
                p._segments[idx] = newsegment[0]
                for nidx in range(len(newsegment) - 1, 0, -1):  # All but the first
                    p._segments.insert(idx + 1, newsegment[nidx])
            elif isinstance(segment, CubicBezier):
                newsegment = offset_cubic(segment, offset, linearize, interpolation)
                if newsegment is None or len(newsegment) == 0:
                    continue
                left_end = idx - 1 + len(newsegment)
                last_point += len(newsegment) - 1
                p._segments[idx] = newsegment[0]
                for nidx in range(len(newsegment) - 1, 0, -1):  # All but the first
                    p._segments.insert(idx + 1, newsegment[nidx])
            elif isinstance(segment, Line):
                newsegment = offset_line(segment, offset)
                if newsegment is None or len(newsegment) == 0:
                    continue
                left_end = idx - 1 + len(newsegment)
                last_point += len(newsegment) - 1
                p._segments[idx] = newsegment[0]
                for nidx in range(len(newsegment) - 1, 0, -1):  # All but the first
                    p._segments.insert(idx + 1, newsegment[nidx])
            stitched = stitch_segments_at_index(
                offset, p, left_end, helper1, radial=radial_connector
            )
            if last_point is not None:
                last_point += stitched
        if last_point is not None and first_point is not None and is_closed:
            seglen = p._segments[first_point].start.distance_to(
                p._segments[last_point].end
            )
            if seglen > MINIMAL_LEN:
                close_subpath(
                    radial_connector, p, first_point, last_point, offset, helper2
                )

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

    CutOpNode.offset_routine = offset_path

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
