"""
This is a giant list of console commands that deal with and often implement the elements system in the program.
"""

from math import cos, isinf, sin, sqrt, tau
from random import randint, shuffle

from meerk40t.core.units import Length

from .element_types import *


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "postboot":
        init_commands(kernel)


def dist(a, b):
    """
    Function to return the Euclidean distance between two points
    @param a:
    @param b:
    @return:
    """
    return sqrt(pow(a[0] - b[0], 2) + pow(a[1] - b[1], 2))


def is_inside(center, radius, p):
    """
    Function to check whether a point lies inside or on the boundaries of the circle
    @param center:
    @param radius:
    @param p:
    @return:
    """
    return dist(center, p) <= radius


# The following two functions are used
# To find the equation of the circle when
# three points are given.


def get_circle_center(bx, by, cx, cy):
    """
    Helper method to get a circle defined by 3 points
    @param bx:
    @param by:
    @param cx:
    @param cy:
    @return:
    """

    B = bx * bx + by * by
    C = cx * cx + cy * cy
    D = bx * cy - by * cx
    return [(cy * B - by * C) / (2 * D), (bx * C - cx * B) / (2 * D)]


def circle_from1(A, B):
    """
    Function to return the smallest circle that intersects 2 points
    @param A:
    @param B:
    @return:
    """
    # Set the center to be the midpoint of A and B
    C = [(A[0] + B[0]) / 2.0, (A[1] + B[1]) / 2.0]

    # Set the radius to be half the distance AB
    return C, dist(A, B) / 2.0


def circle_from2(A, B, C):
    """
    Function to return a unique circle that intersects three points
    @param A:
    @param B:
    @param C:
    @return:
    """
    if A == B:
        I, radius = circle_from1(A, C)
        return I, radius
    elif A == C:
        I, radius = circle_from1(A, B)
        return I, radius
    elif B == C:
        I, radius = circle_from1(A, B)
        return I, radius
    else:
        I = get_circle_center(B[0] - A[0], B[1] - A[1], C[0] - A[0], C[1] - A[1])
        I[0] += A[0]
        I[1] += A[1]
        radius = dist(I, A)
        return I, radius


def is_valid_circle(center, radius, P):
    """
    Function to check whether a circle encloses the given points

    @param center:
    @param radius:
    @param P:
    @return:
    """

    # Iterating through all the points
    # to check  whether the points
    # lie inside the circle or not
    for p in P:
        if not is_inside(center, radius, p):
            return False
    return True


def min_circle_trivial(P):
    """
    Function to return the minimum enclosing circle for N <= 3
    @param P:
    @return:
    """
    assert len(P) <= 3

    if not P:
        return [0, 0], 0

    elif len(P) == 1:
        return P[0], 0

    elif len(P) == 2:
        center, radius = circle_from1(P[0], P[1])
        return center, radius

    # To check if MEC can be determined
    # by 2 points only
    for i in range(3):
        for j in range(i + 1, 3):

            center, radius = circle_from1(P[i], P[j])
            if is_valid_circle(center, radius, P):
                return center, radius

    center, radius = circle_from2(P[0], P[1], P[2])
    return center, radius


def welzl_helper(P, R, n):
    """
    Returns the MEC using Welzl's algorithm takes a set of input points P and a set R points on the circle boundary.
    n represents the number of points in P that are not yet processed.

    @param P:
    @param R:
    @param n:
    @return:
    """
    # print (f"Welzl_helper. P={len(P)} pts, R={len(R)} pts, n={n}")
    # Base case when all points processed or |R| = 3
    if n <= 0 or len(R) == 3:
        center, radius = min_circle_trivial(R)
        return center, radius

    # Pick a random point randomly
    idx = randint(0, n - 1)
    p = P[idx]

    # Put the picked point at the end of P
    # since it's more efficient than
    # deleting from the middle of the vector
    P[idx], P[n - 1] = P[n - 1], P[idx]

    # Get the MEC circle d from the
    # set of points P - :p
    dcenter, dradius = welzl_helper(P, R.copy(), n - 1)

    # If d contains p, return d
    if is_inside(dcenter, dradius, p):
        return dcenter, dradius

    # Otherwise, must be on the boundary of the MEC
    R.append(p)

    # Return the MEC for P - :p and R U :p
    dcenter, dradius = welzl_helper(P, R.copy(), n - 1)
    return dcenter, dradius


def welzl(P):
    P_copy = P.copy()
    shuffle(P_copy)
    center, radius = welzl_helper(P_copy, [], len(P_copy))
    return center, radius


