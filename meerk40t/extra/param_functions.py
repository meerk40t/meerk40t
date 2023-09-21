import math
from meerk40t.core.units import Length
from meerk40t.svgelements import Point, Angle, Matrix, Path, Polyline
from meerk40t.tools.geomstr import Geomstr


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation
        context = kernel.root
        self = context.elements
        classify_new = self.post_classify

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
            post.append(classify_new([node]))
            return "elements", data

        # --- Routines to update shapes according to saved and updated parameters.
        def update_node_circle(node):
            my_id = "circle"
            center = None
            point_on_circle = None
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
                    center = Point(param[2], param[3])
                if param[4] == 0:
                    point_on_circle = Point(param[5], param[6])
            except IndexError:
                valid = False
            if center is None or point_on_circle is None:
                valid = False
            if valid:
                radius = center.distance_to(point_on_circle)
                if radius > 0:
                    node.cx = center.x
                    node.cy = center.y
                    node.rx = radius
                    node.ry = radius
                    node.altered()
                else:
                    valid = False
            if not valid:
                # Let's reset it
                node.functional_parameter = (
                    "circle",
                    0,
                    node.cx,
                    node.cy,
                    0,
                    node.cx + math.cos(math.tau * 7 / 8) * node.rx,
                    node.cy + math.sin(math.tau * 7 / 8) * node.ry,
                )

        def update_node_rect(node):
            my_id = "rect"
            center = None
            point_on_circle = None
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
                    center = Point(param[2], param[3])
                if param[4] == 0:
                    point_on_circle = Point(param[5], param[6])
            except IndexError:
                valid = False
            if center is None or point_on_circle is None:
                valid = False
            if valid:
                radius = center.distance_to(point_on_circle)
                if radius > 0:
                    node.cx = center.x
                    node.cy = center.y
                    node.rx = radius
                    node.ry = radius
                    node.altered()
                else:
                    valid = False
            if not valid:
                # Let's reset it
                node.functional_parameter = (
                    "circle",
                    0,
                    node.cx,
                    node.cy,
                    0,
                    node.cx + math.cos(math.tau * 7 / 8) * node.rx,
                    node.cy + math.sin(math.tau * 7 / 8) * node.ry,
                )

        def update_node_ellipse(node):
            my_id = "ellipse"
            point_a = None
            point_b = None
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
            except IndexError:
                valid = False
            if point_a is None or point_b is None:
                valid = False
            if valid:
                rx = point_a.x - point_b.x
                ry = point_b.y - point_a.y
                center = Point(point_a.x - rx, point_b.y - ry)
                rx = abs(rx)
                ry = abs(ry)
                node.cx = center.x
                node.cy = center.y
                node.rx = rx
                node.ry = ry
                # print(
                #     f"New: ({node.cx:.0f}, {node.cy:.0f}), rx={node.rx:.0f}, ry={node.ry:.0f}"
                # )
                node.altered()
            if not valid:
                # Let's reset it
                node.functional_parameter = (
                    my_id,
                    0,
                    node.cx + node.rx,
                    node.cy,
                    0,
                    node.cx,
                    node.cy + node.ry,
                )

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

        # --- end of node update routines

        # Let's register them
        kernel.register("element_update/circle", update_node_circle)
        kernel.register("element_update/ellipse", update_node_ellipse)
        kernel.register("element_update/rect", update_node_rect)
        kernel.register("element_update/fractaltree", update_node_fractaltree)
