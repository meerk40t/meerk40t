"""
This is a giant list of console commands that deal with and often implement the elements system in the program.
"""

from math import sqrt, atan2

from meerk40t.core.node.node import Fillrule, Linecap, Linejoin, Node
from meerk40t.core.units import UNITS_PER_MM, UNITS_PER_PIXEL, UNITS_PER_POINT, Length
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
)

from .element_types import *


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
        circ = Ellipse(cx=float(x_pos), cy=float(y_pos), r=float(r_pos))
        if circ.is_degenerate():
            channel(_("Shape is degenerate."))
            return "elements", data
        node = self.elem_branch.add(
            shape=circ,
            type="elem ellipse",
            stroke=self.default_stroke,
            stroke_width=self.default_strokewidth,
            fill=self.default_fill,
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
        circ = Ellipse(r=float(r_pos))
        if circ.is_degenerate():
            channel(_("Shape is degenerate."))
            return "elements", data
        node = self.elem_branch.add(shape=circ, type="elem ellipse")
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

    @self.console_argument("x_pos", type=Length)
    @self.console_argument("y_pos", type=Length)
    @self.console_argument("rx_pos", type=Length)
    @self.console_argument("ry_pos", type=Length)
    @self.console_command(
        "ellipse",
        help=_("ellipse <cx> <cy> <rx> <ry>"),
        input_type=("elements", None),
        output_type="elements",
        all_arguments_required=True,
    )
    def element_ellipse(
        channel, _, x_pos, y_pos, rx_pos, ry_pos, data=None, post=None, **kwargs
    ):
        ellip = Ellipse(
            cx=float(x_pos), cy=float(y_pos), rx=float(rx_pos), ry=float(ry_pos)
        )
        if ellip.is_degenerate():
            channel(_("Shape is degenerate."))
            return "elements", data
        node = self.elem_branch.add(shape=ellip, type="elem ellipse")
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
        rect = Rect(x=x_pos, y=y_pos, width=width, height=height, rx=rx, ry=ry)
        if rect.is_degenerate():
            channel(_("Shape is degenerate."))
            return "elements", data
        node = self.elem_branch.add(shape=rect, type="elem rect")
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
        simple_line = SimpleLine(x0, y0, x1, y1)
        node = self.elem_branch.add(shape=simple_line, type="elem line")
        node.stroke = self.default_stroke
        node.stroke_width = self.default_strokewidth
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
        # A render operation will use the LaserRender class
        # and will re-calculate the element bounds
        make_raster = self.lookup("render-op/make_raster")
        if not make_raster:
            # No renderer is registered to perform render.
            return
        for e in data:
            e.set_dirty_bounds()
        # arbitrary bounds...
        bounds = (0, 0, float(Length("5cm")), float(Length("5cm")))
        image = make_raster(
            data,
            bounds=bounds,
            width=500,
            height=500,
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
        if prop is None:
            channel(_("You need to provide the property to set."))
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
            for e in data:
                if prop in ("x", "y"):
                    if hasattr(e, "can_move") and not e.can_move(self.lock_allows_move):
                        channel(
                            _("Element can not be moved: {name}").format(name=str(e))
                        )
                        continue
                    # We need to adjust the matrix
                    if hasattr(e, "matrix"):
                        dx = 0
                        dy = 0
                        otx = e.matrix.value_trans_x()
                        oty = e.matrix.value_trans_y()
                        if prop == "x":
                            dx = new_value - otx
                        else:
                            dy = new_value - oty
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
                            _("Element can not be scaled: {name}").format(name=str(e))
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

                    if "font" in prop:
                        # We need to force a recalculation of the underlying wxfont property
                        if hasattr(e, "wxfont"):
                            delattr(e, "wxfont")
                            text_elems.append(e)
                    if prop in ("mktext", "mkfont"):
                        for property_op in self.kernel.lookup_all("path_updater/.*"):
                            property_op(self.kernel.root, e)
                else:
                    channel(
                        _("Element {name} has no property {field}").format(
                            name=str(e), field=prop
                        )
                    )
                    continue
                e.altered()
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

    @self.console_command(
        "recalc", input_type=("elements", None), output_type="elements"
    )
    def recalc(command, channel, _, data=None, post=None, **kwargs):

        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            return
        for e in data:
            e.set_dirty_bounds()
        self.signal("refresh_scene", "Scene")
        self.validate_selected_area()

    @self.console_command(
        "simplify", input_type=("elements", None), output_type="elements"
    )
    def simplify_path(command, channel, _, data=None, post=None, **kwargs):

        if data is None:
            data = list(self.elems(emphasized=True))
        data_changed = list()
        if len(data) == 0:
            channel("Requires a selected polygon")
            return None
        for node in data:
            try:
                sub_before = len(list(node.as_path().as_subpaths()))
            except AttributeError:
                sub_before = 0

            changed, before, after = self.simplify_node(node)
            if changed:
                node.altered()
                try:
                    sub_after = len(list(node.as_path().as_subpaths()))
                except AttributeError:
                    sub_after = 0
                channel(
                    f"Simplified {node.type} ({node.label}): from {before} to {after}"
                )
                channel(f"Subpaths before: {sub_before} to {sub_after}")
                data_changed.append(node)
            else:
                channel(f"Could not simplify {node.type} ({node.label})")
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
        outer_path = data[0].as_path()
        inner_path = data[1].as_path()
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

    @self.console_command(
        "path",
        help=_("Convert any shapes to paths"),
        input_type="shapes",
        output_type="shapes",
    )
    def element_path_convert(data, **kwargs):
        paths = []
        for e in data:
            paths.append(abs(Path(e)))
        return "shapes", paths

    @self.console_command(
        "geomstr",
        help=_("Convert any element nodes to geomstr nodes"),
        input_type="elements",
        output_type="elements",
    )
    def element_path_convert(data, **kwargs):
        if data is None:
            return "elements", data
        if len(data) == 0:
            return "elements", data

        from meerk40t.tools.geomstr import Geomstr

        geomstr = Geomstr()
        for node in data:
            try:
                e = node.as_path()
            except AttributeError:
                continue
            for seg in e:
                if isinstance(seg, Line):
                    geomstr.line(complex(seg.start), complex(seg.end))
                elif isinstance(seg, QuadraticBezier):
                    geomstr.quad(
                        complex(seg.start), complex(seg.control), complex(seg.end)
                    )
                elif isinstance(seg, CubicBezier):
                    geomstr.cubic(
                        complex(seg.start),
                        complex(seg.control1),
                        complex(seg.control2),
                        complex(seg.end),
                    )
                elif isinstance(seg, Close):
                    geomstr.close()
                    geomstr.end()
            geomstr.end()
        if len(geomstr) == 0:
            return "elements", data
        try:
            fillrule = data[0].fillrule
        except AttributeError:
            fillrule = None
        try:
            cap = data[0].linecap
        except AttributeError:
            cap = None
        try:
            join = data[0].linejoin
        except AttributeError:
            join = None
        node = self.elem_branch.add(
            path=geomstr,
            type="elem geomstr",
            stroke=data[0].stroke,
            fill=data[0].fill,
            fillrule=fillrule,
            linecap=cap,
            linejoin=join,
        )
        self.set_emphasis([node])
        node.focus()
        data.append(node)
        return "elements", data

    @self.console_command(
        "path",
        help=_("Convert any element nodes to paths"),
        input_type="elements",
        output_type="shapes",
    )
    def element_path_convert(data, **kwargs):
        paths = []
        for node in data:
            try:
                e = node.as_path()
            except AttributeError:
                continue
            paths.append(e)
        return "shapes", paths

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
                if node.path.transform.is_identity():
                    channel(
                        f"{str(node)} (Identity): {node.path.d(transformed=not real)}"
                    )
                else:
                    channel(f"{str(node)}: {node.path.d(transformed=not real)}")
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
        except ValueError:
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
        for e in data:
            if hasattr(e, "lock") and e.lock:
                channel(_("Can't modify a locked element: {name}").format(name=str(e)))
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
        help=_("stroke-width <length>"),
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
        for e in data:
            if hasattr(e, "lock") and e.lock:
                channel(_("Can't modify a locked element: {name}").format(name=str(e)))
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
        if color == "none":
            self.set_start_time("stroke")
            for e in apply:
                if hasattr(e, "lock") and e.lock:
                    channel(
                        _("Can't modify a locked element: {name}").format(name=str(e))
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
                        _("Can't modify a locked element: {name}").format(name=str(e))
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
            self.signal("element_property_update", apply)
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
        elif color == "none":
            self.set_start_time("fill")
            for e in apply:
                if hasattr(e, "lock") and e.lock:
                    channel(
                        _("Can't modify a locked element: {name}").format(name=str(e))
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
                        _("Can't modify a locked element: {name}").format(name=str(e))
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
        _element = Rect(x=x_pos, y=y_pos, width=width, height=height)
        node = self.elem_branch.add(shape=_element, type="elem rect")
        node.stroke = Color("red")
        node.altered()
        self.set_emphasis([node])
        node.focus()
        if data is None:
            data = list()
        data.append(node)
        # Newly created! Classification needed?
        post.append(classify_new(data))
        return "elements", data

    @self.console_argument("angle", type=Angle.parse, help=_("angle to rotate by"))
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
                        index=i, angle=node.matrix.rotation.as_turns, name=name
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
            node.update(None)
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
            node.update(None)
        self.signal("refresh_scene", "Scene")
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
            this_area, this_length = self.get_information(elem, density=density)

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
            self.signal("refresh_scene", "Scene")
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
        try:
            area = self.selected_area()
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
            # Don't do anything if scale is 1
            if sx == 1.0 and sy == 1.0:
                scale_str = ""
            else:
                scale_str = f"scale({sx},{sy})"
            if x_pos == x and y_pos == y and scale_str == "":
                return
            #     trans1_str = ""
            #     trans2_str = ""
            # else:
            trans1_str = f"translate({round(x_pos, 7)},{round(y_pos, 7)})"
            trans2_str = f"translate({round(-x, 7)},{round(-y, 7)})"
            matrixstr = f"{trans1_str} {scale_str} {trans2_str}".strip()
            # channel(f"{matrixstr}")
            matrix = Matrix(matrixstr)
            if data is None:
                data = list(self.elems(emphasized=True))
            images = []
            for node in data:
                if hasattr(node, "lock") and node.lock:
                    channel(_("resize: cannot resize a locked element"))
                    continue
                node.matrix *= matrix
                node.modified()
                if hasattr(node, "update"):
                    images.append(node)
            for node in images:
                node.update(None)
            self.signal("refresh_scene", "Scene")
            return "elements", data
        except (ValueError, ZeroDivisionError, TypeError):
            raise CommandSyntaxError

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
            node.update(None)
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
            e.update(None)
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
        for e in data:
            try:
                if e.lock:
                    continue
            except AttributeError:
                pass
            if e.type == "elem path":
                e.path.approximate_bezier_with_circular_arcs()
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


    @self.console_option(
        "interpolation", "i", type=int, help=_("interpolation numbers")
    )
    @self.console_option(
        "tolerance", "t", type=float, help=_("tolerance to combine segments")
    )
    @self.console_option(
        "offset", "o", type=str, help=_("offset")
    )
    @self.console_command(
        "poly_copy",
        help=_("create a polygon out of the given paths"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_poly_copy(command, channel, _, interpolation=None, tolerance=None, offset = None, data=None, post=None, **kwargs):
        import numpy as np

        def normalizeVec(val1, val2):
            s = sqrt(val1 * val1 + val2 * val2)
            if s == 0:
                return val1, val2
            else:
                return val1 / s, val2 / s

        def offset_polygon(points, offset, outer_ccw = 1):

            num_points = len(points)
            newpoints = []

            for curr in range(num_points):
                # Circle around if needed
                prev = (curr + num_points - 1) % num_points
                next = (curr + 1) % num_points
                if curr in (0, num_points-1):
                    print (f"len= {num_points}: prev={prev}, curr={curr}, next={next}")

                vnX =  points[next][0] - points[curr][0]
                vnY =  points[next][1] - points[curr][1]
                vnnX, vnnY = normalizeVec(vnX, vnY)
                nnnX = vnnY
                nnnY = -vnnX

                vpX = points[curr][0] - points[prev][0]
                vpY = points[curr][1] - points[prev][1]
                vpnX, vpnY = normalizeVec(vpX, vpY)
                npnX = vpnY * outer_ccw
                npnY = -vpnX * outer_ccw

                bisX = (nnnX + npnX) * outer_ccw
                bisY = (nnnY + npnY) * outer_ccw

                bisnX, bisnY = normalizeVec(bisX,  bisY)
                bislen = offset / sqrt((1 + nnnX * npnX + nnnY * npnY)/2)
                newx = points[curr][0] + bislen * bisnX
                newy = points[curr][1] + bislen * bisnY
                newpoints.append((newx, newy))
            return newpoints

        def linearize_path(path):
            s = []
            for segment in path:
                t = type(segment).__name__
                if t == "Move":
                    s.append((segment.end[0], segment.end[1]))
                elif t in ("Line", "Close"):
                    s.append((segment.end[0], segment.end[1]))
                    print (f"Close called: {segment.end[0]:.0f}, {segment.end[1]:.0f} - First point was: {s[0][0]:.0f}, {s[0][1]:.0f}")
                else:
                    s.extend(
                        (np[0], np[1]) for np in segment.npoint(np.linspace(0, 1, interpolation))
                    )
            return s

        def simplify_polygon(poly, slope_tolerance):
            # Traverse back and look for same slope...
            last_slope = None
            lastpt = poly[-1]
            for idx in range(len(poly) - 2,  -1, -1):
                thispt = s[idx]
                dx = lastpt[0] - thispt[0]
                dy = lastpt[1] - thispt[1]
                if abs(dx) < 1E-6 and abs(dy) < 1E-6:
                    # identical points!
                    poly.pop(idx + 1)
                else:
                    this_slope = atan2(dy, dx)
                    # if abs(dx) <= 1E-8:
                    #     if dy > 0:
                    #         this_slope = float("inf")
                    #     else:
                    #         this_slope = float("-inf")
                    # else:
                    #     this_slope = dy / dx
                    if last_slope is not None:
                        if abs(last_slope - this_slope) < slope_tolerance:
                            # Combine segments, ie get rid of mid point
                            poly.pop(idx + 1)
                            this_slope = last_slope
                        # print (f"pt #{idx}: last={last_slope:.3f}, this={this_slope:.3f}")
                    last_slope = this_slope
                lastpt = thispt
            # lastpt = poly[-1]
            # thispt = poly[0]

        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            return "elements", data
        if tolerance is None:
            tolerance = 1E-3
        if interpolation is None:
            interpolation = 100
        if offset is None:
            offset = 0
        else:
            try:
                ll = Length(offset)
                offset = float(ll)
            except ValueError:
                offset = 0
        channel(f"Interpolating with {interpolation} points if necessary, tolerance={tolerance}, offset={Length(offset, digits=2, preferred_units='mm').preferred_length}")
        data_out = list()
        for node in data:
            if not hasattr(node, "as_path"):
                continue
            pth = node.as_path()
            for subpath in pth.as_subpaths():
                p = Path(subpath)
                s = linearize_path(p)
                oldlen = len(s)
                if oldlen > 1:
                    simplify_polygon(s, tolerance)
                newlen = len(s)
                channel (f"Length of shape, before: {oldlen}, after: {newlen}")
                if offset != 0:
                    ccw = 1
                    if offset < 0:
                        ccw = -1
                    s = offset_polygon(s, offset, ccw)

                shape = Polyline(s)
                if shape.is_degenerate():
                    continue
                newnode = self.elem_branch.add(shape=shape, type="elem polyline", stroke=node.stroke)
                data_out.append(newnode)

        # Newly created! Classification needed?
        if len(data_out) > 0:
            post.append(classify_new(data_out))
            self.signal("refresh_scene", "Scene")
        return "elements", data_out

    # --------------------------- END COMMANDS ------------------------------