def generate_hull_shape_segment(data):
    pts = []
    for node in data:
        try:
            path = node.as_path()
        except AttributeError:
            path = None
        if path is not None:
            p = path.first_point
            pts.append(p)
            for segment in path:
                p = segment.end
                pts.append(p)
        else:
            bounds = node.bounds
            if bounds:
                pts.extend(
                    [
                        (bounds[0], bounds[1]),
                        (bounds[0], bounds[3]),
                        (bounds[2], bounds[1]),
                        (bounds[2], bounds[3]),
                        (bounds[0], bounds[1]),
                    ]
                )
    return pts


def generate_hull_shape_quick(data):
    if not data:
        return []
    min_val = [float("inf"), float("inf")]
    max_val = [-float("inf"), -float("inf")]
    for node in data:
        bounds = node.bounds
        if bounds:
            min_val[0] = min(min_val[0], bounds[0])
            min_val[1] = min(min_val[1], bounds[1])
            max_val[0] = max(max_val[0], bounds[2])
            max_val[1] = max(max_val[1], bounds[3])
    if isinf(min_val[0]):
        return []
    return [
        (min_val[0], min_val[1]),
        (max_val[0], min_val[1]),
        (max_val[0], max_val[1]),
        (min_val[0], max_val[1]),
        (min_val[0], min_val[1]),
    ]


def generate_hull_shape_hull(data):
    pts = []
    for node in data:
        try:
            path = node.as_path()
            p = path.first_point
            if p is None:
                return None
            pts.append(p)
            for segment in path:
                pts.append(segment.end)
            pts.append(p)
        except AttributeError:
            bounds = node.bounds
            if bounds:
                pts.extend(
                    [
                        (bounds[0], bounds[1]),
                        (bounds[0], bounds[3]),
                        (bounds[2], bounds[1]),
                        (bounds[2], bounds[3]),
                    ]
                )
    hull = list(Point.convex_hull(pts))
    if len(hull) != 0:
        hull.append(hull[0])  # loop
    return hull


def generate_hull_shape_complex(data, resolution=None):
    if resolution is None:
        resolution = 500  # How coarse / fine shall a subpath be split
    else:
        resolution = int(resolution)
    pts = []
    for node in data:
        try:
            path = node.as_path()

            from numpy import linspace

            for subpath in path.as_subpaths():
                psp = Path(subpath)
                p = psp.first_point
                pts.append(p)
                positions = linspace(0, 1, num=resolution, endpoint=True)
                subj = psp.npoint(positions)
                s = list(map(Point, subj))
                pts.extend(s)
        except AttributeError:
            bounds = node.bounds
            if bounds:
                pts.extend(
                    [
                        (bounds[0], bounds[1]),
                        (bounds[0], bounds[3]),
                        (bounds[2], bounds[1]),
                        (bounds[2], bounds[3]),
                    ]
                )
    hull = list(Point.convex_hull(pts))
    if len(hull) != 0:
        hull.append(hull[0])  # loop
    return hull


def generate_hull_shape_circle_data(data):
    pts = []
    for node in data:
        try:
            path = node.as_path()
        except AttributeError:
            path = None
        if path is not None:
            p = path.first_point
            pts += [p]
            for segment in path:
                p = segment.end
                pts += [p]
        else:
            bounds = node.bounds
            if bounds:
                pts += [
                    (bounds[0], bounds[1]),
                    (bounds[0], bounds[3]),
                    (bounds[2], bounds[1]),
                    (bounds[2], bounds[3]),
                ]
    # We could directly call welzl, but for a significant
    # amount of point this will cause a huge amount
    # of recursive calls (which will fail)
    # -> so we apply it to the hull points
    hull = list(Point.convex_hull(pts))
    mec_center, mec_radius = welzl(hull)

    # So now we have a circle with (mec[0], mec[1]), and mec_radius
    return mec_center, mec_radius


def generate_hull_shape_circle(data):
    mec_center, mec_radius = generate_hull_shape_circle_data(data)

    # So now we have a circle with (mec[0], mec[1]), and mec_radius
    hull = []
    RES = 100
    for i in range(RES):
        hull += [
            (
                mec_center[0] + mec_radius * cos(i / RES * tau),
                mec_center[1] + mec_radius * sin(i / RES * tau),
            )
        ]
    if len(hull) != 0:
        hull.append(hull[0])  # loop
    return hull


