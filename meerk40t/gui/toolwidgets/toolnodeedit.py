import math
from copy import copy

import wx

from meerk40t.gui.icons import (
    STD_ICON_SIZE,
    icon_node_add,
    icon_node_append,
    icon_node_break,
    icon_node_close,
    icon_node_curve,
    icon_node_delete,
    icon_node_join,
    icon_node_line,
    icon_node_line_all,
    icon_node_smooth,
    icon_node_smooth_all,
    icon_node_symmetric,
)
from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.gui.scene.sceneconst import (
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
    RESPONSE_DROP,
)
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.gui.wxutils import get_matrix_scale
from meerk40t.svgelements import (
    Arc,
    Close,
    CubicBezier,
    Line,
    Move,
    Path,
    Point,
    Polygon,
    Polyline,
    QuadraticBezier,
)
from meerk40t.tools.geomstr import Geomstr

_ = wx.GetTranslation


class EditTool(ToolWidget):
    """
    Edit tool allows you to view and edit the nodes within a
    selected element in the scene. It can currently handle
    polylines / polygons and paths.
    """

    def __init__(self, scene, mode=None):
        ToolWidget.__init__(self, scene)
        self._listener_active = False
        self.nodes = []
        self.shape = None
        self.path = None
        self.element = None
        self.selected_index = None

        self.move_type = "node"
        self.node_type = "path"
        self.p1 = None
        self.p2 = None
        self.pen = wx.Pen()
        self.pen.SetColour(wx.BLUE)
        # wx.Colour(swizzlecolor(self.scene.context.elements.default_stroke))
        self.pen_ctrl = wx.Pen()
        self.pen_ctrl.SetColour(wx.CYAN)
        self.pen_ctrl_semi = wx.Pen()
        self.pen_ctrl_semi.SetColour(wx.GREEN)
        self.pen_highlight = wx.Pen()
        self.pen_highlight.SetColour(wx.RED)
        self.pen_highlight_line = wx.Pen()
        self.pen_highlight_line.SetColour(wx.Colour(255, 0, 0, 80))
        self.pen_selection = wx.Pen()
        self.pen_selection.SetColour(self.scene.colors.color_selection3)
        self.pen_selection.SetStyle(wx.PENSTYLE_SHORT_DASH)
        self.brush_highlight = wx.Brush(wx.RED_BRUSH)
        self.brush_normal = wx.Brush(wx.TRANSPARENT_BRUSH)
        # want to have sharp edges
        self.pen_selection.SetJoin(wx.JOIN_MITER)
        # "key": (routine, info, available for poly, available for path)
        self.commands = {
            "d": (self.delete_nodes, _("Delete"), True, True),
            "delete": (self.delete_nodes, _("Delete"), True, True),
            "l": (self.convert_to_line, _("Line"), False, True),
            "c": (self.convert_to_curve, _("Curve"), False, True),
            "s": (self.cubic_symmetrical, _("Symmetric"), False, True),
            "i": (self.insert_midpoint, _("Insert"), True, True),
            "insert": (self.insert_midpoint, _("Insert"), True, True),
            "a": (self.append_line, _("Append"), True, True),
            "b": (self.break_path, _("Break"), False, True),
            "j": (self.join_path, _("Join"), False, True),
            "o": (self.smoothen, _("Smooth"), False, True),
            "z": (self.toggle_close, _("Close path"), True, True),
            "v": (self.smoothen_all, _("Smooth all"), False, True),
            "w": (self.linear_all, _("Line all"), False, True),
            "p": (self.convert_to_path, _("To path"), True, False),
        }
        self.define_buttons()
        self.message = ""

    def define_buttons(self):
        def becomes_enabled(needs_selection, active_for_path, active_for_poly):
            def routine(*args):
                # print(
                #     f"Was asked to perform with {my_selection}, {my_active_poly}, {my_active_path} while {self.anyselected} + {self.node_type}"
                # )
                if self.element is None:
                    return False
                flag_sel = True
                flag_poly = False
                flag_path = False
                if my_selection and not self.anyselected:
                    flag_sel = False
                if my_active_poly and self.node_type == "polyline":
                    flag_poly = True
                if my_active_path and self.node_type == "path":
                    flag_path = True
                flag = flag_sel and (flag_path or flag_poly)
                return flag

            my_selection = needs_selection
            my_active_poly = active_for_poly
            my_active_path = active_for_path
            return routine

        def becomes_visible(active_for_path, active_for_poly):
            def routine(*args):
                # print(
                #     f"Was asked to perform with {my_active_poly}, {my_active_path} while {self.anyselected} + {self.node_type}"
                # )
                flag_poly = False
                flag_path = False
                if my_active_poly and self.node_type == "polyline":
                    flag_poly = True
                if my_active_path and self.node_type == "path":
                    flag_path = True
                flag = flag_path or flag_poly
                return flag

            my_active_path = active_for_path
            my_active_poly = active_for_poly
            return routine

        def do_action(code):
            def routine(*args):
                self.perform_action(mycode)

            mycode = code
            return routine

        cmd_icons = {
            # "command": [
            #           image, requires_selection,
            #           active_for_path, active_for_poly,
            #           "tooltiptext", button],
            "i": [
                icon_node_add,
                True,
                True,
                True,
                _("Insert point before"),
                _("Insert"),
            ],
            "a": [
                icon_node_append,
                False,
                True,
                True,
                _("Append point at end"),
                _("Append"),
            ],
            "d": [
                icon_node_delete,
                True,
                True,
                True,
                _("Delete point"),
                _("Delete"),
            ],
            "l": [
                icon_node_line,
                True,
                True,
                False,
                _("Make segment a line"),
                _("> Line"),
            ],
            "c": [
                icon_node_curve,
                True,
                True,
                False,
                _("Make segment a curve"),
                _("> Curve"),
            ],
            "s": [
                icon_node_symmetric,
                True,
                True,
                False,
                _("Make segment symmetrical"),
                _("Symmetric"),
            ],
            "j": [
                icon_node_join,
                True,
                True,
                False,
                _("Join two segments"),
                _("Join"),
            ],
            "b": [
                icon_node_break,
                True,
                True,
                False,
                _("Break segment apart"),
                _("Break"),
            ],
            "o": [
                icon_node_smooth,
                True,
                True,
                False,
                _("Smooth transit to adjacent segments"),
                _("Smooth"),
            ],
            "v": [
                icon_node_smooth_all,
                False,
                True,
                False,
                _("Convert all lines into smooth curves"),
                _("Very smooth"),
            ],
            "w": [
                icon_node_line_all,
                False,
                True,
                False,
                _("Convert all segments into lines"),
                _("Line all"),
            ],
            "z": [
                icon_node_close,
                False,
                True,
                True,
                _("Toggle closed status"),
                _("Close"),
            ],
            "p": [
                icon_node_smooth_all,
                False,
                False,
                True,
                _("Convert polyline to a path element"),
                _("To Path"),
            ],
        }
        icon_size = STD_ICON_SIZE
        for command, entry in cmd_icons.items():
            # print(command, f"button/secondarytool_edit/tool_{command}")
            self.scene.context.kernel.register(
                f"button/secondarytool_edit/tool_{command}",
                {
                    "label": entry[5],
                    "icon": entry[0],
                    "tip": entry[4],
                    "help": "nodeedit",
                    "action": do_action(command),
                    "size": icon_size,
                    "rule_enabled": becomes_enabled(entry[1], entry[2], entry[3]),
                    "rule_visible": becomes_visible(entry[2], entry[3]),
                },
            )

    def enable_rules(self):
        toolbar = self.scene.context.lookup("ribbonbar/tools")
        if toolbar is not None:
            toolbar.apply_enable_rules()

    def final(self, context):
        """
        Shutdown routine for widget that unregisters the listener routines
        and closes the toolbar window.
        This could be called more than once which, if not dealt with, will
        cause a console warning message
        """
        if self._listener_active:
            self.scene.context.unlisten("emphasized", self.on_emphasized_changed)
            self.scene.context.unlisten("nodeedit", self.on_signal_nodeedit)
        self._listener_active = False
        self.scene.request_refresh()

    def init(self, context):
        """
        Startup routine for widget that establishes the listener routines
        and opens the toolbar window
        """
        self.scene.context.listen("emphasized", self.on_emphasized_changed)
        self.scene.context.listen("nodeedit", self.on_signal_nodeedit)
        self._listener_active = True

    def on_emphasized_changed(self, origin, *args):
        """
        Receiver routine for scene selection signal
        """
        selected_node = self.scene.context.elements.first_element(emphasized=True)
        if selected_node is not self.element:
            self.calculate_points(selected_node)
            self.scene.request_refresh()
            self.enable_rules()

    def set_pen_widths(self):
        """
        Calculate the pen widths according to the current scene zoom levels,
        so that they always appear 1 pixel wide - except for the
        pen associated to the path segment outline that gets a 2 pixel wide 'halo'
        """

        def set_width_pen(pen, width):
            try:
                try:
                    pen.SetWidth(width)
                except TypeError:
                    pen.SetWidth(int(width))
            except OverflowError:
                pass  # Exceeds 32 bit signed integer.

        matrix = self.scene.widget_root.scene_widget.matrix
        linewidth = 1.0 / get_matrix_scale(matrix)
        if linewidth < 1:
            linewidth = 1
        set_width_pen(self.pen, linewidth)
        set_width_pen(self.pen_highlight, linewidth)
        set_width_pen(self.pen_ctrl, linewidth)
        set_width_pen(self.pen_ctrl_semi, linewidth)
        set_width_pen(self.pen_selection, linewidth)
        value = linewidth
        if self.element is not None and hasattr(self.element, "stroke_width"):
            if self.element.stroke_width is not None:
                value = self.element.stroke_width
        value += 4 * linewidth
        set_width_pen(self.pen_highlight_line, value)

    def calculate_points(self, selected_node):
        """
        Parse the element and create a list of dictionaries with relevant information required for display and logic
        """
        self.message = ""

        self.element = selected_node
        self.selected_index = None
        self.nodes = []
        # print ("After load:")
        # self.debug_path()
        if selected_node is None:
            return
        self.shape = None
        self.path = None
        if selected_node.type == "elem polyline":
            self.node_type = "polyline"
            try:
                self.shape = selected_node.shape
            except AttributeError:
                return
            start = 0
            for idx, pt in enumerate(self.shape.points):
                self.nodes.append(
                    {
                        "prev": None,
                        "next": None,
                        "point": pt,
                        "segment": None,
                        "path": self.shape,
                        "type": "point",
                        "connector": -1,
                        "selected": False,
                        "segtype": "L",
                        "start": start,
                    }
                )
        else:
            self.node_type = "path"
            #    self.path = selected_node.geometry.as_path()
            if hasattr(selected_node, "path"):
                self.path = selected_node.path
            elif hasattr(selected_node, "geometry"):
                self.path = selected_node.geometry.as_path()
            elif hasattr(selected_node, "as_geometry"):
                self.path = selected_node.as_geometry().as_path()
            elif hasattr(selected_node, "as_path"):
                self.path = selected_node.as_path()
            else:
                return
            # print(self.path.d(), self.path)
            if self.path is None:
                return
            self.path.approximate_arcs_with_cubics()
            # print(self.path.d(), self.path)
            # try:
            # except AttributeError:
            #    return
            # print (f"Path: {str(path)}")
            prev_seg = None
            start = 0
            # Idx of last point
            l_idx = 0
            for idx, segment in enumerate(self.path):
                # print(
                #     f"{idx}# {type(segment).__name__} - S={segment.start} - E={segment.end}"
                # )
                if idx < len(self.path) - 1:
                    next_seg = self.path[idx + 1]
                else:
                    next_seg = None
                if isinstance(segment, Move):
                    if idx != start:
                        start = idx

                if isinstance(segment, Close):
                    # We don't do anything with a Close - it's drawn anyway
                    pass
                elif isinstance(segment, Line):
                    self.nodes.append(
                        {
                            "prev": prev_seg,
                            "next": next_seg,
                            "point": segment.end,
                            "segment": segment,
                            "path": self.path,
                            "type": "point",
                            "connector": -1,
                            "selected": False,
                            "segtype": "Z" if isinstance(segment, Close) else "L",
                            "start": start,
                            "pathindex": idx,
                        }
                    )
                    nidx = len(self.nodes) - 1
                elif isinstance(segment, Move):
                    self.nodes.append(
                        {
                            "prev": prev_seg,
                            "next": next_seg,
                            "point": segment.end,
                            "segment": segment,
                            "path": self.path,
                            "type": "point",
                            "connector": -1,
                            "selected": False,
                            "segtype": "M",
                            "start": start,
                            "pathindex": idx,
                        }
                    )
                    nidx = len(self.nodes) - 1
                elif isinstance(segment, QuadraticBezier):
                    self.nodes.append(
                        {
                            "prev": prev_seg,
                            "next": next_seg,
                            "point": segment.end,
                            "segment": segment,
                            "path": self.path,
                            "type": "point",
                            "connector": -1,
                            "selected": False,
                            "segtype": "Q",
                            "start": start,
                            "pathindex": idx,
                        }
                    )
                    nidx = len(self.nodes) - 1
                    self.nodes.append(
                        {
                            "prev": None,
                            "next": None,
                            "point": segment.control,
                            "segment": segment,
                            "path": self.path,
                            "type": "control",
                            "connector": nidx,
                            "selected": False,
                            "segtype": "",
                            "start": start,
                            "pathindex": idx,
                        }
                    )
                elif isinstance(segment, CubicBezier):
                    self.nodes.append(
                        {
                            "prev": prev_seg,
                            "next": next_seg,
                            "point": segment.end,
                            "segment": segment,
                            "path": self.path,
                            "type": "point",
                            "connector": -1,
                            "selected": False,
                            "segtype": "C",
                            "start": start,
                            "pathindex": idx,
                        }
                    )
                    nidx = len(self.nodes) - 1
                    self.nodes.append(
                        {
                            "prev": None,
                            "next": None,
                            "point": segment.control1,
                            "segment": segment,
                            "path": self.path,
                            "type": "control",
                            "connector": l_idx,
                            "selected": False,
                            "segtype": "",
                            "start": start,
                            "pathindex": idx,
                        }
                    )
                    self.nodes.append(
                        {
                            "prev": None,
                            "next": None,
                            "point": segment.control2,
                            "segment": segment,
                            "path": self.path,
                            "type": "control",
                            "connector": nidx,
                            "selected": False,
                            "segtype": "",
                            "start": start,
                            "pathindex": idx,
                        }
                    )
                    # midp = segment.point(0.5)
                    midp = self.get_bezier_point(segment, 0.5)
                    self.nodes.append(
                        {
                            "prev": None,
                            "next": None,
                            "point": midp,
                            "segment": segment,
                            "path": self.path,
                            "type": "midpoint",
                            "connector": -1,
                            "selected": False,
                            "segtype": "",
                            "start": start,
                            "pathindex": idx,
                        }
                    )
                elif isinstance(segment, Arc):
                    self.nodes.append(
                        {
                            "prev": prev_seg,
                            "next": next_seg,
                            "point": segment.end,
                            "segment": segment,
                            "path": self.path,
                            "type": "point",
                            "connector": -1,
                            "selected": False,
                            "segtype": "A",
                            "start": start,
                            "pathindex": idx,
                        }
                    )
                    nidx = len(self.nodes) - 1
                    self.nodes.append(
                        {
                            "prev": None,
                            "next": None,
                            "point": segment.center,
                            "segment": segment,
                            "path": self.path,
                            "type": "control",
                            "connector": nidx,
                            "selected": False,
                            "segtype": "",
                            "start": start,
                            "pathindex": idx,
                        }
                    )
                prev_seg = segment
                l_idx = nidx
        for cmd in self.commands:
            action = self.commands[cmd]
            if self.node_type == "path" and action[3]:
                if self.message:
                    self.message += ", "
                self.message += f"{cmd}: {action[1]}"
            if self.node_type == "polyline" and action[2]:
                if self.message:
                    self.message += ", "
                self.message += f"{cmd}: {action[1]}"

        self.enable_rules()

    def calc_and_draw(self, gc):
        """
        Takes a svgelements.Path and converts it to a GraphicsContext.Graphics Path
        """

        def deal_with_segment(seg, init):
            if isinstance(seg, Line):
                if not init:
                    init = True
                    ptx, pty = node.matrix.point_in_matrix_space(seg.start)
                    p.MoveToPoint(ptx, pty)
                ptx, pty = node.matrix.point_in_matrix_space(seg.end)
                p.AddLineToPoint(ptx, pty)
            elif isinstance(seg, Close):
                if not init:
                    init = True
                    ptx, pty = node.matrix.point_in_matrix_space(seg.start)
                    p.MoveToPoint(ptx, pty)
                p.CloseSubpath()
            elif isinstance(seg, QuadraticBezier):
                if not init:
                    init = True
                    ptx, pty = node.matrix.point_in_matrix_space(seg.start)
                    p.MoveToPoint(ptx, pty)
                ptx, pty = node.matrix.point_in_matrix_space(seg.end)
                c1x, c1y = node.matrix.point_in_matrix_space(seg.control)
                p.AddQuadCurveToPoint(c1x, c1y, ptx, pty)
            elif isinstance(seg, CubicBezier):
                if not init:
                    init = True
                    ptx, pty = node.matrix.point_in_matrix_space(seg.start)
                    p.MoveToPoint(ptx, pty)
                ptx, pty = node.matrix.point_in_matrix_space(seg.end)
                c1x, c1y = node.matrix.point_in_matrix_space(seg.control1)
                c2x, c2y = node.matrix.point_in_matrix_space(seg.control2)
                p.AddCurveToPoint(c1x, c1y, c2x, c2y, ptx, pty)
            elif isinstance(seg, Arc):
                if not init:
                    init = True
                    ptx, pty = node.matrix.point_in_matrix_space(seg.start)
                    p.MoveToPoint(ptx, pty)
                for curve in seg.as_cubic_curves():
                    ptx, pty = node.matrix.point_in_matrix_space(curve.end)
                    c1x, c1y = node.matrix.point_in_matrix_space(curve.control1)
                    c2x, c2y = node.matrix.point_in_matrix_space(curve.control2)
                    p.AddCurveToPoint(c1x, c1y, c2x, c2y, ptx, pty)
            return init

        node = self.element
        p = gc.CreatePath()
        if self.node_type == "polyline":
            for idx, entry in enumerate(self.nodes):
                ptx, pty = node.matrix.point_in_matrix_space(entry["point"])
                # print (f"Idx={idx}, selected={entry['selected']}, prev={'-' if idx == 0 else self.nodes[idx-1]['selected']}")
                if idx == 1 and (
                    self.nodes[0]["selected"] or self.nodes[1]["selected"]
                ):
                    p.AddLineToPoint(ptx, pty)
                elif idx == 0 or not entry["selected"]:
                    p.MoveToPoint(ptx, pty)
                else:
                    p.AddLineToPoint(ptx, pty)
        else:
            # path = self.path
            init = False
            for idx, entry in enumerate(self.nodes):
                if not entry["type"] == "point":
                    continue
                # treatment = ""
                e = entry["segment"]
                if isinstance(e, Move):
                    if entry["selected"]:
                        # The next segment needs to be highlighted...
                        ptx, pty = node.matrix.point_in_matrix_space(e.end)
                        p.MoveToPoint(ptx, pty)
                        e = entry["next"]
                        init = deal_with_segment(e, init)
                        # treatment = "move+next"
                    else:
                        ptx, pty = node.matrix.point_in_matrix_space(e.end)
                        p.MoveToPoint(ptx, pty)
                        init = True
                        # treatment = "move"
                elif not entry["selected"]:
                    ptx, pty = node.matrix.point_in_matrix_space(e.end)
                    p.MoveToPoint(ptx, pty)
                    init = True
                    # treatment = "nonselected"
                else:
                    init = deal_with_segment(e, init)
                    # treatment = "selected"
                # print (f"#{idx} {entry['type']} got treatment: {treatment}")

        gc.SetPen(self.pen_highlight_line)
        gc.DrawPath(p)

    def process_draw(self, gc: wx.GraphicsContext):
        """
        Widget-Routine to draw the different elements on the provided GraphicContext
        """

        def draw_selection_rectangle():
            x0 = min(self.p1.real, self.p2.real)
            y0 = min(self.p1.imag, self.p2.imag)
            x1 = max(self.p1.real, self.p2.real)
            y1 = max(self.p1.imag, self.p2.imag)
            gc.SetPen(self.pen_selection)
            gc.SetBrush(wx.TRANSPARENT_BRUSH)
            gc.DrawRectangle(x0, y0, x1 - x0, y1 - y0)

        if not self.nodes:
            return
        self.set_pen_widths()
        if self.p1 is not None and self.p2 is not None:
            # Selection mode!
            draw_selection_rectangle()
            return
        offset = 5
        s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
        offset /= s
        gc.SetBrush(wx.TRANSPARENT_BRUSH)
        idx = -1
        node = self.element
        self.calc_and_draw(gc)
        for entry in self.nodes:
            idx += 1
            ptx, pty = node.matrix.point_in_matrix_space(entry["point"])
            if entry["type"] == "point":
                if idx == self.selected_index or entry["selected"]:
                    gc.SetPen(self.pen_highlight)
                    gc.SetBrush(self.brush_highlight)
                    factor = 1.25
                else:
                    gc.SetPen(self.pen)
                    gc.SetBrush(self.brush_normal)
                    factor = 1
                gc.DrawEllipse(
                    ptx - factor * offset,
                    pty - factor * offset,
                    offset * 2 * factor,
                    offset * 2 * factor,
                )
            elif entry["type"] == "control":
                if idx == self.selected_index or entry["selected"]:
                    factor = 1.25
                    gc.SetPen(self.pen_highlight)
                else:
                    factor = 1
                    gc.SetPen(self.pen_ctrl)
                    # Do we have a second controlpoint at the same segment?
                    if isinstance(entry["segment"], CubicBezier):
                        orgnode = None
                        if idx > 0 and self.nodes[idx - 1]["type"] == "point":
                            orgnode = self.nodes[idx - 1]
                        elif idx > 1 and self.nodes[idx - 2]["type"] == "point":
                            orgnode = self.nodes[idx - 2]
                        if orgnode is not None and orgnode["selected"]:
                            gc.SetPen(self.pen_ctrl_semi)
                pattern = [
                    (ptx - factor * offset, pty),
                    (ptx, pty + factor * offset),
                    (ptx + factor * offset, pty),
                    (ptx, pty - factor * offset),
                    (ptx - factor * offset, pty),
                ]
                gc.DrawLines(pattern)
                if 0 <= entry["connector"] < len(self.nodes):
                    orgnode = self.nodes[entry["connector"]]
                    org_pt = orgnode["point"]
                    org_ptx, org_pty = node.matrix.point_in_matrix_space(org_pt)
                    pattern = [(ptx, pty), (org_ptx, org_pty)]
                    gc.DrawLines(pattern)
            elif entry["type"] == "midpoint":
                if idx == self.selected_index or entry["selected"]:
                    factor = 1.25
                    gc.SetPen(self.pen_highlight)
                else:
                    factor = 1
                    gc.SetPen(self.pen_ctrl)
                pattern = [
                    (ptx - factor * offset, pty),
                    (ptx, pty + factor * offset),
                    (ptx + factor * offset, pty),
                    (ptx, pty - factor * offset),
                    (ptx - factor * offset, pty),
                ]
                gc.DrawLines(pattern)

    def done(self):
        """
        We are done with node editing, so shutdown stuff
        """
        self.scene.pane.tool_active = False
        self.scene.pane.modif_active = False
        self.scene.pane.suppress_selection = False
        self.p1 = None
        self.p2 = None
        self.move_type = "node"
        self.scene.context("tool none\n")
        self.scene.context.signal("statusmsg", "")
        self.scene.context.elements.validate_selected_area()
        self.scene.request_refresh()

    def modify_element(self, reload=True):
        """
        Central routine that tells the system that the node was
        changed, if 'reload' is set to True then it requires
        reload/recalculation of the properties (e.g. after the
        segment structure of a path was changed)
        """
        if self.element is None:
            return
        if self.shape is not None:
            self.element.geometry = Geomstr.svg(Path(self.shape))
        elif self.path is not None:
            self.element.geometry = Geomstr.svg(self.path)
        self.element.altered()
        try:
            __ = self.element.bbox()
        except AttributeError:
            pass
        self.scene.context.elements.validate_selected_area()
        self.scene.request_refresh()
        self.scene.context.signal("element_property_reload", [self.element])
        if reload:
            self.calculate_points(self.element)
            self.scene.request_refresh()
            self.enable_rules()

    def clear_selection(self):
        """
        Clears the selection
        """
        if self.nodes is not None:
            for entry in self.nodes:
                entry["selected"] = False
        self.enable_rules()

    def first_segment_in_subpath(self, index):
        """
        Provides the first non-move/close segment in the subpath
        to which the segment at location index belongs to
        """
        result = None
        if not self.element is None and hasattr(self.element, "path"):
            for idx in range(index, -1, -1):
                seg = self.path[idx]
                if isinstance(seg, (Move, Close)):
                    break
                result = seg
        return result

    def last_segment_in_subpath(self, index):
        """
        Provides the last non-move/close segment in the subpath
        to which the segment at location index belongs to
        """
        result = None
        if not self.element is None and hasattr(self.element, "path"):
            for idx in range(index, len(self.path)):
                seg = self.path[idx]
                if isinstance(seg, (Move, Close)):
                    break
                result = seg
        return result

    def is_closed_subpath(self, index):
        """
        Provides the last segment in the subpath
        to which the segment at location index belongs to
        """
        result = False
        if not self.element is None and hasattr(self.element, "path"):
            for idx in range(index, len(self.path)):
                seg = self.path[idx]
                if isinstance(seg, Move):
                    break
                if isinstance(seg, Close):
                    result = True
                    break
        return result

    def convert_to_path(self):
        """
        Converts a polyline element to a path and reloads the scene
        """
        if self.element is None or hasattr(self.element, "path"):
            return
        node = self.element
        oldstuff = []
        for attrib in ("stroke", "fill", "stroke_width", "stroke_scaled"):
            if hasattr(node, attrib):
                oldval = getattr(node, attrib, None)
                oldstuff.append([attrib, oldval])
        try:
            path = node.as_path()
            # There are some challenges around the treatment
            # of arcs within svgelements, so let's circumvent
            # them for the time being (until resolved)
            # by replacing arc segments with cubic Béziers
            if node.type in ("elem path", "elem ellipse"):
                path.approximate_arcs_with_cubics()
        except AttributeError:
            return
        newnode = node.replace_node(path=path, type="elem path")
        for item in oldstuff:
            setattr(newnode, item[0], item[1])
        newnode.altered()
        self.element = newnode
        self.shape = None
        self.path = path
        self.modify_element(reload=True)

    def toggle_close(self):
        """
        Toggle the closed status for a polyline or path element
        """
        if self.element is None or self.nodes is None:
            return
        modified = False
        if self.node_type == "polyline":
            dist = (self.shape.points[0].x - self.shape.points[-1].x) ** 2 + (
                self.shape.points[0].y - self.shape.points[-1].y
            ) ** 2
            if dist < 1:  # Closed
                newshape = Polyline(self.shape)
                if len(newshape.points) > 2:
                    newshape.points.pop(-1)
            else:
                newshape = Polygon(self.shape)
            self.shape = newshape
            modified = True
        else:
            dealt_with = []
            if not self.anyselected:
                # Let's select the last point, so the last segment will be closed/opened
                for idx in range(len(self.nodes) - 1, -1, -1):
                    entry = self.nodes[idx]
                    if entry["type"] == "point":
                        entry["selected"] = True
                        break

            for idx in range(len(self.nodes) - 1, -1, -1):
                entry = self.nodes[idx]
                if entry["selected"] and entry["type"] == "point":
                    # What's the index of the last selected element
                    # Have we dealt with that before? i.e. not multiple toggles.
                    segstart = entry["start"]
                    if segstart in dealt_with:
                        continue
                    dealt_with.append(segstart)
                    # Let's establish the last segment in the path
                    prevseg = None
                    is_closed = False
                    firstseg = None
                    for sidx in range(segstart, len(self.path), 1):
                        seg = self.path[sidx]
                        if isinstance(seg, Move) and prevseg is None:
                            # Not the one at the very beginning!
                            continue
                        if isinstance(seg, Move):
                            # Ready
                            break
                        if isinstance(seg, Close):
                            # Ready
                            is_closed = True
                            break
                        if firstseg is None:
                            firstseg = seg
                        lastidx = sidx
                        prevseg = seg
                    if firstseg is not None and not is_closed:
                        dist = firstseg.start.distance_to(prevseg.end)
                        if dist < 1:
                            lastidx -= 1
                            is_closed = True
                    # else:
                    #     dist = 1e6
                    if is_closed:
                        # it's enough just to delete it...
                        del self.path[lastidx + 1]
                        modified = True
                    else:
                        # Need to insert a Close segment
                        # print(f"Inserting a close, dist={dist:.2f}")
                        # print(
                        #     f"First seg, idx={segstart}, type={type(firstseg).__name__}"
                        # )
                        # print(f"Last seg, idx={lastidx}, type={type(prevseg).__name__}")
                        newseg = Close(
                            start=Point(prevseg.end.x, prevseg.end.y),
                            end=Point(prevseg.end.x, prevseg.end.y),
                        )
                        self.path.insert(lastidx + 1, newseg)
                        modified = True

        if modified:
            self.modify_element(True)

    @staticmethod
    def get_bezier_point(segment, t):
        """
        Provide a point on the cubic Bézier curve for t (0 <= t <= 1)
        Args:
            segment (PathSegment): a cubic bezier
            t (float): (0 <= t <= 1)
        Computation: b(t) = (1-t)^3 * P0 + 3*(1-t)^2*t*P1 + 3*(1-t)*t^2*P2 + t^3 * P3
        """
        p0 = segment.start
        p1 = segment.control1
        p2 = segment.control2
        p3 = segment.end
        result = (
            (1 - t) ** 3 * p0
            + 3 * (1 - t) ** 2 * t * p1
            + 3 * (1 - t) * t**2 * p2
            + t**3 * p3
        )
        return result

    @staticmethod
    def revise_bezier_to_point(segment, midpoint, change_2nd_control=False):
        """
        Adjust the two control points for a cubic Bézier segment,
        so that the given point will lie on the cubic Bézier curve for t=0.5
        Args:
            segment (PathSegment): a cubic bezier segment to be amended
            midpoint (Point): the new point
            change_2nd_control: modify the 2nd control point, rather than the first
        Computation: b(t) = (1-t)^3 * P0 + 3*(1-t)^2*t*P1 + 3*(1-t)*t^2*P2 + t^3 * P3
        """
        t = 0.5
        p0 = segment.start
        p1 = segment.control1
        p2 = segment.control2
        p3 = segment.end
        if change_2nd_control:
            factor = 1 / (3 * (1 - t) * t**2)
            result = (
                midpoint - (1 - t) ** 3 * p0 - 3 * (1 - t) ** 2 * t * p1 - t**3 * p3
            ) * factor
            segment.control2 = result
        else:
            factor = 1 / (3 * (1 - t) ** 2 * t)
            result = (
                midpoint - (1 - t) ** 3 * p0 - 3 * (1 - t) * t**2 * p2 - t**3 * p3
            ) * factor
            segment.control1 = result

    def adjust_midpoint(self, index):
        """
        Computes and sets the midpoint of a cubic bezier segment
        """
        for j in range(3):
            k = index + 1 + j
            if k < len(self.nodes) and self.nodes[k]["type"] == "midpoint":
                self.nodes[k]["point"] = self.get_bezier_point(
                    self.nodes[index]["segment"], 0.5
                )
                break

    def smoothen(self):
        """
        Smoothen a circular bezier segment to adjacent segments, i.e. adjust
        the control points so that they are an extension of the previous/next segment
        """
        if self.element is None or self.nodes is None:
            return
        modified = False
        if self.node_type == "polyline":
            # Not valid for a polyline Could make a path now but that might be more than the user expected...
            return
        for entry in self.nodes:
            if entry["selected"] and entry["segtype"] == "C":  # Cubic Bezier only
                segment = entry["segment"]
                pt_start = segment.start
                pt_end = segment.end
                other_segment = entry["prev"]
                if other_segment is not None:
                    if isinstance(other_segment, Line):
                        other_pt_x = other_segment.start.x
                        other_pt_y = other_segment.start.y
                        dx = pt_start.x - other_pt_x
                        dy = pt_start.y - other_pt_y
                        segment.control1.x = pt_start.x + 0.25 * dx
                        segment.control1.y = pt_start.y + 0.25 * dy
                        modified = True
                    elif isinstance(other_segment, CubicBezier):
                        other_pt_x = other_segment.control2.x
                        other_pt_y = other_segment.control2.y
                        dx = pt_start.x - other_pt_x
                        dy = pt_start.y - other_pt_y
                        segment.control1.x = pt_start.x + dx
                        segment.control1.y = pt_start.y + dy
                        modified = True
                    elif isinstance(other_segment, QuadraticBezier):
                        other_pt_x = other_segment.control.x
                        other_pt_y = other_segment.control.y
                        dx = pt_start.x - other_pt_x
                        dy = pt_start.y - other_pt_y
                        segment.control1.x = pt_start.x + dx
                        segment.control1.y = pt_start.y + dy
                        modified = True
                    elif isinstance(other_segment, Arc):
                        # We need the tangent in the end-point,
                        other_pt_x = other_segment.end.x
                        other_pt_y = other_segment.end.y
                        dx = pt_start.x - other_pt_x
                        dy = pt_start.y - other_pt_y
                        segment.control1.x = pt_start.x + dx
                        segment.control1.y = pt_start.y + dy
                        modified = True
                other_segment = entry["next"]
                if other_segment is not None:
                    if isinstance(other_segment, Line):
                        other_pt_x = other_segment.end.x
                        other_pt_y = other_segment.end.y
                        dx = pt_end.x - other_pt_x
                        dy = pt_end.y - other_pt_y
                        segment.control2.x = pt_end.x + 0.25 * dx
                        segment.control2.y = pt_end.y + 0.25 * dy
                        modified = True
                    elif isinstance(other_segment, CubicBezier):
                        other_pt_x = other_segment.control1.x
                        other_pt_y = other_segment.control1.y
                        dx = pt_end.x - other_pt_x
                        dy = pt_end.y - other_pt_y
                        segment.control2.x = pt_end.x + dx
                        segment.control2.y = pt_end.y + dy
                        modified = True
                    elif isinstance(other_segment, QuadraticBezier):
                        other_pt_x = other_segment.control.x
                        other_pt_y = other_segment.control.y
                        dx = pt_end.x - other_pt_x
                        dy = pt_end.y - other_pt_y
                        segment.control2.x = pt_end.x + dx
                        segment.control2.y = pt_end.y + dy
                        modified = True
                    elif isinstance(other_segment, Arc):
                        # We need the tangent in the end-point,
                        other_pt_x = other_segment.start.x
                        other_pt_y = other_segment.start.y
                        dx = pt_end.x - other_pt_x
                        dy = pt_end.y - other_pt_y
                        segment.control2.x = pt_end.x + dx
                        segment.control2.y = pt_end.y + dy
                        modified = True
        if modified:
            self.modify_element(True)

    def smoothen_all(self):
        """
        Convert all segments of the path that are not cubic Béziers into
        such segments and apply the same smoothen logic as in smoothen(),
        i.e. adjust the control points of two neighbouring segments
        so that the three points
        'prev control2' - 'prev/end=next start' - 'next control1'
        are collinear
        """
        if self.element is None or self.nodes is None:
            return
        modified = False
        if self.node_type == "polyline":
            # Not valid for a polyline Could make a path now but that might be more than the user expected...
            return
        # Pass 1 - make all lines a cubic bezier
        for idx, segment in enumerate(self.path):
            if isinstance(segment, Line):
                startpt = copy(segment.start)
                endpt = copy(segment.end)
                ctrl1pt = Point(
                    startpt.x + 0.25 * (endpt.x - startpt.x),
                    startpt.y + 0.25 * (endpt.y - startpt.y),
                )
                ctrl2pt = Point(
                    startpt.x + 0.75 * (endpt.x - startpt.x),
                    startpt.y + 0.75 * (endpt.y - startpt.y),
                )
                newsegment = CubicBezier(
                    start=startpt, end=endpt, control1=ctrl1pt, control2=ctrl2pt
                )
                self.path[idx] = newsegment
                modified = True
            elif isinstance(segment, QuadraticBezier):
                # The cubic control - points lie on 2/3 of the way of the
                # line-segments from the endpoint to the quadratic control-point
                startpt = copy(segment.start)
                endpt = copy(segment.end)
                dx = segment.control.x - startpt.x
                dy = segment.control.y - startpt.y
                ctrl1pt = Point(startpt.x + 2 / 3 * dx, startpt.y + 2 / 3 * dy)
                dx = segment.control.x - endpt.x
                dy = segment.control.y - endpt.y
                ctrl2pt = Point(endpt.x + 2 / 3 * dx, endpt.y + 2 / 3 * dy)
                newsegment = CubicBezier(
                    start=startpt, end=endpt, control1=ctrl1pt, control2=ctrl2pt
                )
                self.path[idx] = newsegment
                modified = True
            elif isinstance(segment, Arc):
                for newsegment in list(segment.as_cubic_curves(1)):
                    self.path[idx] = newsegment
                    break
                modified = True
        # Pass 2 - make all control lines align
        prevseg = None
        lastidx = len(self.path) - 1
        for idx, segment in enumerate(self.path):
            nextseg = None
            if idx < lastidx:
                nextseg = self.path[idx + 1]
                if isinstance(nextseg, (Move, Close)):
                    nextseg = None
            if isinstance(segment, CubicBezier):
                if prevseg is None:
                    if self.is_closed_subpath(idx):
                        otherseg = self.last_segment_in_subpath(idx)
                        prevseg = Line(
                            start=Point(otherseg.end.x, otherseg.end.y),
                            end=Point(segment.start.x, segment.start.y),
                        )
                if prevseg is not None:
                    angle1 = Point.angle(prevseg.end, prevseg.start)
                    angle2 = Point.angle(segment.start, segment.end)
                    d_angle = math.tau / 2 - (angle1 - angle2)
                    while d_angle >= math.tau:
                        d_angle -= math.tau
                    while d_angle < -math.tau:
                        d_angle += math.tau

                    # print (f"to prev: Angle 1 = {angle1/math.tau*360:.1f}°, Angle 2 = {angle2/math.tau*360:.1f}°, Delta = {d_angle/math.tau*360:.1f}°")
                    dist = segment.start.distance_to(segment.control1)
                    candidate1 = Point.polar(segment.start, angle2 - d_angle / 2, dist)
                    candidate2 = Point.polar(segment.start, angle1 + d_angle / 2, dist)
                    if segment.end.distance_to(candidate1) < segment.end.distance_to(
                        candidate2
                    ):
                        segment.control1 = candidate1
                    else:
                        segment.control1 = candidate2
                    modified = True
                if nextseg is None:
                    if self.is_closed_subpath(idx):
                        otherseg = self.first_segment_in_subpath(idx)
                        nextseg = Line(
                            start=Point(segment.end.x, segment.end.y),
                            end=Point(otherseg.start.x, otherseg.start.y),
                        )
                if nextseg is not None:
                    angle1 = Point.angle(segment.end, segment.start)
                    angle2 = Point.angle(nextseg.start, nextseg.end)
                    d_angle = math.tau / 2 - (angle1 - angle2)
                    while d_angle >= math.tau:
                        d_angle -= math.tau
                    while d_angle < -math.tau:
                        d_angle += math.tau

                    # print (f"to next: Angle 1 = {angle1/math.tau*360:.1f}°, Angle 2 = {angle2/math.tau*360:.1f}°, Delta = {d_angle/math.tau*360:.1f}°")
                    dist = segment.end.distance_to(segment.control2)
                    candidate1 = Point.polar(segment.end, angle2 - d_angle / 2, dist)
                    candidate2 = Point.polar(segment.end, angle1 + d_angle / 2, dist)
                    if segment.start.distance_to(
                        candidate1
                    ) < segment.start.distance_to(candidate2):
                        segment.control2 = candidate1
                    else:
                        segment.control2 = candidate2
                    modified = True
            if isinstance(segment, (Move, Close)):
                prevseg = None
            else:
                prevseg = segment
        if modified:
            self.modify_element(True)

    def cubic_symmetrical(self):
        """
        Adjust the two control points control1 and control2 of a cubic segment
        so that they are symmetrical to the perpendicular bisector on start - end
        """
        if self.element is None or self.nodes is None:
            return
        modified = False
        if self.node_type == "polyline":
            # Not valid for a polyline Could make a path now but that might be more than the user expected...
            return
        for entry in self.nodes:
            if entry["selected"] and entry["segtype"] == "C":  # Cubic Bezier only
                segment = entry["segment"]
                pt_start = segment.start
                pt_end = segment.end
                midpoint = Point(
                    (pt_end.x + pt_start.x) / 2, (pt_end.y + pt_start.y) / 2
                )
                angle_to_end = midpoint.angle_to(pt_end)
                angle_to_start = midpoint.angle_to(pt_start)
                angle_to_control2 = midpoint.angle_to(segment.control2)
                distance = midpoint.distance_to(segment.control2)
                # The new point
                angle_to_control1 = angle_to_start + (angle_to_end - angle_to_control2)
                # newx = midpoint.x + distance * math.cos(angle_to_control1)
                # newy = midpoint.y + distance * math.sin(angle_to_control1)
                # segment.control1 = Point(newx, newy)
                segment.control1 = Point.polar(
                    (midpoint.x, midpoint.y), angle_to_control1, distance
                )
                modified = True
        if modified:
            self.modify_element(True)

    def delete_nodes(self):
        """
        Delete all selected (point) nodes
        """
        if self.element is None or self.nodes is None:
            return
        modified = False
        for idx in range(len(self.nodes) - 1, -1, -1):
            entry = self.nodes[idx]
            if entry["selected"] and entry["type"] == "point":
                if self.node_type == "polyline":
                    if len(self.shape.points) > 2:
                        modified = True
                        self.shape.points.pop(idx)
                    else:
                        break
                else:
                    idx = entry["pathindex"]
                    prevseg = None
                    nextseg = None
                    seg = self.path[idx]
                    if idx > 0:
                        prevseg = self.path[idx - 1]
                    if idx < len(self.path) - 1:
                        nextseg = self.path[idx + 1]
                    if nextseg is None:
                        # Last point of the path
                        # Can just be deleted, provided we have something
                        # in front...
                        if prevseg is None or isinstance(prevseg, (Move, Close)):
                            continue
                        del self.path[idx]
                        modified = True
                    elif isinstance(nextseg, (Move, Close)):
                        # last point of the subsegment...
                        # We need to have another full segment in the front
                        # otherwise we would end up with a single point...
                        if prevseg is None or isinstance(prevseg, (Move, Close)):
                            continue
                        nextseg.start.x = seg.start.x
                        nextseg.start.y = seg.start.y
                        if isinstance(nextseg, Close):
                            nextseg.end.x = seg.start.x
                            nextseg.end.y = seg.start.y

                        del self.path[idx]
                        modified = True
                    else:
                        # Could be the first point...
                        if prevseg is None and (
                            nextseg is None or isinstance(nextseg, (Move, Close))
                        ):
                            continue
                        if prevseg is None:  # # Move
                            seg.end = Point(nextseg.end.x, nextseg.end.y)
                            del self.path[idx + 1]
                            modified = True
                        elif isinstance(seg, Move):  # # Move
                            seg.end = Point(nextseg.end.x, nextseg.end.y)
                            del self.path[idx + 1]
                            modified = True
                        else:
                            nextseg.start.x = prevseg.end.x
                            nextseg.start.y = prevseg.end.y
                            del self.path[idx]
                            modified = True

        if modified:
            self.modify_element(True)

    def convert_to_line(self):
        """
        Convert all selected segments to a line
        """
        if self.element is None or self.nodes is None:
            return
        modified = False
        if self.node_type == "polyline":
            # Not valid for a polyline Could make a path now but that might be more than the user expected...
            return
        for entry in self.nodes:
            if entry["selected"] and entry["type"] == "point":
                idx = entry["pathindex"]
                if entry["segment"] is None or entry["segment"].start is None:
                    continue
                startpt = Point(entry["segment"].start.x, entry["segment"].start.y)
                endpt = Point(entry["segment"].end.x, entry["segment"].end.y)
                if entry["segtype"] not in ("C", "Q", "A"):
                    continue
                newsegment = Line(start=startpt, end=endpt)
                self.path[idx] = newsegment
                modified = True
        if modified:
            self.modify_element(True)

    def linear_all(self):
        """
        Convert all segments of the path to a line
        """
        if self.element is None or self.nodes is None:
            return
        modified = False
        if self.node_type == "polyline":
            # Not valid for a polyline Could make a path now but that might be more than the user expected...
            return
        for idx, segment in enumerate(self.path):
            if isinstance(segment, (Close, Move, Line)):
                continue
            startpt = Point(segment.start.x, segment.start.y)
            endpt = Point(segment.end.x, segment.end.y)
            newsegment = Line(start=startpt, end=endpt)
            self.path[idx] = newsegment
            modified = True

        if modified:
            self.modify_element(True)

    def convert_to_curve(self):
        """
        Convert all selected segments to a circular bezier
        """
        if self.element is None or self.nodes is None:
            return
        modified = False
        if self.node_type == "polyline":
            # Not valid for a polyline Could make a path now but that might be more than the user expected...
            return
        for entry in self.nodes:
            if entry["selected"] and entry["type"] == "point":
                idx = entry["pathindex"]
                if entry["segment"] is None or entry["segment"].start is None:
                    continue
                startpt = Point(entry["segment"].start.x, entry["segment"].start.y)
                endpt = Point(entry["segment"].end.x, entry["segment"].end.y)
                if entry["segtype"] == "L":
                    ctrl1pt = Point(
                        startpt.x + 0.25 * (endpt.x - startpt.x),
                        startpt.y + 0.25 * (endpt.y - startpt.y),
                    )
                    ctrl2pt = Point(
                        startpt.x + 0.75 * (endpt.x - startpt.x),
                        startpt.y + 0.75 * (endpt.y - startpt.y),
                    )
                elif entry["segtype"] == "Q":
                    ctrl1pt = Point(
                        entry["segment"].control.x, entry["segment"].control.y
                    )
                    ctrl2pt = Point(endpt.x, endpt.y)
                elif entry["segtype"] == "A":
                    ctrl1pt = Point(
                        startpt.x + 0.25 * (endpt.x - startpt.x),
                        startpt.y + 0.25 * (endpt.y - startpt.y),
                    )
                    ctrl2pt = Point(
                        startpt.x + 0.75 * (endpt.x - startpt.x),
                        startpt.y + 0.75 * (endpt.y - startpt.y),
                    )
                else:
                    continue

                newsegment = CubicBezier(
                    start=startpt, end=endpt, control1=ctrl1pt, control2=ctrl2pt
                )
                self.path[idx] = newsegment
                modified = True
        if modified:
            self.modify_element(True)

    def break_path(self):
        """
        Break a path at the selected (point) nodes
        """
        if self.element is None or self.nodes is None:
            return
        # Stub for breaking the path
        modified = False
        if self.node_type == "polyline":
            # Not valid for a polyline Could make a path now but that might be more than the user expected...
            return
        for idx in range(len(self.nodes) - 1, -1, -1):
            entry = self.nodes[idx]
            if entry["selected"] and entry["type"] == "point":
                idx = entry["pathindex"]
                seg = entry["segment"]
                if isinstance(seg, (Move, Close)):
                    continue
                # Is this the last point? Then no use to break the path
                nextseg = None
                if idx in (0, len(self.path) - 1):
                    # Don't break at the first or last point
                    continue
                nextseg = self.path[idx + 1]
                if isinstance(nextseg, (Move, Close)):
                    # Not at end of subpath
                    continue
                prevseg = self.path[idx - 1]
                if isinstance(prevseg, (Move, Close)):
                    # We could still be at the end point of the first segment...
                    if entry["point"] == seg.start:
                        # Not at start of subpath
                        continue
                newseg = Move(
                    start=Point(seg.end.x, seg.end.y),
                    end=Point(nextseg.start.x, nextseg.start.y),
                )
                self.path.insert(idx + 1, newseg)
                # Now let's validate whether the 'right' path still has a
                # close segment at its end. That will be removed as this would
                # create an unwanted behaviour
                prevseg = None
                is_closed = False
                for sidx in range(idx + 1, len(self.path), 1):
                    seg = self.path[sidx]
                    if isinstance(seg, Move) and prevseg is None:
                        # Not the one at the very beginning!
                        continue
                    if isinstance(seg, Move):
                        # Ready
                        break
                    if isinstance(seg, Close):
                        # Ready
                        is_closed = True
                        break
                    lastidx = sidx
                    prevseg = seg
                if is_closed:
                    # it's enough just to delete it...
                    del self.path[lastidx + 1]

                modified = True
        if modified:
            self.modify_element(True)

    def join_path(self):
        """
        Join two selected (point) nodes if they are on different subpath
        """
        if self.element is None or self.nodes is None:
            return
        modified = False
        if self.node_type == "polyline":
            # Not valid for a polyline
            return
        for idx in range(len(self.nodes) - 1, -1, -1):
            entry = self.nodes[idx]
            if entry["selected"] and entry["type"] == "point":
                idx = entry["pathindex"]
                seg = entry["segment"]
                prevseg = None
                nextseg = None
                if idx > 0:
                    prevseg = self.path[idx - 1]
                if idx < len(self.path) - 1:
                    nextseg = self.path[idx + 1]
                if isinstance(seg, (Move, Close)):
                    # Beginning of path
                    if prevseg is None:
                        # Very beginning?! Ignore...
                        continue
                    if nextseg is None:
                        continue
                    if isinstance(nextseg, (Move, Close)):
                        # Two consecutive moves? Ignore....
                        continue
                    nextseg.start.x = seg.start.x
                    nextseg.start.y = seg.start.y
                    del self.path[idx]
                    modified = True
                else:
                    # Let's look at the next segment
                    if nextseg is None:
                        continue
                    if not isinstance(nextseg, Move):
                        continue
                    seg.end.x = nextseg.end.x
                    seg.end.y = nextseg.end.y
                    del self.path[idx + 1]
                    modified = True

        if modified:
            self.modify_element(True)

    def insert_midpoint(self):
        """
        Insert a point in the middle of a selected segment
        """
        if self.element is None or self.nodes is None:
            return
        modified = False
        # Move backwards as len will change
        for idx in range(len(self.nodes) - 1, -1, -1):
            entry = self.nodes[idx]
            if entry["selected"] and entry["type"] == "point":
                if self.node_type == "polyline":
                    pt1 = self.shape.points[idx]
                    if idx == 0:
                        # Very first point? Mirror first segment and take midpoint
                        pt2 = Point(
                            self.shape.points[idx + 1].x,
                            self.shape.points[idx + 1].y,
                        )
                        pt2.x = pt1.x - (pt2.x - pt1.x)
                        pt2.y = pt1.y - (pt2.y - pt1.y)
                        pt2.x = (pt1.x + pt2.x) / 2
                        pt2.y = (pt1.y + pt2.y) / 2
                        self.shape.points.insert(0, pt2)
                    else:
                        pt2 = Point(
                            self.shape.points[idx - 1].x,
                            self.shape.points[idx - 1].y,
                        )
                        pt2.x = (pt1.x + pt2.x) / 2
                        pt2.y = (pt1.y + pt2.y) / 2
                        # Mid point
                        self.shape.points.insert(idx, pt2)
                    modified = True
                else:
                    # Path
                    idx = entry["pathindex"]
                    if entry["segment"] is None:
                        continue
                    segment = entry["segment"]

                    # def pt_info(pt):
                    #     return f"({pt.x:.0f}, {pt.y:.0f})"

                    if entry["segtype"] == "L":
                        # Line
                        mid_x = (segment.start.x + segment.end.x) / 2
                        mid_y = (segment.start.y + segment.end.y) / 2
                        newsegment = Line(
                            start=Point(mid_x, mid_y),
                            end=Point(segment.end.x, segment.end.y),
                        )
                        self.path.insert(idx + 1, newsegment)
                        # path.insert may change the start and end point
                        # of the segement to make sure it maintains a
                        # contiguous path, so we need to set it again...
                        newsegment.start.x = mid_x
                        newsegment.start.y = mid_y
                        segment.end.x = mid_x
                        segment.end.y = mid_y
                        modified = True
                    elif entry["segtype"] == "C":
                        midpoint = segment.point(0.5)
                        mid_x = midpoint.x
                        mid_y = midpoint.y
                        newsegment = CubicBezier(
                            start=Point(mid_x, mid_y),
                            end=Point(segment.end.x, segment.end.y),
                            control1=Point(mid_x, mid_y),
                            control2=Point(segment.control2.x, segment.control2.y),
                        )
                        self.path.insert(idx + 1, newsegment)
                        segment.end.x = mid_x
                        segment.end.y = mid_y
                        segment.control2.x = mid_x
                        segment.control2.y = mid_y
                        newsegment.start.x = mid_x
                        newsegment.start.y = mid_y
                        modified = True
                    elif entry["segtype"] == "A":
                        midpoint = segment.point(0.5)
                        mid_x = midpoint.x
                        mid_y = midpoint.y
                        # newsegment = Arc(
                        #     start=Point(mid_x, mid_y),
                        #     end=Point(segment.end.x, segment.end.y),
                        #     control=Point(segment.center.x, segment.center.y),
                        # )
                        newsegment = copy(segment)
                        newsegment.start.x = mid_x
                        newsegment.start.y = mid_y
                        self.path.insert(idx + 1, newsegment)
                        segment.end.x = mid_x
                        segment.end.y = mid_y
                        newsegment.start.x = mid_x
                        newsegment.start.y = mid_y
                        modified = True
                    elif entry["segtype"] == "Q":
                        midpoint = segment.point(0.5)
                        mid_x = midpoint.x
                        mid_y = midpoint.y
                        newsegment = QuadraticBezier(
                            start=Point(mid_x, mid_y),
                            end=Point(segment.end.x, segment.end.y),
                            control=Point(segment.control.x, segment.control.y),
                        )
                        self.path.insert(idx + 1, newsegment)
                        segment.end.x = mid_x
                        segment.end.y = mid_y
                        segment.control.x = mid_x
                        segment.control.y = mid_y
                        newsegment.start.x = mid_x
                        newsegment.start.y = mid_y
                        modified = True
                    elif entry["segtype"] == "M":
                        # Very first point? Mirror first segment and take midpoint
                        nextseg = entry["next"]
                        if nextseg is None:
                            continue
                        p1x = nextseg.start.x
                        p1y = nextseg.start.y
                        p2x = nextseg.end.x
                        p2y = nextseg.end.y
                        p2x = p1x - (p2x - p1x)
                        p2y = p1y - (p2y - p1y)
                        pt1 = Point((p1x + p2x) / 2, (p1y + p2y) / 2)
                        pt2 = copy(nextseg.start)
                        newsegment = Line(start=pt1, end=pt2)
                        self.path.insert(idx + 1, newsegment)
                        segment.end = pt1
                        newsegment.start.x = pt1.x
                        newsegment.start.y = pt1.y
                        # We need to step forward to assess whether there is a close segment
                        for idx2 in range(idx + 1, len(self.path)):
                            if isinstance(self.path[idx2], Move):
                                break
                            if isinstance(self.path[idx2], Close):
                                # Adjust the close segment to that it points again
                                # to the first move end
                                self.path[idx2].end = Point(pt1.x, pt1.y)
                                break

                        modified = True

        if modified:
            self.modify_element(True)

    def append_line(self):
        """
        Append a point to the selected element, works all the time and does not require a valid selection
        """
        if self.element is None or self.nodes is None:
            return
        modified = False
        if self.node_type == "polyline":
            idx = len(self.shape.points) - 1
            pt1 = self.shape.points[idx - 1]
            pt2 = self.shape.points[idx]
            newpt = Point(pt2.x + (pt2.x - pt1.x), pt2.y + (pt2.y - pt1.y))
            self.shape.points.append(newpt)
            modified = True
        else:
            # path
            try:
                valididx = len(self.path) - 1
            except AttributeError:
                # Shape
                return
            while valididx >= 0 and isinstance(self.path[valididx], (Close, Move)):
                valididx -= 1
            if valididx >= 0:
                seg = self.path[valididx]
                pt1 = seg.start
                pt2 = seg.end
                newpt = Point(pt2.x + (pt2.x - pt1.x), pt2.y + (pt2.y - pt1.y))
                newsegment = Line(start=Point(seg.end.x, seg.end.y), end=newpt)
                if valididx < len(self.path) - 1:
                    if self.path[valididx + 1].end == self.path[valididx + 1].start:
                        self.path[valididx + 1].end.x = newpt.x
                        self.path[valididx + 1].end.y = newpt.y
                    self.path[valididx + 1].start.x = newpt.x
                    self.path[valididx + 1].start.y = newpt.y

                self.path.insert(valididx + 1, newsegment)
                newsegment.start.x = seg.end.x
                newsegment.start.y = seg.end.y
                modified = True

        if modified:
            self.modify_element(True)

    @property
    def anyselected(self):
        if self.nodes:
            for entry in self.nodes:
                if entry["selected"]:
                    return True
        return False

    def event(
        self,
        window_pos=None,
        space_pos=None,
        event_type=None,
        nearest_snap=None,
        modifiers=None,
        keycode=None,
        **kwargs,
    ):
        """
        The routine dealing with propagated scene events

        Args:
            window_pos (tuple): The coordinates of the mouse position in window coordinates
            space_pos (tuple): The coordinates of the mouse position in scene coordinates
            event_type (string): [description]. Defaults to None.
            nearest_snap (tuple, optional): If set the coordinates of the nearest snap point in scene coordinates.
            modifiers (string): If available provides a  list of modifier keys that were pressed (shift, alt, ctrl).
            keycode (string): if available the keycode that was pressed

        Returns:
            Indicator how to proceed with this event after its execution (consume, chain etc.)
        """
        if self.scene.pane.active_tool != "edit":
            return RESPONSE_CHAIN
        # print (f"event: {event_type}, modifiers: '{modifiers}', keycode: '{keycode}'")
        offset = 5
        s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
        offset /= s
        elements = self.scene.context.elements
        if event_type in ("leftdown", "leftclick"):
            self.pen = wx.Pen()
            self.pen.SetColour(wx.Colour(swizzlecolor(elements.default_stroke)))
            self.pen.SetWidth(25)
            self.scene.pane.tool_active = True
            self.scene.pane.modif_active = True

            self.scene.context.signal("statusmsg", self.message)
            self.move_type = "node"

            xp = space_pos[0]
            yp = space_pos[1]
            if self.nodes:
                w = offset * 4
                h = offset * 4
                node = self.element
                for i, entry in enumerate(self.nodes):
                    pt = entry["point"]
                    ptx, pty = node.matrix.point_in_matrix_space(pt)
                    x = ptx - 2 * offset
                    y = pty - 2 * offset
                    if x <= xp <= x + w and y <= yp <= y + h:
                        self.selected_index = i
                        if entry["type"] == "control":
                            # We select the corresponding segment
                            for entry2 in self.nodes:
                                entry2["selected"] = False
                            orgnode = None
                            for j in range(0, 3):
                                k = i - j - 1
                                if k >= 0 and self.nodes[k]["type"] == "point":
                                    orgnode = self.nodes[k]
                                    break
                            if orgnode is not None:
                                orgnode["selected"] = True
                            entry["selected"] = True
                        else:
                            # Shift-Key Pressed?
                            if "shift" not in modifiers:
                                self.clear_selection()
                                entry["selected"] = True
                            else:
                                entry["selected"] = not entry["selected"]
                        break
                else:  # For-else == icky
                    self.selected_index = None
            self.enable_rules()
            if self.selected_index is None:
                if event_type == "leftclick":
                    # Have we clicked outside the bbox? Then we call it a day...
                    outside = False
                    if not self.element:
                        # Element is required.
                        return RESPONSE_CONSUME
                    bb = self.element.bbox()
                    if bb is None:
                        return RESPONSE_CONSUME
                    if space_pos[0] < bb[0] or space_pos[0] > bb[2]:
                        outside = True
                    if space_pos[1] < bb[1] or space_pos[1] > bb[3]:
                        outside = True
                    if outside:
                        self.done()
                        return RESPONSE_CONSUME
                    else:
                        # Clear selection
                        self.clear_selection()
                        self.scene.request_refresh()
                else:
                    # Fine we start a selection rectangle to select multiple nodes
                    self.move_type = "selection"
                    self.p1 = complex(space_pos[0], space_pos[1])
            else:
                self.scene.request_refresh()
            return RESPONSE_CONSUME
        elif event_type == "rightdown":
            # We stop
            self.done()
            return RESPONSE_CONSUME
        elif event_type == "move":
            if self.move_type == "selection":
                if self.p1 is not None:
                    self.p2 = complex(space_pos[0], space_pos[1])
                    self.scene.request_refresh()
            else:
                if self.selected_index is None or self.selected_index < 0:
                    self.scene.request_refresh()
                    return RESPONSE_CONSUME
                current = self.nodes[self.selected_index]
                pt = current["point"]
                if nearest_snap is None:
                    spt = Point(space_pos[0], space_pos[1])
                else:
                    spt = Point(nearest_snap[0], nearest_snap[1])

                m = self.element.matrix.point_in_inverse_space(spt)
                # Special treatment for the virtual midpoint:
                if current["type"] == "midpoint" and self.node_type == "path":
                    self.scene.context.signal(
                        "statusmsg",
                        _(
                            "Drag to change the curve shape (ctrl to affect the other side)"
                        ),
                    )
                    idx = self.selected_index
                    newpt = Point(m[0], m[1])
                    change2nd = bool("ctrl" in modifiers)
                    self.revise_bezier_to_point(
                        current["segment"], newpt, change_2nd_control=change2nd
                    )
                    self.modify_element(False)
                    self.calculate_points(self.element)
                    self.selected_index = idx
                    self.nodes[idx]["selected"] = True
                    orgnode = None
                    for j in range(0, 3):
                        k = idx - j - 1
                        if k >= 0 and self.nodes[k]["type"] == "point":
                            orgnode = self.nodes[k]
                            break
                    if orgnode is not None:
                        orgnode["selected"] = True
                    self.scene.request_refresh()
                    return RESPONSE_CONSUME
                pt.x = m[0]
                pt.y = m[1]
                if self.node_type == "path":
                    current["point"] = pt
                    # We need to adjust the start-point of the next segment
                    # unless it's a closed path then we need to adjust the
                    # very first - need to be mindful of closed subpaths
                    if current["segtype"] == "M":
                        # We changed the end, let's check whether the last segment in
                        # the subpath is a Close then we need to change this .end as well
                        for nidx in range(self.selected_index + 1, len(self.path), 1):
                            nextseg = self.path[nidx]
                            if isinstance(nextseg, Move):
                                break
                            if isinstance(nextseg, Close):
                                nextseg.end.x = m[0]
                                nextseg.end.y = m[1]
                                break
                    nextseg = current["next"]
                    if nextseg is not None and nextseg.start is not None:
                        nextseg.start.x = m[0]
                        nextseg.start.y = m[1]

                    if isinstance(current["segment"], CubicBezier):
                        self.adjust_midpoint(self.selected_index)
                    elif isinstance(current["segment"], Move):
                        if nextseg is not None and isinstance(nextseg, CubicBezier):
                            self.adjust_midpoint(self.selected_index + 1)

                    # self.debug_path()
                self.modify_element(False)
            return RESPONSE_CONSUME
        elif event_type == "key_down":
            if not self.scene.pane.tool_active:
                return RESPONSE_CHAIN
            # print (f"event: {event_type}, modifiers: '{modifiers}', keycode: '{keycode}'")
            return RESPONSE_CONSUME
        elif event_type == "key_up":
            if not self.scene.pane.tool_active:
                return RESPONSE_CHAIN
            # print (f"event: {event_type}, modifiers: '{modifiers}', keycode: '{keycode}'")
            if modifiers == "escape":
                self.done()
                return RESPONSE_CONSUME
            # print(f"Key: '{keycode}'")
            # if self.selected_index is not None:
            #     entry = self.nodes[self.selected_index]
            # else:
            #     entry = None
            self.perform_action(modifiers)

            return RESPONSE_CONSUME

        elif event_type == "lost":
            if self.scene.pane.tool_active:
                self.done()
                return RESPONSE_CONSUME
            else:
                return RESPONSE_CHAIN
        elif event_type == "leftup":
            if (
                self.move_type == "selection"
                and self.p1 is not None
                and self.p2 is not None
            ):
                if "shift" not in modifiers:
                    self.clear_selection()
                x0 = min(self.p1.real, self.p2.real)
                y0 = min(self.p1.imag, self.p2.imag)
                x1 = max(self.p1.real, self.p2.real)
                y1 = max(self.p1.imag, self.p2.imag)
                dx = self.p1.real - self.p2.real
                dy = self.p1.imag - self.p2.imag
                if abs(dx) < 1e-10 or abs(dy) < 1e-10:
                    return RESPONSE_CONSUME
                # We select all points (not controls) inside
                if self.element:
                    for entry in self.nodes:
                        pt = entry["point"]
                        if (
                            entry["type"] == "point"
                            and x0 <= pt.x <= x1
                            and y0 <= pt.y <= y1
                        ):
                            entry["selected"] = True
                self.scene.request_refresh()
                self.enable_rules()
            self.p1 = None
            self.p2 = None
            return RESPONSE_CONSUME
        return RESPONSE_DROP

    def perform_action(self, code):
        """
        Translates a keycode into a command to execute
        """
        # print(f"Perform action called with {code}")
        if self.element is None or self.nodes is None:
            return
        if code in self.commands:
            action = self.commands[code]
            # print(f"Execute {action[1]}")
            action[0]()
        # else:
        #     print (f"Did not find {code}")

    def _tool_change(self):
        selected_node = None
        elements = self.scene.context.elements.elem_branch
        for node in elements.flat(emphasized=True):
            if node.type in ("elem path", "elem polyline"):
                selected_node = node
                break
        self.scene.pane.suppress_selection = selected_node is not None
        if selected_node is None:
            self.done()
        else:
            self.calculate_points(selected_node)
            self.enable_rules()
        self.scene.request_refresh()

    def signal(self, signal, *args, **kwargs):
        """
        Signal routine for stuff that's passed along within a scene,
        does not receive global signals
        """
        # print(f"Signal: {signal}")
        if signal == "tool_changed":
            if len(args) > 0 and len(args[0]) > 1 and args[0][1] == "edit":
                self._tool_change()
            return
        elif signal == "rebuild_tree":
            self._tool_change()
        elif signal == "emphasized":
            self._tool_change()
        if self.element is None:
            return
