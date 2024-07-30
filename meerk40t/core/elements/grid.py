"""
This is a giant list of console commands that deal with and often implement the elements system in the program.
"""

from copy import copy
from math import cos, sin

from meerk40t.core.node.node import Node
from meerk40t.core.units import Angle, Length
from meerk40t.kernel import CommandSyntaxError
from meerk40t.svgelements import Matrix


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "postboot":
        init_commands(kernel)


def init_commands(kernel):
    self = kernel.elements

    _ = kernel.translation

    classify_new = self.post_classify

    # ==========
    # GRID SUBTYPE
    # ==========

    @self.console_argument("c", type=int, help=_("Number of columns"))
    @self.console_argument("r", type=int, help=_("Number of rows"))
    @self.console_argument("x", type=str, help=_("x distance"))
    @self.console_argument("y", type=str, help=_("y distance"))
    @self.console_option(
        "origin",
        "o",
        type=int,
        nargs=2,
        help=_("Position of original in matrix (e.g '2,2' or '4,3')"),
    )
    @self.console_option(
        "relative",
        "r",
        type=bool,
        action="store_true",
        help=_("Distance not absolute but as relative gap"),
    )
    @self.console_command(
        "grid",
        help=_("grid <columns> <rows> <x_distance> <y_distance> <origin>"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_grid(
        command,
        channel,
        _,
        c: int,
        r: int,
        x: str,
        y: str,
        origin=None,
        relative=None,
        data=None,
        post=None,
        **kwargs,
    ):
        if r is None:
            raise CommandSyntaxError
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No item selected."))
            return
        if relative is None:
            relative = False
        try:
            bounds = Node.union_bounds(data)
            width = bounds[2] - bounds[0]
            height = bounds[3] - bounds[1]
        except TypeError:
            raise CommandSyntaxError
        if x is None:
            x = "100%"
        if y is None:
            y = "100%"
        try:
            x = float(Length(x, relative_length=Length(amount=width).length_mm))
            y = float(Length(y, relative_length=Length(amount=height).length_mm))
        except ValueError:
            raise CommandSyntaxError("Length could not be parsed.")
        if relative:
            x += width
            y += height
        if origin is None:
            origin = (1, 1)
        cx, cy = origin
        data_out = list(data)
        if cx is None:
            cx = 1
        if cy is None:
            cy = 1
        start_x = -1 * x * (cx - 1)
        start_y = -1 * y * (cy - 1)
        y_pos = start_y
        for j in range(r):
            x_pos = start_x
            for k in range(c):
                if j != (cy - 1) or k != (cx - 1):
                    add_elem = list(map(copy, data))
                    for e in add_elem:
                        e.matrix *= Matrix.translate(x_pos, y_pos)
                        self.elem_branch.add_node(e)
                    data_out.extend(add_elem)
                x_pos += x
            y_pos += y
        # Newly created! Classification needed?
        post.append(classify_new(data_out))
        self.signal("refresh_scene", "Scene")
        return "elements", data_out

    @self.console_argument("repeats", type=int, help=_("Number of repeats"))
    @self.console_argument("radius", type=self.length, help=_("Radius"))
    @self.console_argument("startangle", type=Angle, help=_("Start-Angle"))
    @self.console_argument("endangle", type=Angle, help=_("End-Angle"))
    @self.console_option(
        "rotate",
        "r",
        type=bool,
        action="store_true",
        help=_("Rotate copies towards center?"),
    )
    @self.console_option(
        "deltaangle",
        "d",
        type=Angle,
        help=_("Delta-Angle (if omitted will take (end-start)/repeats )"),
    )
    @self.console_command(
        "radial",
        help=_("radial <repeats> <radius> <startangle> <endangle> <rotate>"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_radial(
        command,
        channel,
        _,
        repeats: int,
        radius=None,
        startangle=None,
        endangle=None,
        rotate=None,
        deltaangle=None,
        data=None,
        post=None,
        **kwargs,
    ):
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0 and self._emphasized_bounds is None:
            channel(_("No item selected."))
            return

        if repeats is None:
            raise CommandSyntaxError
        if repeats <= 1:
            raise CommandSyntaxError(_("repeats should be greater or equal to 2"))
        if radius is None:
            radius = 0

        if startangle is None:
            startangle = Angle("0deg")
        if endangle is None:
            endangle = Angle("360deg")
        if rotate is None:
            rotate = False

        # print ("Segment to cover: %f - %f" % (startangle.as_degrees, endangle.as_degrees))
        bounds = Node.union_bounds(data)
        if bounds is None:
            return
        data_out = list(data)
        if deltaangle is None:
            segment_len = (endangle - startangle) / repeats
        else:
            segment_len = deltaangle

        # Notabene: we are following the cartesian system here, but as the Y-Axis is top screen to bottom screen,
        # the perceived angle travel is CCW (which is counter-intuitive)
        center_x = (bounds[2] + bounds[0]) / 2.0 - radius
        center_y = (bounds[3] + bounds[1]) / 2.0

        # print ("repeats: %d, Radius: %.1f" % (repeats, radius))
        # print ("Center: %.1f, %.1f" % (center_x, center_y))
        # print ("Startangle, Endangle, segment_len: %.1f, %.1f, %.1f" % (180 * startangle.as_radians / pi, 180 * endangle.as_radians / pi, 180 * segment_len / pi))

        currentangle = segment_len
        for cc in range(1, repeats):
            # print ("Angle: %f rad = %f deg" % (currentangle, currentangle/pi * 180))
            add_elem = list(map(copy, data))
            for e in add_elem:
                if rotate:
                    # x_pos = -1 * radius
                    # y_pos = 0
                    # e *= "translate(%f, %f)" % (x_pos, y_pos)
                    e.matrix *= f"rotate({currentangle.angle_preferred}, {center_x}, {center_y})"
                else:
                    x_pos = -1 * radius + radius * cos(currentangle)
                    y_pos = radius * sin(currentangle)
                    e.matrix *= f"translate({x_pos}, {y_pos})"
                self.elem_branch.add_node(e)

            data_out.extend(add_elem)

            currentangle += segment_len

        # Newly created! Classification needed?
        post.append(classify_new(data_out))
        self.signal("refresh_scene", "Scene")
        return "elements", data_out

    @self.console_argument("copies", type=int, help=_("Number of copies"))
    @self.console_argument("radius", type=self.length, help=_("Radius"))
    @self.console_argument("startangle", type=Angle, help=_("Start-Angle"))
    @self.console_argument("endangle", type=Angle, help=_("End-Angle"))
    @self.console_option(
        "rotate",
        "r",
        type=bool,
        action="store_true",
        help=_("Rotate copies towards center?"),
    )
    @self.console_option(
        "deltaangle",
        "d",
        type=Angle,
        help=_("Delta-Angle (if omitted will take (end-start)/copies )"),
    )
    @self.console_command(
        "circ_copy",
        help=_("circ_copy <copies> <radius> <startangle> <endangle> <rotate>"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_circularcopies(
        command,
        channel,
        _,
        copies: int,
        radius=None,
        startangle=None,
        endangle=None,
        rotate=None,
        deltaangle=None,
        data=None,
        post=None,
        **kwargs,
    ):
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0 and self._emphasized_bounds is None:
            channel(_("No item selected."))
            return

        if copies is None:
            raise CommandSyntaxError
        if copies <= 0:
            copies = 1
        if radius is None:
            radius = 0

        if startangle is None:
            startangle = Angle("0deg")
        if endangle is None:
            endangle = Angle("360deg")
        if rotate is None:
            rotate = False

        # print ("Segment to cover: %f - %f" % (startangle.as_degrees, endangle.as_degrees))
        bounds = Node.union_bounds(data)
        if bounds is None:
            return
        # width = bounds[2] - bounds[0]

        data_out = list(data)
        if deltaangle is None:
            segment_len = (endangle - startangle) / copies
        else:
            segment_len = deltaangle
        # Notabene: we are following the cartesian system here, but as the Y-Axis is top screen to bottom screen,
        # the perceived angle travel is CCW (which is counter-intuitive)
        currentangle = startangle
        # bounds = self._emphasized_bounds
        center_x = (bounds[2] + bounds[0]) / 2.0
        center_y = (bounds[3] + bounds[1]) / 2.0
        images = []
        for cc in range(copies):
            # print ("Angle: %f rad = %f deg" % (currentangle, currentangle/pi * 180))
            add_elem = list(map(copy, data))
            for e in add_elem:
                if rotate:
                    x_pos = radius
                    y_pos = 0
                    e.matrix *= f"translate({x_pos}, {y_pos})"
                    e.matrix *= f"rotate({currentangle.angle_preferred}, {center_x}, {center_y})"
                    e.modified()
                    if hasattr(e, "update"):
                        images.append(e)
                else:
                    x_pos = radius * cos(currentangle)
                    y_pos = radius * sin(currentangle)
                    e.matrix *= f"translate({x_pos}, {y_pos})"
                    e.translated(x_pos, y_pos)
                self.elem_branch.add_node(e)
            data_out.extend(add_elem)
            currentangle += segment_len
        for e in images:
            e.update(None)

        post.append(classify_new(data_out))
        self.signal("refresh_scene", "Scene")
        return "elements", data_out

    # --------------------------- END COMMANDS ------------------------------