def init_commands(kernel):
    self = kernel.elements

    _ = kernel.translation

    choices = [
        {
            "attr": "trace_start_method",
            "object": self,
            "default": 0,
            "type": int,
            "label": _("Delay hull trace"),
            "tip": _("Establish if and how an element hull trace should wait"),
            "page": "Laser",
            "section": "General",
            "style": "option",
            "display": (_("Immediate"), _("User confirmation"), _("Delay 5 seconds")),
            "choices": (0, 1, 2),
        },
    ]
    kernel.register_choices("preferences", choices)

    classify_new = self.post_classify

    # ==========
    # TRACE OPERATIONS
    # ==========

    @self.console_argument(
        "method",
        help=_("Method to use (one of quick, hull, complex, segment, circle)"),
    )
    @self.console_argument("resolution")
    @self.console_option(
        "start",
        "s",
        type=int,
        help=_("0=immediate, 1=User interaction, 2=wait for 5 seconds"),
    )
    @self.console_command(
        "trace",
        help=_("trace the given elements"),
        input_type=("elements", "shapes", None),
    )
    def trace_trace_spooler(
        command,
        channel,
        _,
        method=None,
        resolution=None,
        start=None,
        data=None,
        **kwargs,
    ):
        if method is None:
            method = "quick"
        method = method.lower()
        if method not in ("segment", "quick", "hull", "complex", "circle"):
            channel(
                _(
                    "Invalid method, please use one of quick, hull, complex, segment, circle."
                )
            )
            return

        spooler = self.device.spooler
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No elements bounds to trace"))
            return
        if method == "segment":
            hull = generate_hull_shape_segment(data)
        elif method == "quick":
            hull = generate_hull_shape_quick(data)
        elif method == "hull":
            hull = generate_hull_shape_hull(data)
        elif method == "complex":
            hull = generate_hull_shape_complex(data, resolution)
        elif method == "circle":
            hull = generate_hull_shape_circle(data)
        else:
            raise ValueError
        if start is None:
            # Lets take system default
            start = self.trace_start_method
        if start < 0 or start > 2:
            start = 0
        if hull is None or len(hull) == 0:
            channel(_("No elements bounds to trace."))
            return

        def run_shape(_spooler, startmethod, _hull):
            def trace_hull(startmethod=0):
                if startmethod == 0:
                    # Immediately
                    pass
                elif startmethod == 1:
                    # Dialog
                    yield ("console", 'interrupt "Trace is about to start"')
                elif startmethod == 2:
                    # Wait for some seconds
                    yield ("wait", 5000)

                yield "wait_finish"
                yield "rapid_mode"
                idx = 0
                for p in _hull:
                    idx += 1
                    yield (
                        "move_abs",
                        Length(amount=p[0]).length_mm,
                        Length(amount=p[1]).length_mm,
                    )

            _spooler.laserjob(
                list(trace_hull(startmethod)), label=f"Trace Job: {method}", helper=True
            )

        run_shape(spooler, start, hull)

    @self.console_argument(
        "method",
        help=_("Method to use (one of quick, hull, complex, segment, circle)"),
    )
    @self.console_argument(
        "resolution", help=_("Resolution for complex slicing, default=500")
    )
    @self.console_command(
        "tracegen",
        help=_("create the trace around the given elements"),
        input_type=("elements", "shapes", None),
        output_type="elements",
    )
    def trace_trace_generator(
        command,
        channel,
        _,
        method=None,
        resolution=None,
        data=None,
        post=None,
        **kwargs,
    ):
        if method is None:
            method = "quick"
        method = method.lower()
        if not method in ("segment", "quick", "hull", "complex", "circle"):
            channel(
                _(
                    "Invalid method, please use one of quick, hull, complex, segment, circle."
                )
            )
            return

        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No elements bounds to trace"))
            return
        shape_type = "elem polyline"
        if method == "segment":
            hull = generate_hull_shape_segment(data)
        elif method == "quick":
            hull = generate_hull_shape_quick(data)
        elif method == "hull":
            hull = generate_hull_shape_hull(data)
        elif method == "complex":
            hull = generate_hull_shape_complex(data, resolution)
        elif method == "circle":
            shape_type = "elem ellipse"
            s_center, s_radius = generate_hull_shape_circle_data(data)
        else:
            raise ValueError
        if shape_type == "elem polyline":

            if len(hull) == 0:
                channel(_("No elements bounds to trace."))
                return
            shape = Polyline(hull)
            if shape.is_degenerate():
                channel(_("Shape is degenerate."))
                return "elements", data
        elif shape_type == "elem ellipse":
            shape = Circle(cx=s_center[0], cy=s_center[1], rx=s_radius, ry=s_radius)
            if shape.is_degenerate():
                channel(_("Shape is degenerate."))
                return "elements", data
        node = self.elem_branch.add(shape=shape, type=shape_type)
        node.stroke = self.default_stroke
        node.stroke_width = self.default_strokewidth
        node.fill = self.default_fill
        node.altered()
        self.set_emphasis([node])
        node.focus()
        data.append(node)
        # Newly created! Classification needed?
        post.append(classify_new(data))
        return "elements", data

    # --------------------------- END COMMANDS ------------------------------
