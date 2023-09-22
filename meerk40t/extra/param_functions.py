"""
This module exposes a couple of routines to create shapes,
that have additional functional parameters set to allow
parametric editing
"""
import math

from meerk40t.core.units import Length
from meerk40t.kernel import CommandSyntaxError
from meerk40t.svgelements import Angle, Point, Polygon
from meerk40t.tools.geomstr import Geomstr


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation
        context = kernel.root
        self = context.elements
        classify_new = self.post_classify

        def getit(param, idx, default):
            if idx >= len(param):
                return default
            return param[idx]

        def create_copied_grid(start_pt, node, cols, rows, sdx, sdy):
            # print(
            #     f"Create a {cols}x{rows} grid, gap={sdx:.0f} x {sdy:.0f} at ({start_pt.x:.0f}, {start_pt.y:.0f})..."
            # )
            geom = Geomstr()
            try:
                orggeom = node.as_geometry()
                bb = orggeom.bbox()
                width = bb[2] - bb[0]
                height = bb[3] - bb[1]
            except AttributeError:
                return geom
            x = start_pt.x
            for scol in range(cols):
                y = start_pt.y
                for srow in range(rows):
                    tempgeom = Geomstr(orggeom)
                    dx = x - bb[0]
                    dy = y - bb[1]
                    # print(f"{scol}x{srow}: translate by {dx:.0f}x{dy:.0f}")
                    tempgeom.translate(dx, dy)
                    geom.append(tempgeom)
                    y += sdy + height
                x += sdx + width
            return geom

        @self.console_argument("sx", type=Length)
        @self.console_argument("sy", type=Length)
        @self.console_argument("cols", type=int)
        @self.console_argument("rows", type=int)
        @self.console_argument("id", type=str)
        @self.console_option("dx", "x", type=Length, help=_("Horizontal delta"))
        @self.console_option("dy", "y", type=Length, help=_("Vertical delta"))
        @context.console_command("pgrid", help=_("pgrid sx, sy, cols, rows, id"))
        def param_grid(
            command,
            channel,
            _,
            sx=None,
            sy=None,
            cols=None,
            rows=None,
            id=None,
            dx=None,
            dy=None,
            post=None,
            **kwargs,
        ):
            try:
                if sx is None:
                    sx = Length("0cm")
                ssx = float(sx)
                if sy is None:
                    sy = Length("0cm")
                ssy = float(sy)
                if cols is None:
                    cols = 2
                if rows is None:
                    rows = 2
                if dx is None:
                    dx = Length("0mm")
                sdx = float(dx)
                if dy is None:
                    dy = Length("0mm")
                sdy = float(dy)
            except ValueError:
                channel("Invalid data provided")
                return
            self.validate_ids()
            found_node = None
            if id is not None:
                # We look for such a node, both in elements and regmarks.
                for node in self.elems():
                    if node.id == id and hasattr(node, "as_geometry"):
                        found_node = node
                        break
                if found_node is None:
                    for node in self.regmarks():
                        if node.id == id and hasattr(node, "as_geometry"):
                            found_node = node
                            break
            if found_node is None:
                # We try the first selected element
                for node in self.elems(emphasized=True):
                    if hasattr(node, "as_geometry"):
                        id = node.id
                        found_node = node
                        break
            if found_node is None:
                channel("No matching element found.")
            start_pt = Point(ssx, ssy)
            geom = create_copied_grid(start_pt, found_node, cols, rows, sdx, sdy)
            node = self.elem_branch.add(type="elem path", geometry=geom)
            bb = geom.bbox()
            width = bb[2] - bb[0]
            height = bb[3] - bb[1]
            node.stroke = self.default_stroke
            node.stroke_width = self.default_strokewidth
            node.altered()
            node.functional_parameter = (
                "grid",
                3,
                id,
                0,
                start_pt.x + sdx,
                start_pt.y,
                0,
                start_pt.x + width,
                start_pt.y + sdy,
                1,
                cols,
                1,
                rows,
            )
            # Newly created! Classification needed?
            data = [node]
            post.append(classify_new(data))
            return "elements", data

        def update_node_grid(node):

            my_id = "grid"
            valid = True
            try:
                param = node.functional_parameter
                if param is None or param[0] != my_id:
                    valid = False
            except (AttributeError, IndexError):
                valid = False
            if not valid:
                # Not for me...
                return
            nodeid = getit(param, 2, None)
            if nodeid is None:
                return
            found_node = None
            for e in self.elems():
                if e.id == nodeid and hasattr(e, "as_geometry"):
                    found_node = e
                    break
            if found_node is None:
                for e in self.regmarks():
                    if e.id == nodeid and hasattr(e, "as_geometry"):
                        found_node = e
                        break
            if found_node is None:
                return
            bb = node.as_geometry().bbox()
            start_pt = Point(bb[0], bb[1])
            sdx = getit(param, 4, bb[0])
            sdx = sdx - bb[0]
            sdy = getit(param, 8, bb[3])
            sdy = sdy - bb[1]
            cols = getit(param, 10, 1)
            rows = getit(param, 12, 1)
            geom = create_copied_grid(start_pt, found_node, cols, rows, sdx, sdy)
            node.geometry = geom
            bb = node.as_geometry().bbox()
            node.functional_parameter = (
                "grid",
                3,
                nodeid,
                0,
                bb[0] + sdx,
                bb[1],
                0,
                bb[2],
                bb[1] + sdy,
                1,
                cols,
                1,
                rows,
            )
            node.altered()

        # --- Fractal Tree
        def create_fractal_tree(first_pt, second_pt, iterations, ratio):
            def tree_fractal(geom, startpt, endpt, depth, ratio):
                #
                # create a line from startpt to endpt and add it to the geometry
                if depth < 0:
                    return
                angle = startpt.angle_to(endpt)
                dist = startpt.distance_to(endpt)
                delta = math.tau / 8
                # print(
                #     f"{depth}: ({startpt.x:.0f}, {startpt.y:.0f}) - ({endpt.x:.0f}, {endpt.y:.0f}) : {dist:.0f}"
                # )
                geom.line(complex(startpt.x, startpt.y), complex(endpt.x, endpt.y))
                newstart = Point(endpt)
                newend = Point.polar(endpt, angle - delta, dist * ratio)
                tree_fractal(geom, newstart, newend, depth - 1, ratio)
                newend = Point.polar(endpt, angle + delta, dist * ratio)
                tree_fractal(geom, newstart, newend, depth - 1, ratio)

            geometry = Geomstr()
            # print("create fractal", first_pt, second_pt)
            tree_fractal(geometry, first_pt, second_pt, iterations, ratio)
            return geometry

        @self.console_argument("sx", type=Length)
        @self.console_argument("sy", type=Length)
        @self.console_argument("branch", type=Length)
        @self.console_argument("iterations", type=int)
        @context.console_command(
            "fractal_tree", help=_("fractal_tree sx, sy, branch, iterations")
        )
        def fractal_tree(
            command,
            channel,
            _,
            sx=None,
            sy=None,
            branch=None,
            iterations=None,
            data=None,
            post=None,
            **kwargs,
        ):
            ratio = 0.75
            try:
                if sx is None:
                    sx = Length("5cm")
                ssx = float(sx)
                if sy is None:
                    sy = Length("5cm")
                ssy = float(sy)
                if branch is None:
                    branch = Length("4cm")
                blen = float(branch)
                if iterations is None:
                    iterations = 10
                iterations = int(iterations)
            except ValueError:
                channel("Invalid data provided")
                return
            start_pt = Point(ssx, ssy)
            end_pt = Point.polar(start_pt, 0, blen)
            geom = create_fractal_tree(start_pt, end_pt, iterations, ratio)
            node = self.elem_branch.add(type="elem path", geometry=geom)
            node.stroke = self.default_stroke
            node.stroke_width = self.default_strokewidth
            node.altered()
            node.functional_parameter = (
                "fractaltree",
                0,
                start_pt.x,
                start_pt.y,
                0,
                end_pt.x,
                end_pt.y,
                1,
                iterations,
                2,
                ratio,
            )
            # Newly created! Classification needed?
            data = [node]
            post.append(classify_new(data))
            return "elements", data

        # --- Routines to update shapes according to saved and updated parameters.

        def update_node_fractaltree(node):
            my_id = "fractaltree"
            point_a = None
            point_b = None
            iterations = 5
            ratio = 0.75
            valid = True
            try:
                param = node.functional_parameter
                if param is None or param[0] != my_id:
                    valid = False
            except (AttributeError, IndexError):
                valid = False
            if not valid:
                # Not for me...
                return
            try:
                if param[1] == 0:
                    point_a = Point(param[2], param[3])
                if param[4] == 0:
                    point_b = Point(param[5], param[6])
                if param[7] == 1:
                    iterations = param[8]
                if param[9] == 2:
                    ratio = param[10]
            except IndexError:
                valid = False
            if point_a is None or point_b is None:
                valid = False
            if valid:
                geom = create_fractal_tree(point_a, point_b, iterations, ratio)
                node.geometry = geom
                node.altered()

        # --- Start like shapes
        def create_star_shape(
            cx,
            cy,
            corners,
            startangle,
            radius,
            radius_inner,
            alternate_seq,
            density,
        ):
            geom = Geomstr()
            if corners <= 2:
                # No need to look at side_length parameter as we are considering the radius value as an edge anyway...
                if startangle is None:
                    startangle = Angle.parse("0deg")

                if corners == 1:
                    geom.point(cx + 1j * cy)
                if corners == 2:
                    x = cx + math.cos(startangle.as_radians) * radius
                    y = cy + math.sin(startangle.as_radians) * radius
                    geom.line(cx + 1j * cy, x + 1j * y)
            else:
                i_angle = startangle.as_radians
                delta_angle = math.tau / corners
                ct = 0
                pts = []
                for j in range(corners):
                    if ct < alternate_seq:
                        r = radius
                    #    dbg = "outer"
                    else:
                        r = radius_inner
                    #    dbg = "inner"
                    thisx = cx + r * math.cos(i_angle)
                    thisy = cy + r * math.sin(i_angle)
                    # print(
                    #    "pt %d, Angle=%.1f: %s radius=%.1f: (%.1f, %.1f)"
                    #    % (j, i_angle / math.pi * 180, dbg, r, thisx, thisy)
                    # )
                    ct += 1
                    if ct >= 2 * alternate_seq:
                        ct = 0
                    if j == 0:
                        firstx = thisx
                        firsty = thisy
                    i_angle += delta_angle
                    thispt = thisx + 1j * thisy
                    pts.append(thispt)
                # Close the path
                thispt = firstx + 1j * firsty
                pts.append(thispt)

                if len(pts) > 0:

                    star_points = [pts[0]]
                    idx = density
                    hitted = []
                    while idx != 0:
                        if idx in hitted:
                            break
                        hitted.append(idx)
                        star_points.append(pts[idx])
                        idx += density
                        if idx >= corners:
                            idx -= corners
                    for idx in range(1, len(star_points)):
                        geom.line(star_points[idx - 1], star_points[idx])
                    geom.line(star_points[-1], star_points[0])
            # print(f"Created geometry from {len(pts) / 2} pts: {geom.capacity}")
            return geom

        # Shape (ie star) routine
        @self.console_argument(
            "corners", type=int, help=_("Number of corners/vertices")
        )
        @self.console_argument(
            "cx", type=self.length_x, help=_("X-Value of polygon's center")
        )
        @self.console_argument(
            "cy", type=self.length_y, help=_("Y-Value of polygon's center")
        )
        @self.console_argument(
            "radius",
            type=self.length_x,
            help=_("Radius (length of side if --side_length is used)"),
        )
        @self.console_option("startangle", "s", type=Angle.parse, help=_("Start-Angle"))
        @self.console_option(
            "inscribed",
            "i",
            type=bool,
            action="store_true",
            help=_("Shall the polygon touch the inscribing circle?"),
        )
        @self.console_option(
            "side_length",
            "l",
            type=bool,
            action="store_true",
            help=_(
                "Do you want to treat the length value for radius as the length of one edge instead?"
            ),
        )
        @self.console_option(
            "radius_inner",
            "r",
            type=str,
            help=_("Alternating radius for every other vertex"),
        )
        @self.console_option(
            "alternate_seq",
            "a",
            type=int,
            help=_(
                "Length of alternating sequence (1 for starlike figures, >=2 for more gear-like patterns)"
            ),
        )
        @self.console_option(
            "density", "d", type=int, help=_("Amount of vertices to skip")
        )
        @self.console_command(
            "shape",
            help=_(
                "shape <corners> <x> <y> <r> <startangle> <inscribed> or shape <corners> <r>"
            ),
            input_type=("elements", None),
            output_type="elements",
        )
        def element_shape(
            command,
            channel,
            _,
            corners,
            cx,
            cy,
            radius,
            startangle=None,
            inscribed=None,
            side_length=None,
            radius_inner=None,
            alternate_seq=None,
            density=None,
            data=None,
            post=None,
            **kwargs,
        ):
            if corners is None:
                raise CommandSyntaxError

            if cx is None:
                if corners <= 2:
                    raise CommandSyntaxError(
                        _(
                            "Please provide at least one additional value (which will act as radius then)"
                        )
                    )
                cx = 0
            if cy is None:
                cy = 0
            if radius is None:
                radius = 0
            if corners <= 2:
                # No need to look at side_length parameter as we are considering the radius value as an edge anyway...
                geom = create_star_shape(
                    cx,
                    cy,
                    corners,
                    startangle,
                    radius,
                    radius_inner,
                    alternate_seq,
                    density,
                )
            else:
                # do we have something like 'shape 3 4cm' ? If yes, reassign the parameters
                if radius is None:
                    radius = cx
                    cx = 0
                    cy = 0
                if startangle is None:
                    startangle = Angle.parse("0deg")

                if alternate_seq is None:
                    if radius_inner is None:
                        alternate_seq = 0
                    else:
                        alternate_seq = 1

                if density is None:
                    density = 1
                if density < 1 or density > corners:
                    density = 1

                # Do we have to consider the radius value as the length of one corner?
                if side_length is not None:
                    # Let's recalculate the radius then...
                    # d_oc = s * csc( math.pi / n)
                    radius = 0.5 * radius / math.sin(math.pi / corners)

                if radius_inner is None:
                    radius_inner = radius
                else:
                    try:
                        radius_inner = float(
                            Length(radius_inner, relative_length=radius)
                        )
                    except ValueError:
                        raise CommandSyntaxError

                if inscribed:
                    if side_length is None:
                        radius = radius / math.cos(math.pi / corners)
                    else:
                        channel(
                            _(
                                "You have as well provided the --side_length parameter, this takes precedence, so --inscribed is ignored"
                            )
                        )

                if alternate_seq < 1:
                    radius_inner = radius

                # print(
                #   "Your parameters are:\n cx=%.1f, cy=%.1f\n radius=%.1f, inner=%.1f\n corners=%d, density=%d\n seq=%d, angle=%.1f"
                #   % (cx, cy, radius, radius_inner, corners, density, alternate_seq, startangle)
                # )
                geom = create_star_shape(
                    cx,
                    cy,
                    corners,
                    startangle,
                    radius,
                    radius_inner,
                    alternate_seq,
                    density,
                )
                pts = list(geom.as_points())
                if len(pts) < corners:
                    ct = 0
                    possible_combinations = ""
                    for i in range(corners - 1):
                        j = i + 2
                        if math.gcd(j, corners) == 1:
                            if ct % 3 == 0:
                                possible_combinations += (
                                    f"\n shape {corners} ... -d {j}"
                                )
                            else:
                                possible_combinations += (
                                    f", shape {corners} ... -d {j} "
                                )
                            ct += 1
                    channel(_("Just for info: we have missed a couple of vertices..."))
                    channel(
                        _(
                            "To hit all, the density parameters should be e.g. {combinations}"
                        ).format(combinations=possible_combinations)
                    )

            node = self.elem_branch.add(type="elem path", geometry=geom)
            node.stroke = self.default_stroke
            node.stroke_width = self.default_strokewidth
            node.fill = self.default_fill
            node.altered()
            node.emphasized = True
            node.focus()

            data = [node]
            # Newly created! Classification needed?
            post.append(classify_new(data))

            center = Point(cx, cy)
            opposing_angle = startangle + math.tau / 2
            while opposing_angle < 0:
                opposing_angle += math.tau
            while opposing_angle >= math.tau:
                opposing_angle -= math.tau
            first_point = Point.polar(center, startangle, radius)
            second_point = Point.polar(center, opposing_angle, radius_inner)
            node.functional_parameter = (
                "star",
                0,
                cx,
                cy,
                0,
                first_point.x,
                first_point.y,
                0,
                second_point.x,
                second_point.y,
                1,
                corners,
                1,
                alternate_seq,
                1,
                density,
            )

            return "elements", data

        # --- end of node update routines
        def update_node_star_shape(node):
            my_id = "star"
            valid = True
            try:
                param = node.functional_parameter
                if param is None or param[0] != my_id:
                    valid = False
            except (AttributeError, IndexError):
                valid = False
            if not valid:
                # Not for me...
                return
            param = node.functional_parameter
            if param is None:
                return
            cx = getit(param, 2, 0)
            cy = getit(param, 3, 0)
            p1x = getit(param, 5, 0)
            p1y = getit(param, 6, 0)
            p2x = getit(param, 8, 0)
            p2y = getit(param, 9, 0)
            corners = getit(param, 11, 3)
            alternate_seq = getit(param, 13, 0)
            density = getit(param, 15, 1)
            if density < 1 or density > corners:
                density = 1
            center = Point(cx, cy)
            pt1 = Point(p1x, p1y)
            pt2 = Point(p2x, p2y)
            startangle = center.angle_to(pt1)
            radius = center.distance_to(pt1)
            radius_inner = center.distance_to(pt2)
            if radius == 0:
                valid = False
            if corners <= 0:
                valid = False
            if alternate_seq < 0:
                valid = False
            if valid:
                geom = create_star_shape(
                    cx,
                    cy,
                    corners,
                    startangle,
                    radius,
                    radius_inner,
                    alternate_seq,
                    density,
                )
                node.geometry = geom
                node.altered()
                center = Point(cx, cy)
                opposing_angle = startangle + math.tau / 2
                while opposing_angle < 0:
                    opposing_angle += math.tau
                while opposing_angle >= math.tau:
                    opposing_angle -= math.tau
                first_point = Point.polar(center, startangle, radius)
                second_point = Point.polar(center, opposing_angle, radius_inner)
                node.functional_parameter = (
                    "star",
                    0,
                    cx,
                    cy,
                    0,
                    first_point.x,
                    first_point.y,
                    0,
                    second_point.x,
                    second_point.y,
                    1,
                    corners,
                    1,
                    alternate_seq,
                    1,
                    density,
                )

        # Let's register them
        info = (
            update_node_grid,
            {
                "0": ("ID",),
                "1": ("Horizontal gap",),
                "2": ("Vertical gap",),
                "3": ("Columns", 1, 25),
                "4": ("Rows", 1, 25),
            },
        )
        kernel.register("element_update/grid", info)

        info = (
            update_node_fractaltree,
            {
                "0": ("Startpoint",),
                "1": ("End of base stem",),
                "2": ("Iterations", 2, 13),
                "3": ("Branch length",),
            },
        )
        kernel.register("element_update/fractaltree", info)
        max_corner_gui = 50
        info = (
            update_node_star_shape,
            {
                "0": ("Center",),
                "1": ("Outer radius",),
                "2": ("Inner radius",),
                "3": ("Corners", 3, max_corner_gui),
                "4": ("Alternation", 0, 10),
                "5": ("Density", 1, max_corner_gui - 1),
            },
        )
        kernel.register("element_update/star", info)

        info = (
            None,  # Let the node deal with it
            {
                "0": ("Rounded corner",),
            },
        )
        kernel.register("element_update/rect", info)
