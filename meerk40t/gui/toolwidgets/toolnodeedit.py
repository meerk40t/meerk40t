import math

import wx

from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.gui.scene.sceneconst import (
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
    RESPONSE_DROP,
)
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.svgelements import Move, Close, Arc, CubicBezier, QuadraticBezier, Line
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
        self.pen_ctrl.SetColour(wx.CYAN)
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

    def init(self, context):
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
        for idx, segment in enumerate(path._segments):
            if idx < len(path._segments) - 1:
                next_seg = path._segments[idx + 1]
            else:
                next_seg = None

            if isinstance(segment, (Line, Close)):
                self.nodes.append(
                    {
                        "next": next_seg,
                        "point": segment.end,
                        "segment": segment,
                        "path": path,
                        "type": "point",
                        "connector": -1,
                        "selected": False,
                    }
                )
            elif isinstance(segment, Move):
                self.nodes.append(
                    {
                        "next": next_seg,
                        "point": segment.end,
                        "segment": segment,
                        "path": path,
                        "type": "point",
                        "connector": -1,
                        "selected": False,
                    }
                )
            elif isinstance(segment, QuadraticBezier):
                self.nodes.append(
                    {
                        "next": next_seg,
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
            elif isinstance(segment, CubicBezier):
                self.nodes.append(
                    {
                        "next": next_seg,
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

    def done(self):
        self.scene.tool_active = False
        self.scene.modif_active = False
        self.p1 = None
        self.p2 = None
        self.move_type = "node"
        self.scene.context.signal("statusmsg", "")
        self.scene.context.elements.validate_selected_area()
        self.scene.request_refresh()

    def clear_selection(self):
        if self.nodes is not None:
            for entry in self.nodes:
                entry["selected"] = False

    def modify_element(self, reload=True):
        if self.element is None:
            return
        from meerk40t.svgelements import Move, QuadraticBezier, CubicBezier, Line, Arc
        totalstr = ""
        laststr = ""
        lastseg = None
        for idx, seg in enumerate(self.element.path):

            if isinstance(seg, Move):
                segstr = "M "
            elif isinstance(seg, Line):
                segstr = "L "
            elif isinstance(seg, QuadraticBezier):
                segstr = "Q "
            elif isinstance(seg, CubicBezier):
                segstr = "C "
            elif isinstance(seg, Arc):
                segstr = "A "
            else:
                segstr = "? "
            if hasattr(seg, "start"):
                if seg.start is None:
                    segstr += "none - "
                else:
                    segstr += f"{seg.start.x:.1f}, {seg.start.y:.1f} - "
                if idx > 0 and lastseg is not None and seg.start != lastseg:
                    print (f"Differed at #{idx}: {laststr} - {segstr}")

            lastseg = None
            if hasattr(seg, "end"):
                lastseg = seg.end
                if seg.end is None:
                    segstr += "none - "
                else:
                    segstr += f"{seg.end.x:.1f}, {seg.end.y:.1f}"

            totalstr += " " + segstr
            laststr = segstr
        # print (totalstr)
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
        # Stub for deleting a segment
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
        elements = self.scene.context.elements
        if event_type == "leftdown":
            self.pen = wx.Pen()
            self.pen.SetColour(wx.Colour(swizzlecolor(elements.default_stroke)))
            self.pen.SetWidth(elements.default_strokewidth)
            self.scene.tool_active = True
            self.scene.modif_active = True

            self._active = True

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
                node = self.element
                m = node.matrix.point_in_inverse_space(space_pos[:2])
                pt.x = m[0]
                pt.y = m[1]
                current["point"] = pt
                # We need to adjust the start-point of the next segment
                # unless it's a closed path then we need to adjust the
                # very first - need to be mindful of closed subpaths
                if "next" in current:
                    nextseg = current["next"]
                    if hasattr(nextseg, "start"):
                        nextseg.start.x = m[0]
                        nextseg.start.y = m[1]
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
                self.done()
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
        #  print (f"Signal: {signal}, args={args}")
        if signal == "tool_changed":
            if len(args) > 1 and args[1] == "edit":
                selected_node = self.scene.context.elements.first_element(
                    emphasized=True
                )
                if selected_node is not None:
                    self.calculate_points(selected_node)
                    self.scene.request_refresh()
            return
        if self.element is None:
            return
        if signal == "nodeedit" and args[0]:
            keycode = args[0]
            if keycode in self.commands:
                action = self.commands[keycode]
                # print(f"Execute {action[1]}")
                action[0]()
