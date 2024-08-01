"""
This is a giant list of console commands that deal with and often implement the elements system in the program.
"""

from meerk40t.core.units import Angle, Length
from meerk40t.svgelements import Matrix
from meerk40t.tools.geomstr import BeamTable, Geomstr


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "postboot":
        init_commands(kernel)


def init_commands(kernel):
    self = kernel.elements

    _ = kernel.translation

    # ==========
    # Geometry
    # ==========

    @self.console_command(
        "node",
        help=_("Convert any shapes to pathnodes"),
        input_type="geometry",
        output_type="elements",
    )
    def element_shape_convert(data, **kwargs):
        param = None
        if hasattr(data, "parameter_store"):
            param = getattr(data, "parameter_store", None)
            del data.parameter_store
        node = self.elem_branch.add(
            geometry=data,
            stroke=self.default_stroke,
            stroke_width=self.default_strokewidth,
            type="elem path",
        )
        if param is not None:
            node.functional_parameter = param

        return "elements", [node]

    @self.console_argument("copies", type=int)
    @self.console_command(
        "copies",
        help=_("Convert any element nodes to paths"),
        input_type="geometry",
        output_type="geometry",
    )
    def geometry_copies(data: Geomstr, copies, **kwargs):
        data.copies(copies)
        return "geometry", data

    @self.console_command(
        "geometry",
        help=_("Convert any element nodes to paths"),
        input_type=(None, "elements"),
        output_type="geometry",
    )
    def geometry_base(data=None, **kwargs):
        path = Geomstr()
        index = 0
        if data:
            for node in data:
                try:
                    e = node.as_geometry()
                except AttributeError:
                    continue
                e.flag_settings(index)
                index += 1
                path.append(e)
        return "geometry", path

    @self.console_command("validate", input_type="geometry", output_type="geometry")
    def geometry_validate(channel, _, data=None, **kwargs):
        try:
            data.validate()
            channel(_("Geometry is valid."))
        except AssertionError:
            channel(_("Geometry was not valid."))

    @self.console_argument("x_pos", type=Length)
    @self.console_argument("y_pos", type=Length)
    @self.console_argument("r_pos", type=Length)
    @self.console_command(
        "circle",
        help=_("circle <x> <y> <r>"),
        input_type="geometry",
        output_type="geometry",
        all_arguments_required=True,
    )
    def element_circle(channel, _, x_pos, y_pos, r_pos, data=None, post=None, **kwargs):
        data.append(Geomstr.circle(r_pos, x_pos, y_pos, slices=4))
        return "geometry", data

    @self.console_argument(
        "x_pos",
        type=Length,
        help=_("x position for top left corner of rectangle."),
    )
    @self.console_argument(
        "y_pos",
        type=Length,
        help=_("y position for top left corner of rectangle."),
    )
    @self.console_argument("width", type=Length, help=_("width of the rectangle."))
    @self.console_argument("height", type=Length, help=_("height of the rectangle."))
    @self.console_option("rx", "x", type=Length, help=_("rounded rx corner value."))
    @self.console_option("ry", "y", type=Length, help=_("rounded ry corner value."))
    @self.console_command(
        "rect",
        help=_("adds rectangle to geometry"),
        input_type="geometry",
        output_type="geometry",
        all_arguments_required=True,
    )
    def element_rect(
        channel,
        _,
        x_pos,
        y_pos,
        width,
        height,
        rx=None,
        ry=None,
        data=None,
        post=None,
        **kwargs,
    ):
        """
        Draws a svg rectangle with optional rounded corners.
        """
        if rx is None:
            rx = 0
        if ry is None:
            ry = 0
        data.append(
            Geomstr.rect(
                x=float(x_pos),
                y=float(y_pos),
                width=float(width),
                height=float(height),
                rx=float(rx),
                ry=float(ry),
            )
        )
        return "geometry", data

    @self.console_command(
        "hull",
        help=_("convex hull of the current selected elements"),
        input_type="geometry",
        output_type="geometry",
    )
    def geometry_hull(channel, _, data: Geomstr, **kwargs):
        """
        Provides the convex hull of the given geometry.
        """
        return "geometry", Geomstr.hull(data)

    @self.console_option(
        "chunk",
        "c",
        type=int,
        help=_("Maximum forward-search for potential swaps"),
        default=0,
    )
    @self.console_option(
        "max_passes",
        "m",
        type=int,
        help=_("Maximum number of optimizations passes"),
        default=10,
    )
    @self.console_command(
        "two-opt",
        help=_("Perform two-opt on the current geometry"),
        input_type="geometry",
        output_type="geometry",
    )
    def geometry_two_opt(channel, _, data: Geomstr, max_passes=10, chunk=0, **kwargs):
        """
        Provides a two-opt optimized version of the current data.
        """
        if max_passes < 0:
            max_passes = None
        data.two_opt_distance(max_passes=max_passes, chunk=0)
        return "geometry", data

    @self.console_option(
        "no_flips",
        "x",
        type=bool,
        action="store_true",
        help=_("Do not allow segment flips"),
        default=10,
    )
    @self.console_command(
        "greedy",
        help=_("Perform greedy optimization on the current geometry"),
        input_type="geometry",
        output_type="geometry",
    )
    def geometry_greedy(channel, _, data: Geomstr, no_flips=False, **kwargs):
        """
        Provides a two-opt optimized version of the current data.
        """
        data.greedy_distance(0j, flips=not no_flips)
        return "geometry", data

    @self.console_argument("tx", type=Length, help=_("translate x value"))
    @self.console_argument("ty", type=Length, help=_("translate y value"))
    @self.console_command(
        "translate",
        help=_("translate <tx> <ty>"),
        input_type="geometry",
        output_type="geometry",
    )
    def element_translate(tx, ty, data: Geomstr, **kwargs):
        data.translate(tx, ty)
        return "geometry", data

    @self.console_argument("scale", type=float, help=_("uniform scale value"))
    @self.console_command(
        "uscale",
        help=_("scale <scale-factor>"),
        input_type="geometry",
        output_type="geometry",
    )
    def element_uscale(scale, data: Geomstr, **kwargs):
        data.uscale(scale)
        return "geometry", data

    @self.console_argument("sx", type=float, help=_("Scale X value"))
    @self.console_argument("sy", type=float, help=_("Scale Y value"))
    @self.console_command(
        "scale",
        help=_("scale <scale-factor>"),
        input_type="geometry",
        output_type="geometry",
    )
    def element_scale(data: Geomstr, sx: float, sy: float, **kwargs):
        data.transform(Matrix.scale(sx, sy))
        return "geometry", data

    @self.console_argument("angle", type=Angle, help=_("rotation angle"))
    @self.console_command(
        "rotate",
        help=_("scale <scale-factor>"),
        input_type="geometry",
        output_type="geometry",
    )
    def element_rotate(angle: Angle, data: Geomstr, **kwargs):
        data.rotate(angle.radians)
        return "geometry", data

    @self.console_option("distance", "d", type=Length, default="1mm")
    @self.console_option("angle", "a", type=Angle, default="0deg")
    @self.console_command(
        "hatch",
        help=_("Add hatch geometry"),
        input_type="geometry",
        output_type="geometry",
    )
    def geometry_hatch(data: Geomstr, distance: Length, angle: Angle, **kwargs):
        segments = data.segmented()
        hatch = Geomstr.hatch(segments, angle=angle.radians, distance=float(distance))
        data.append(hatch)
        return "geometry", data

    @self.console_command(
        "combine",
        help=_("Constructive Area Geometry, Combine"),
        input_type="geometry",
        output_type="geometry",
    )
    def element_cag_combine(data: Geomstr, **kwargs):
        bt = BeamTable(data)
        data = bt.combine()
        return "geometry", data

    @self.console_argument("subject", type=int, help=_("Subject polygon shape"))
    @self.console_argument("clip", type=int, help=_("Clipping polygon shape"))
    @self.console_command(
        "union",
        help=_("Constructive Area Geometry, Union"),
        input_type="geometry",
        output_type="geometry",
    )
    def element_cag_union(subject: int, clip: int, data: Geomstr, **kwargs):
        bt = BeamTable(data)
        data = bt.union(subject, clip)
        return "geometry", data

    @self.console_argument("subject", type=int, help=_("Subject polygon shape"))
    @self.console_argument("clip", type=int, help=_("Clipping polygon shape"))
    @self.console_command(
        "intersection",
        help=_("Constructive Area Geometry, intersection"),
        input_type="geometry",
        output_type="geometry",
    )
    def element_cag_intersection(subject: int, clip: int, data: Geomstr, **kwargs):
        bt = BeamTable(data)
        data = bt.intersection(subject, clip)
        return "geometry", data

    @self.console_argument("subject", type=int, help=_("Subject polygon shape"))
    @self.console_argument("clip", type=int, help=_("Clipping polygon shape"))
    @self.console_command(
        "xor",
        help=_("Constructive Area Geometry, xor"),
        input_type="geometry",
        output_type="geometry",
    )
    def element_cag_xor(subject: int, clip: int, data: Geomstr, **kwargs):
        bt = BeamTable(data)
        data = bt.xor(subject, clip)
        return "geometry", data

    @self.console_argument("subject", type=int, help=_("Subject polygon shape"))
    @self.console_argument("clip", type=int, help=_("Clipping polygon shape"))
    @self.console_command(
        "difference",
        help=_("Constructive Area Geometry, difference"),
        input_type="geometry",
        output_type="geometry",
    )
    def element_cag_difference(subject: int, clip: int, data: Geomstr, **kwargs):
        bt = BeamTable(data)
        data = bt.difference(subject, clip)
        return "geometry", data

    # --------------------------- END COMMANDS ------------------------------
