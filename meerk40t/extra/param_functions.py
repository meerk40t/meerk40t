"""
This module exposes a couple of routines to create shapes,
that have additional functional parameters set to allow
parametric editing
"""
import math

from meerk40t.core.units import Angle, Length
from meerk40t.kernel import CommandSyntaxError
from meerk40t.svgelements import Point
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
                if isinstance(node, Geomstr):
                    # That may be the case if we have lost the connection to the original node.
                    # In that case we are getting passed the first geometry subpath to reuse
                    orggeom = node
                else:
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
            clone=None,
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
            # height = bb[3] - bb[1]
            if hasattr(found_node, "stroke"):
                node.stroke = found_node.stroke
            else:
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
            node.emphasized = True
            post.append(classify_new(data))
            return "elements", data

        def update_node_grid(node):
            my_id = "grid"
            try:
                param = node.functional_parameter
                if param is None or param[0] != my_id:
                    return
            except (AttributeError, IndexError):
                return
            node_id = getit(param, 2, None)
            if node_id is None:
                return
            found_node = None
            for e in self.elems():
                if e.id == node_id and hasattr(e, "as_geometry"):
                    found_node = e
                    break
            if found_node is None:
                for e in self.regmarks():
                    if e.id == node_id and hasattr(e, "as_geometry"):
                        found_node = e
                        break
            if found_node is None:
                return
            geom = node.as_geometry()
            # That has already the matrix applied, so we need to reverse that
            # Use ~ inversion operator to create an inversed copy
            geom.transform(~node.matrix)
            bb = geom.bbox()
            start_pt = Point(bb[0], bb[1])

            sdx = getit(param, 4, bb[0])
            sdy = getit(param, 8, bb[1])
            sdx = sdx - bb[0]
            sdy = sdy - bb[1]
            cols = getit(param, 10, 1)
            rows = getit(param, 12, 1)

            geom = create_copied_grid(start_pt, found_node, cols, rows, sdx, sdy)
            node.geometry = geom
            bb = geom.bbox()
            node.functional_parameter = (
                "grid",
                3,
                node_id,
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

        @self.console_argument(
            "turtle", type=str, help="turtle-path for the fractal seed"
        )
        @self.console_argument("n", type=int, default=4, help="Angle divisors")
        @self.console_argument(
            "iterations",
            type=int,
            default=5,
            help="Number of fractal iterations to add",
        )
        @self.console_option(
            "base", "b", type=str, help="turtle-path for the fractal base"
        )
        @context.console_command(
            "tfractal",
            help=_("tfractal iterations"),
            output_type="geometry",
            hidden=True,
        )
        def fractal_t(command, channel, turtle, n, iterations, base=None, **kwargs):
            """
            Add a turtle fractal to the scene. All fractals are geometry outputs.
            F - Forward
            f - Forward (y-flipped)
            B - Forward (walking backwards)
            b - Forward(walking backwards, y-flipped).
            D - Set new distance (units in sqrt of specified value)
            d - Set new distance (units given)
            + - Turn right (also R).
            - - Turn left (also L).

            For example:
            tfractal F+++D2Fd1-B 8 7 node

            Would produce the Dragon of Eve fractal (iteration=7)
            """
            if turtle is None:
                channel("No turtle definition found")
                return
            seed = Geomstr.turtle(turtle, n)
            pattern_base = base
            pattern_repeat = 1
            if base is None:
                base = Geomstr.svg("M0,0 H65535")
            else:
                base = Geomstr.turtle(base, n, d=65535)
                if pattern_base.startswith("n"):
                    idx = 1
                    pattern = ""
                    while pattern_base[idx] in "0123456789":
                        pattern += pattern_base[idx]
                        idx += 1
                    try:
                        pattern_repeat = int(pattern)
                    except ValueError:
                        pass

            for i in range(iterations):
                base.fractal(seed)

            base.parameter_store = (
                "tfractal",
                3,
                turtle,
                3,
                pattern_base,
                1,
                n,
                1,
                iterations,
                1,
                pattern_repeat,
                1,
                0,  # line connector
            )
            return "geometry", base

        @self.console_option(
            "amount", "a", type=float, help="corner rounding amount", default=0.2
        )
        @self.console_command(
            "round_corners", input_type="geometry", output_type="geometry"
        )
        def round_corners(command, channel, data, amount=0.2, **kwargs):
            data.round_corners(amount)
            if hasattr(data, "parameter_store"):
                param = list(data.parameter_store)  # make it editable
                if len(param) > 12:
                    # Round corners
                    param[12] = 1
                data.parameter_store = param
            return "geometry", data

        @self.console_option(
            "amount", "a", type=float, help="corner-bezier amount", default=0.2
        )
        @self.console_command(
            "quad_corners", input_type="geometry", output_type="geometry"
        )
        def quad_corners(command, channel, data, amount=0.2, **kwargs):
            data.bezier_corners(amount)
            if hasattr(data, "parameter_store"):
                param = list(data.parameter_store)  # make it editable
                if len(param) > 12:
                    # Bezier corners
                    param[12] = 2
                data.parameter_store = param
            return "geometry", data

        def update_node_tfractal(node):
            my_id = "tfractal"
            try:
                param = node.functional_parameter
                if param is None or param[0] != my_id:
                    return
            except (AttributeError, IndexError):
                return
            turtle = getit(param, 2, "")
            basepattern = getit(param, 4, "")
            if basepattern == "":
                basepattern = None
            n = getit(param, 6, 1)
            iterations = getit(param, 8, 1)
            pattern_repeat = getit(param, 10, 1)
            connector = getit(param, 12, 0)
            seed = Geomstr.turtle(turtle, n)
            # Let's see whether we need to reconstruct the base
            # Store it
            targetpattern = basepattern
            if basepattern is not None:
                if basepattern.startswith("n"):
                    basepattern = basepattern[1:]
                    previous = ""
                    while len(basepattern) and basepattern[0] in "0123456789":
                        previous += basepattern[0]
                        basepattern = basepattern[1:]
                    if previous:
                        try:
                            prev_len = int(previous)
                        except ValueError:
                            prev_len = 1
                        # Need add 1 to the length as the connector symbol
                        # is not present after the last repetition
                        if (len(basepattern) + 1) % prev_len == 0:
                            # old = basepattern
                            basepattern = basepattern[
                                0 : int(len(basepattern) / prev_len)
                            ]
                        else:
                            # that's wrong...
                            pattern_repeat = 1

                if pattern_repeat > 1:
                    targetpattern = f"n{pattern_repeat}"
                    for idx in range(pattern_repeat):
                        if idx > 0:
                            targetpattern += "+"
                        targetpattern += basepattern
                else:
                    targetpattern = basepattern

            if targetpattern == "":
                targetpattern = None

            if targetpattern is None:
                base = Geomstr.svg("M0,0 H65535")
            else:
                base = Geomstr.turtle(targetpattern, n, d=65535)

            for i in range(iterations):
                base.fractal(seed)
            if connector == 2:
                amount = 0.2
                base.bezier_corners(amount)
            elif connector == 1:
                amount = 0.2
                base.round_corners(amount)
            node.geometry = base
            node.altered()
            # Rewrite the functional_parameter
            node.functional_parameter = (
                "tfractal",
                3,
                turtle,
                3,
                targetpattern,
                1,
                n,
                1,
                iterations,
                1,
                pattern_repeat,
                1,
                connector,  # line connector
            )

        @self.console_argument("svg_path", type=str)
        @self.console_argument("iterations", type=int)
        @self.console_argument("inversions", nargs="*", type=int)
        @context.console_command(
            "ffractal",
            help=_("fractal iterations"),
            output_type="geometry",
            hidden=True,
        )
        def fractal_f(command, channel, svg_path, iterations, inversions, **kwargs):
            seed = Geomstr.svg(svg_path)
            segments = seed.segments
            for i, q in enumerate(inversions):
                if len(segments) > i:
                    segments[i][1] = q
                    segments[i][3] = q
            base = Geomstr.svg("M0,0 H65535")
            for i in range(iterations):
                base.fractal(seed)
            return "geometry", base

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
            node.emphasized = True
            post.append(classify_new(data))
            return "elements", data

        def update_node_fractaltree(node):
            my_id = "fractaltree"
            try:
                param = node.functional_parameter
                if param is None or param[0] != my_id:
                    return
            except (AttributeError, IndexError):
                return
            point_a = None
            point_b = None
            iterations = 5
            ratio = 0.75
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
                return
            if point_a is None or point_b is None:
                return
            geom = create_fractal_tree(point_a, point_b, iterations, ratio)
            node.geometry = geom
            node.altered()

        # --- Fractal Dragon - now superceded by generic tfractal routine
        # def create_fractal_dragon(first_pt, second_pt, iterations):
        #
        #     # Code based on https://github.com/GuidoDipietro/python_art
        #     def rotate(t):
        #         t[0], t[1] = -1 * t[1], t[0]
        #         return t
        #
        #     def turtle_lines(coords, x, y):
        #         turtle_coords = []
        #         for i, point in enumerate(coords):
        #             line_coords = [(x, y), (x + point[0], y + point[1])]
        #             x, y = x + point[0], y + point[1]
        #             turtle_coords.append(line_coords)
        #         return turtle_coords
        #
        #     step = first_pt.distance_to(second_pt)
        #     origin_x = first_pt.x
        #     origin_y = first_pt.y
        #
        #     # list of moves in x,y axes. Start with (1,0) (straight line to right)
        #     moves = [[step, 0]]
        #
        #     for i in range(0, iterations):
        #         copied = list(map(rotate, copy.deepcopy(moves)[::-1]))
        #         moves += copied
        #
        #     dragon_coords = turtle_lines(moves, origin_x, origin_y)
        #
        #     geometry = Geomstr()
        #     for c in dragon_coords:
        #         geometry.line(c[0][0] + 1j * c[0][1], c[1][0] + 1j * c[1][1])
        #     return geometry
        #
        # @self.console_argument("sx", type=Length)
        # @self.console_argument("sy", type=Length)
        # @self.console_argument("step", type=Length)
        # @self.console_argument("iterations", type=int)
        # @context.console_command(
        #     "fractal_dragon", help=_("fractal_dragon sx, sy, step, iterations")
        # )
        # def fractal_dragon(
        #     command,
        #     channel,
        #     _,
        #     sx=None,
        #     sy=None,
        #     step=None,
        #     iterations=None,
        #     data=None,
        #     post=None,
        #     **kwargs,
        # ):
        #     ratio = 0.75
        #     try:
        #         if sx is None:
        #             sx = Length("5cm")
        #         ssx = float(sx)
        #         if sy is None:
        #             sy = Length("5cm")
        #         ssy = float(sy)
        #         if step is None:
        #             step = Length("0.5cm")
        #         blen = float(step)
        #         if iterations is None:
        #             iterations = 10
        #         iterations = int(iterations)
        #     except ValueError:
        #         channel("Invalid data provided")
        #         return
        #     start_pt = Point(ssx, ssy)
        #     end_pt = Point.polar(start_pt, 0, blen)
        #     geom = create_fractal_dragon(start_pt, end_pt, iterations)
        #     node = self.elem_branch.add(type="elem path", geometry=geom)
        #     node.stroke = self.default_stroke
        #     node.stroke_width = self.default_strokewidth
        #     node.altered()
        #     node.functional_parameter = (
        #         "fractaldragon",
        #         0,
        #         start_pt.x,
        #         start_pt.y,
        #         0,
        #         end_pt.x,
        #         end_pt.y,
        #         1,
        #         iterations,
        #     )
        #     # Newly created! Classification needed?
        #     data = [node]
        #     post.append(classify_new(data))
        #     return "elements", data
        #
        # def update_node_fractaldragon(node):
        #     my_id = "fractaldragon"
        #     point_a = None
        #     point_b = None
        #     iterations = 5
        #     valid = True
        #     try:
        #         param = node.functional_parameter
        #         if param is None or param[0] != my_id:
        #             valid = False
        #     except (AttributeError, IndexError):
        #         valid = False
        #     if not valid:
        #         # Not for me...
        #         return
        #     try:
        #         if param[1] == 0:
        #             point_a = Point(param[2], param[3])
        #         if param[4] == 0:
        #             point_b = Point(param[5], param[6])
        #         if param[7] == 1:
        #             iterations = param[8]
        #     except IndexError:
        #         valid = False
        #     if point_a is None or point_b is None:
        #         valid = False
        #     if valid:
        #         geom = create_fractal_dragon(point_a, point_b, iterations)
        #         node.geometry = geom
        #         node.altered()
        #         dist = point_a.distance_to(point_b)
        #         # Put second pt at right spot
        #         point_b = Point(point_a.x + dist, point_a.y)
        #
        #         node.functional_parameter = (
        #             "fractaldragon",
        #             0,
        #             point_a.x,
        #             point_a.y,
        #             0,
        #             point_b.x,
        #             point_b.y,
        #             1,
        #             iterations,
        #         )

        # Cycloid Shape
        def create_cycloid_shape(cx, cy, r_major, r_minor, rotations):
            series = []
            degree_step = 1
            if rotations == 0:
                rotations = 20

            radian_step = math.radians(degree_step)
            t = 0
            m = math.tau * rotations
            if r_minor == 0:
                r_minor = 1
            count = 0
            offset = 0
            while t < m:
                px = (r_minor + r_major) * math.cos(t) - (r_minor + offset) * math.cos(
                    ((r_major + r_minor) / r_minor) * t
                )
                py = (r_minor + r_major) * math.sin(t) - (r_minor + offset) * math.sin(
                    ((r_major + r_minor) / r_minor) * t
                )
                series.append((px + cx, py + cy))
                t += radian_step
                count += 1
            # print(
            #     f"Done: {count} steps, major={r_major:.0f}, minor={r_minor:.0f}, offset={offset:.0f}, rot={rotations}"
            # )
            geometry = Geomstr()
            last = None
            for m in series:
                if last is not None:
                    geometry.line(last[0] + 1j * last[1], m[0] + 1j * m[1])
                last = m
            return geometry

        @self.console_argument("sx", type=Length)
        @self.console_argument("sy", type=Length)
        @self.console_argument("r_major", type=Length)
        @self.console_argument("r_minor", type=Length)
        @self.console_argument("iterations", type=int)
        @context.console_command(
            "cycloid", help=_("cycloid sx sy r_major r_minor iterations")
        )
        def cycloid(
            command,
            channel,
            _,
            sx=None,
            sy=None,
            r_major=None,
            r_minor=None,
            iterations=None,
            data=None,
            post=None,
            **kwargs,
        ):
            try:
                if sx is None:
                    sx = Length("5cm")
                ssx = float(sx)
                if sy is None:
                    sy = Length("5cm")
                ssy = float(sy)
                if r_major is None:
                    r_major = Length("5cm")
                radius_major = float(r_major)
                if r_minor is None:
                    r_minor = Length("3cm")
                radius_minor = float(r_minor)
                if iterations is None:
                    iterations = 20
                iterations = int(iterations)
            except ValueError:
                channel("Invalid data provided")
                return
            start_pt = Point(ssx, ssy)
            point_major = Point(ssx + radius_major, ssy)
            point_minor = Point(ssx, ssy - radius_minor)
            geom = create_cycloid_shape(
                ssx, ssy, radius_major, radius_minor, iterations
            )
            node = self.elem_branch.add(type="elem path", geometry=geom)
            node.label = f"Cycloid {iterations} iterations"
            node.stroke = self.default_stroke
            node.stroke_width = self.default_strokewidth
            node.altered()
            node.functional_parameter = (
                "cycloid",
                0,
                start_pt.x,
                start_pt.y,
                0,
                point_major.x,
                point_major.y,
                0,
                point_minor.x,
                point_minor.y,
                1,
                iterations,
            )
            # Newly created! Classification needed?
            data = [node]
            node.emphasized = True
            post.append(classify_new(data))
            return "elements", data

        def update_node_cycloid(node):
            my_id = "cycloid"
            try:
                param = node.functional_parameter
                if param is None or param[0] != my_id:
                    return
            except (AttributeError, IndexError):
                return
            point_c = None
            point_major = None
            point_minor = None
            try:
                if param[1] == 0:
                    point_c = Point(param[2], param[3])
                if param[4] == 0:
                    point_major = Point(param[5], param[6])
                if param[7] == 0:
                    point_minor = Point(param[8], param[9])
                if param[10] == 1:
                    iterations = param[11]
            except IndexError:
                return
            if point_c is None or point_major is None or point_minor is None:
                return
            radius_major = point_c.distance_to(point_major)
            radius_minor = point_c.distance_to(point_minor)
            ssx = point_c.x
            ssy = point_c.y
            geom = create_cycloid_shape(
                ssx, ssy, radius_major, radius_minor, iterations
            )
            node.geometry = geom
            node.altered()
            point_major = Point(ssx + radius_major, ssy)
            point_minor = Point(ssx, ssy - radius_minor)
            node.functional_parameter = (
                "cycloid",
                0,
                point_c.x,
                point_c.y,
                0,
                point_major.x,
                point_major.y,
                0,
                point_minor.x,
                point_minor.y,
                1,
                iterations,
            )

        # --- Star like shapes
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
            # center = Point(cx, cy)
            if startangle is None:
                startangle = 0

            if corners <= 2:
                if corners == 1:
                    geom.point(cx + 1j * cy)
                if corners == 2:
                    x = cx + math.cos(startangle) * radius
                    y = cy + math.sin(startangle) * radius
                    geom.line(cx + 1j * cy, x + 1j * y)
            else:
                i_angle = startangle
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
                    # tpoint = center.polar_to(i_angle, r)
                    # thisx = tpoint.x
                    # thisy = tpoint.y
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

        # Shape (i.e. star) routine
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
        @self.console_option("startangle", "s", type=Angle, help=_("Start-Angle"))
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
            sangle = 0 if startangle is None else float(startangle)
            if corners <= 2:
                # No need to look at side_length parameter as we are considering the radius value as an edge anyway...
                geom = create_star_shape(
                    cx,
                    cy,
                    corners,
                    sangle,
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
                    startangle = Angle("0deg")

                sangle = float(startangle)
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
                    sangle,
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
            # _("Create shape")
            with self.undoscope("Create shape"):
                node = self.elem_branch.add(type="elem path", geometry=geom)
                node.stroke = self.default_stroke
                node.stroke_width = self.default_strokewidth
                node.fill = self.default_fill
                node.altered()
            self.set_emphasis([node])
            node.focus()

            data = [node]
            # Newly created! Classification needed?
            post.append(classify_new(data))

            center = Point(cx, cy)
            sangle = float(startangle)
            opposing_angle = sangle + math.tau / 2
            while opposing_angle < 0:
                opposing_angle += math.tau
            while opposing_angle >= math.tau:
                opposing_angle -= math.tau
            first_point = Point.polar(center, sangle, radius)
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
            if alternate_seq < 1:
                radius_inner = radius
            if radius_inner == radius:
                alternate_seq = 0
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

        def create_growing_shape(
            cx, cy, sides, iterations, ratio_in_percent, sidelen, startangle, gap
        ):
            geom = Geomstr()
            if sides < 3:
                sides = 3
            shape_angle = math.tau / sides
            myangle = startangle
            sidelength = sidelen
            sidedelta = sidelength * ratio_in_percent / 100.0
            pt1 = cx + 1j * cy
            for idx in range(iterations):
                for side in range(sides):
                    while myangle < 0:
                        myangle += math.tau
                    while myangle > math.tau:
                        myangle -= math.tau

                    pt2 = geom.polar(pt1, myangle, sidelength)
                    geom.line(pt1, pt2)
                    pt1 = pt2
                    sidelength += sidedelta
                    # sidedelta = sidelength * ratio_in_percent
                    myangle += shape_angle
                    myangle += gap
            return geom

        def update_node_growing_shape(node):
            my_id = "growingshape"
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
            pt0x = getit(param, 2, 0)
            pt0y = getit(param, 3, 0)
            pt1x = getit(param, 5, 0)
            pt1y = getit(param, 6, 0)
            ratio_in_percent = getit(param, 8, 0)
            sides = getit(param, 10, 0)
            iterations = getit(param, 12, 0)
            igap = getit(param, 14, 0)
            pt0 = Point(pt0x, pt0y)
            pt1 = Point(pt1x, pt1y)
            sidelen = pt0.distance_to(pt1)
            startangle = pt0.angle_to(pt1)
            gap = igap / 360 * math.tau
            geom = create_growing_shape(
                pt0x,
                pt0y,
                sides,
                iterations,
                ratio_in_percent,
                sidelen,
                startangle,
                gap,
            )
            node.geometry = geom
            node.altered()
            pt0 = None
            pt1 = None
            for pt in geom.as_points():
                if pt0 is None:
                    pt0 = Point(pt.real, pt.imag)
                elif pt1 is None:
                    pt1 = Point(pt.real, pt.imag)
                else:
                    break
            opposite_angle = math.tau / 2 + gap
            while opposite_angle > math.tau:
                opposite_angle -= math.tau
            while opposite_angle < 0:
                opposite_angle += math.tau
            # pt2 = Point.polar(pt0, opposite_angle, sidelen * ratio_in_percent)
            node.functional_parameter = (
                "growingshape",
                0,
                pt0.x,
                pt0.y,
                0,
                pt1.x,
                pt1.y,
                1,
                ratio_in_percent,
                1,
                sides,
                1,
                iterations,
                1,
                igap,
            )

        @self.console_argument("sx", type=Length)
        @self.console_argument("sy", type=Length)
        @self.console_argument("sides", type=int)
        @self.console_argument("iterations", type=int)
        @self.console_argument("firstlength", type=Length)
        @self.console_option("ratio", "r", type=int, help=_("Growth in %"))
        @self.console_option("angle", "a", type=Angle, help=_("Start angle"))
        @self.console_option(
            "gap", "g", type=int, help=_("Delta angle between moves in degrees")
        )
        @context.console_command(
            "growingshape", help=_("growingshape sx sy sides iterations")
        )
        def growing_shape(
            command,
            channel,
            _,
            sx=None,
            sy=None,
            sides=None,
            iterations=None,
            firstlength=None,
            ratio=None,
            angle=None,
            gap=None,
            data=None,
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
                if sides is None or sides < 3:
                    sides = 3
                if iterations is None:
                    iterations = 5
                if iterations < 1:
                    iterations = 1
                if angle is None:
                    angle = Angle("0deg")
                startangle = float(angle)
                if firstlength is None:
                    firstlength = Length("0.5cm")
                sidelen = float(firstlength)
                if ratio is None:
                    ratio = 2  #  2% growth
                if gap is None:
                    gap = 0
            except ValueError:
                channel("Invalid data provided")
                return
            gap_angle = gap / 360 * math.tau
            geom = create_growing_shape(
                ssx,
                ssy,
                sides,
                iterations,
                ratio,
                sidelen,
                startangle,
                gap_angle,
            )
            # _("Create shape")
            with self.undoscope("Create shape"):
                node = self.elem_branch.add(type="elem path", geometry=geom)
                node.label = f"Growing Polygon w. {sides} sides"
                node.stroke = self.default_stroke
                node.stroke_width = 1000  # self.default_strokewidth
                node.altered()
            pt0 = None
            pt1 = None
            for pt in geom.as_points():
                if pt0 is None:
                    pt0 = Point(pt.real, pt.imag)
                elif pt1 is None:
                    pt1 = Point(pt.real, pt.imag)
                else:
                    break
            node.functional_parameter = (
                "growingshape",
                0,
                pt0.x,
                pt0.y,
                0,
                pt1.x,
                pt1.y,
                1,
                ratio,
                1,
                sides,
                1,
                iterations,
                1,
                gap,
            )
            # Newly created! Classification needed?
            data = [node]
            node.emphasized = True
            post.append(classify_new(data))
            return "elements", data

        # Let's register them
        # The info tuple contains three entries
        # 1) The function to be called to update the node after a parameter change
        # 2) A dict with information how to read/display the different parameter entries
        # 3) A boolean parameter that indicates whether this is a routine that needs
        #    to be automatically called after a change of a related source node
        #    This needs the id of the related node to be in the very 'first' parameter
        #    of the functional_parameter structure, so something like
        #       node.functional_parameter = ("grid", 3, source_node.id, ....)
        info = (
            update_node_grid,
            {
                "0": ("ID",),
                "1": ("Horizontal gap",),
                "2": ("Vertical gap",),
                "3": ("Columns", 1, 25),
                "4": ("Rows", 1, 25),
            },
            True,  # Yes this something that needs to be updated on source changes
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
            False,
        )
        kernel.register("element_update/fractaltree", info)

        # info = (
        #     update_node_fractaldragon,
        #     {
        #         "0": ("Startpoint",),
        #         "1": ("End of base stem",),
        #         "2": ("Iterations", 2, 20),
        #     },
        # )
        # kernel.register("element_update/fractaldragon", info)

        info = (
            update_node_cycloid,
            {
                "0": ("Startpoint",),
                "1": ("Major axis",),
                "2": ("Minor axis",),
                "3": ("Iterations", 2, 30),
            },
            False,
        )
        kernel.register("element_update/cycloid", info)

        max_corner_gui = 32
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
            False,
        )
        kernel.register("element_update/star", info)

        info = (
            update_node_tfractal,
            {
                "0": ("Turtle code",),
                "1": ("Base code",),
                "2": ("Segmentation", 1, 20),
                "3": ("Iterations", 1, 20),
                "4": ("Shaping", 1, 20),
                "5": ("Cornertype", 0, 2),
            },
            False,
        )
        kernel.register("element_update/tfractal", info)

        info = (
            None,  # Let the node deal with it
            {
                "0": ("Rounded corner",),
            },
            False,
        )
        kernel.register("element_update/rect", info)

        info = (
            update_node_growing_shape,
            {
                "0": ("First point",),
                "1": ("First edge",),
                "2": ("Growth Ratio", 0, 100),
                "3": ("Sides", 3, 12),
                "4": ("Iterations", 1, 45),
                "5": ("Gap", 0, 15),
            },
            False,
        )
        kernel.register("element_update/growingshape", info)
