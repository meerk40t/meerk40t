import math

import wx
from meerk40t.gui.icons import icons8_node_edit_50
from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.scene.sceneconst import (
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
    RESPONSE_DROP,
)
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget

_ = wx.GetTranslation


class EditTool(ToolWidget):
    """
    Edit tool allows you to view and edit the nodes within the scene.
    """

    def __init__(self, scene):
        ToolWidget.__init__(self, scene)
        self.nodes = None
        self.element = None
        self.selected_index = None
        self.move_type = "node"
        self.p1 = None
        self.p2 = None
        self.pen = wx.Pen()
        self.pen.SetColour(wx.BLUE)
        # wx.Colour(swizzlecolor(self.scene.context.elements.default_stroke))
        self.pen.SetWidth(1000)
        self.pen_ctrl = wx.Pen()
        self.pen_ctrl.SetColour(wx.BLACK)
        self.pen_ctrl.SetWidth(1000)
        self.pen_highlight = wx.Pen()
        self.pen_highlight.SetColour(wx.RED)
        self.pen_highlight.SetWidth(1000)
        self.pen_selection = wx.Pen()
        self.pen_selection.SetColour(self.scene.colors.color_selection3)
        self.pen_selection.SetStyle(wx.PENSTYLE_SHORT_DASH)
        self.pen_selection.SetWidth(25)
        # want to have sharp edges
        self.pen_selection.SetJoin(wx.JOIN_MITER)
        self.commands = {
            "c": (self.clear_selection, _("Clear")),
            "d": (self.delete_nodes, _("Delete")),
            "b": (self.convert_to_bezier, _("Bezier")),
            "l": (self.convert_to_line, _("Line")),
            "q": (self.convert_to_quad, _("Quad")),
            "x": (self.break_path, _("Break")),
            "i": (self.insert_midpoint, _("Insert")),
            "a": (self.append_line, _("Append")),
        }
        self.message = ""
        for cmd in self.commands:
            action = self.commands[cmd]
            if self.message:
                self.message += ", "
            self.message += f"{cmd}: {action[1]}"

    def final(self, context):
        self.scene.context.unlisten("emphasized", self.on_emphasized_changed)
        self.scene.context("window close NodeEditIcons\n")
        self.scene.request_refresh()

    def init(self, context):
        self.scene.context("window open NodeEditIcons\n")
        self.scene.context.listen("emphasized", self.on_emphasized_changed)

    def on_emphasized_changed(self, origin, *args):
        selected_node = self.scene.context.elements.first_element(emphasized=True)
        self.calculate_points(selected_node)
        self.scene.request_refresh()

    def calculate_points(self, selected_node):
        # Set points...
        self.element = selected_node
        self.selected_index = None
        self.nodes = []
        offset = 5
        s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
        offset /= s
        try:
            path = selected_node.path
        except AttributeError:
            return
        for segment in path:
            q = type(segment).__name__
            if q in ("Line", "Close"):
                self.nodes.append(
                    {
                        "point": segment.end,
                        "segment": segment,
                        "path": path,
                        "type": "point",
                        "connector": -1,
                        "selected": False,
                    }
                )
            elif q == "Move":
                self.nodes.append(
                    {
                        "point": segment.end,
                        "segment": segment,
                        "path": path,
                        "type": "point",
                        "connector": -1,
                        "selected": False,
                    }
                )
            elif q == "QuadraticBezier":
                self.nodes.append(
                    {
                        "point": segment.end,
                        "segment": segment,
                        "path": path,
                        "type": "point",
                        "connector": -1,
                        "selected": False,
                    }
                )
                idx = len(self.nodes) - 1
                self.nodes.append(
                    {
                        "point": segment.control,
                        "segment": segment,
                        "path": path,
                        "type": "control",
                        "connector": idx,
                        "selected": False,
                    }
                )
            elif q == "CubicBezier":
                self.nodes.append(
                    {
                        "point": segment.end,
                        "segment": segment,
                        "path": path,
                        "type": "point",
                        "connector": -1,
                        "selected": False,
                    }
                )
                idx = len(self.nodes) - 1
                self.nodes.append(
                    {
                        "point": segment.control1,
                        "segment": segment,
                        "path": path,
                        "type": "control",
                        "connector": idx,
                        "selected": False,
                    }
                )
                self.nodes.append(
                    {
                        "point": segment.control2,
                        "segment": segment,
                        "path": path,
                        "type": "control",
                        "connector": idx,
                        "selected": False,
                    }
                )

    def process_draw(self, gc: wx.GraphicsContext):
        if not self.nodes:
            return
        if self.p1 is not None and self.p2 is not None:
            # Selection mode!
            x0 = min(self.p1.real, self.p2.real)
            y0 = min(self.p1.imag, self.p2.imag)
            x1 = max(self.p1.real, self.p2.real)
            y1 = max(self.p1.imag, self.p2.imag)
            gc.SetPen(self.pen_selection)
            gc.SetBrush(wx.TRANSPARENT_BRUSH)
            gc.DrawRectangle(x0, y0, x1 - x0, y1 - y0)
        else:
            offset = 5
            s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
            offset /= s
            gc.SetBrush(wx.TRANSPARENT_BRUSH)
            idx = -1
            for entry in self.nodes:
                idx += 1
                node = self.element
                ptx, pty = node.matrix.point_in_matrix_space(entry["point"])
                if entry["type"] == "point":
                    if idx == self.selected_index or entry["selected"]:
                        gc.SetPen(self.pen_highlight)
                    else:
                        gc.SetPen(self.pen)
                    gc.DrawEllipse(ptx - offset, pty - offset, offset * 2, offset * 2)
                elif entry["type"] == "control":
                    if idx == self.selected_index or entry["selected"]:
                        gc.SetPen(self.pen_highlight)
                    else:
                        gc.SetPen(self.pen_ctrl)
                    pattern = [
                        (ptx - offset, pty),
                        (ptx, pty + offset),
                        (ptx + offset, pty),
                        (ptx, pty - offset),
                        (ptx - offset, pty),
                    ]
                    gc.DrawLines(pattern)
                    if 0 <= entry["connector"] < len(self.nodes):
                        gc.SetPen(self.pen_ctrl)
                        orgnode = self.nodes[entry["connector"]]
                        org_pt = orgnode["point"]
                        org_ptx, org_pty = node.matrix.point_in_matrix_space(org_pt)
                        pattern = [(ptx, pty), (org_ptx, org_pty)]
                        gc.DrawLines(pattern)

    def done(self, forgood=False):
        self.scene.tool_active = False
        self.p1 = None
        self.p2 = None
        self.move_type = "node"
        self.scene.context.elements.validate_selected_area()
        self.scene.request_refresh()
        if forgood:
            self.scene.context("tool none\n")
            self.scene.context("window close NodeEditIcons\n")
            self.scene.context.signal("statusmsg", "")

    def clear_selection(self):
        if self.nodes is not None:
            for entry in self.nodes:
                entry["selected"] = False

    def modify_element(self, reload=True):
        if self.element is None:
            return
        self.element.path.validate_connections()
        self.element.altered()
        try:
            bb = self.element.bbox()
        except AttributeError:
            pass
        self.scene.context.elements.validate_selected_area()
        self.scene.request_refresh()
        self.scene.context.signal("element_property_reload", [self.element])
        if reload:
            self.calculate_points(self.element)
            self.scene.request_refresh()

    def delete_nodes(self):
        # Stub for append a line
        modified = False
        for entry in self.nodes:
            if entry["selected"] and entry["type"] == "point":
                pass
        if modified:
            self.modify_element(True)

    def convert_to_bezier(self):
        # Stub for converting segment to a bezier
        modified = False
        for entry in self.nodes:
            if entry["selected"] and entry["type"] == "point":
                pass
        if modified:
            self.modify_element(True)

    def convert_to_line(self):
        # Stub for converting segment to a line
        modified = False
        for entry in self.nodes:
            if entry["selected"] and entry["type"] == "point":
                pass
        if modified:
            self.modify_element(True)

    def convert_to_quad(self):
        # Stub for converting segment to a quad
        modified = False
        for entry in self.nodes:
            if entry["selected"] and entry["type"] == "point":
                pass
        if modified:
            self.modify_element(True)

    def break_path(self):
        # Stub for breaking the path
        modified = False
        for entry in self.nodes:
            if entry["selected"] and entry["type"] == "point":
                pass
        if modified:
            self.modify_element(True)

    def insert_midpoint(self):
        # Stub for inserting a point...
        modified = False
        for entry in self.nodes:
            if entry["selected"] and entry["type"] == "point":
                pass
        if modified:
            self.modify_element(True)

    def append_line(self):
        # Stub for append a line
        modified = False
        # Code to follow
        if modified:
            self.modify_element(True)

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
        if self.scene.active_tool != "edit":
            return RESPONSE_CHAIN
        # print (f"event: {event_type}, modifiers: '{modifiers}', keycode: '{keycode}'")
        offset = 5
        s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
        offset /= s

        if event_type == "leftdown":
            self.scene.tool_active = True
            self._active = True
            self.scene.context("window open NodeEditIcons\n")
            # Refocus, to allow typing...
            self.scene.gui.scene_panel.SetFocus()

            self.scene.context.signal("statusmsg", self.message)
            self.move_type = "node"

            xp = space_pos[0]
            yp = space_pos[1]
            if self.nodes:
                w = offset * 4
                h = offset * 4
                for i, entry in enumerate(self.nodes):
                    pt = entry["point"]
                    node = self.element
                    ptx, pty = node.matrix.point_in_matrix_space(pt)
                    x = ptx - 2 * offset
                    y = pty - 2 * offset
                    if x <= xp <= x + w and y <= yp <= y + h:
                        self.selected_index = i
                        if entry["type"] == "control":
                            # We select the corresponding end point
                            j = entry["connector"]
                            for entry2 in self.nodes:
                                entry2["selected"] = False
                            self.nodes[j]["selected"] = True
                        else:
                            # Shift-Key Pressed?
                            if "shift" not in modifiers:
                                self.clear_selection()
                            entry["selected"] = not entry["selected"]
                        break
                else:  # For-else == icky
                    self.selected_index = None
            if self.selected_index is None:
                # Fine we start a selection rectangle to select multiple nodes
                self.move_type = "selection"
                self.p1 = complex(space_pos[0], space_pos[1])
            return RESPONSE_CONSUME
        elif event_type == "middledown" or event_type == "rightdown":
            return RESPONSE_DROP
        elif event_type == "move":
            if self.move_type == "selection":
                if self.p1 is not None:
                    self.p2 = complex(space_pos[0], space_pos[1])
                    self.scene.request_refresh()
            else:
                if not self.selected_index:
                    self.scene.request_refresh()
                    return RESPONSE_CONSUME
                current = self.nodes[self.selected_index]
                pt = current["point"]
                seg = current["segment"]
                node = self.element
                m = node.matrix.point_in_inverse_space(space_pos[:2])
                pt.x = m[0]
                pt.y = m[1]
                current["point"] = pt
                if seg is node.path._segments[0]:
                    seg.start = pt

                self.modify_element(False)
            return RESPONSE_CONSUME
        elif event_type == "key_down":
            if not self.scene.tool_active:
                return RESPONSE_CHAIN
            # print (f"event: {event_type}, modifiers: '{modifiers}', keycode: '{keycode}'")
            return RESPONSE_CONSUME
        elif event_type == "key_up":
            if not self.scene.tool_active:
                return RESPONSE_CHAIN
            # print (f"event: {event_type}, modifiers: '{modifiers}', keycode: '{keycode}'")
            if modifiers == "escape":
                self.done(forgood=True)
                return RESPONSE_CONSUME
            # print(f"Key: '{keycode}'")
            if not self.selected_index is None:
                entry = self.nodes[self.selected_index]
            else:
                entry = None
            if keycode in self.commands:
                action = self.commands[keycode]
                # print(f"Execute {action[1]}")
                action[0]()

            return RESPONSE_CONSUME

        elif event_type == "lost":
            if self.scene.tool_active:
                self.done(forgood=True)
                return RESPONSE_CONSUME
            else:
                return RESPONSE_CHAIN
        elif event_type == "rightdown":
            self.done(forgood=True)
            return RESPONSE_CONSUME
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
                for entry in self.nodes:
                    pt = entry["point"]
                    if (
                        entry["type"] == "point"
                        and x0 <= pt.x <= x1
                        and y0 <= pt.y <= y1
                    ):
                        entry["selected"] = True
                self.scene.request_refresh()
            self.p1 = None
            self.p2 = None
            return RESPONSE_CONSUME
        return RESPONSE_DROP

    def signal(self, signal, *args, **kwargs):
        if isinstance(args, (tuple, list)) and len(args)==1:
            if isinstance(args[0], (tuple, list)):
                args = args[0]
        if signal == "tool_changed":
            if len(args) > 1 and args[1] == "edit":
                selected_node = self.scene.context.elements.first_element(
                    emphasized=True
                )
                if selected_node is not None:
                    self.calculate_points(selected_node)
                    self.scene.request_refresh()
            else:
                # Someone else...
                print (f"Not for me?! {signal} - 0: {args[0]}, 1: {args[1]}, len={len(args)}")
                self.done(forgood=True)
            return
        if self.element is None:
            return
        if signal == "nodeedit" and args[0]:
            keycode = args[0]
            if keycode in self.commands:
                action = self.commands[keycode]
                # print(f"Execute {action[1]}")
                action[0]()

class NodeEditPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: clsLasertools.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        buttonsizer = wx.GridSizer(cols=3, gap=wx.Size(2, 2))
        self.commands = (
            # icon, label, signal, condition
            ("c", icons8_node_edit_50, _("Clear")),
            ("d", icons8_node_edit_50, _("Delete")),
            ("b", icons8_node_edit_50, _("Bezier")),
            ("l", icons8_node_edit_50, _("Line")),
            ("q", icons8_node_edit_50, _("Quad")),
            ("x", icons8_node_edit_50, _("Break")),
            ("i", icons8_node_edit_50, _("Insert")),
            ("a", icons8_node_edit_50, _("Append")),
        )
        self.buttons = []
        for cmd in self.commands:
            btn = wx.BitmapButton(
                self, wx.ID_ANY, cmd[1].GetBitmap(resize=25, use_theme=False)
            )
            btn.Bind(wx.EVT_BUTTON, self.send_signal(cmd[0]))
            btn.SetToolTip(cmd[2])
            self.buttons.append(btn)
            buttonsizer.Add(btn, 0, 0, 0)
        mainsizer.Add(buttonsizer, 0, 0, 0)
        self.SetSizer(mainsizer)

        self.Layout()

    #
    def send_signal(self, code):
        def handler(event):
            self.context.signal("nodeedit", code)

        return handler


class NodeEditWindow(MWindow):
    def __init__(self, *args, **kwds):
        rows = 3
        cols = 3
        iconsize = 25
        super().__init__(
            (cols + 1) * iconsize, (rows + 1) * iconsize, submenu="", *args, **kwds
        )
        self.panel = NodeEditPanel(self, wx.ID_ANY, context=self.context)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_node_edit_50.GetBitmap(resize=25))
        # _icon.CopyFromBitmap(icons8_computer_support_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Node-Editor"))

    def window_open(self):
        pass

    def window_close(self):
        pass

    def delegates(self):
        yield self.panel

    @staticmethod
    def submenu():
        # Suppress = True
        return ("", "Node-Editor", True)
