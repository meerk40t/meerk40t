import math
from copy import copy

import wx

from meerk40t.gui.icons import PyEmbeddedImage, STD_ICON_SIZE
from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.scene.sceneconst import (
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
    RESPONSE_DROP,
)
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.kernel import signal_listener
from meerk40t.svgelements import (
    Arc,
    Close,
    CubicBezier,
    Line,
    Move,
    Point,
    Polygon,
    Polyline,
    QuadraticBezier,
)

_ = wx.GetTranslation


class NodeIconPanel(wx.Panel):
    """
    The Node-Editor toolbar, will interact with the tool class by exchanging signals
    """

    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        mainsizer = wx.BoxSizer(wx.HORIZONTAL)
        node_add = PyEmbeddedImage(
            b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZAQMAAAD+JxcgAAAABlBMVEUAAAD///+l2Z/dAAAA"
            b"CXBIWXMAAA7EAAAOxAGVKw4bAAAAJ0lEQVQImWP4//h/AwM24g+DPDKBU93//yCCoR5G2KEQ"
            b"YIAmBlcMABg0P3m4MIsZAAAAAElFTkSuQmCC"
        )

        node_append = PyEmbeddedImage(
            b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZAQMAAAD+JxcgAAAABlBMVEUAAAD///+l2Z/dAAAA"
            b"CXBIWXMAAA7EAAAOxAGVKw4bAAAALklEQVQImWP4//h/AwM24g+DPDKBU93//zCC/wd7A8P7"
            b"39+RiRfM3zHEwOpAOgBQXErXEDO0NAAAAABJRU5ErkJggg=="
        )

        node_break = PyEmbeddedImage(
            b"iVBORw0KGgoAAAANSUhEUgAAABcAAAAZAQMAAADg7ieTAAAABlBMVEUAAAD///+l2Z/dAAAA"
            b"CXBIWXMAAA7EAAAOxAGVKw4bAAAAOElEQVQImWP4//8fw39GIK6FYIYaBjgbLA6Sf4+EGaG4"
            b"GYiPQ8Qa/jEx7Pv3C4zt/v2As0HiQP0AnIQ8UXzwP+sAAAAASUVORK5CYII="
        )

        node_curve = PyEmbeddedImage(
            b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZAQMAAAD+JxcgAAAABlBMVEUAAAD///+l2Z/dAAAA"
            b"CXBIWXMAAA7EAAAOxAGVKw4bAAAARklEQVQImWP4//9/AwOUOAgi7gKJP7JA4iGIdR4kJg+U"
            b"/VcPIkDq/oCInyDiN4j4DCK+w4nnIOI9iGgGEbtRiWYk2/43AADobVHMAT+avQAAAABJRU5E"
            b"rkJggg=="
        )

        node_delete = PyEmbeddedImage(
            b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZAQMAAAD+JxcgAAAABlBMVEUAAAD///+l2Z/dAAAA"
            b"CXBIWXMAAA7EAAAOxAGVKw4bAAAAKUlEQVQImWP4//9/AwM24g+DPDKBUx0SMakeSOyvh3FB"
            b"LDBAE4OoA3IBbltJOc3s08cAAAAASUVORK5CYII="
        )

        node_join = PyEmbeddedImage(
            b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZAQMAAAD+JxcgAAAABlBMVEUAAAD///+l2Z/dAAAA"
            b"CXBIWXMAAA7EAAAOxAGVKw4bAAAAPklEQVQImWP4//9/A8OD/80NDO/+74YSff93IHPBsv+/"
            b"/0chGkDEQRDxGC72H04wgIg6GNFQx4DMhcgC1QEARo5M+gzPuwgAAAAASUVORK5CYII="
        )

        node_line = PyEmbeddedImage(
            b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZAQMAAAD+JxcgAAAABlBMVEUAAAD///+l2Z/dAAAA"
            b"CXBIWXMAAA7EAAAOxAGVKw4bAAAARElEQVQImWP4//9/A8P//wdAxD0sRAOIsAcS/+qBxB+Q"
            b"4p8g4jOIeA4izoOI+SDCHkj8qwcSf0CGNoKIvViIRoiV/xsA49JQrrbQItQAAAAASUVORK5C"
            b"YII="
        )

        node_symmetric = PyEmbeddedImage(
            b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZAQMAAAD+JxcgAAAABlBMVEUAAAD///+l2Z/dAAAA"
            b"CXBIWXMAAA7EAAAOxAGVKw4bAAAAV0lEQVQImV3NqxGAMBRE0R2qQoXS2ApICVDJowRKQEYi"
            b"YsIAWX6DIObIeyGJeGgllDTKwKjMl147MesgJq3Eoo0IjES0QCTzROdqYnAV4S1dZbvz/B5/"
            b"TrOwSVb5BTbFAAAAAElFTkSuQmCC"
        )

        node_smooth = PyEmbeddedImage(
            b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAYAAADE6YVjAAAAAXNSR0IArs4c6QAAAARnQU1B"
            b"AACxjwv8YQUAAAAJcEhZcwAADsQAAA7EAZUrDhsAAAIgSURBVEhLY/wPBAw0BkxQmqZg+FhC"
            b"VJx8+fyZ4fKVK1AeBEhKSDAoKCpCefgBUZZcvHCBITo6CsqDgJjYWIaKikooDz8gKrjevX8P"
            b"ZSHAh3fvGX7//g3l4Qc4ffLz50+G9evWMSxftpTh7r17UFFUwM3NzeDm6saQlJLMoKioBBXF"
            b"BFgtOX/+HENNdRXDw4ePwHwZGVmGJ08eg9kwICQkxPDj+3eGb0DMxMTEkJySwpCdncPAwsIC"
            b"VYEAGJZs3bqFoaaqiuH3nz8Mjg6ODHkFBWADFy1cCFUBAdo6Ogx2dnYMq1etYpg6dQrDly9f"
            b"GKysbRgmTpzIwMnJCVUFBSBLYODgwYP/dXV1/usB8do1a6CihMGLF8//h4YE/9fW0vyfmZn5"
            b"/++fP1AZCIBb8ubNm/8W5mb/dbS1/m/ftg0qSjz4/Pnz/4AAf7BF8+bOhYpCANyS2tpqsIKO"
            b"jnaoCOng/v37/40MDf4bGxmCHQ0DYEtAAoYG+mCfAMMWLEEu6O7qAjt22rSpUJH//8H55MD+"
            b"/Qy/fv1i8A8IACdLSkBkZCSY3rVzJ5gGAWZ+Pr6G7du3MgB9wyAsJMzwB5iq1DU0oNKkg/Xr"
            b"1zFcOHeO4dWrVwzfvn4DZofzDIwgr0HlwcDZ2Ylh4qQpUB7pwNfHh+H+fUTmBYXMaH1CEmA8"
            b"duwYSpyAihB1dXUoj3QAqhZA5RkMMDMzEVefUApGI54EwMAAANLW9DiEznjCAAAAAElFTkSu"
            b"QmCC"
        )

        node_smooth_all = PyEmbeddedImage(
            b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAAsTAAALEwEAmpwY"
            b"AAACs0lEQVR4nO2YO2hUQRSGj4r4loh2Rldws3P+/+zdK2xhSB+idop2FqJgFUEt1FJERBtt"
            b"VKy0UvCBz0IR0UKsTBoRBEVREcEHiEh8JBrlZu+uIbmYx97sA+eDKbaY/86/c86cMyPi8Xg8"
            b"Ho/nP6RYLM404PDIETjnpJlob22dY8TvkQPAOmkmzCxMMkJq9yaRGdLIFAqFeaa606DPkkwM"
            b"Gx8NOBoE2VZpNACsJfR1ZbHQH0b8SjDxrbI70D5Sd4vIdGkESN1rxGApdPAmCp8gCBYRuEui"
            b"Z/gw0w1mroPE5coc4FImk5ldVxMG7Bm2C6edcwvGPddcF6HvYjM36pY7Zq6rEj7Agclp2Mpy"
            b"SJJ6UGpNsVicS+JFbOJMNVr5fK5A4iuh/aqal1pCanc5J7LZ7MIU9PbF4XkxnRWOEwJPSka4"
            b"Q1LaYSM+EDoQtrUtlVpAMhsfn/1hGLakp4sTkW4e2CpTjVEvEHgQn1Sfo9+q2l6tLum2EHhY"
            b"0tWnQ9+h7qpWN3DORVojhyS3HdxYvREcS2hnzlera+Y6ktbsjYyF35HJh9boxEkr2UsHifbF"
            b"CX81tWSH3owNDEZ1aijZpxoC14eOYNXOtDTzwOa4eD+SWkHq9rjtOZeaJnAv1jyUlubYHyXn"
            b"E/opqvCBc0G1ennVzrh4DwDISJ2uBr3R3X+yOrlcbolRX8Y16aTU5QWG6C0nfTabnTVRjTAM"
            b"WyodCPRVmq3UhDCzZUa8jRdy3zm3YrxzA+cCoz6O534huUrqCYA2As//LkiPRIai4jnqCg3s"
            b"V9WcAcfj94LolHoPYLU0Aqq62ICzw4pZdM///q9HDStdnW+RXC6NRqlC65Xyv53cvOKnUe+Q"
            b"XCMi06SRiR43DHotwURPtHvSTBj0VIKR29Js5FXXJzyQb6v3ujwej8fj8Uid+AMS4JbuhXD/"
            b"gAAAAABJRU5ErkJggg=="
        )

        node_close = PyEmbeddedImage(
            b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAAsTAAALEwEAmpwY"
            b"AAACpklEQVR4nO2YSWsVQRRGjwlOcWM0YCDguFHzUKMrccClszEgiCKSgBiCYOJGI7qX4MYg"
            b"auLsD3DnhD5F/AGaxAHEZKFunDfqwiQ+KbgNl6K7051+TbpNHajV++7te19VV9dX4HA4HA7H"
            b"xDAFOA5cAGrJMTuBkoy3QB05Za1qJPfNHMtzM3OBrUCLvCOvIjSzAOgQfdhoAbbIM1KhEjgI"
            b"PAFGrML9xh0r/k2EGD2GgcfAAaCiXE1sAgZiFvLUyvExZnxJjT5gY9Imjsi/Yyd/DzwEbslS"
            b"0r99ApZbeVYD3UBPyDC5TM4PATPUNt4mTvkkuww0KM1ea6mZJgokpwG44rOMO+MmagL+qgTv"
            b"gBWWZpU1W6aJesrLSmBQPWMUaIwaPAf4oYL7A3aRfSk34VFjvaPfgGoicFYFfQUWBuhmAL3A"
            b"bWAp6bIY+K7q6horYBbwWwUcJTt0qLp+AVVh4t1K/BmYRnaYLivEq29XmLhXCa+RPW6o+i6F"
            b"CR8o4SGyx2FV3/0w4Usl3Eb22GHtpoH0K+F2su2B+ibF0upRwutkj5uqvotRt98vsuXlcvut"
            b"ko+NJ24nm270JzBzrIAu61yzKOUClwH3gPPA1ADNEuuIciZK4moraEAObmlQLwdO71l7fDQ1"
            b"1mfBLK/ZUR/QKEdmL3hQju1pNmEsQcHHlwxZx3izBcei0zI1xuRcFbeXlILVxIiYNO/ib40c"
            b"kWxjZS4oxkVbgNU1drQo9jTMvnZbjtJvJkpil02uYoC//wO0kpANwIsElwemMM2zmPHPgXWU"
            b"iQq5mikGzFDYeG3luhshZhh4BOwv53WQnxXeDDQDp2UrDBongPlWfJ3PzcuQ5GqW3JGsbBao"
            b"lZnSzZwkp/jNzHr+k2aayDHzgHPyjlROdDEOh8PhmJz8A+PVbUCLkfVDAAAAAElFTkSuQmCC"
        )

        self.icons = {
            # "command": [
            #           image, requires_selection,
            #           active_for_path, active_for_poly,
            #           "tooltiptext", button],
            "i": [
                node_add,
                True,
                True,
                True,
                _("Insert point before"),
                None,
                _("Insert"),
            ],
            "a": [
                node_append,
                False,
                True,
                True,
                _("Append point at end"),
                None,
                _("Append"),
            ],
            "d": [
                node_delete,
                True,
                True,
                True,
                _("Delete point"),
                None,
                _("Delete"),
            ],
            "l": [
                node_line,
                True,
                True,
                False,
                _("Make segment a line"),
                None,
                _("> Line"),
            ],
            "c": [
                node_curve,
                True,
                True,
                False,
                _("Make segment a curve"),
                None,
                _("> Curve"),
            ],
            "s": [
                node_symmetric,
                True,
                True,
                False,
                _("Make segment symmetrical"),
                None,
                _("Symmetric"),
            ],
            "j": [
                node_join,
                True,
                True,
                False,
                _("Join two segments"),
                None,
                _("Join"),
            ],
            "b": [
                node_break,
                True,
                True,
                False,
                _("Break segment apart"),
                None,
                _("Break"),
            ],
            "o": [
                node_smooth,
                True,
                True,
                False,
                _("Smoothen transit to adjacent segments"),
                None,
                _("Smooth"),
            ],
            "v": [
                node_smooth_all,
                False,
                True,
                False,
                _("Convert all lines into curves and smoothen"),
                None,
                _("Very smooth"),
            ],
            "z": [
                node_close,
                False,
                True,
                True,
                _("Toggle closed status"),
                None,
                _("Close"),
            ],
        }
        icon_size = STD_ICON_SIZE
        font = wx.Font(
            7,
            wx.FONTFAMILY_TELETYPE,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
        )
        # label = entry[6]
        label = ""
        for command in self.icons:
            entry = self.icons[command]
            button = wx.Button(
                self,
                wx.ID_ANY,
                label,
                size=wx.Size(icon_size + 10, icon_size + 10),
                style=wx.BU_BOTTOM | wx.BU_LEFT,
            )
            button.SetBitmap(entry[0].GetBitmap(resize=icon_size))
            button.Bind(wx.EVT_BUTTON, self.button_action(command))
            button.SetFont(font)
            # button = wx.StaticBitmap(
            #     self, wx.ID_ANY, size=wx.Size(icon_size + 10, icon_size + 10)
            # )
            # # button.SetBitmap(entry[0].GetBitmap(resize=icon_size))
            # button.SetBitmap(entry[0].GetBitmap(resize=icon_size))
            button.SetToolTip(entry[4])
            button.Enable(False)
            entry[5] = button
            button.Bind(wx.EVT_LEFT_DOWN, self.button_action(command))
            mainsizer.Add(button, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.SetSizer(mainsizer)
        self.Layout()

    @signal_listener("nodeedit")
    def realize(self, origin, *args):
        # print (f"Bar receives: {origin} - {args}")
        if args:
            if isinstance(args[0], (list, tuple)):
                mode = args[0][0]
                selection = args[0][1]
            else:
                mode = args[0]
                selection = args[1]
            if mode == "polyline":
                for command in self.icons:
                    entry = self.icons[command]
                    flag = True
                    if entry[1] and not selection:
                        # Only if something is selected
                        flag = False
                    if not entry[3]:
                        # Not for polyline mode
                        flag = False
                    entry[5].Enable(flag)
            elif mode == "path":
                for command in self.icons:
                    entry = self.icons[command]
                    flag = True
                    if entry[1] and not selection:
                        # Only if something is selected
                        flag = False
                    if not entry[2]:
                        # Not for path mode
                        flag = False
                    entry[5].Enable(flag)

    def button_action(self, command):
        def action(event):
            self.context.signal("nodeedit", ("action", command))

        return action


class NodeEditToolbar(MWindow):
    """
    Wrapper Window to display to Node-Editor toolbar
    Will hide itself from public view by expressing
    'return (xxx, xxx, False)' in method 'submenu'
    """

    def __init__(self, *args, **kwds):
        iconsize = STD_ICON_SIZE
        iconsize += 10
        iconcount = 11
        super().__init__(
            iconcount * iconsize - 10, iconsize + 35, submenu="", *args, **kwds
        )
        self.panel = NodeIconPanel(self, wx.ID_ANY, context=self.context)
        self.SetTitle(_("Node-Editor"))

    def window_open(self):
        pass

    def window_close(self):
        self.context("tool none\n")

    def delegates(self):
        yield self.panel

    @staticmethod
    def submenu():
        # Suppress = True
        return ("", "Node-Editor", True)


class EditTool(ToolWidget):
    """
    Edit tool allows you to view and edit the nodes within a
    selected element in the scene. It can currently handle
    polylines / polygons and paths.
    """

    def __init__(self, scene):
        ToolWidget.__init__(self, scene)
        self._listener_active = False
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
        # want to have sharp edges
        self.pen_selection.SetJoin(wx.JOIN_MITER)
        self.commands = {
            "d": (self.delete_nodes, _("Delete")),
            "l": (self.convert_to_line, _("Line")),
            "c": (self.convert_to_curve, _("Curve")),
            "s": (self.quad_symmetrical, _("Symmetric")),
            "i": (self.insert_midpoint, _("Insert")),
            "a": (self.append_line, _("Append")),
            "b": (self.break_path, _("Break")),
            "j": (self.join_path, _("Join")),
            "o": (self.smoothen, _("Smoothen")),
            "z": (self.toggle_close, _("Close path")),
            "v": (self.smoothen_all, _("Smooth all")),
            "w": (self.linear_all, _("Line all")),
        }
        self.message = ""
        for cmd in self.commands:
            action = self.commands[cmd]
            if self.message:
                self.message += ", "
            self.message += f"{cmd}: {action[1]}"
        self.debug_current = None

    def final(self, context):
        if self._listener_active:
            self.scene.context.unlisten("emphasized", self.on_emphasized_changed)
            self.scene.context.unlisten("nodeedit", self.on_signal_nodeedit)
        self._listener_active = False
        self.scene.request_refresh()
        try:
            self.scene.context("window close NodeEditToolbar\n")
        except (AssertionError, RuntimeError, KeyError):
            pass

    def init(self, context):
        self.scene.context.listen("emphasized", self.on_emphasized_changed)
        self.scene.context.listen("nodeedit", self.on_signal_nodeedit)
        self._listener_active = True
        self.scene.context("window open NodeEditToolbar\n")

    def on_emphasized_changed(self, origin, *args):
        selected_node = self.scene.context.elements.first_element(emphasized=True)
        if selected_node is not self.element:
            self.calculate_points(selected_node)
            self.scene.request_refresh()

    def set_pen_widths(self):
        def set_width_pen(pen, width):
            try:
                try:
                    pen.SetWidth(width)
                except TypeError:
                    pen.SetWidth(int(width))
            except OverflowError:
                pass  # Exceeds 32 bit signed integer.

        matrix = self.scene.widget_root.scene_widget.matrix
        linewidth = 1.0 / matrix.value_scale_x()
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

    def on_signal_nodeedit(self, origin, *args):
        # print (f"Signal: {origin} - {args}")
        if isinstance(args[0], (list, tuple)):
            mode = args[0][0]
            keycode = args[0][1]
        else:
            mode = args[0]
            keycode = args[1]
        if mode == "action":
            self.perform_action(keycode)

    # def debug_path(self):
    #     if self.element is None or not hasattr(self.element, "path"):
    #         return
    #     path = self.element.path
    #     starts = []
    #     ends = []
    #     types = []
    #     for seg in path:
    #         types.append(type(seg).__name__)
    #         starts.append(seg.start)
    #         ends.append(seg.end)
    #     for idx in range(len(starts)):
    #         p_idx = idx - 1 if idx > 0 else len(starts) - 1
    #         n_idx = idx + 1 if idx < len(starts) - 1 else 0
    #         start_status = ""
    #         end_status = ""
    #         if starts[idx] is None:
    #             if ends[p_idx] is not None:
    #                 start_status = "Start: None (Prev: not None)"
    #         else:
    #             if ends[p_idx] is None:
    #                 start_status = "Start: Not None (Prev: None)"
    #             else:
    #                 if starts[idx].x != ends[p_idx].x or starts[idx].y != ends[p_idx].y:
    #                     start_status = "Start: != Prev end"
    #         if ends[idx] is None:
    #             if starts[n_idx] is not None:
    #                 end_status = "End: None (Next: not None)"
    #         else:
    #             if starts[n_idx] is None:
    #                 end_status = "End: Not None (Next: None)"
    #             else:
    #                 if starts[n_idx].x != ends[idx].x or starts[n_idx].y != ends[idx].y:
    #                     end_status = "End: != Next start"
    #         if types[idx] == "Move" and types[p_idx] == "Close":
    #             if ends[idx].x != ends[p_idx].x or ends[idx].y != ends[p_idx].y:
    #                 start_status += ", end points !="
    #             else:
    #                 start_status += ", end points =="

    #         print(
    #             f"#{idx} {types[idx]} - {start_status} - {end_status} (Prev: {types[p_idx]}, Next = {types[n_idx]})"
    #         )

    def calculate_points(self, selected_node):
        # Set points...
        self.debug_current = None
        self.element = selected_node
        self.selected_index = None
        self.nodes = []
        # print ("After load:")
        # self.debug_path()
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
            for idx, segment in enumerate(path):
                # print (f"{idx}# {type(segment).__name__} - S={segment.start} - E={segment.end}")
                if idx < len(path) - 1:
                    next_seg = path[idx + 1]
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
                    # midp = segment.point(0.5)
                    midp = self.get_bezier_point(segment, 0.5)
                    self.nodes.append(
                        {
                            "prev": None,
                            "next": None,
                            "point": midp,
                            "segment": segment,
                            "path": path,
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
        self.scene.context.signal("nodeedit", (self.node_type, False))

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
            path = node.path
            init = False
            for idx, entry in enumerate(self.nodes):
                if not entry["type"] == "point":
                    continue
                treatment = ""
                e = entry["segment"]
                if isinstance(e, Move):
                    if entry["selected"]:
                        # The next segment needs to be highlighted...
                        ptx, pty = node.matrix.point_in_matrix_space(e.end)
                        p.MoveToPoint(ptx, pty)
                        e = entry["next"]
                        init = deal_with_segment(e, init)
                        treatment = "move+next"
                    else:
                        ptx, pty = node.matrix.point_in_matrix_space(e.end)
                        p.MoveToPoint(ptx, pty)
                        init = True
                        treatment = "move"
                elif not entry["selected"]:
                    ptx, pty = node.matrix.point_in_matrix_space(e.end)
                    p.MoveToPoint(ptx, pty)
                    init = True
                    treatment = "nonselected"
                else:
                    init = deal_with_segment(e, init)
                    treatment = "selected"
                # print (f"#{idx} {entry['type']} got treatment: {treatment}")

        gc.SetPen(self.pen_highlight_line)
        gc.DrawPath(p)

    def process_draw(self, gc: wx.GraphicsContext):
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
                else:
                    gc.SetPen(self.pen)
                gc.DrawEllipse(ptx - offset, pty - offset, offset * 2, offset * 2)
            elif entry["type"] == "control":
                if idx == self.selected_index or entry["selected"]:
                    gc.SetPen(self.pen_highlight)
                else:
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
                    (ptx - offset, pty),
                    (ptx, pty + offset),
                    (ptx + offset, pty),
                    (ptx, pty - offset),
                    (ptx - offset, pty),
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

    def done(self):
        self.scene.tool_active = False
        self.scene.modif_active = False
        self.p1 = None
        self.p2 = None
        self.move_type = "node"
        self.scene.context("tool none\n")
        self.scene.context.signal("statusmsg", "")
        self.scene.context.elements.validate_selected_area()
        self.scene.request_refresh()

    def modify_element(self, reload=True):
        if self.element is None:
            return
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

    def first_segment_in_subpath(self, index):
        """
        Provides the first non-move/close segment in the subpath to which the segment at location index belongs to
        """
        result = None
        if not self.element is None and hasattr(self.element, "path"):
            for idx in range(index, -1, -1):
                seg = self.element.path[idx]
                if isinstance(seg, (Move, Close)):
                    break
                result = seg
        return result

    def last_segment_in_subpath(self, index):
        """
        Provides the last non-move/close segment in the subpath to which the segment at location index belongs to
        """
        result = None
        if not self.element is None and hasattr(self.element, "path"):
            for idx in range(index, len(self.element.path)):
                seg = self.element.path[idx]
                if isinstance(seg, (Move, Close)):
                    break
                result = seg
        return result

    def is_closed_subpath(self, index):
        """
        Provides the last segment in the subpath to which the segment at location index belongs to
        """
        result = False
        if not self.element is None and hasattr(self.element, "path"):
            for idx in range(index, len(self.element.path)):
                seg = self.element.path[idx]
                if isinstance(seg, Move):
                    break
                if isinstance(seg, Close):
                    result = True
                    break
        return result

    def toggle_close(self):

        modified = False
        if self.node_type == "polyline":
            if isinstance(self.element.shape, Polygon):
                newshape = Polyline(self.element.shape)
            else:
                newshape = Polygon(self.element.shape)
            self.element.shape = newshape
            modified = True
        else:
            dealt_with = []
            anyselected = False
            for entry in self.nodes:
                if entry["selected"] and entry["type"] == "point":
                    anyselected = True
                    break
            if not anyselected:
                # Lets select the last point, so the last segment will be closed/opened
                for idx in range(len(self.nodes) - 1, -1, -1):
                    entry = self.nodes[idx]
                    if entry["type"] == "point":
                        entry["selected"] = True
                        break

            for idx in range(len(self.nodes) - 1, -1, -1):
                entry = self.nodes[idx]
                if entry["selected"] and entry["type"] == "point":
                    # What's the index of the last selected element
                    # Have we dealt with that before? ie not multiple toggles..
                    segstart = entry["start"]
                    if segstart in dealt_with:
                        continue
                    dealt_with.append(segstart)
                    # Lets establish the last segment in the path
                    prevseg = None
                    is_closed = False
                    for sidx in range(segstart, len(self.element.path), 1):
                        seg = self.element.path[sidx]
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
                        del self.element.path[lastidx + 1]
                        modified = True
                    else:
                        # Need to insert a Close segment
                        newseg = Close(
                            start=Point(prevseg.end.x, prevseg.end.y),
                            end=Point(prevseg.end.x, prevseg.end.y),
                        )
                        self.element.path.insert(lastidx + 1, newseg)
                        modified = True

        if modified:
            self.modify_element(True)

    @staticmethod
    def get_bezier_point(segment, t):
        """
        Provide a point on the cubic bezier curve for t (0 <= t <= 1)
        Args:
            segment (PathSegment): a cubic bezier
            t (float): (0 <= t <= 1)
            Computation: b(t) = (1-t)^3 * P0 + 3*(1-t)^2*t*P1 + 3*(1-t)*t^2*P2 + t^3 * P3
        """
        p0 = segment.start
        p1 = segment.control1
        p2 = segment.control2
        p3 = segment.end
        result = (1 - t)**3 * p0 + 3 * (1 - t)**2 * t * p1 + 3 * (1 - t) * t**2 * p2 + t**3 * p3
        return result

    @staticmethod
    def revise_bezier_to_point(segment, midpoint, change_2nd_control=False):
        """
        Adjust the two control points for a cubic bezier segment,
        so that the given point will lie on the cubic bezier curve for t=0.5
        Args:
            segment (PathSegment): a cubic bezier segment to be amended
            midpoint (Point): the new point
            Computation: b(t) = (1-t)^3 * P0 + 3*(1-t)^2*t*P1 + 3*(1-t)*t^2*P2 + t^3 * P3
        """
        t = 0.5
        p0 = segment.start
        p1 = segment.control1
        p2 = segment.control2
        p3 = segment.end
        if change_2nd_control:
            factor = 1 / (3 * (1 - t) * t**2)
            result = (midpoint - (1 - t)**3 * p0  - 3 * (1 - t)**2 * t * p1 - t**3 * p3) * factor
            segment.control2 = result
        else:
            factor = 1 / (3 * (1 - t)**2 * t)
            result = (midpoint - (1 - t)**3 * p0  - 3 * (1 - t) * t**2 * p2 - t**3 * p3) * factor
            segment.control1 = result

    def adjust_midpoint(self, index):
        # We need to update the midpoint of a cubic bezier
        for j in range(3):
            k = index + 1 + j
            if (
                k < len(self.nodes) and 
                self.nodes[k]["type"] == "midpoint"
            ):
                self.nodes[k]["point"] = self.get_bezier_point(self.nodes[index]["segment"], 0.5)
                break

    def smoothen(self):
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
        modified = False
        if self.node_type == "polyline":
            # Not valid for a polyline Could make a path now but that might be more than the user expected...
            return
        # Pass 1 - make all lines a cubic bezier
        for idx, segment in enumerate(self.element.path):
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
                self.element.path[idx] = newsegment
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
                self.element.path[idx] = newsegment
                modified = True
            elif isinstance(segment, Arc):
                for newsegment in list(segment.as_cubic_curves(1)):
                    self.element.path[idx] = newsegment
                    break
                modified = True
        # Pass 2 - make all control lines align
        prevseg = None
        lastidx = len(self.element.path) - 1
        for idx, segment in enumerate(self.element.path):
            nextseg = None
            if idx < lastidx:
                nextseg = self.element.path[idx + 1]
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

    def quad_symmetrical(self):
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
        modified = False
        for idx in range(len(self.nodes) - 1, -1, -1):
            entry = self.nodes[idx]
            if entry["selected"] and entry["type"] == "point":
                if self.node_type == "polyline":
                    if len(self.element.shape.points) > 2:
                        modified = True
                        self.element.shape.points.pop(idx)
                    else:
                        break
                else:
                    idx = entry["pathindex"]
                    prevseg = None
                    nextseg = None
                    seg = self.element.path[idx]
                    if idx > 0:
                        prevseg = self.element.path[idx - 1]
                    if idx < len(self.element.path) - 1:
                        nextseg = self.element.path[idx + 1]
                    if nextseg is None:
                        # Last point of the path
                        # Can just be deleted, provided we have something
                        # in front...
                        if prevseg is None or isinstance(prevseg, (Move, Close)):
                            continue
                        del self.element.path[idx]
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

                        del self.element.path[idx]
                        modified = True
                    else:
                        # Could be the first point...
                        if prevseg is None and (
                            nextseg is None or isinstance(nextseg, (Move, Close))
                        ):
                            continue
                        if prevseg is None:  # # Move
                            seg.end = Point(nextseg.end.x, nextseg.end.y)
                            del self.element.path[idx + 1]
                            modified = True
                        elif isinstance(seg, Move):  # # Move
                            seg.end = Point(nextseg.end.x, nextseg.end.y)
                            del self.element.path[idx + 1]
                            modified = True
                        else:
                            nextseg.start.x = prevseg.end.x
                            nextseg.start.y = prevseg.end.y
                            del self.element.path[idx]
                            modified = True

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
                self.element.path[idx] = newsegment
                modified = True
        if modified:
            self.modify_element(True)

    def linear_all(self):
        # Stub for converting segment to a line
        modified = False
        if self.node_type == "polyline":
            # Not valid for a polyline Could make a path now but that might be more than the user expected...
            return
        for idx, segment in enumerate(self.element.path):
            if isinstance(segment, (Close, Move, Line)):
                continue
            startpt = Point(segment.start.x, segment.start.y)
            endpt = Point(segment.end.x, segment.end.y)
            newsegment = Line(start=startpt, end=endpt)
            self.element.path[idx] = newsegment
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
                self.element.path[idx] = newsegment
                modified = True
        if modified:
            self.modify_element(True)

    def break_path(self):
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
                if idx in (0, len(self.element.path) - 1):
                    # Dont break at the first or last point
                    continue
                nextseg = self.element.path[idx + 1]
                if isinstance(nextseg, (Move, Close)):
                    # Not at end of subpath
                    continue
                prevseg = self.element.path[idx - 1]
                if isinstance(prevseg, (Move, Close)):
                    # We could still be at the end point of the first segment...
                    if entry["point"] == seg.start:
                        # Not at start of subpath
                        continue
                newseg = Move(
                    start=Point(seg.end.x, seg.end.y),
                    end=Point(nextseg.start.x, nextseg.start.y),
                )
                self.element.path.insert(idx + 1, newseg)
                # Now let's validate whether the 'right' path still has a
                # close segment at it's end. That will be removed as this would
                # create an unwanted behaviour
                prevseg = None
                is_closed = False
                for sidx in range(idx + 1, len(self.element.path), 1):
                    seg = self.element.path[sidx]
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
                    del self.element.path[lastidx + 1]

                modified = True
        if modified:
            self.modify_element(True)

    def join_path(self):
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
                prevseg = None
                nextseg = None
                if idx > 0:
                    prevseg = self.element.path[idx - 1]
                if idx < len(self.element.path) - 1:
                    nextseg = self.element.path[idx + 1]
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
                    del self.element.path[idx]
                    modified = True
                else:
                    # Let's look at the next segment
                    if nextseg is None:
                        continue
                    if not isinstance(nextseg, Move):
                        continue
                    seg.end.x = nextseg.end.x
                    seg.end.y = nextseg.end.y
                    del self.element.path[idx + 1]
                    modified = True

        if modified:
            self.modify_element(True)

    def insert_midpoint(self):
        # Stub for inserting a point...
        modified = False
        # Move backwards as len will change
        for idx in range(len(self.nodes) - 1, -1, -1):
            entry = self.nodes[idx]
            if entry["selected"] and entry["type"] == "point":
                if self.node_type == "polyline":
                    pt1 = self.element.shape.points[idx]
                    if idx == 0:
                        # Very first point? Mirror first segment and take midpoint
                        pt2 = Point(
                            self.element.shape.points[idx + 1].x,
                            self.element.shape.points[idx + 1].y,
                        )
                        pt2.x = pt1.x - (pt2.x - pt1.x)
                        pt2.y = pt1.y - (pt2.y - pt1.y)
                        pt2.x = (pt1.x + pt2.x) / 2
                        pt2.y = (pt1.y + pt2.y) / 2
                        self.element.shape.points.insert(0, pt2)
                    else:
                        pt2 = Point(
                            self.element.shape.points[idx - 1].x,
                            self.element.shape.points[idx - 1].y,
                        )
                        pt2.x = (pt1.x + pt2.x) / 2
                        pt2.y = (pt1.y + pt2.y) / 2
                        # Mid point
                        self.element.shape.points.insert(idx, pt2)
                    modified = True
                else:
                    # Path
                    idx = entry["pathindex"]
                    if entry["segment"] is None:
                        continue
                    segment = entry["segment"]
                    if entry["segtype"] == "L":
                        # Line
                        mid_x = (segment.start.x + segment.end.x) / 2
                        mid_y = (segment.start.y + segment.end.y) / 2
                        newsegment = Line(
                            start=Point(mid_x, mid_y),
                            end=Point(segment.end.x, segment.end.y),
                        )
                        self.element.path.insert(idx + 1, newsegment)
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
                        self.element.path.insert(idx + 1, newsegment)
                        segment.end.x = mid_x
                        segment.end.y = mid_y
                        segment.control2.x = mid_x
                        segment.control2.y = mid_y
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
                        self.element.path.insert(idx + 1, newsegment)
                        segment.end.x = mid_x
                        segment.end.y = mid_y
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
                        self.element.path.insert(idx + 1, newsegment)
                        segment.end.x = mid_x
                        segment.end.y = mid_y
                        segment.control.x = mid_x
                        segment.control.y = mid_y
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
                        self.element.path.insert(idx + 1, newsegment)
                        segment.end = pt1
                        # We need to step forward to assess whether there is a close segment
                        for idx2 in range(idx + 1, len(self.element.path)):
                            if isinstance(self.element.path[idx2], Move):
                                break
                            if isinstance(self.element.path[idx2], Close):
                                # Adjust the close segment to that it points again
                                # to the first move end
                                self.element.path[idx2].end = Point(pt1.x, pt1.y)
                                break

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
            newpt = Point(pt2.x + (pt2.x - pt1.x), pt2.y + (pt2.y - pt1.y))
            self.element.shape.points.append(newpt)
            modified = True
        else:
            # path
            valididx = len(self.element.path) - 1
            while valididx >= 0 and isinstance(
                self.element.path[valididx], (Close, Move)
            ):
                valididx -= 1
            if valididx >= 0:
                seg = self.element.path[valididx]
                pt1 = seg.start
                pt2 = seg.end
                newpt = Point(pt2.x + (pt2.x - pt1.x), pt2.y + (pt2.y - pt1.y))
                newsegment = Line(start=Point(seg.end.x, seg.end.y), end=newpt)
                if valididx < len(self.element.path) - 1:
                    if (
                        self.element.path[valididx + 1].end
                        == self.element.path[valididx + 1].start
                    ):
                        self.element.path[valididx + 1].end.x = newpt.x
                        self.element.path[valididx + 1].end.y = newpt.y
                    self.element.path[valididx + 1].start.x = newpt.x
                    self.element.path[valididx + 1].start.y = newpt.y

                self.element.path.insert(valididx + 1, newsegment)
                modified = True

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
        if event_type in ("leftdown", "leftclick"):
            self.pen = wx.Pen()
            self.pen.SetColour(wx.Colour(swizzlecolor(elements.default_stroke)))
            self.pen.SetWidth(25)
            self.scene.tool_active = True
            self.scene.modif_active = True

            self.scene.context.signal("statusmsg", self.message)
            self.move_type = "node"

            xp = space_pos[0]
            yp = space_pos[1]
            anyselected = False
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
                            anyselected = True
                        else:
                            # Shift-Key Pressed?
                            if "shift" not in modifiers:
                                self.clear_selection()
                                entry["selected"] = True
                                anyselected = True
                            else:
                                entry["selected"] = not entry["selected"]
                                for chk in self.nodes:
                                    if chk["selected"]:
                                        anyselected = True
                                        break
                        break
                else:  # For-else == icky
                    self.selected_index = None
            self.scene.context.signal("nodeedit", (self.node_type, anyselected))
            if self.selected_index is None:
                if event_type == "leftclick":
                    # Have we clicked outside the bbox? Then we call it a day...
                    outside = False
                    bb = self.element.bbox()
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

                m = self.element.matrix.point_in_inverse_space(space_pos[:2])
                # Special treatment for the virtual midpoint:
                if current["type"] == "midpoint" and self.node_type == "path":
                    self.scene.context.signal("statusmsg", _("Drag to change the curve shape (ctrl to affect the other side)"))
                    idx = self.selected_index
                    newpt = Point(m[0], m[1])
                    change2nd = bool("ctrl" in modifiers)
                    self.revise_bezier_to_point(current["segment"], newpt, change_2nd_control=change2nd)
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
                        for nidx in range(
                            self.selected_index + 1, len(self.element.path), 1
                        ):
                            nextseg = self.element.path[nidx]
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
                        if (
                            nextseg is not None and 
                            isinstance(nextseg, CubicBezier)
                        ):
                            self.adjust_midpoint(self.selected_index + 1)

                        
                    # self.debug_path()
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
                anyselected = False
                for entry in self.nodes:
                    pt = entry["point"]
                    if (
                        entry["type"] == "point"
                        and x0 <= pt.x <= x1
                        and y0 <= pt.y <= y1
                    ):
                        entry["selected"] = True
                    if entry["selected"]:
                        # Could as well be another one not inside the
                        # current selection
                        anyselected = True
                self.scene.request_refresh()
                self.scene.context.signal("nodeedit", (self.node_type, anyselected))
            self.p1 = None
            self.p2 = None
            return RESPONSE_CONSUME
        return RESPONSE_DROP

    def perform_action(self, code):
        if code in self.commands:
            action = self.commands[code]
            # print(f"Execute {action[1]}")
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
