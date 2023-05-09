"""
This adds console commands that deal with the creation of an offset
"""
from copy import copy
from math import atan2, sqrt, tau

from meerk40t.core.node.node import Linejoin
from meerk40t.core.units import UNITS_PER_PIXEL, Length
from meerk40t.svgelements import (
    Arc,
    Close,
    CubicBezier,
    Line,
    Matrix,
    Move,
    Path,
    Point,
    QuadraticBezier,
    Rect,
)

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
generating a new offseted segement
c) Finally it stitches those segments together, treating for the simplifaction
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




def is_clockwise(path):
    def poly_clockwise(poly):
        """
        returns True if the polygon is clockwise ordered, false if not
        """

        total = poly[-1].x * poly[0].y - poly[0].x * poly[-1].y  # last point to first point
        for i in range(len(poly) - 1):
            total += poly[i].x * poly[i + 1].y - poly[i + 1].x * poly[i].y

        if total <= 0:
            return True
        else:
            return False

    poly = []
    for seg in path._segments:
        if isinstance(seg, (Arc, Line, QuadraticBezier, CubicBezier)):
            if len(poly) == 0:
                poly.append(seg.start)
            poly.append(seg.end)
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
                        # Combine segments, ie get rid of mid point
                        this_slope = last_slope
                        appendit = False
                last_slope = this_slope

        if appendit or not reduce:
            s.append(np)
        else:
            s[-1] = np
        t += delta
        lastpt = np
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
            angle = centerpt.angle_to(segment.start),
            distance = centerpt.distance_to(segment.start) + offset,
        )
        endpt = centerpt.polar_to(
            angle = centerpt.angle_to(segment.end),
            distance = centerpt.distance_to(segment.end) + offset,
        )
        newseg = Arc(
                 startpt, endpt, centerpt,
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
        control1=segment.control,
        control2=segment.control,
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

        Beware, this has limitations! Its not dealing well with curves that have cusps
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
        # They dont have an interference
        return None, None, None

    s = 1 / deter * (d * (w.x - x.x) + -b * (w.y - x.y))
    t = 1 / deter * (-c * (w.x - x.x) + a * (w.y - x.y))
    p1 = w + t * (z - w)
    p2 = x + s * (y - x)
    # print (f"p1 = ({p1.x:.3f}, {p1.y:.3f})")
    # print (f"p2 = ({p2.x:.3f}, {p2.y:.3f})")
    p = p1
    return p, s, t


def offset_path(
    path, offset_value=0, radial_connector=False, linearize=True, interpolation=500
):
    def stitch_segments_at_index(
        stitchpath, index, orgintersect, radial=False, closed=False
    ):
        # Stitch the two segments index and index+1 together
        seg1 = stitchpath._segments[index]
        lp = len(stitchpath)
        idx2 = index + 1
        if idx2 >= lp:
            if not closed:
                return
            # Look for the first segment
            idx2 = idx2 % lp
            while not isinstance(
                stitchpath._segments[idx2], (Arc, Line, QuadraticBezier, CubicBezier)
            ):
                idx2 += 1
        seg2 = stitchpath._segments[idx2]

        # print (f"Stitch {index}: {type(seg1).__name__}, {idx2}: {type(seg2).__name__}")
        needs_connector = False
        if isinstance(seg1, Close):
            # Close will be dealt with differently...
            return
        elif isinstance(seg1, Move):
            seg1.end = Point(seg2.start)
        elif isinstance(seg1, Line):
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
                    if 0 <= s <= 1 and 0 <= t <= 1:
                        # We shorten the segments accordingly.
                        seg1.end = Point(p)
                        seg2.start = Point(p)
                        if idx2 > 0 and isinstance(
                            stitchpath._segments[idx2 - 1], Move
                        ):
                            stitchpath._segments[idx2 - 1].end = Point(p)
                        needs_connector = False
                        # print ("Used interal intersect")
                    else:
                        if not radial:
                            seg1.end = Point(p)
                            seg2.start = Point(p)
                            if idx2 > 0 and isinstance(
                                stitchpath._segments[idx2 - 1], Move
                            ):
                                stitchpath._segments[idx2 - 1].end = Point(p)
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

        if needs_connector and seg1.end != seg1.start:
            if radial:
                # print ("Inserted an arc")
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
            else:
                # print ("Inserted a Line")
                connect_seg = Line(Point(seg1.end), Point(seg2.start))
            stitchpath._segments.insert(index + 1, connect_seg)
        elif needs_connector:
            # print ("Need connector but end points were identical")
            pass
        else:
            # print ("No connector needed")
            pass

    results = []
    # This needs to be a continuous path
    for subpath in path.as_subpaths():
        p = Path(subpath)
        p.approximate_arcs_with_cubics()
        offset = offset_value
        # # No offset bigger than half the path size, otherwise stuff will get crazy
        # if offset > 0:
        #     bb = p.bbox()
        #     offset = min(offset, bb[2] - bb[0])
        #     offset = min(offset, bb[3] - bb[1])
        is_closed = False
        remember = False
        remember_helper = None
        # Lets check the first and last valid point. If they are identical
        # we consider this to be a closed path even if it has no closed indicator.
        firstp_start = None
        firstp_end = None
        lastp = None
        idx = 0
        while (idx < len(p)) and not isinstance(
            p._segments[idx], (Arc, Line, QuadraticBezier, CubicBezier)
        ):
            idx += 1
        firstp_start = Point(p._segments[idx].start)
        firstp_end = Point(p._segments[idx].end)
        idx = len(p._segments) - 1
        while idx >= 0 and not isinstance(
            p._segments[idx], (Arc, Line, QuadraticBezier, CubicBezier)
        ):
            idx -= 1
        lastp = Point(p._segments[idx].end)
        if firstp_start == lastp:
            remember = True
            remember_helper = Point(lastp)
        # We need to establish if this is a closed path and if the first segment goes counterclockwise
        if not is_closed:
            for idx in range(len(p._segments) - 1, -1, -1):
                if isinstance(p._segments[idx], Close):
                    is_closed = True
                    break
        if is_closed:
            if is_clockwise(p):
                offset = -1 * offset

        for idx in range(len(p._segments) - 1, -1, -1):
            segment = p._segments[idx]
            if isinstance(segment, Close):
                remember = True
                # Lets add an additional line and replace the closed segment by this new segment
                idx1 = idx
                while (idx1 >= 0) and not isinstance(
                    p._segments[idx1], (Arc, Line, QuadraticBezier, CubicBezier)
                ):
                    idx1 -= 1
                idx2 = 0
                while (idx2 < len(p)) and not isinstance(
                    p._segments[idx2], (Arc, Line, QuadraticBezier, CubicBezier)
                ):
                    idx2 += 1
                segment = Line(
                    Point(p._segments[idx1].end), Point(p._segments[idx2].start)
                )
                p._segments[idx] = segment
                remember_helper = Point(p._segments[idx2].start)

            helper = Point(p._segments[idx].end)
            idxend = idx
            if isinstance(segment, Arc):
                print(f"{idx}/{len(p._segments)}: Arc")
                newsegment = offset_arc(segment, offset, linearize, interpolation)
                idxend = idx - 1 + len(newsegment)
                p._segments[idx] = newsegment[0]
                for nidx in range(len(newsegment) - 1, 0, -1):  # All but the first
                    p._segments.insert(idx + 1, newsegment[nidx])
            elif isinstance(segment, QuadraticBezier):
                newsegment = offset_quad(segment, offset, linearize, interpolation)
                idxend = idx - 1 + len(newsegment)
                p._segments[idx] = newsegment[0]
                for nidx in range(len(newsegment) - 1, 0, -1):  # All but the first
                    p._segments.insert(idx + 1, newsegment[nidx])
            elif isinstance(segment, CubicBezier):
                newsegment = offset_cubic(segment, offset, linearize, interpolation)
                idxend = idx - 1 + len(newsegment)
                p._segments[idx] = newsegment[0]
                for nidx in range(len(newsegment) - 1, 0, -1):  # All but the first
                    p._segments.insert(idx + 1, newsegment[nidx])
            elif isinstance(segment, Line):
                newsegment = offset_line(segment, offset)
                idxend = idx - 1 + len(newsegment)
                p._segments[idx] = newsegment[0]
                for nidx in range(len(newsegment) - 1, 0, -1):  # All but the first
                    p._segments.insert(idx + 1, newsegment[nidx])
            stitch_segments_at_index(p, idxend, helper, radial=radial_connector)
        if remember:
            helper = remember_helper
            stitch_segments_at_index(
                p, len(p._segments) - 1, helper, radial=radial_connector, closed=True
            )
        results.append(p)

    if len(results) == 0:
        # Strange, should never happen
        return path
    result = results[0]
    for idx in range(1, len(results)):
        result += results[idx]
    return result


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "postboot":
        init_commands(kernel)


def init_commands(kernel):
    self = kernel.elements

    _ = kernel.translation

    classify_new = self.post_classify

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
        "offset",
        help=_("create an offset path for any of the given elements"),
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
        import numpy as np

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
                bb = node.bounds()
                r = Rect(x=bb[0], y=bb[1], width=bb[2] - bb[0], height=bb[3] - bb[1])
                p = Path(r)

            node_path = offset_path(
                p,
                offset,
                radial_connector=radial,
                linearize=linearize,
                interpolation=interpolation,
            )
            node_path.validate_connections()
            newnode = self.elem_branch.add(
                path=node_path, type="elem path", stroke=node.stroke
            )
            newnode.stroke_width = UNITS_PER_PIXEL
            newnode.linejoin = Linejoin.JOIN_ROUND
            newnode.label = f"Offset of {node.id if node.label is None else node.label}"
            data_out.append(newnode)

        # Newly created! Classification needed?
        if len(data_out) > 0:
            post.append(classify_new(data_out))
            self.signal("refresh_scene", "Scene")
        return "elements", data_out

    # --------------------------- END COMMANDS ------------------------------
