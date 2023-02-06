import math

import wx

from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.gui.scene.sceneconst import (
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
    RESPONSE_DROP,
)
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.svgelements import Move, Close, Arc, CubicBezier, QuadraticBezier, Line, Point
from meerk40t.gui.icons import PyEmbeddedImage

_ = wx.GetTranslation


class NodeIconPanel(wx.Panel):
    def __init__(self, *args, context=None, edit_tool=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.edit_tool = edit_tool

        mainsizer = wx.BoxSizer(wx.HORIZONTAL)
        node_add = PyEmbeddedImage(
            b'iVBORw0KGgoAAAANSUhEUgAAABkAAAAZAQMAAAD+JxcgAAAABlBMVEUAAAD///+l2Z/dAAAA'
            b'CXBIWXMAAA7EAAAOxAGVKw4bAAAAJ0lEQVQImWP4//h/AwM24g+DPDKBU93//yCCoR5G2KEQ'
            b'YIAmBlcMABg0P3m4MIsZAAAAAElFTkSuQmCC')

        node_append = PyEmbeddedImage(
            b'iVBORw0KGgoAAAANSUhEUgAAABkAAAAZAQMAAAD+JxcgAAAABlBMVEUAAAD///+l2Z/dAAAA'
            b'CXBIWXMAAA7EAAAOxAGVKw4bAAAALklEQVQImWP4//h/AwM24g+DPDKBU93//zCC/wd7A8P7'
            b'39+RiRfM3zHEwOpAOgBQXErXEDO0NAAAAABJRU5ErkJggg==')

        node_break = PyEmbeddedImage(
            b'iVBORw0KGgoAAAANSUhEUgAAABcAAAAZAQMAAADg7ieTAAAABlBMVEUAAAD///+l2Z/dAAAA'
            b'CXBIWXMAAA7EAAAOxAGVKw4bAAAAOElEQVQImWP4//8fw39GIK6FYIYaBjgbLA6Sf4+EGaG4'
            b'GYiPQ8Qa/jEx7Pv3C4zt/v2As0HiQP0AnIQ8UXzwP+sAAAAASUVORK5CYII=')

        node_curve = PyEmbeddedImage(
            b'iVBORw0KGgoAAAANSUhEUgAAABkAAAAZAQMAAAD+JxcgAAAABlBMVEUAAAD///+l2Z/dAAAA'
            b'CXBIWXMAAA7EAAAOxAGVKw4bAAAARklEQVQImWP4//9/AwOUOAgi7gKJP7JA4iGIdR4kJg+U'
            b'/VcPIkDq/oCInyDiN4j4DCK+w4nnIOI9iGgGEbtRiWYk2/43AADobVHMAT+avQAAAABJRU5E'
            b'rkJggg==')

        node_delete = PyEmbeddedImage(
            b'iVBORw0KGgoAAAANSUhEUgAAABkAAAAZAQMAAAD+JxcgAAAABlBMVEUAAAD///+l2Z/dAAAA'
            b'CXBIWXMAAA7EAAAOxAGVKw4bAAAAKUlEQVQImWP4//9/AwM24g+DPDKBUx0SMakeSOyvh3FB'
            b'LDBAE4OoA3IBbltJOc3s08cAAAAASUVORK5CYII=')

        node_join = PyEmbeddedImage(
            b'iVBORw0KGgoAAAANSUhEUgAAABkAAAAZAQMAAAD+JxcgAAAABlBMVEUAAAD///+l2Z/dAAAA'
            b'CXBIWXMAAA7EAAAOxAGVKw4bAAAAPklEQVQImWP4//9/A8OD/80NDO/+74YSff93IHPBsv+/'
            b'/0chGkDEQRDxGC72H04wgIg6GNFQx4DMhcgC1QEARo5M+gzPuwgAAAAASUVORK5CYII=')

        node_line = PyEmbeddedImage(
            b'iVBORw0KGgoAAAANSUhEUgAAABkAAAAZAQMAAAD+JxcgAAAABlBMVEUAAAD///+l2Z/dAAAA'
            b'CXBIWXMAAA7EAAAOxAGVKw4bAAAARElEQVQImWP4//9/A8P//wdAxD0sRAOIsAcS/+qBxB+Q'
            b'4p8g4jOIeA4izoOI+SDCHkj8qwcSf0CGNoKIvViIRoiV/xsA49JQrrbQItQAAAAASUVORK5C'
            b'YII=')

        node_symmetric = PyEmbeddedImage(
            b'iVBORw0KGgoAAAANSUhEUgAAABkAAAAZAQMAAAD+JxcgAAAABlBMVEUAAAD///+l2Z/dAAAA'
            b'CXBIWXMAAA7EAAAOxAGVKw4bAAAAV0lEQVQImV3NqxGAMBRE0R2qQoXS2ApICVDJowRKQEYi'
            b'YsIAWX6DIObIeyGJeGgllDTKwKjMl147MesgJq3Eoo0IjES0QCTzROdqYnAV4S1dZbvz/B5/'
            b'TrOwSVb5BTbFAAAAAElFTkSuQmCC')

        node_smooth = PyEmbeddedImage(
            b'iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAYAAADE6YVjAAAAAXNSR0IArs4c6QAAAARnQU1B'
            b'AACxjwv8YQUAAAAJcEhZcwAADsQAAA7EAZUrDhsAAAIgSURBVEhLY/wPBAw0BkxQmqZg+FhC'
            b'VJx8+fyZ4fKVK1AeBEhKSDAoKCpCefgBUZZcvHCBITo6CsqDgJjYWIaKikooDz8gKrjevX8P'
            b'ZSHAh3fvGX7//g3l4Qc4ffLz50+G9evWMSxftpTh7r17UFFUwM3NzeDm6saQlJLMoKioBBXF'
            b'BFgtOX/+HENNdRXDw4ePwHwZGVmGJ08eg9kwICQkxPDj+3eGb0DMxMTEkJySwpCdncPAwsIC'
            b'VYEAGJZs3bqFoaaqiuH3nz8Mjg6ODHkFBWADFy1cCFUBAdo6Ogx2dnYMq1etYpg6dQrDly9f'
            b'GKysbRgmTpzIwMnJCVUFBSBLYODgwYP/dXV1/usB8do1a6CihMGLF8//h4YE/9fW0vyfmZn5'
            b'/++fP1AZCIBb8ubNm/8W5mb/dbS1/m/ftg0qSjz4/Pnz/4AAf7BF8+bOhYpCANyS2tpqsIKO'
            b'jnaoCOng/v37/40MDf4bGxmCHQ0DYEtAAoYG+mCfAMMWLEEu6O7qAjt22rSpUJH//8H55MD+'
            b'/Qy/fv1i8A8IACdLSkBkZCSY3rVzJ5gGAWZ+Pr6G7du3MgB9wyAsJMzwB5iq1DU0oNKkg/Xr'
            b'1zFcOHeO4dWrVwzfvn4DZofzDIwgr0HlwcDZ2Ylh4qQpUB7pwNfHh+H+fUTmBYXMaH1CEmA8'
            b'duwYSpyAihB1dXUoj3QAqhZA5RkMMDMzEVefUApGI54EwMAAANLW9DiEznjCAAAAAElFTkSu'
            b'QmCC')

        self.icons = {
            # "command": (image, active_for_path, active_for_poly, "tooltiptext"),
            "i": (node_add, True, True, _("Insert point before")),
            "a": (node_append, True, True, _("Append point at end")),
            "d": (node_delete, True, True, _("Delete point")),
            "l": (node_line, True, False, _("Make segment a line")),
            "c": (node_curve, True, False, _("Make segment a curve")),
            "s": (node_symmetric, True, False, _("Make segment symmetrical")),
            "j": (node_join, True, False, _("Join two segments")),
            "b": (node_break, True, False, _("Break segment apart")),
            "o": (node_smooth, True, False, _("Smoothen transit to adjacent segments")),
        }
        for command, entry in self.icons:
            button = wx.Button(self, wx.ID_ANY, "")
            button.SetBitmap(entry[0].GetBitmap(resize=25))
            button.Bind(wx.EVT_BUTTON, self.button_action(command))
            mainsizer.Add(button, 0, 0, 0)
        self.SetSizer(mainsizer)
        self.Layout()

    def button_action(self, command):
        def action(event):
            self.edit_tool.perform_action(command)

        return action

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
        self.node_type = "path"
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
            "d": (self.delete_nodes, _("Delete")),
            "l": (self.convert_to_line, _("Line")),
            "c": (self.convert_to_curve, _("Curve")),
            "s": (self.quad_symmetrical, _("Symmetrical")),
            "i": (self.insert_midpoint, _("Insert")),
            "a": (self.append_line, _("Append")),
            "b": (self.break_path, _("Break")),
            "j": (self.join_path, _("Join")),
            "o": (self.smoothen, _("Smoothen")),
        }
        self.message = ""
        for cmd in self.commands:
            action = self.commands[cmd]
            if self.message:
                self.message += ", "
            self.message += f"{cmd}: {action[1]}"
        self.debug_current = None

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
        self.debug_current = None
        self.element = selected_node
        self.selected_index = None
        self.nodes = []
        if selected_node is None:
            return
        if selected_node.type == "elem polyline":
            self.node_type = "polyline"
            try:
                shape = selected_node.shape
            except AttributeError:
                return
            start = 0
            for idx, pt in enumerate(shape.points):
                self.nodes.append(
                    {
                        "prev": None,
                        "next": None,
                        "point": pt,
                        "segment": None,
                        "path": shape,
                        "type": "point",
                        "connector": -1,
                        "selected": False,
                        "segtype": "L",
                        "start": start,
                    }
                )
        else:
            self.node_type = "path"
            try:
                path = selected_node.path
            except AttributeError:
                return
            # print (f"Path: {str(path)}")
            prev_seg = None
            start = 0
            # Idx of last point
            l_idx = 0
            for idx, segment in enumerate(path._segments):
                if idx < len(path._segments) - 1:
                    next_seg = path._segments[idx + 1]
                else:
                    next_seg = None
                if isinstance(segment, Move):
                    if idx != start:
                        start = idx

                if isinstance(segment, (Line, Close)):
                    self.nodes.append(
                        {
                            "prev": prev_seg,
                            "next": next_seg,
                            "point": segment.end,
                            "segment": segment,
                            "path": path,
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
                            "path": path,
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
                            "path": path,
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
                            "path": path,
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
                            "path": path,
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
                            "path": path,
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
                            "path": path,
                            "type": "control",
                            "connector": nidx,
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
                            "path": path,
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
                            "path": path,
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
        self.scene.context.signal("tool none")
        self.scene.context.signal("statusmsg", "")
        self.scene.context.elements.validate_selected_area()
        self.scene.request_refresh()

    def modify_element(self, reload=True):
        if self.element is None:
            return
        # Debugging....
        # totalstr = ""
        # laststr = ""
        # lastseg = None
        # for idx, seg in enumerate(self.element.path):

        #     if isinstance(seg, Move):
        #         segstr = "M "
        #     elif isinstance(seg, Line):
        #         segstr = "L "
        #     elif isinstance(seg, QuadraticBezier):
        #         segstr = "Q "
        #     elif isinstance(seg, CubicBezier):
        #         segstr = "C "
        #     elif isinstance(seg, Arc):
        #         segstr = "A "
        #     else:
        #         segstr = "? "
        #     if hasattr(seg, "start"):
        #         if seg.start is None:
        #             segstr += "none - "
        #         else:
        #             segstr += f"{seg.start.x:.1f}, {seg.start.y:.1f} - "
        #         if idx > 0 and lastseg is not None and seg.start != lastseg:
        #             # Debug message to indicate there's something wrong
        #             # print (f"Differed at #{idx}: {laststr} - {segstr}")
        #             pass

        #     lastseg = None
        #     if hasattr(seg, "end"):
        #         lastseg = seg.end
        #         if seg.end is None:
        #             segstr += "none - "
        #         else:
        #             segstr += f"{seg.end.x:.1f}, {seg.end.y:.1f}"

        #     totalstr += " " + segstr
        #     laststr = segstr
        # # print (totalstr)
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

    def clear_selection(self):
        if self.nodes is not None:
            for entry in self.nodes:
                entry["selected"] = False

    def smoothen(self):
        modified = False
        if self.node_type == "polyline":
            # Not valid for a polyline Could make a path now but that might be more than the user expected...
            return
        for entry in self.nodes:
            if entry["selected"] and entry["segtype"] == "C": # Cubic Bezier only
                segment = entry["segment"]
                pt_start = segment.start
                pt_end = segment.end
                pt_control1 = segment.control1
                pt_control2 = segment.control2
                other_segment = entry["prev"]
                if other_segment is not None:
                    if isinstance(other_segment, Line):
                        other_pt_x = (other_segment.start.x)
                        other_pt_y = (other_segment.start.y)
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

    def quad_symmetrical(self):
        modified = False
        if self.node_type == "polyline":
            # Not valid for a polyline Could make a path now but that might be more than the user expected...
            return
        for entry in self.nodes:
            if entry["selected"] and entry["segtype"] == "C": # Cubic Bezier only
                segment = entry["segment"]
                pt_start = segment.start
                pt_end = segment.end
                midpoint = Point((pt_end.x + pt_start.x) / 2, (pt_end.y + pt_start.y) / 2)
                angle_to_end = midpoint.angle_to(pt_end)
                angle_to_start = midpoint.angle_to(pt_start)
                angle_to_control2 = midpoint.angle_to(segment.control2)
                distance = midpoint.distance_to(segment.control2)
                # The new point
                angle_to_control1 = angle_to_start + (angle_to_end - angle_to_control2)
                newx = midpoint.x + distance * math.cos(angle_to_control1)
                newy = midpoint.y + distance * math.sin(angle_to_control1)
                segment.control1 = Point(newx, newy)
                modified = True
        if modified:
            self.modify_element(True)

    def delete_nodes(self):
        # Stub for deleting a segment
        modified = False
        for idx, entry in enumerate(self.nodes):
            if entry["selected"] and entry["type"] == "point":
                if self.node_type == "polyline":
                    if len(self.element.shape.points) > 2:
                        modified = True
                        self.element.shape.points.pop(idx)
                    else:
                        break
                pass
        if modified:
            self.modify_element(True)

    def convert_to_line(self):
        # Stub for converting segment to a line
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
                if entry["segtype"] in ("C", "Q", "A"):
                    pass
                else:
                    continue
                newsegment = Line(start=startpt, end=endpt)
                self.element.path._segments[idx] = newsegment
                modified = True
        if modified:
            self.modify_element(True)

    def convert_to_curve(self):
        # Stub for converting segment to a quad
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
                    ctrl1pt = Point(startpt.x + 0.25 *(endpt.x - startpt.x), startpt.y + 0.25 * (endpt.y - startpt.y))
                    ctrl2pt = Point(startpt.x + 0.75 *(endpt.x - startpt.x), startpt.y + 0.75 * (endpt.y - startpt.y))
                elif entry["segtype"] == "Q":
                    ctrl1pt = Point(entry["segment"].control.x, entry["segment"].control.y)
                    ctrl2pt = Point(endpt.x, endpt.y)
                elif entry["segtype"] == "A":
                    ctrl1pt = Point(startpt.x + 0.25 *(endpt.x - startpt.x), startpt.y + 0.25 * (endpt.y - startpt.y))
                    ctrl2pt = Point(startpt.x + 0.75 *(endpt.x - startpt.x), startpt.y + 0.75 * (endpt.y - startpt.y))
                else:
                    continue

                newsegment = CubicBezier(start=startpt, end=endpt, control1=ctrl1pt, control2=ctrl2pt)
                self.element.path._segments[idx] = newsegment
                modified = True
        if modified:
            self.modify_element(True)

    def break_path(self):
        # Stub for breaking the path
        modified = False
        if self.node_type == "polyline":
            # Not valid for a polyline Could make a path now but that might be more than the user expected...
            return
        for entry in self.nodes:
            if entry["selected"] and entry["type"] == "point":
                pass
        if modified:
            self.modify_element(True)

    def join_path(self):
        # Stub for breaking the path
        modified = False
        if self.node_type == "polyline":
            # Not valid for a polyline Could make a path now but that might be more than the user expected...
            return
        for entry in self.nodes:
            if entry["selected"] and entry["type"] == "point":
                pass
        if modified:
            self.modify_element(True)

    def insert_midpoint(self):
        # Stub for inserting a point...
        modified = False
        # Back to
        for idx in range(len(self.nodes) - 1, -1, -1):
            entry = self.nodes[idx]
            if entry["selected"] and entry["type"] == "point":
                if self.node_type == "polyline":
                    pt1 = self.element.shape.points[idx]
                    if idx == 0:
                        # Very first point? Mirror first segment and take midpoint
                        pt2 = Point(self.element.shape.points[idx + 1].x, self.element.shape.points[idx + 1].y)
                        pt2.x = pt1.x - (pt2.x - pt1.x)
                        pt2.y = pt1.y - (pt2.y - pt1.y)
                        pt2.x = (pt1.x + pt2.x) / 2
                        pt2.y = (pt1.y + pt2.y) / 2
                        self.element.shape.points.insert(0, pt2)
                    else:
                        pt2 = Point(self.element.shape.points[idx - 1].x, self.element.shape.points[idx - 1].y)
                        pt2.x = (pt1.x + pt2.x) / 2
                        pt2.y = (pt1.y + pt2.y) / 2
                        # Mid point
                        self.element.shape.points.insert(idx, pt2)
                    modified = True
        if modified:
            self.modify_element(True)

    def append_line(self):
        # Stub for appending a line, works all the time and does not require a valid selection
        modified = False
        if self.node_type == "polyline":
            idx = len(self.element.shape.points) - 1
            pt1 = self.element.shape.points[idx - 1]
            pt2 = self.element.shape.points[idx]
            newpt = Point(pt2.x + (pt2.x - pt1.x) / 2, pt2.y + (pt2.y - pt1.y) / 2)
            self.element.shape.points.append(newpt)
            modified = True
        else:
            # path
            # Code to follow
            pass
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
                node = self.element
                # pnode = current["prev"]
                # if pnode is not None:
                #     if pnode.start is not None:
                #         sx = f"{pnode.start.x:.1f}, {pnode.start.y:.1f}"
                #     else:
                #         sx = "<none>"
                #     if pnode.end is not None:
                #         sy = f"{pnode.end.x:.1f}, {pnode.end.y:.1f}"
                #     else:
                #         sy = "<none>"
                #     print (f"Prev: {pnode.d()}, {sx} - {sy}")
                # else:
                #     print ("Prev: ---")
                # pnode = current["segment"]
                # if pnode.start is not None:
                #     sx = f"{pnode.start.x:.1f}, {pnode.start.y:.1f}"
                # else:
                #     sx = "<none>"
                # if pnode.end is not None:
                #     sy = f"{pnode.end.x:.1f}, {pnode.end.y:.1f}"
                # else:
                #     sy = "<none>"
                # print (f"This: {pnode.d()}, {sx} - {sy}")
                # pnode = current["next"]
                # if pnode is not None:
                #     if pnode.start is not None:
                #         sx = f"{pnode.start.x:.1f}, {pnode.start.y:.1f}"
                #     else:
                #         sx = "<none>"
                #     if pnode.end is not None:
                #         sy = f"{pnode.end.x:.1f}, {pnode.end.y:.1f}"
                #     else:
                #         sy = "<none>"
                #     print (f"Next: {pnode.d()}, {sx} - {sy}")
                # else:
                #     print ("Next: ---")

                m = node.matrix.point_in_inverse_space(space_pos[:2])
                pt.x = m[0]
                pt.y = m[1]
                if self.node_type == "path":
                    if current["segtype"] == "M" and current["start"] == self.selected_index: # First
                        current["segment"].start = pt
                    current["point"] = pt
                    # We need to adjust the start-point of the next segment
                    # unless it's a closed path then we need to adjust the
                    # very first - need to be mindful of closed subpaths
                    nextseg = current["next"]
                    if nextseg is not None:
                        if nextseg.start is not None:
                            nextseg.start.x = m[0]
                            nextseg.start.y = m[1]
                        # if isinstance(current["segment"], Close):
                        #     # We need to change the startseg
                        #     if "start" in current:
                        #         startidx = current["start"]
                        #         if startidx >= 0:
                        #             startseg = self.nodes[startidx]["segment"]
                        #             if startseg.start == startseg.end:
                        #                 startseg.start = Point(m[0], m[1])
                        #             startseg.end = Point(m[0], m[1])

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
            self.perform_action(keycode)

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

    def perform_action(self, code):
        if code in self.commands:
            action = self.commands[code]
            print(f"Execute {action[1]}")
            action[0]()

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
            self.perform_action(keycode)
