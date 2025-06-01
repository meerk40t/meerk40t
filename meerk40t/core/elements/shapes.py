"""
This module contains a collection of console commands that manage and implement the elements system within the application.
It provides functionalities for creating, modifying, and classifying various geometric shapes and elements.

Functions:
- plugin: Initializes the console commands for the elements system.
- init_commands: Sets up the console commands related to shapes and elements.
- element_circle: Creates a circle element at specified coordinates with a given radius.
- element_circle_r: Creates a circle element at the origin with a specified radius.
- element_ellipse: Creates an ellipse element with specified center and radii.
- element_rect: Draws a rectangle with optional rounded corners.
- element_line: Draws a line between two specified points.
- effect_remove: Removes effects from selected elements.
- effect_hatch: Adds a hatch effect to selected elements.
- effect_wobble: Adds a wobble effect to selected elements.
- element_text: Creates a text element with specified content and font size.
- element_text_anchor: Sets the text anchor for a text element.
- element_text_edit: Edits the text content of a text element.
- element_property_set: Sets a specified property to a new value for selected elements.
- recalc: Recalculates the bounds of selected elements.
- simplify_path: Simplifies the geometry of selected paths.
- create_pattern: Creates a pattern from selected elements.
- element_poly: Creates a polygon or polyline from specified points.
- element_pathd_info: Lists the path data of recognized paths.
- element_path: Creates a path element from SVG path syntax.
- element_stroke_width: Adjusts the stroke width of selected elements.
- element_cap: Sets the line cap style for selected paths.
- element_join: Sets the line join style for selected paths.
- element_rule: Sets the fill rule for selected paths.
- element_stroke: Sets the stroke color for selected elements.
- element_fill: Sets the fill color for selected elements.
- element_frame: Draws a frame around the currently selected elements.
- element_rotate: Rotates selected elements by a specified angle.
- element_scale: Scales selected elements by specified factors.
- element_area: Provides information about or changes the area of selected elements.
- element_translate: Translates selected elements by specified offsets.
- element_position: Sets the position of selected elements to specified coordinates.
- element_move_to_laser: Moves selected elements to the current position of the laser head.
- element_resize: Resizes selected elements to specified dimensions.
- element_matrix: Sets the transformation matrix for selected elements.
- reset: Resets affine transformations for selected elements.
- element_reify: Reifies affine transformations for selected elements.
- element_circ_arc_path: Converts paths to use circular arcs.
- element_classify: Classifies selected elements into operations.
- declassify: Declassifies selected elements.

"""

from math import sqrt

from meerk40t.core.node.node import Fillrule, Linecap, Linejoin, Node
from meerk40t.core.units import (
    UNITS_PER_MM,
    UNITS_PER_PIXEL,
    UNITS_PER_POINT,
    Angle,
    Length,
)
from meerk40t.kernel import CommandSyntaxError
from meerk40t.svgelements import (
    SVG_RULE_EVENODD,
    SVG_RULE_NONZERO,
    Color,
    Matrix,
    Path,
    Polygon,
    Polyline,
)
from meerk40t.tools.geomstr import Geomstr, stitch_geometries, stitcheable_nodes


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "postboot":
        init_commands(kernel)


