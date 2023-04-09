"""
This is a giant list of console commands that deal with and often implement the elements system in the program.
"""

import os.path
import re
from copy import copy
from math import cos, gcd, isinf, pi, sin, sqrt, tau
from random import randint, shuffle

from meerk40t.kernel import CommandSyntaxError

from meerk40t.svgelements import (
    SVG_RULE_EVENODD,
    SVG_RULE_NONZERO,
    Angle,
    Close,
    Color,
    CubicBezier,
    Line,
    Matrix,
    QuadraticBezier,
    Viewbox,
)
from .element_types import *
from meerk40t.core.node.elem_image import ImageNode
from meerk40t.core.node.elem_path import PathNode
from meerk40t.core.node.node import Fillrule, Linecap, Linejoin, Node
from meerk40t.core.node.op_cut import CutOpNode
from meerk40t.core.node.op_dots import DotsOpNode
from meerk40t.core.node.op_engrave import EngraveOpNode
from meerk40t.core.node.op_hatch import HatchOpNode
from meerk40t.core.node.op_image import ImageOpNode
from meerk40t.core.node.op_raster import RasterOpNode
from meerk40t.core.node.util_console import ConsoleOperation
from meerk40t.core.node.util_input import InputOperation
from meerk40t.core.node.util_output import OutputOperation
from meerk40t.core.node.util_wait import WaitOperation
from meerk40t.core.units import (
    UNITS_PER_INCH,
    UNITS_PER_MM,
    UNITS_PER_PIXEL,
    UNITS_PER_POINT,
    Length,
)


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
    @self.console_argument("startangle", type=Angle.parse, help=_("Start-Angle"))
    @self.console_argument("endangle", type=Angle.parse, help=_("End-Angle"))
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
        type=Angle.parse,
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
            startangle = Angle.parse("0deg")
        if endangle is None:
            endangle = Angle.parse("360deg")
        if rotate is None:
            rotate = False

        # print ("Segment to cover: %f - %f" % (startangle.as_degrees, endangle.as_degrees))
        bounds = Node.union_bounds(data)
        if bounds is None:
            return
        width = bounds[2] - bounds[0]

        data_out = list(data)
        if deltaangle is None:
            segment_len = (endangle.as_radians - startangle.as_radians) / repeats
        else:
            segment_len = deltaangle.as_radians
        # Notabene: we are following the cartesian system here, but as the Y-Axis is top screen to bottom screen,
        # the perceived angle travel is CCW (which is counter-intuitive)
        currentangle = startangle.as_radians
        # bounds = self._emphasized_bounds
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
                    x_pos = -1 * radius
                    y_pos = 0
                    # e *= "translate(%f, %f)" % (x_pos, y_pos)
                    e.matrix *= f"rotate({currentangle}rad, {center_x}, {center_y})"
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
    @self.console_argument("startangle", type=Angle.parse, help=_("Start-Angle"))
    @self.console_argument("endangle", type=Angle.parse, help=_("End-Angle"))
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
        type=Angle.parse,
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
            startangle = Angle.parse("0deg")
        if endangle is None:
            endangle = Angle.parse("360deg")
        if rotate is None:
            rotate = False

        # print ("Segment to cover: %f - %f" % (startangle.as_degrees, endangle.as_degrees))
        bounds = Node.union_bounds(data)
        if bounds is None:
            return
        width = bounds[2] - bounds[0]

        data_out = list(data)
        if deltaangle is None:
            segment_len = (endangle.as_radians - startangle.as_radians) / copies
        else:
            segment_len = deltaangle.as_radians
        # Notabene: we are following the cartesian system here, but as the Y-Axis is top screen to bottom screen,
        # the perceived angle travel is CCW (which is counter-intuitive)
        currentangle = startangle.as_radians
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
                    e.matrix *= f"rotate({currentangle}rad, {center_x}, {center_y})"
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

        self.signal("refresh_scene", "Scene")
        return "elements", data_out

    @self.console_argument("corners", type=int, help=_("Number of corners/vertices"))
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
    @self.console_option("density", "d", type=int, help=_("Amount of vertices to skip"))
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
            if startangle is None:
                startangle = Angle.parse("0deg")

            star_points = [(cx, cy)]
            if corners == 2:
                star_points += [
                    (
                        cx + cos(startangle.as_radians) * radius,
                        cy + sin(startangle.as_radians) * radius,
                    )
                ]
        else:
            # do we have something like 'polyshape 3 4cm' ? If yes, reassign the parameters
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
                # d_oc = s * csc( pi / n)
                radius = 0.5 * radius / sin(pi / corners)

            if radius_inner is None:
                radius_inner = radius
            else:
                try:
                    radius_inner = float(Length(radius_inner, relative_length=radius))
                except ValueError:
                    raise CommandSyntaxError

            if inscribed:
                if side_length is None:
                    radius = radius / cos(pi / corners)
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
            pts = []
            i_angle = startangle.as_radians
            delta_angle = tau / corners
            ct = 0
            for j in range(corners):
                if ct < alternate_seq:
                    r = radius
                #    dbg = "outer"
                else:
                    r = radius_inner
                #    dbg = "inner"
                thisx = cx + r * cos(i_angle)
                thisy = cy + r * sin(i_angle)
                # print(
                #    "pt %d, Angle=%.1f: %s radius=%.1f: (%.1f, %.1f)"
                #    % (j, i_angle / pi * 180, dbg, r, thisx, thisy)
                # )
                ct += 1
                if ct >= 2 * alternate_seq:
                    ct = 0
                if j == 0:
                    firstx = thisx
                    firsty = thisy
                i_angle += delta_angle
                pts += [(thisx, thisy)]
            # Close the path
            pts += [(firstx, firsty)]

            star_points = [(pts[0][0], pts[0][1])]
            idx = density
            while idx != 0:
                star_points += [(pts[idx][0], pts[idx][1])]
                idx += density
                if idx >= corners:
                    idx -= corners
            if len(star_points) < corners:
                ct = 0
                possible_combinations = ""
                for i in range(corners - 1):
                    j = i + 2
                    if gcd(j, corners) == 1:
                        if ct % 3 == 0:
                            possible_combinations += f"\n shape {corners} ... -d {j}"
                        else:
                            possible_combinations += f", shape {corners} ... -d {j} "
                        ct += 1
                channel(
                    _("Just for info: we have missed {count} vertices...").format(
                        count=(corners - len(star_points))
                    )
                )
                channel(
                    _(
                        "To hit all, the density parameters should be e.g. {combinations}"
                    ).format(combinations=possible_combinations)
                )

        poly_path = Polygon(star_points)
        if data is None:
            data = list()
        node = self.elem_branch.add(shape=poly_path, type="elem polyline")
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
