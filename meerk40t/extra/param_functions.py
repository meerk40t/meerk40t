"""
This module exposes a couple of routines to create shapes,
that have additional functional parameters set to allow
parametric editing
"""
import math
from meerk40t.core.units import Length
from meerk40t.svgelements import Point
from meerk40t.tools.geomstr import Geomstr


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation
        context = kernel.root
        self = context.elements
        classify_new = self.post_classify

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
            def getit(param, idx, default):
                if idx >= len(param):
                    return default
                return param[idx]

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

        # --- end of node update routines

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
        info = (
            None,  # Let the node deal with it
            {
                "0": ("Rounded corner",),
            },
        )
        kernel.register("element_update/rect", info)