def init_commands(kernel):
    self = kernel.elements

    _ = kernel.translation

    classify_new = self.post_classify

    # ==========
    # ELEMENT/SHAPE COMMANDS
    # ==========
    @self.console_argument("x_pos", type=Length)
    @self.console_argument("y_pos", type=Length)
    @self.console_argument("r_pos", type=Length)
    @self.console_command(
        "circle",
        help=_("circle <x> <y> <r>"),
        input_type=("elements", None),
        output_type="elements",
        all_arguments_required=True,
    )
    def element_circle(channel, _, x_pos, y_pos, r_pos, data=None, post=None, **kwargs):
        node = self.elem_branch.add(
            cx=float(x_pos),
            cy=float(y_pos),
            rx=float(r_pos),
            ry=float(r_pos),
            stroke=self.default_stroke,
            stroke_width=self.default_strokewidth,
            fill=self.default_fill,
            type="elem ellipse",
        )
        self.set_emphasis([node])
        node.focus()
        if data is None:
            data = list()
        data.append(node)
        # Newly created! Classification needed?
        post.append(classify_new(data))
        return "elements", data

    @self.console_argument("r_pos", type=Length)
    @self.console_command(
        "circle_r",
        help=_("circle_r <r>"),
        input_type=("elements", None),
        output_type="elements",
        all_arguments_required=True,
    )
    def element_circle_r(channel, _, r_pos, data=None, post=None, **kwargs):
        node = self.elem_branch.add(
            cx=0,
            cy=0,
            rx=float(r_pos),
            ry=float(r_pos),
            stroke=self.default_stroke,
            stroke_width=self.default_strokewidth,
            fill=self.default_fill,
            type="elem ellipse",
        )
        node.altered()
        self.set_emphasis([node])
        node.focus()
        if data is None:
            data = list()
        data.append(node)
        # Newly created! Classification needed?
        post.append(classify_new(data))
        return "elements", data

    @self.console_argument("x_pos", type=Length)
    @self.console_argument("y_pos", type=Length)
    @self.console_argument("rx", type=Length)
    @self.console_argument("ry", type=Length)
    @self.console_command(
        "ellipse",
        help=_("ellipse <cx> <cy> <rx> <ry>"),
        input_type=("elements", None),
        output_type="elements",
        all_arguments_required=True,
    )
    def element_ellipse(
        channel, _, x_pos, y_pos, rx, ry, data=None, post=None, **kwargs
    ):
        node = self.elem_branch.add(
            cx=float(x_pos),
            cy=float(y_pos),
            rx=float(rx),
            ry=float(ry),
            stroke=self.default_stroke,
            stroke_width=self.default_strokewidth,
            fill=self.default_fill,
            type="elem ellipse",
        )
        node.altered()
        self.set_emphasis([node])
        node.focus()
        if data is None:
            data = list()
        data.append(node)
        # Newly created! Classification needed?
        post.append(classify_new(data))
        return "elements", data

    @self.console_argument("x_pos", type=Length, help=_("X-coordinate of center"))
    @self.console_argument("y_pos", type=Length, help=_("Y-coordinate of center"))
    @self.console_argument("rx", type=Length, help=_("Primary radius of ellipse"))
    @self.console_argument(
        "ry",
        type=Length,
        help=_("Secondary radius of ellipse (default equal to primary radius=circle)"),
    )
    @self.console_argument(
        "start_angle", type=Angle, help=_("Start angle of arc (default 0°)")
    )
    @self.console_argument(
        "end_angle", type=Angle, help=_("End angle of arc (default 360°)")
    )
    @self.console_option("rotation", "r", type=Angle, help=_("Rotation of arc"))
    @self.console_command(
        "arc",
        help=_("arc <cx> <cy> <rx> <ry> <start> <end>"),
        input_type=("elements", None),
        output_type="elements",
        all_arguments_required=True,
    )
    def element_arc(
        channel,
        _,
        x_pos,
        y_pos,
        rx,
        ry=None,
        start_angle=None,
        end_angle=None,
        rotation=None,
        data=None,
        post=None,
        **kwargs,
    ):
        if start_angle is None:
            start_angle = Angle("0deg")
        if end_angle is None:
            end_angle = Angle("360deg")
        if rotation is None:
            rotation = Angle("0deg")
        if ry is None:
            ry = rx
        rx_val = float(rx)
        ry_val = float(ry)
        cx = float(x_pos)
        cy = float(y_pos)
        geom = Geomstr()
        geom.arc_as_cubics(
            start_t=start_angle.radians,
            end_t=end_angle.radians,
            rx=rx_val,
            ry=ry_val,
            cx=cx,
            cy=cy,
            rotation=rotation.radians,
        )
        node = self.elem_branch.add(
            label="Arc",
            geometry=geom,
            stroke=self.default_stroke,
            stroke_width=self.default_strokewidth,
            fill=self.default_fill,
            type="elem path",
        )
        node.altered()
        self.set_emphasis([node])
        node.focus()
        if data is None:
            data = list()
        data.append(node)

        # Newly created! Classification needed?
        post.append(classify_new(data))
        return "elements", data

    @self.console_argument(
        "x_pos",
        type=self.length_x,
        help=_("x position for top left corner of rectangle."),
    )
    @self.console_argument(
        "y_pos",
        type=self.length_y,
        help=_("y position for top left corner of rectangle."),
    )
    @self.console_argument(
        "width", type=self.length_x, help=_("width of the rectangle.")
    )
    @self.console_argument(
        "height", type=self.length_y, help=_("height of the rectangle.")
    )
    @self.console_option(
        "rx", "x", type=self.length_x, help=_("rounded rx corner value.")
    )
    @self.console_option(
        "ry", "y", type=self.length_y, help=_("rounded ry corner value.")
    )
    @self.console_command(
        "rect",
        help=_("adds rectangle to scene"),
        input_type=("elements", None),
        output_type="elements",
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
        node = self.elem_branch.add(
            x=x_pos,
            y=y_pos,
            width=width,
            height=height,
            rx=rx,
            ry=ry,
            stroke=self.default_stroke,
            stroke_width=self.default_strokewidth,
            fill=self.default_fill,
            type="elem rect",
        )
        self.set_emphasis([node])
        node.focus()
        if data is None:
            data = list()
        data.append(node)
        # Newly created! Classification needed?
        post.append(classify_new(data))
        return "elements", data

    @self.console_argument("x0", type=self.length_x, help=_("start x position"))
    @self.console_argument("y0", type=self.length_y, help=_("start y position"))
    @self.console_argument("x1", type=self.length_x, help=_("end x position"))
    @self.console_argument("y1", type=self.length_y, help=_("end y position"))
    @self.console_command(
        "line",
        help=_("adds line to scene"),
        input_type=("elements", None),
        output_type="elements",
        all_arguments_required=True,
    )
    def element_line(command, x0, y0, x1, y1, data=None, post=None, **kwargs):
        """
        Draws a svg line in the scene.
        """
        node = self.elem_branch.add(
            x1=x0,
            y1=y0,
            x2=x1,
            y2=y1,
            stroke=self.default_stroke,
            stroke_width=self.default_strokewidth,
            type="elem line",
        )
        node.altered()
        self.set_emphasis([node])
        node.focus()
        if data is None:
            data = list()
        data.append(node)
        # Newly created! Classification needed?
        post.append(classify_new(data))
        return "elements", data

    @self.console_command(
        "effect-remove",
        help=_("remove effects from element"),
        input_type=(None, "elements"),
    )
    def effect_remove(
        command,
        channel,
        _,
        data=None,
        post=None,
        **kwargs,
    ):
        if data is None:
            data = list(self.elems(emphasized=True))

        if len(data) == 0:
            channel(_("No selected elements."))
            return
        for node in data:
            eparent = node.parent
            nparent = eparent
            while True:
                if nparent.type.startswith("effect"):
                    break
                if nparent.parent is None:
                    nparent = None
                    break
                if nparent.parent is self.elem_branch:
                    nparent = None
                    break
                nparent = nparent.parent
            if nparent is None:
                continue
            was_emphasized = node.emphasized
            node._parent = None  # Otherwise add_node will fail below
            try:
                idx = eparent._children.index(node)
                if idx >= 0:
                    eparent._children.pop(idx)
            except IndexError:
                pass
            nparent.parent.add_node(node)
            if len(nparent.children) == 0:
                nparent.remove_node()
            else:
                nparent.altered()
                node.emphasized = was_emphasized
        self.signal("refresh_scene", "Scene")

    @self.console_option("etype", "e", type=str, default="scanline")
    @self.console_option("distance", "d", type=Length, default=None)
    @self.console_option("angle", "a", type=Angle, default=None)
    @self.console_option("angle_delta", "b", type=Angle, default=None)
    @self.console_command(
        "effect-hatch",
        help=_("adds hatch-effect to scene"),
        input_type=(None, "elements"),
    )
    def effect_hatch(
        command,
        channel,
        _,
        data=None,
        etype=None,
        angle=None,
        angle_delta=None,
        distance=None,
        post=None,
        **kwargs,
    ):
        """
        Add an effect hatch object
        """

        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No selected elements."))
            return

        if distance is None and hasattr(self.device, "effect_hatch_default_distance"):
            distance = getattr(self.device, "effect_hatch_default_distance")
        elif distance is None:
            distance = "1mm"

        if angle is None and hasattr(self.device, "effect_hatch_default_angle"):
            angle = Angle(getattr(self.device, "effect_hatch_default_angle"))
        elif angle is None:
            angle = Angle("0deg")

        if angle_delta is None and hasattr(
            self.device, "effect_hatch_default_angle_delta"
        ):
            angle_delta = Angle(
                getattr(self.device, "effect_hatch_default_angle_delta")
            )
        elif angle_delta is None:
            angle_delta = Angle("0deg")

        if etype is None:
            etype = "scanline"
        first_node = data[0]

        node = first_node.parent.add(
            type="effect hatch",
            label="Hatch Effect",
            hatch_type=etype,
            hatch_angle=angle.radians,
            hatch_angle_delta=angle_delta.radians,
            hatch_distance=distance,
        )
        for n in data:
            node.append_child(n)

        # Newly created! Classification needed?
        post.append(classify_new([node]))

        self.set_emphasis([node])
        node.focus()

    @self.console_option("wtype", "w", type=str, default="circle")
    @self.console_option("radius", "r", type=Length, default=None)
    @self.console_option("interval", "i", type=Length, default=None)
    @self.console_command(
        "effect-wobble",
        help=_("adds wobble-effect to selected elements"),
        input_type=(None, "elements"),
    )
    def effect_wobble(
        command,
        channel,
        _,
        data=None,
        wtype=None,
        radius=None,
        interval=None,
        post=None,
        **kwargs,
    ):
        """
        Add an effect hatch object
        """
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            return
        if wtype is None:
            wtype = "circle"

        if radius is None and hasattr(self.device, "effect_wobble_default_radius"):
            radius = getattr(self.device, "effect_wobble_default_radius")
        elif radius is None:
            radius = "0.5mm"

        if interval is None and hasattr(self.device, "effect_wobble_default_interval"):
            interval = getattr(self.device, "effect_wobble_default_interval")
        elif interval is None:
            interval = "0.5mm"

        wtype = wtype.lower()
        allowed = list(self.kernel.root.match("wobble", suffix=True))
        if wtype not in allowed:
            channel(f"Invalid wobble type, allowed: {','.join(allowed)}")
            return
        try:
            rlen = Length(radius)
        except ValueError:
            channel("Invalid value for radius")
            return
        try:
            ilen = Length(interval)
        except ValueError:
            channel("Invalid value for interval")
            return
        first_node = data[0]
        node = first_node.parent.add(
            type="effect wobble",
            label="Wobble Effect",
            wobble_type=wtype,
            wobble_radius=rlen.length_mm,
            wobble_interval=ilen.length_mm,
        )
        for n in data:
            node.append_child(n)

        # Newly created! Classification needed?
        post.append(classify_new([node]))

        self.set_emphasis([node])
        node.focus()

    @self.console_option(
        "size", "s", type=float, default=16, help=_("font size to for object")
    )
    @self.console_argument("text", type=str, help=_("quoted string of text"))
    @self.console_command(
        "text",
        help=_("text <text>"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_text(
        command, channel, _, data=None, text=None, size=None, post=None, **kwargs
    ):
        if text is None:
            channel(_("No text specified"))
            return
        node = self.elem_branch.add(
            text=text, matrix=Matrix(f"scale({UNITS_PER_PIXEL})"), type="elem text"
        )
        node.font_size = size
        node.stroke = self.default_stroke
        node.stroke_width = self.default_strokewidth
        node.fill = self.default_fill
        node.altered()
        self.set_emphasis([node])
        node.focus()
        if data is None:
            data = list()
        data.append(node)
        # Newly created! Classification needed?
        post.append(classify_new(data))
        return "elements", data

    @self.console_argument(
        "anchor", type=str, default="start", help=_("set text anchor")
    )
    @self.console_command(
        "text-anchor",
        help=_("set text object text-anchor; start, middle, end"),
        input_type=(
            None,
            "elements",
        ),
        output_type="elements",
    )
    def element_text_anchor(command, channel, _, data, anchor=None, **kwargs):
        if anchor not in ("start", "middle", "end"):
            raise CommandSyntaxError(
                _("Only 'start', 'middle', and 'end' are valid anchors.")
            )
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No selected elements."))
            return
        for e in data:
            if hasattr(e, "can_modify") and not e.can_modify:
                channel(_("Can't modify a locked element: {name}").format(name=str(e)))
                continue
            if e.type == "elem text":
                old_anchor = e.anchor
                e.anchor = anchor
                channel(f"Node {e} anchor changed from {old_anchor} to {anchor}")

            e.altered()
        return "elements", data

    @self.console_argument("new_text", type=str, help=_("set new text contents"))
    @self.console_command(
        "text-edit",
        help=_("set text object text to new text"),
        input_type=(
            None,
            "elements",
        ),
        output_type="elements",
        all_arguments_required=True,
    )
    def element_text_edit(command, channel, _, data, new_text=None, **kwargs):
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No selected elements."))
            return
        for e in data:
            if hasattr(e, "can_modify") and not e.can_modify:
                channel(_("Can't modify a locked element: {name}").format(name=str(e)))
                continue
            if e.type == "elem text":
                old_text = e.text
                e.text = new_text
            elif hasattr(e, "mktext"):
                old_text = e.mktext
                e.mktext = new_text
                for property_op in self.kernel.lookup_all("path_updater/.*"):
                    property_op(self.kernel.root, e)
            else:
                continue
            channel(f"Node {e} anchor changed from {old_text} to {new_text}")
            e.altered()

        return "elements", data

    def calculate_text_bounds(data):
        """
        A render operation will use the LaserRender class
        and will re-calculate the element bounds
        @param data:
        @return:
        """
        make_raster = self.lookup("render-op/make_raster")
        if not make_raster:
            # No renderer is registered to perform render.
            return
        for e in data:
            e.set_dirty_bounds()
        # arbitrary bounds...
        bounds = (0, 0, float(Length("5cm")), float(Length("5cm")))
        try:
            image = make_raster(
                data,
                bounds=bounds,
                width=500,
                height=500,
            )
        except Exception:
            pass  # Not relevant...

    @self.console_argument("prop", type=str, help=_("property to get"))
    @self.console_command(
        "property-get",
        help=_("get property value"),
        input_type=(
            None,
            "elements",
        ),
        output_type="elements",
    )
    def element_property_get(command, channel, _, data, post=None, prop=None, **kwargs):
        def possible_representation(node, prop) -> str:
            def simple_rep(prop, value):
                if isinstance(value, (float, int)) and prop in (
                    "x",
                    "y",
                    "cx",
                    "cy",
                    "r",
                    "rx",
                    "ry",
                ):
                    try:
                        s = Length(value).length_mm
                        return s
                    except ValueError:
                        pass
                elif isinstance(value, Length):
                    return value.length_mm
                elif isinstance(value, Angle):
                    return value.angle_degrees
                elif isinstance(value, str):
                    return f"'{value}'"
                return repr(value)

            value = getattr(node, prop, None)
            if isinstance(value, (str, float, int)):
                return simple_rep(prop, value)
            elif isinstance(value, (tuple, list)):
                stuff = []
                for v in value:
                    stuff.append(simple_rep("x", v))
                return ",".join(stuff)
            return simple_rep(prop, value)

        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No selected elements."))
            return
        if prop is None or (prop == "?"):
            channel(_("You need to provide the property to get."))
            identified = []
            for op in data:
                if op.type in identified:
                    continue
                identified.append(op.type)
                prop_str = f"{op.type} has the following properties:"
                first = True
                for d in op.__dict__:
                    if d.startswith("_"):
                        continue
                    prop_str = f"{prop_str}{'' if first else ','} {d}"
                    first = False
                channel(prop_str)
            return
        for d in data:
            if not hasattr(d, prop):
                channel(
                    f"Node: {d.display_label()} (Type: {d.type}) has no property called '{prop}'"
                )
            else:
                channel(
                    f"Node: {d.display_label()} (Type: {d.type}): {prop}={getattr(d, prop, '')} ({possible_representation(d, prop)})"
                )

    @self.console_argument("prop", type=str, help=_("property to set"))
    @self.console_argument("new_value", type=str, help=_("new property value"))
    @self.console_command(
        "property-set",
        help=_("set property to new value"),
        input_type=(
            None,
            "elements",
        ),
        output_type="elements",
        all_arguments_required=True,
    )
    def element_property_set(
        command, channel, _, data, post=None, prop=None, new_value=None, **kwargs
    ):
        """
        Generic node manipulation routine, use with care
        """
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No selected elements."))
            return
        if prop is None or (prop == "?" and new_value == "?"):
            channel(_("You need to provide the property to set."))
            if prop == "?":
                identified = []
                for op in data:
                    if op.type in identified:
                        continue
                    identified.append(op.type)
                    prop_str = f"{op.type} has the following properties:"
                    first = True
                    for d in op.__dict__:
                        if d.startswith("_"):
                            continue
                        prop_str = f"{prop_str}{'' if first else ','} {d}"
                        first = False
                    channel(prop_str)
                channel(
                    "Be careful what you do - this is a failsafe method to crash MeerK40t, burn down your house or whatever..."
                )
            return
        classify_required = False
        prop = prop.lower()
        if len(new_value) == 0:
            new_value = None
        if prop in ("fill", "stroke") and self.classify_on_color:
            classify_required = True
        # Let's distinguish a couple of special cases...
        prevalidated = False
        if prop in ("fill", "stroke", "color"):
            if new_value is not None:
                if new_value.lower() == "none":
                    # The text...
                    new_value = None
                try:
                    new_value = Color(new_value)
                    prevalidated = True
                except ValueError:
                    channel(_("Invalid color value: {value}").format(value=new_value))
                    return
        elif prop in ("x", "y", "width", "height", "stroke_width"):
            if new_value is None:
                channel(_("Invalid length: {value}").format(value=new_value))
                return
            else:
                try:
                    new_value = float(Length(new_value))
                    prevalidated = True
                except ValueError:
                    channel(_("Invalid length: {value}").format(value=new_value))
                    return

        changed = []
        text_elems = []

        if prop == "lock":
            if new_value.lower() in ("1", "true"):
                setval = True
            elif new_value.lower() in ("0", "false"):
                setval = False
            else:
                try:
                    setval = bool(new_value)
                except ValueError:
                    channel(
                        _("Can't set '{val}' for {field}.").format(
                            val=new_value, field=prop
                        )
                    )
                    return
            # print (f"Will set lock to {setval} ({new_value})")
            for e in data:
                if hasattr(e, "lock"):
                    e.lock = setval
                    changed.append(e)
        else:
            # _("Update property")
            with self.undoscope("Update property"):
                for e in data:
                    # dbg = ""
                    # if hasattr(e, "bounds"):
                    #     bb = e.bounds
                    #     dbg += (
                    #         f"x:{Length(bb[0], digits=2).length_mm}, "
                    #         + f"y:{Length(bb[1], digits=2).length_mm}, "
                    #         + f"w:{Length(bb[2]-bb[0], digits=2).length_mm}, "
                    #         + f"h:{Length(bb[3]-bb[1], digits=2).length_mm}, "
                    #     )
                    # dbg += f"{prop}:{str(getattr(e, prop)) if hasattr(e, prop) else '--'}"
                    # print (f"Before: {dbg}")
                    if prop in ("x", "y"):
                        if not e.can_move(self.lock_allows_move):
                            channel(
                                _("Element can not be moved: {name}").format(
                                    name=str(e)
                                )
                            )
                            continue
                        # We need to adjust the matrix
                        if hasattr(e, "bounds") and hasattr(e, "matrix"):
                            dx = 0
                            dy = 0
                            bb = e.bounds
                            if prop == "x":
                                dx = new_value - bb[0]
                            else:
                                dy = new_value - bb[1]
                            e.matrix.post_translate(dx, dy)
                        else:
                            channel(
                                _("Element has no matrix to modify: {name}").format(
                                    name=str(e)
                                )
                            )
                            continue
                    elif prop in ("width", "height"):
                        if new_value == 0:
                            channel(_("Can't set {field} to zero").format(field=prop))
                            continue
                        if hasattr(e, "can_scale") and not e.can_scale:
                            channel(
                                _("Element can not be scaled: {name}").format(
                                    name=str(e)
                                )
                            )
                            continue
                        if hasattr(e, "matrix") and hasattr(e, "bounds"):
                            bb = e.bounds
                            sx = 1.0
                            sy = 1.0
                            wd = bb[2] - bb[0]
                            ht = bb[3] - bb[1]
                            if prop == "width":
                                sx = new_value / wd
                            else:
                                sy = new_value / ht
                            e.matrix.post_scale(sx, sy)
                        else:
                            channel(
                                _("Element has no matrix to modify: {name}").format(
                                    name=str(e)
                                )
                            )
                            continue
                    elif hasattr(e, prop):
                        if hasattr(e, "can_modify") and not e.can_modify:
                            channel(
                                _("Can't modify a locked element: {name}").format(
                                    name=str(e)
                                )
                            )
                            continue
                        try:
                            oldval = getattr(e, prop)
                            if prevalidated:
                                setval = new_value
                            else:
                                if oldval is not None:
                                    proptype = type(oldval)
                                    setval = proptype(new_value)
                                    if isinstance(oldval, bool):
                                        if new_value.lower() in ("1", "true"):
                                            setval = True
                                        elif new_value.lower() in ("0", "false"):
                                            setval = False
                                else:
                                    setval = new_value
                            setattr(e, prop, setval)
                        except TypeError:
                            channel(
                                _(
                                    "Can't set '{val}' for {field} (invalid type, old={oldval})."
                                ).format(val=new_value, field=prop, oldval=oldval)
                            )
                        except ValueError:
                            channel(
                                _(
                                    "Can't set '{val}' for {field} (invalid value, old={oldval})."
                                ).format(val=new_value, field=prop, oldval=oldval)
                            )
                        except AttributeError:
                            channel(
                                _(
                                    "Can't set '{val}' for {field} (incompatible attribute, old={oldval})."
                                ).format(val=new_value, field=prop, oldval=oldval)
                            )

                        if "font" in prop:
                            # We need to force a recalculation of the underlying wxfont property
                            if hasattr(e, "wxfont"):
                                delattr(e, "wxfont")
                                text_elems.append(e)
                        if prop in ("mktext", "mkfont"):
                            for property_op in self.kernel.lookup_all(
                                "path_updater/.*"
                            ):
                                property_op(self.kernel.root, e)
                        if prop in (
                            "dpi",
                            "dither",
                            "dither_type",
                            "invert",
                            "red",
                            "green",
                            "blue",
                            "lightness",
                        ):
                            # Images require some recalculation too
                            self.do_image_update(e)

                    else:
                        channel(
                            _("Element {name} has no property {field}").format(
                                name=str(e), field=prop
                            )
                        )
                        continue
                    e.altered()
                    # dbg = ""
                    # if hasattr(e, "bounds"):
                    #     bb = e.bounds
                    #     dbg += (
                    #         f"x:{Length(bb[0], digits=2).length_mm}, "
                    #         + f"y:{Length(bb[1], digits=2).length_mm}, "
                    #         + f"w:{Length(bb[2]-bb[0], digits=2).length_mm}, "
                    #         + f"h:{Length(bb[3]-bb[1], digits=2).length_mm}, "
                    #     )
                    # dbg += f"{prop}:{str(getattr(e, prop)) if hasattr(e, prop) else '--'}"
                    # print (f"After: {dbg}")
                    changed.append(e)
        if len(changed) > 0:
            if len(text_elems) > 0:
                # Recalculate bounds
                calculate_text_bounds(text_elems)
            self.signal("refresh_scene", "Scene")
            self.signal("element_property_update", changed)
            self.validate_selected_area()
            if classify_required:
                post.append(classify_new(changed))

        return "elements", data

    @self.console_argument("prop", type=str, help=_("property to set"))
    @self.console_argument("new_value", type=str, help=_("new property value"))
    @self.console_command(
        "op-property-set",
        help=_("set operation property to new value"),
        input_type=(
            None,
            "ops",
        ),
        output_type="ops",
        all_arguments_required=True,
    )
    def operation_property_set(
        command, channel, _, data, post=None, prop=None, new_value=None, **kwargs
    ):
        """
        Generic node manipulation routine, use with care
        """
        if data is None:
            data = list(self.ops(selected=True))
        if not data:
            channel(_("No selected operations."))
            return
        if prop is None or (prop == "?" and new_value == "?"):
            channel(_("You need to provide the property to set."))
            if prop == "?":
                identified = []
                for op in data:
                    if op.type in identified:
                        continue
                    identified.append(op.type)
                    prop_str = f"{op.type} has the following properties: "
                    for d in op.__dict__:
                        if d.startswith("_"):
                            continue
                        prop_str = f"{prop_str}, {d}"
                    channel(prop_str)
                channel(
                    "Be careful what you do - this is a failsafe method to crash MeerK40t, burn down your house or whatever..."
                )
            return
        prop = prop.lower()
        if len(new_value) == 0:
            new_value = None
        # Let's distinguish a couple of special cases...
        prevalidated = False
        if prop == "color":
            if new_value is not None:
                if new_value.lower() == "none":
                    # The text...
                    new_value = None
                try:
                    new_value = Color(new_value)
                    prevalidated = True
                except ValueError:
                    channel(_("Invalid color value: {value}").format(value=new_value))
                    return
        if prop in ("power", "speed", "dpi"):
            try:
                testval = float(new_value)
            except ValueError:
                channel(f"Invalid value: {new_value}")
                return
            if testval < 0:
                channel(f"Invalid value: {new_value}")
                return
            if prop == "power" and testval > 1000:
                channel(f"Invalid value: {new_value}")
                return
            new_value = testval
            prevalidated = True

        changed = []
        # _("Update property")
        with self.undoscope("Update property"):
            for e in data:
                if hasattr(e, prop):
                    if hasattr(e, "can_modify") and not e.can_modify:
                        channel(
                            _("Can't modify a locked element: {name}").format(
                                name=str(e)
                            )
                        )
                        continue
                    try:
                        oldval = getattr(e, prop)
                        if prevalidated:
                            setval = new_value
                        else:
                            if oldval is not None:
                                proptype = type(oldval)
                                setval = proptype(new_value)
                                if isinstance(oldval, bool):
                                    if new_value.lower() in ("1", "true"):
                                        setval = True
                                    elif new_value.lower() in ("0", "false"):
                                        setval = False
                            else:
                                setval = new_value
                        setattr(e, prop, setval)
                    except TypeError:
                        channel(
                            _(
                                "Can't set '{val}' for {field} (invalid type, old={oldval})."
                            ).format(val=new_value, field=prop, oldval=oldval)
                        )
                    except ValueError:
                        channel(
                            _(
                                "Can't set '{val}' for {field} (invalid value, old={oldval})."
                            ).format(val=new_value, field=prop, oldval=oldval)
                        )
                    except AttributeError:
                        channel(
                            _(
                                "Can't set '{val}' for {field} (incompatible attribute, old={oldval})."
                            ).format(val=new_value, field=prop, oldval=oldval)
                        )

                else:
                    channel(
                        _("Operation {name} has no property {field}").format(
                            name=str(e), field=prop
                        )
                    )
                    continue
                e.altered()
                changed.append(e)
        if len(changed) > 0:
            self.signal("refresh_scene", "Scene")
            self.signal("element_property_update", changed)

        return "ops", data

    @self.console_command(
        "recalc", input_type=("elements", None), output_type="elements"
    )
    def recalc(command, channel, _, data=None, post=None, **kwargs):
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No selected elements."))
            return
        for e in data:
            e.set_dirty_bounds()
        self.signal("refresh_scene", "Scene")
        self.validate_selected_area()

    @self.console_option("douglas", "d", type=bool, action="store_true", default=False)
    @self.console_option(
        "visvalingam", "v", type=bool, action="store_true", default=False
    )
    @self.console_option(
        "tolerance",
        "t",
        type=float,
        help=_("simplification tolerance"),
    )
    @self.console_command(
        "simplify", input_type=("elements", None), output_type="elements"
    )
    def simplify_path(
        command,
        channel,
        _,
        data=None,
        tolerance=None,
        douglas=None,
        visvalingam=None,
        post=None,
        **kwargs,
    ):
        if data is None:
            data = list(self.elems(emphasized=True))
        data_changed = list()
        if len(data) == 0:
            channel("Requires a selected polygon")
            return None
        method = "douglaspeucker"
        if douglas:
            method = "douglaspeucker"
        if visvalingam:
            method = "visvalingam"
        if tolerance is None:
            tolerance = 25  # About 1/1000 mil
        # _("Simplify")
        with self.undoscope("Simplify"):
            for node in data:
                try:
                    sub_before = len(list(node.as_geometry().as_subpaths()))
                except AttributeError:
                    sub_before = 0
                if hasattr(node, "geometry"):
                    geom = node.geometry
                    seg_before = node.geometry.index
                    if method == "douglaspeucker":
                        node.geometry = geom.simplify(tolerance)
                    else:
                        # Let's try Visvalingam line simplification
                        node.geometry = geom.simplify_geometry(threshold=tolerance)
                    node.altered()
                    seg_after = node.geometry.index
                    try:
                        sub_after = len(list(node.as_geometry().as_subpaths()))
                    except AttributeError:
                        sub_after = 0
                    channel(
                        f"Simplified {node.type} ({node.display_label()}), tolerance: {tolerance}={Length(tolerance, digits=4).length_mm})"
                    )
                    if seg_before:
                        saving = f"({(seg_before - seg_after) / seg_before * 100:.1f}%)"
                    else:
                        saving = ""
                    channel(f"Subpaths before: {sub_before} to {sub_after}")
                    channel(f"Segments before: {seg_before} to {seg_after} {saving}")
                    data_changed.append(node)
                else:
                    channel(
                        f"Invalid node for simplify {node.type} ({node.display_label()})"
                    )
        if len(data_changed) > 0:
            self.signal("element_property_update", data_changed)
            self.signal("refresh_scene", "Scene")
        return "elements", data

    @self.console_command(
        "polycut", input_type=("elements", None), output_type="elements"
    )
    def create_pattern(command, channel, _, data=None, post=None, **kwargs):
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) <= 1:
            channel("Requires a selected cutter polygon")
            return None
        data.sort(key=lambda n: n.emphasized_time)
        try:
            outer_path = data[0].as_path()
            inner_path = data[1].as_path()
        except AttributeError:
            # elem text does not have an as_path() object
            return "elements", data
        data[1].remove_node()

        from meerk40t.tools.pathtools import VectorMontonizer

        vm = VectorMontonizer()
        outer_path = Polygon(
            [outer_path.point(i / 1000.0, error=1e4) for i in range(1001)]
        )
        vm.add_polyline(outer_path)
        path = Path()
        for sub_inner in inner_path.as_subpaths():
            sub_inner = Path(sub_inner)
            pts_sub = [sub_inner.point(i / 1000.0, error=1e4) for i in range(1001)]
            for i in range(len(pts_sub) - 1, -1, -1):
                pt = pts_sub[i]
                if not vm.is_point_inside(pt[0], pt[1]):
                    del pts_sub[i]
            path += Path(Polyline(pts_sub))
        node = self.elem_branch.add(path=path, type="elem path")
        data.append(node)
        node.stroke = self.default_stroke
        node.stroke_width = self.default_strokewidth
        node.fill = self.default_fill
        node.altered()
        self.set_emphasis([node])
        node.focus()
        post.append(classify_new(data))
        return "elements", data

    @self.console_argument("mlist", type=Length, help=_("list of positions"), nargs="*")
    @self.console_command(
        ("polygon", "polyline"),
        help=_("poly(gon|line) (Length Length)*"),
        input_type=("elements", None),
        output_type="elements",
        all_arguments_required=True,
    )
    def element_poly(command, channel, _, mlist, data=None, post=None, **kwargs):
        try:
            pts = [float(Length(p)) for p in mlist]
            if command == "polygon":
                shape = Polygon(pts)
            else:
                shape = Polyline(pts)
        except ValueError:
            raise CommandSyntaxError(
                _("Must be a list of spaced delimited length pairs.")
            )
        if shape.is_degenerate():
            channel(_("Shape is degenerate."))
            return "elements", data
        node = self.elem_branch.add(shape=shape, type="elem polyline")
        node.stroke = self.default_stroke
        node.stroke_width = self.default_strokewidth
        node.fill = self.default_fill
        node.altered()
        self.set_emphasis([node])
        node.focus()
        if data is None:
            data = list()
        data.append(node)
        # Newly created! Classification needed?
        post.append(classify_new(data))
        return "elements", data

    @self.console_option(
        "real",
        "r",
        action="store_true",
        type=bool,
        help="Display non-transformed path",
    )
    @self.console_command(
        "path_d_info",
        help=_("List the path_d of any recognized paths"),
        input_type="elements",
    )
    def element_pathd_info(command, channel, _, data, real=True, **kwargs):
        for node in data:
            try:
                g = node.as_geometry()
                path = g.as_path()
                ident = " (Identity)" if node.matrix.is_identity() else ""
                channel(f"{str(node)}{ident}: {path.d(transformed=not real)}")
            except AttributeError:
                channel(f"{str(node)}: Invalid")

    @self.console_argument(
        "path_d", type=str, help=_("svg path syntax command (quoted).")
    )
    @self.console_command(
        "path",
        help=_("path <svg path>"),
        output_type="elements",
    )
    def element_path(path_d, data, post=None, **kwargs):
        if path_d is None:
            raise CommandSyntaxError(_("Not a valid path_d string"))
        try:
            path = Path(path_d)
            path *= f"Scale({UNITS_PER_PIXEL})"
        except (ValueError, AttributeError):
            raise CommandSyntaxError(_("Not a valid path_d string (try quotes)"))

        node = self.elem_branch.add(path=path, type="elem path")
        node.stroke = self.default_stroke
        node.stroke_width = self.default_strokewidth
        node.fill = self.default_fill
        node.altered()
        self.set_emphasis([node])
        node.focus()
        if data is None:
            data = list()
        data.append(node)
        # Newly created! Classification needed?
        post.append(classify_new(data))
        return "elements", data

    @self.console_argument(
        "stroke_width",
        type=self.length,
        help=_("Stroke-width for the given stroke"),
    )
    @self.console_command(
        "stroke-width",
        help=_("stroke-width <length>"),
        input_type=(
            None,
            "elements",
        ),
        output_type="elements",
    )
    def element_stroke_width(command, channel, _, stroke_width, data=None, **kwargs):
        def width_string(value):
            if value is None:
                return "-"
            res = ""
            display_units = (
                (1, ""),
                (UNITS_PER_PIXEL, "px"),
                (UNITS_PER_POINT, "pt"),
                (UNITS_PER_MM, "mm"),
            )
            for unit in display_units:
                unit_value = value / unit[0]
                if res != "":
                    res += ", "
                res += f"{unit_value:.3f}{unit[1]}"
            return res

        if data is None:
            data = list(self.elems(emphasized=True))
        if stroke_width is None:
            # Display data about stroke widths.
            channel("----------")
            channel(_("Stroke-Width Values:"))
            for i, e in enumerate(self.elems()):
                name = str(e)
                if len(name) > 50:
                    name = name[:50] + "…"
                try:
                    stroke_width = e.stroke_width
                except AttributeError:
                    # Has no stroke width.
                    continue
                if not hasattr(e, "stroke_scaled"):
                    # Can't have a scaled stroke.
                    channel(
                        _(
                            "{index}: {name} - {typename}\n   stroke-width = {stroke_width}\n   scaled-width = {scaled_stroke_width}"
                        ).format(
                            index=i,
                            typename="scaled-stroke",
                            stroke_width=width_string(stroke_width),
                            scaled_stroke_width=width_string(None),
                            name=name,
                        )
                    )
                    continue
                factor = 1.0
                if e.stroke_scaled:
                    typename = "scaled-stroke"
                    try:
                        factor = e.stroke_factor
                    except AttributeError:
                        pass
                else:
                    typename = "non-scaling-stroke"
                implied_value = factor * stroke_width
                channel(
                    _(
                        "{index}: {name} - {typename}\n   stroke-width = {stroke_width}\n   scaled-width = {scaled_stroke_width}"
                    ).format(
                        index=i,
                        typename=typename,
                        stroke_width=width_string(stroke_width),
                        scaled_stroke_width=width_string(implied_value),
                        name=name,
                    )
                )
            channel("----------")
            return

        if len(data) == 0:
            channel(_("No selected elements."))
            return
        # _("Set stroke-width")
        with self.undoscope("Set stroke-width"):
            for e in data:
                if hasattr(e, "lock") and e.lock:
                    channel(
                        _("Can't modify a locked element: {name}").format(name=str(e))
                    )
                    continue
                e.stroke_width = stroke_width
                try:
                    e.stroke_width_zero()
                except AttributeError:
                    pass
                # No full modified required, we are effectively only adjusting
                # the painted_bounds
                e.translated(0, 0)
        self.signal("element_property_update", data)
        self.signal("refresh_scene", "Scene")
        return "elements", data

    @self.console_command(
        ("enable_stroke_scale", "disable_stroke_scale"),
        input_type=(
            None,
            "elements",
        ),
        hidden=True,
        output_type="elements",
    )
    def element_stroke_scale_enable(command, channel, _, data=None, **kwargs):
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No selected elements."))
            return
        # _("Update stroke-scale")
        with self.undoscope("Update stroke-scale"):
            for e in data:
                if hasattr(e, "lock") and e.lock:
                    channel(
                        _("Can't modify a locked element: {name}").format(name=str(e))
                    )
                    continue
                e.stroke_scaled = command == "enable_stroke_scale"
                e.altered()
        self.signal("element_property_update", data)
        self.signal("refresh_scene", "Scene")
        return "elements", data

    @self.console_option("filter", "f", type=str, help="Filter indexes")
    @self.console_argument(
        "cap",
        type=str,
        help=_("Linecap to apply to the path (one of butt, round, square)"),
    )
    @self.console_command(
        "linecap",
        help=_("linecap <cap>"),
        input_type=(
            None,
            "elements",
        ),
        output_type="elements",
    )
    def element_cap(command, channel, _, cap=None, data=None, filter=None, **kwargs):
        if data is None:
            data = list(self.elems(emphasized=True))
        apply = data
        if filter is not None:
            apply = list()
            for value in filter.split(","):
                try:
                    value = int(value)
                except ValueError:
                    continue
                try:
                    apply.append(data[value])
                except IndexError:
                    channel(_("index {index} out of range").format(index=value))
        if cap is None:
            channel("----------")
            channel(_("Linecaps:"))
            i = 0
            for e in self.elems():
                name = str(e)
                if len(name) > 50:
                    name = name[:50] + "…"
                if hasattr(e, "linecap"):
                    if e.linecap == Linecap.CAP_SQUARE:
                        capname = "square"
                    elif e.linecap == Linecap.CAP_BUTT:
                        capname = "butt"
                    else:
                        capname = "round"
                    channel(
                        _("{index}: linecap = {linecap} - {name}").format(
                            index=i, linecap=capname, name=name
                        )
                    )
                i += 1
            channel("----------")
            return
        else:
            capvalue = None
            if cap.lower() == "butt":
                capvalue = Linecap.CAP_BUTT
            elif cap.lower() == "round":
                capvalue = Linecap.CAP_ROUND
            elif cap.lower() == "square":
                capvalue = Linecap.CAP_SQUARE
            if capvalue is not None:
                for e in apply:
                    if hasattr(e, "linecap"):
                        if hasattr(e, "lock") and e.lock:
                            channel(
                                _("Can't modify a locked element: {name}").format(
                                    name=str(e)
                                )
                            )
                            continue
                        e.linecap = capvalue
                        e.altered()
            return "elements", data

    @self.console_option("filter", "f", type=str, help="Filter indexes")
    @self.console_argument(
        "join",
        type=str,
        help=_(
            "jointype to apply to the path (one of arcs, bevel, miter, miter-clip, round)"
        ),
    )
    @self.console_command(
        "linejoin",
        help=_("linejoin <join>"),
        input_type=(
            None,
            "elements",
        ),
        output_type="elements",
    )
    def element_join(command, channel, _, join=None, data=None, filter=None, **kwargs):
        if data is None:
            data = list(self.elems(emphasized=True))
        apply = data
        if filter is not None:
            apply = list()
            for value in filter.split(","):
                try:
                    value = int(value)
                except ValueError:
                    continue
                try:
                    apply.append(data[value])
                except IndexError:
                    channel(_("index {index} out of range").format(index=value))
        if join is None:
            channel("----------")
            channel(_("Linejoins:"))
            i = 0
            for e in self.elems():
                name = str(e)
                if len(name) > 50:
                    name = name[:50] + "…"
                if hasattr(e, "linejoin"):
                    if e.linejoin == Linejoin.JOIN_ARCS:
                        joinname = "arcs"
                    elif e.linejoin == Linejoin.JOIN_BEVEL:
                        joinname = "bevel"
                    elif e.linejoin == Linejoin.JOIN_MITER_CLIP:
                        joinname = "miter-clip"
                    elif e.linejoin == Linejoin.JOIN_MITER:
                        joinname = "miter"
                    elif e.linejoin == Linejoin.JOIN_ROUND:
                        joinname = "round"
                    channel(
                        _("{index}: linejoin = {linejoin} - {name}").format(
                            index=i, linejoin=joinname, name=name
                        )
                    )
                i += 1
            channel("----------")
            return
        else:
            joinvalue = None
            if join.lower() == "arcs":
                joinvalue = Linejoin.JOIN_ARCS
            elif join.lower() == "bevel":
                joinvalue = Linejoin.JOIN_BEVEL
            elif join.lower() == "miter":
                joinvalue = Linejoin.JOIN_MITER
            elif join.lower() == "miter-clip":
                joinvalue = Linejoin.JOIN_MITER_CLIP
            elif join.lower() == "round":
                joinvalue = Linejoin.JOIN_ROUND
            if joinvalue is not None:
                for e in apply:
                    if hasattr(e, "linejoin"):
                        if hasattr(e, "lock") and e.lock:
                            channel(
                                _("Can't modify a locked element: {name}").format(
                                    name=str(e)
                                )
                            )
                            continue
                        e.linejoin = joinvalue
                        e.altered()
            return "elements", data

    @self.console_option("filter", "f", type=str, help="Filter indexes")
    @self.console_argument(
        "rule",
        type=str,
        help=_("rule to apply to fill the path (one of {nonzero}, {evenodd})").format(
            nonzero=SVG_RULE_NONZERO, evenodd=SVG_RULE_EVENODD
        ),
    )
    @self.console_command(
        "fillrule",
        help=_("fillrule <rule>"),
        input_type=(
            None,
            "elements",
        ),
        output_type="elements",
    )
    def element_rule(command, channel, _, rule=None, data=None, filter=None, **kwargs):
        if data is None:
            data = list(self.elems(emphasized=True))
        apply = data
        if filter is not None:
            apply = list()
            for value in filter.split(","):
                try:
                    value = int(value)
                except ValueError:
                    continue
                try:
                    apply.append(data[value])
                except IndexError:
                    channel(_("index {index} out of range").format(index=value))
        if rule is None:
            channel("----------")
            channel(_("fillrules:"))
            i = 0
            for e in self.elems():
                name = str(e)
                if len(name) > 50:
                    name = name[:50] + "…"
                if hasattr(e, "fillrule"):
                    if e.fillrule == Fillrule.FILLRULE_EVENODD:
                        rulename = SVG_RULE_EVENODD
                    elif e.fillrule == Fillrule.FILLRULE_NONZERO:
                        rulename = SVG_RULE_NONZERO
                    channel(
                        _("{index}: fillrule = {fillrule} - {name}").format(
                            index=i, fillrule=rulename, name=name
                        )
                    )
                i += 1
            channel("----------")
            return
        else:
            rulevalue = None
            if rule.lower() == SVG_RULE_EVENODD:
                rulevalue = Fillrule.FILLRULE_EVENODD
            elif rule.lower() == SVG_RULE_NONZERO:
                rulevalue = Fillrule.FILLRULE_NONZERO
            if rulevalue is not None:
                for e in apply:
                    if hasattr(e, "fillrule"):
                        if hasattr(e, "lock") and e.lock:
                            channel(
                                _("Can't modify a locked element: {name}").format(
                                    name=str(e)
                                )
                            )
                            continue
                        e.fillrule = rulevalue
                        e.altered()
            return "elements", data

    @self.console_option(
        "classify", "c", type=bool, action="store_true", help="Reclassify element"
    )
    @self.console_option("filter", "f", type=str, help="Filter indexes")
    @self.console_argument(
        "color", type=Color, help=_("Color to color the given stroke")
    )
    @self.console_command(
        "stroke",
        help=_("stroke <svg color>"),
        input_type=(
            None,
            "elements",
        ),
        output_type="elements",
    )
    def element_stroke(
        command, channel, _, color, data=None, classify=None, filter=None, **kwargs
    ):
        if data is None:
            data = list(self.elems(emphasized=True))
            was_emphasized = True
            old_first = self.first_emphasized
        else:
            was_emphasized = False
            old_first = None
        apply = data
        if filter is not None:
            apply = list()
            for value in filter.split(","):
                try:
                    value = int(value)
                except ValueError:
                    continue
                try:
                    apply.append(data[value])
                except IndexError:
                    channel(_("index {index} out of range").format(index=value))
        if color is None:
            channel("----------")
            channel(_("Stroke Values:"))
            i = 0
            for e in self.elems():
                name = str(e)
                if len(name) > 50:
                    name = name[:50] + "…"
                if not hasattr(e, "stroke"):
                    pass
                elif hasattr(e, "stroke") and e.stroke is None or e.stroke == "none":
                    channel(f"{i}: stroke = none - {name}")
                else:
                    channel(f"{i}: stroke = {e.stroke.hex} - {name}")
                i += 1
            channel("----------")
            return
        self.set_start_time("full_load")
        # _("Set stroke")
        with self.undoscope("Set stroke"):
            if color == "none":
                self.set_start_time("stroke")
                for e in apply:
                    if hasattr(e, "lock") and e.lock:
                        channel(
                            _("Can't modify a locked element: {name}").format(
                                name=str(e)
                            )
                        )
                        continue
                    e.stroke = None
                    e.translated(0, 0)
                    # e.altered()
                self.set_end_time("stroke")
            else:
                self.set_start_time("stroke")
                for e in apply:
                    if hasattr(e, "lock") and e.lock:
                        channel(
                            _("Can't modify a locked element: {name}").format(
                                name=str(e)
                            )
                        )
                        continue
                    e.stroke = Color(color)
                    e.translated(0, 0)
                    # e.altered()
                self.set_end_time("stroke")
            if classify is None:
                classify = False
            if classify:
                self.set_start_time("classify")
                self.remove_elements_from_operations(apply)
                self.classify(apply)
                if was_emphasized:
                    for e in apply:
                        e.emphasized = True
                    if len(apply) == 1:
                        apply[0].focus()
                if old_first is not None and old_first in apply:
                    self.first_emphasized = old_first
                else:
                    self.first_emphasized = None
                self.set_end_time("classify")
                # self.signal("rebuild_tree")
                self.signal("refresh_tree", apply)
            else:
                self.signal("element_property_reload", apply)
                self.signal("refresh_scene", "Scene")
        return "elements", data

    @self.console_option(
        "classify", "c", type=bool, action="store_true", help="Reclassify element"
    )
    @self.console_option("filter", "f", type=str, help="Filter indexes")
    @self.console_argument("color", type=Color, help=_("Color to set the fill to"))
    @self.console_command(
        "fill",
        help=_("fill <svg color>"),
        input_type=(
            None,
            "elements",
        ),
        output_type="elements",
    )
    def element_fill(
        command, channel, _, color, data=None, classify=None, filter=None, **kwargs
    ):
        if data is None:
            data = list(self.elems(emphasized=True))
            was_emphasized = True
            old_first = self.first_emphasized
        else:
            was_emphasized = False
            old_first = None
        apply = data
        if filter is not None:
            apply = list()
            for value in filter.split(","):
                try:
                    value = int(value)
                except ValueError:
                    continue
                try:
                    apply.append(data[value])
                except IndexError:
                    channel(_("index {index} out of range").format(index=value))
        if color is None:
            channel("----------")
            channel(_("Fill Values:"))
            i = 0
            for e in self.elems():
                name = str(e)
                if len(name) > 50:
                    name = name[:50] + "…"
                if not hasattr(e, "fill"):
                    pass
                elif e.fill is None or e.fill == "none":
                    channel(
                        _("{index}: fill = none - {name}").format(index=i, name=name)
                    )
                else:
                    channel(
                        _("{index}: fill = {fill} - {name}").format(
                            index=i, fill=e.fill.hex, name=name
                        )
                    )
                i += 1
            channel("----------")
            return "elements", data
        # _("Set fill")
        with self.undoscope("Set fill"):
            if color == "none":
                self.set_start_time("fill")
                for e in apply:
                    if hasattr(e, "lock") and e.lock:
                        channel(
                            _("Can't modify a locked element: {name}").format(
                                name=str(e)
                            )
                        )
                        continue
                    e.fill = None
                    e.translated(0, 0)
                    # e.altered()
                self.set_end_time("fill")
            else:
                self.set_start_time("fill")
                for e in apply:
                    if hasattr(e, "lock") and e.lock:
                        channel(
                            _("Can't modify a locked element: {name}").format(
                                name=str(e)
                            )
                        )
                        continue
                    e.fill = Color(color)
                    e.translated(0, 0)
                    # e.altered()
                self.set_end_time("fill")
            if classify is None:
                classify = False
            if classify:
                self.set_start_time("classify")
                self.remove_elements_from_operations(apply)
                self.classify(apply)
                if was_emphasized:
                    for e in apply:
                        e.emphasized = True
                    if len(apply) == 1:
                        apply[0].focus()
                if old_first is not None and old_first in apply:
                    self.first_emphasized = old_first
                else:
                    self.first_emphasized = None
                self.signal("refresh_tree", apply)
                #                self.signal("rebuild_tree")
                self.set_end_time("classify")
            else:
                self.signal("element_property_update", apply)
                self.signal("refresh_scene", "Scene")
        return "elements", data

    @self.console_argument(
        "x_offset", type=self.length_x, help=_("x offset."), default="0"
    )
    @self.console_argument(
        "y_offset", type=self.length_y, help=_("y offset"), default="0"
    )
    @self.console_command(
        "frame",
        help=_("Draws a frame the current selected elements"),
        input_type=(
            None,
            "elements",
        ),
        output_type="elements",
    )
    def element_frame(
        command,
        channel,
        _,
        x_offset=None,
        y_offset=None,
        data=None,
        post=None,
        **kwargs,
    ):
        """
        Draws an outline of the current shape.
        """
        bounds = self.selected_area()
        if bounds is None:
            channel(_("Nothing Selected"))
            return
        x_pos = bounds[0]
        y_pos = bounds[1]
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        x_pos -= x_offset
        y_pos -= y_offset
        width += x_offset * 2
        height += y_offset * 2
        node = self.elem_branch.add(
            x=x_pos,
            y=y_pos,
            width=width,
            height=height,
            stroke=Color("red"),
            type="elem rect",
        )
        self.set_emphasis([node])
        node.focus()
        if data is None:
            data = list()
        data.append(node)
        # Newly created! Classification needed?
        post.append(classify_new(data))
        return "elements", data

    @self.console_argument("angle", type=Angle, help=_("angle to rotate by"))
    @self.console_option("cx", "x", type=self.length_x, help=_("center x"))
    @self.console_option("cy", "y", type=self.length_y, help=_("center y"))
    @self.console_option(
        "absolute",
        "a",
        type=bool,
        action="store_true",
        help=_("angle_to absolute angle"),
    )
    @self.console_command(
        "rotate",
        help=_("rotate <angle>"),
        input_type=(
            None,
            "elements",
        ),
        output_type="elements",
    )
    def element_rotate(
        command,
        channel,
        _,
        angle,
        cx=None,
        cy=None,
        absolute=False,
        data=None,
        **kwargs,
    ):
        if angle is None:
            channel("----------")
            channel(_("Rotate Values:"))
            i = 0
            for node in self.elems():
                name = str(node)
                if len(name) > 50:
                    name = name[:50] + "…"
                channel(
                    _("{index}: rotate({angle}turn) - {name}").format(
                        index=i,
                        angle=Angle(node.matrix.rotation).angle_turns[:-4],
                        name=name,
                    )
                )
                i += 1
            channel("----------")
            return
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No selected elements."))
            return
        self.validate_selected_area()
        bounds = self.selected_area()
        if bounds is None:
            channel(_("No selected elements."))
            return

        if cx is None:
            cx = (bounds[2] + bounds[0]) / 2.0
        if cy is None:
            cy = (bounds[3] + bounds[1]) / 2.0
        images = []
        # _("Rotate")
        with self.undoscope("Rotate"):
            try:
                if not absolute:
                    for node in data:
                        if hasattr(node, "lock") and node.lock:
                            continue
                        node.matrix.post_rotate(angle, cx, cy)
                        node.modified()
                        if hasattr(node, "update"):
                            images.append(node)
                else:
                    for node in data:
                        if hasattr(node, "lock") and node.lock:
                            continue
                        start_angle = node.matrix.rotation
                        node.matrix.post_rotate(angle - start_angle, cx, cy)
                        node.modified()
                        if hasattr(node, "update"):
                            images.append(node)
            except ValueError:
                raise CommandSyntaxError
            for node in images:
                self.do_image_update(node)

        self.signal("refresh_scene", "Scene")
        return "elements", data

    @self.console_argument("scale_x", type=str, help=_("scale_x value"))
    @self.console_argument("scale_y", type=str, help=_("scale_y value"))
    @self.console_option("px", "x", type=self.length_x, help=_("scale x origin point"))
    @self.console_option("py", "y", type=self.length_y, help=_("scale y origin point"))
    @self.console_option(
        "absolute",
        "a",
        type=bool,
        action="store_true",
        help=_("scale to absolute size"),
    )
    @self.console_command(
        "scale",
        help=_("scale <scale> [<scale-y>]?"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_scale(
        command,
        channel,
        _,
        scale_x=None,
        scale_y=None,
        px=None,
        py=None,
        absolute=False,
        data=None,
        **kwargs,
    ):
        if scale_x is None:
            channel("----------")
            channel(_("Scale Values:"))
            i = 0
            for node in self.elems():
                name = str(node)
                if len(name) > 50:
                    name = name[:50] + "…"
                channel(
                    f"{i}: scale({node.matrix.value_scale_x()}, {node.matrix.value_scale_y()}) - {name}"
                )
                i += 1
            channel("----------")
            return
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No selected elements."))
            return
        # print (f"Start: {scale_x} ({type(scale_x).__name__}), {scale_y} ({type(scale_y).__name__})")
        factor = 1
        if scale_x.endswith("%"):
            factor = 0.01
            scale_x = scale_x[:-1]
        try:
            scale_x = factor * float(scale_x)
        except ValueError:
            scale_x = 1
        if scale_y is None:
            scale_y = scale_x
        else:
            factor = 1
            if scale_y.endswith("%"):
                factor = 0.01
                scale_y = scale_y[:-1]
            try:
                scale_y = factor * float(scale_y)
            except ValueError:
                scale_y = 1
        # print (f"End: {scale_x} ({type(scale_x).__name__}), {scale_y} ({type(scale_y).__name__})")

        bounds = Node.union_bounds(data)
        if px is None:
            px = (bounds[2] + bounds[0]) / 2.0
        if py is None:
            py = (bounds[3] + bounds[1]) / 2.0
        if scale_x == 0 or scale_y == 0:
            channel(_("Scaling by Zero Error"))
            return
        matrix = Matrix(f"scale({scale_x},{scale_y},{px},{py})")
        images = []
        with self.undoscope("Scale"):
            try:
                if not absolute:
                    for node in data:
                        if hasattr(node, "lock") and node.lock:
                            continue
                        node.matrix *= matrix
                        node.scaled(sx=scale_x, sy=scale_y, ox=px, oy=py)
                        if hasattr(node, "update"):
                            images.append(node)
                else:
                    for node in data:
                        if hasattr(node, "lock") and node.lock:
                            continue
                        osx = node.matrix.value_scale_x()
                        osy = node.matrix.value_scale_y()
                        nsx = scale_x / osx
                        nsy = scale_y / osy
                        matrix = Matrix(f"scale({nsx},{nsy},{px},{px})")
                        node.matrix *= matrix
                        node.scaled(sx=nsx, sy=nsy, ox=px, oy=py)
                        if hasattr(node, "update"):
                            images.append(node)
            except ValueError:
                raise CommandSyntaxError
            for node in images:
                self.do_image_update(node)
            self.process_keyhole_updates(None)
        self.signal("refresh_scene", "Scene")
        self.signal("modified_by_tool")
        return "elements", data

    @self.console_option(
        "new_area", "n", type=self.area, help=_("provide a new area to cover")
    )
    @self.console_option(
        "density", "d", type=int, help=_("Defines the interpolation density")
    )
    @self.console_command(
        "area",
        help=_("provides information about/changes the area of a selected element"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_area(
        command,
        channel,
        _,
        new_area=None,
        density=None,
        data=None,
        **kwargs,
    ):
        if density is None:
            density = 200
        if new_area is None:
            display_only = True
        else:
            if new_area == 0:
                channel(_("You shouldn't collapse a shape to a zero-sized thing"))
                return
            display_only = False
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No selected elements."))
            return
        total_area = 0
        if display_only:
            channel("----------")
            channel(_("Area values (Density={density})").format(density=density))

        units = ("mm", "cm", "in")
        square_unit = [0] * len(units)
        for idx, u in enumerate(units):
            value = float(Length(f"1{u}"))
            square_unit[idx] = value * value

        i = 0
        for elem in data:
            try:
                geometry = elem.as_geometry()
            except AttributeError:
                continue
            # this_length = geometry.length()
            this_area = geometry.area(density=density)

            if display_only:
                name = str(elem)
                if len(name) > 50:
                    name = name[:50] + "…"
                channel(f"{i}: {name}")
                for idx, u in enumerate(units):
                    this_area_local = this_area / square_unit[idx]
                    channel(
                        _(" Area= {area:.3f} {unit}²").format(
                            area=this_area_local, unit=u
                        )
                    )
            i += 1
            total_area += this_area
        if display_only:
            channel("----------")
        else:
            if total_area == 0:
                channel(_("You can't reshape a zero-sized shape"))
                return

            ratio = sqrt(new_area / total_area)
            self(f"scale {ratio}\n")

        return "elements", data
        # Do we have a new value to set? If yes scale by sqrt(of the fraction)

    @self.console_argument("tx", type=self.length_x, help=_("translate x value"))
    @self.console_argument("ty", type=self.length_y, help=_("translate y value"))
    @self.console_option(
        "absolute",
        "a",
        type=bool,
        action="store_true",
        help=_("translate to absolute position"),
    )
    @self.console_command(
        "translate",
        help=_("translate <tx> <ty>"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_translate(
        command, channel, _, tx, ty, absolute=False, data=None, **kwargs
    ):
        if tx is None:
            channel("----------")
            channel(_("Translate Values:"))
            i = 0
            for node in self.elems():
                name = str(node)
                if len(name) > 50:
                    name = name[:50] + "…"
                channel(
                    f"{i}: translate({node.matrix.value_trans_x():.1f}, {node.matrix.value_trans_y():.1f}) - {name}"
                )
                i += 1
            channel("----------")
            return
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No selected elements."))
            return
        if tx is None:
            tx = 0
        if ty is None:
            ty = 0
        changes = False
        matrix = Matrix.translate(tx, ty)
        with self.undoscope("Translate"):
            try:
                if not absolute:
                    for node in data:
                        if not node.can_move(self.lock_allows_move):
                            continue

                        node.matrix *= matrix
                        node.translated(tx, ty)
                        changes = True
                else:
                    for node in data:
                        if not node.can_move(self.lock_allows_move):
                            continue
                        otx = node.matrix.value_trans_x()
                        oty = node.matrix.value_trans_y()
                        ntx = tx - otx
                        nty = ty - oty
                        matrix = Matrix.translate(ntx, nty)
                        node.matrix *= matrix
                        node.translated(ntx, nty)
                        changes = True
            except ValueError:
                raise CommandSyntaxError
        if changes:
            self.signal("refresh_scene", "Scene")
            self.signal("modified_by_tool")
        return "elements", data

    @self.console_argument("tx", type=self.length_x, help=_("New x value"))
    @self.console_argument("ty", type=self.length_y, help=_("New y value"))
    @self.console_command(
        "position",
        help=_("position <tx> <ty>"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_position(
        command, channel, _, tx, ty, absolute=False, data=None, **kwargs
    ):
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No selected elements."))
            return
        if tx is None or ty is None:
            channel(_("You need to provide a new position."))
            return
        with self.undoscope("Position"):
            changes = False
            dbounds = Node.union_bounds(data)
            for node in data:
                if not node.can_move(self.lock_allows_move):
                    continue
                nbounds = node.bounds
                dx = tx - dbounds[0]
                dy = ty - dbounds[1]
                if dx != 0 or dy != 0:
                    node.matrix.post_translate(dx, dy)
                    # node.modified()
                    node.translated(dx, dy)
                    changes = True
            if changes:
                self.process_keyhole_updates(None)
                self.signal("refresh_scene", "Scene")
                self.signal("modified_by_tool")
        return "elements", data

    @self.console_command(
        "move_to_laser",
        help=_("translates the selected element to the laser head"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_move_to_laser(command, channel, _, data=None, **kwargs):
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No selected elements."))
            return
        tx, ty = self.device.current
        with self.undoscope("Translate to laser"):
            try:
                bounds = Node.union_bounds(data)
                otx = bounds[0]
                oty = bounds[1]
                ntx = tx - otx
                nty = ty - oty
                for node in data:
                    if not node.can_move(self.lock_allows_move):
                        continue
                    node.matrix.post_translate(ntx, nty)
                    # node.modified()
                    node.translated(ntx, nty)
            except ValueError:
                raise CommandSyntaxError
        return "elements", data

    @self.console_argument(
        "x_pos", type=self.length_x, help=_("x position for top left corner")
    )
    @self.console_argument(
        "y_pos", type=self.length_y, help=_("y position for top left corner")
    )
    @self.console_argument("width", type=self.length_x, help=_("new width of selected"))
    @self.console_argument(
        "height", type=self.length_y, help=_("new height of selected")
    )
    @self.console_command(
        "resize",
        help=_("resize <x-pos> <y-pos> <width> <height>"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_resize(
        command, channel, _, x_pos, y_pos, width, height, data=None, **kwargs
    ):
        if height is None:
            raise CommandSyntaxError
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No selected elements."))
            return
        area = Node.union_bounds(data)
        if area is None:
            channel(_("resize: nothing selected"))
            return
        x, y, x1, y1 = area
        w, h = x1 - x, y1 - y
        if w == 0 or h == 0:  # dot
            channel(_("resize: cannot resize a dot"))
            return
        sx = width / w
        sy = height / h
        if sx == 0 or sy == 0:
            channel(_("Invalid width/height"))
            return
        px = area[0]
        py = area[2]
        matrix = Matrix(f"scale({sx},{sy},{px},{py})")
        with self.undoscope("Resize"):
            images = []
            if sx != 1.0 or sy != 1.0:
                # Don't do anything if scale is 1
                for node in data:
                    if not hasattr(node, "matrix"):
                        continue
                    if hasattr(node, "lock") and node.lock:
                        continue
                    node.matrix *= matrix
                    node.modified()
                    if hasattr(node, "update") and node not in images:
                        images.append(node)

            # Calculate again
            area = Node.union_bounds(data)
            dx = x_pos - area[0]
            dy = y_pos - area[1]
            if dx != 0.0 or dy != 0.0:
                # Don't do anything if scale is 1
                for node in data:
                    if not hasattr(node, "matrix"):
                        continue
                    node.matrix.post_translate(dx, dy)
                    node.modified()
                    if hasattr(node, "update") and node not in images:
                        images.append(node)

            for node in images:
                self.do_image_update(node)
        self.signal("refresh_scene", "Scene")
        return "elements", data

    @self.console_argument("sx", type=float, help=_("scale_x value"))
    @self.console_argument("kx", type=float, help=_("skew_x value"))
    @self.console_argument("ky", type=float, help=_("skew_y value"))
    @self.console_argument("sy", type=float, help=_("scale_y value"))
    @self.console_argument("tx", type=self.length_x, help=_("translate_x value"))
    @self.console_argument("ty", type=self.length_y, help=_("translate_y value"))
    @self.console_command(
        "matrix",
        help=_("matrix <sx> <kx> <ky> <sy> <tx> <ty>"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_matrix(
        command, channel, _, sx, kx, ky, sy, tx, ty, data=None, **kwargs
    ):
        if data is None:
            data = list(self.elems(emphasized=True))
        if ty is None:
            channel("----------")
            channel(_("Matrix Values:"))
            i = 0
            for node in data:
                name = str(node)
                if len(name) > 50:
                    name = name[:50] + "…"
                channel(f"{i}: {str(node.matrix)} - {name}")
                i += 1
            channel("----------")
            return
        if len(data) == 0:
            channel(_("No selected elements."))
            return
        with self.undoscope("Matrix"):
            images = []
            try:
                # SVG 7.15.3 defines the matrix form as:
                # [a c  e]
                # [b d  f]
                m = Matrix(
                    sx,
                    kx,
                    ky,
                    sy,
                    tx,
                    ty,
                )
                for node in data:
                    if hasattr(node, "lock") and node.lock:
                        continue
                    node.matrix = Matrix(m)
                    node.modified()
                    if hasattr(node, "update"):
                        images.append(node)
            except ValueError:
                raise CommandSyntaxError
            for node in images:
                self.do_image_update(node)
        self.signal("refresh_scene", "Scene")
        return

    @self.console_command(
        "reset",
        help=_("reset affine transformations"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def reset(command, channel, _, data=None, **kwargs):
        if data is None:
            data = list(self.elems(emphasized=True))
        with self.undoscope("Reset"):
            images = []
            for e in data:
                if hasattr(e, "lock") and e.lock:
                    continue
                name = str(e)
                if len(name) > 50:
                    name = name[:50] + "…"
                channel(_("reset - {name}").format(name=name))
                e.matrix.reset()
                e.modified()
                if hasattr(e, "update"):
                    images.append(e)
            for e in images:
                self.do_image_update(e)
        self.signal("refresh_scene", "Scene")
        return "elements", data

    @self.console_command(
        "reify",
        help=_("reify affine transformations"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_reify(command, channel, _, data=None, **kwargs):
        if data is None:
            data = list(self.elems(emphasized=True))
        with self.undoscope("Reify"):
            for e in data:
                try:
                    if e.lock:
                        continue
                except AttributeError:
                    pass

                name = str(e)
                if len(name) > 50:
                    name = name[:50] + "…"
                try:
                    e.stroke_reify()
                except AttributeError:
                    pass

                try:
                    e.shape.reify()
                except AttributeError as err:
                    try:
                        e.path.reify()
                    except AttributeError:
                        channel(_("Couldn't reify - %s - %s") % (name, err))
                        return "elements", data
                try:
                    e.stroke_width_zero()
                except AttributeError:
                    pass
                e.altered()
                channel(_("reified - %s") % name)
        return "elements", data

    @self.console_command(
        "circle_arc_path",
        help=_("Convert paths to use circular arcs."),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_circ_arc_path(command, channel, _, data=None, **kwargs):
        if data is None:
            data = list(self.elems(emphasized=True))
        # _("Convert paths")
        with self.undoscope("Convert paths"):
            for e in data:
                try:
                    if e.lock:
                        continue
                except AttributeError:
                    pass
                if e.type == "elem path":
                    g = e.geometry
                    path = g.as_path()
                    path.approximate_bezier_with_circular_arcs()
                    e.geometry = Geomstr.svg(path)
                    e.altered()

        return "elements", data

    @self.console_command(
        "classify",
        help=_("classify elements into operations"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_classify(command, channel, _, data=None, **kwargs):
        if data is None:
            data = list(self.elems(emphasized=True))
            was_emphasized = True
            old_first = self.first_emphasized
        else:
            was_emphasized = False
            old_first = None
        if len(data) == 0:
            channel(_("No selected elements."))
            return
        with self.undoscope("Classify"):
            self.classify(data)
        if was_emphasized:
            for e in data:
                e.emphasized = True
            if len(data) == 1:
                data[0].focus()
            if old_first is not None and old_first in data:
                self.first_emphasized = old_first
            else:
                self.first_emphasized = None

        return "elements", data

    @self.console_command(
        "declassify",
        help=_("declassify selected elements"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def declassify(command, channel, _, data=None, **kwargs):
        if data is None:
            data = list(self.elems(emphasized=True))
            was_emphasized = True
            old_first = self.first_emphasized
        else:
            was_emphasized = False
            old_first = None
        if len(data) == 0:
            channel(_("No selected elements."))
            return
        self.remove_elements_from_operations(data)
        # restore emphasized flag as it is relevant for subsequent operations
        if was_emphasized:
            for e in data:
                e.emphasized = True
            if len(data) == 1:
                data[0].focus()
            if old_first is not None and old_first in data:
                self.first_emphasized = old_first
            else:
                self.first_emphasized = None
        return "elements", data

    @self.console_argument(
        "tolerance", type=str, help=_("Tolerance to stitch paths together")
    )
    @self.console_option(
        "keep",
        "k",
        type=bool,
        action="store_true",
        default=False,
        help=_("Keep original paths"),
    )
    @self.console_command(
        "stitch",
        help=_("stitch selected elements"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def stitched(
        command, channel, _, data=None, tolerance=None, keep=None, post=None, **kwargs
    ):
        def _prepare_stitching_params(channel, data, tolerance, keep):
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0:
                channel("There is nothing to be stitched together")
                return data, tolerance, keep, False
            if keep is None:
                keep = False
            if tolerance is None:
                tolerance_val = 0
            else:
                try:
                    tolerance_val = float(Length(tolerance))
                except ValueError as e:
                    channel(f"Invalid tolerance value: {tolerance}")
                    return data, tolerance, keep, False
            return data, tolerance_val, keep, True

        data, tolerance, keep, valid = _prepare_stitching_params(
            channel, data, tolerance, keep
        )
        if not valid:
            return
        s_data = stitcheable_nodes(data, tolerance)
        if not s_data:
            channel("No stitcheable nodes found")
            return

        geoms = []
        data_out = []
        to_be_deleted = []
        # _("Stitch paths")
        with self.undoscope("Stitch paths"):
            default_stroke = None
            default_strokewidth = None
            default_fill = None
            for node in s_data:
                geom: Geomstr = node.as_geometry()
                geoms.extend(iter(geom.as_contiguous()))
                if default_stroke is None and hasattr(node, "stroke"):
                    default_stroke = node.stroke
                if default_strokewidth is None and hasattr(node, "stroke_width"):
                    default_strokewidth = node.stroke_width
                to_be_deleted.append(node)
            prev_len = len(geoms)
            if geoms:
                result = stitch_geometries(geoms, tolerance)
                if result is None:
                    channel("Could not stitch anything")
                    return
                if not keep:
                    for node in to_be_deleted:
                        node.remove_node()
                for idx, g in enumerate(result):
                    node = self.elem_branch.add(
                        label=f"Stitch # {idx + 1}",
                        stroke=default_stroke,
                        stroke_width=default_strokewidth,
                        fill=default_fill,
                        geometry=g,
                        type="elem path",
                    )
                    data_out.append(node)
            new_len = len(data_out)
            channel(
                f"Sub-Paths before: {prev_len} -> consolidated to {new_len} sub-paths"
            )

        post.append(classify_new(data_out))
        self.set_emphasis(data_out)
        return "elements", data_out

    @self.console_argument("xpos", type=Length, help=_("X-Position of cross center"))
    @self.console_argument("ypos", type=Length, help=_("Y-Position of cross center"))
    @self.console_argument("diameter", type=Length, help=_("Diameter of cross"))
    @self.console_option(
        "circle",
        "c",
        type=bool,
        action="store_true",
        default=False,
        help=_("Draw a circle around cross"),
    )
    @self.console_option(
        "diagonal",
        "d",
        type=bool,
        action="store_true",
        default=False,
        help=_("Draw the cross diagonally"),
    )
    @self.console_command(
        "cross",
        help=_("Create a small cross at the given position"),
        input_type=None,
        output_type="elements",
    )
    def cross(
        command,
        channel,
        _,
        data=None,
        xpos=None,
        ypos=None,
        diameter=None,
        circle=None,
        diagonal=None,
        post=None,
        **kwargs,
    ):
        if xpos is None or ypos is None or diameter is None:
            channel(_("You need to provide center-point and diameter: cross x y d"))
            return
        try:
            xp = float(xpos)
            yp = float(ypos)
            dia = float(diameter)
        except ValueError:
            channel(_("Invalid values given"))
            return
        if circle is None:
            circle = False
        if diagonal is None:
            diagonal = False
        geom = Geomstr()
        if diagonal:
            sincos45 = dia / 2 * sqrt(2) / 2
            geom.line(
                complex(xp - sincos45, yp - sincos45),
                complex(xp + sincos45, yp + sincos45),
            )
            geom.line(
                complex(xp + sincos45, yp - sincos45),
                complex(xp - sincos45, yp + sincos45),
            )
        else:
            geom.line(complex(xp - dia / 2, yp), complex(xp + dia / 2, yp))
            geom.line(complex(xp, yp - dia / 2), complex(xp, yp + dia / 2))
        if circle:
            geom.append(Geomstr.circle(dia / 2, xp, yp))
        # _("Create cross") - hint for translator
        with self.undoscope("Create cross"):
            node = self.elem_branch.add(
                label=_("Cross at ({xp}, {yp})").format(
                    xp=xpos.length_mm, yp=ypos.length_mm
                ),
                geometry=geom,
                stroke=self.default_stroke,
                stroke_width=self.default_strokewidth,
                fill=None,
                type="elem path",
            )
            if data is None:
                data = []
            data.append(node)

            # Newly created! Classification needed?
            post.append(classify_new(data))
        self.signal("refresh_scene", "Scene")
        return "elements", data

    # --------------------------- END COMMANDS ------------------------------
