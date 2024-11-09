import math
import numpy as np
import wx

from meerk40t.gui.scene.sceneconst import RESPONSE_CHAIN, RESPONSE_CONSUME
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.gui.wxutils import dip_size, get_matrix_scale, get_gc_scale
from meerk40t.tools.geomstr import NON_GEOMETRY_TYPES

_ = wx.GetTranslation


class SimpleCheckbox:
    def __init__(self, index, scene, x, y, trailer, magnification=1):
        self.identifier = index
        self._value = False
        self.scene = scene
        self.x = x
        self.y = y
        self.magnification = magnification
        self.pt_offset = 5
        if trailer is None:
            trailer = ""
        self.trailer = trailer

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, newval):
        self._value = bool(newval)

    def set_position(self, x, y):
        self.x = x
        self.y = y

    def process_draw(self, gc: wx.GraphicsContext):
        """
        Widget-Routine to draw the different elements on the provided GraphicContext
        """
        gc.PushState()
        s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
        offset = self.magnification * self.pt_offset / s
        gc.SetBrush(wx.TRANSPARENT_BRUSH)
        mypen = wx.Pen(wx.LIGHT_GREY)
        linewidth = 1 / s
        try:
            mypen.SetWidth(linewidth)
        except TypeError:
            mypen.SetWidth(int(linewidth))
        gc.SetPen(mypen)
        gc.DrawRectangle(
            int(self.x - offset), int(self.y - offset), int(2 * offset), int(2 * offset)
        )
        if self._value:
            gc.SetBrush(wx.RED_BRUSH)
            mypen.SetColour(wx.RED)
            gc.SetPen(mypen)
            # gc.DrawRectangle(
            #     int(self.x - 0.75 * offset),
            #     int(self.y - 0.75 * offset),
            #     int(1.5 * offset),
            #     int(1.5 * offset),
            # )
            gc.DrawLines(
                [
                    (int(self.x - offset), int(self.y - offset)),
                    (int(self.x + offset), int(self.y + offset)),
                ]
            )
            gc.DrawLines(
                [
                    (int(self.x - offset), int(self.y + offset)),
                    (int(self.x + offset), int(self.y - offset)),
                ]
            )
        if self.trailer:
            font_size = 8 * self.magnification / s
            if font_size < 1.0:
                font_size = 1.0
            try:
                font = wx.Font(
                    font_size,
                    wx.FONTFAMILY_SWISS,
                    wx.FONTSTYLE_NORMAL,
                    wx.FONTWEIGHT_NORMAL,
                )
            except TypeError:
                font = wx.Font(
                    int(font_size),
                    wx.FONTFAMILY_SWISS,
                    wx.FONTSTYLE_NORMAL,
                    wx.FONTWEIGHT_NORMAL,
                )
            gc.SetFont(font, wx.Colour(red=255, green=0, blue=0))
            (t_width, t_height) = gc.GetTextExtent(self.trailer)
            x = self.x + 2 * offset
            y = self.y - t_height / 2
            gc.DrawText(self.trailer, int(x), int(y))

        gc.PopState()

    def hit(self, xpos, ypos):
        s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
        offset = self.magnification * self.pt_offset / s
        inside = bool(abs(self.x - xpos) <= offset and abs(self.y - ypos) <= offset)
        return inside


class SimpleSlider:
    def __init__(self, index, scene, minimum, maximum, x, y, width, trailer, magnification=1):
        self.identifier = index
        self._minimum = min(minimum, maximum)
        self._maximum = max(minimum, maximum)
        if self._minimum == self._maximum:
            # print("min + max were equal")
            self._maximum += 1
        self._value = self._minimum
        self.scene = scene
        self.x = x
        self.y = y
        self.width = width
        self.ptx = x
        self.pty = y
        self.magnification = magnification
        self.pt_offset = 5
        if trailer is None:
            trailer = ""
        self.trailer = trailer

    @property
    def value(self):
        return self._value

    def update_value_pos(self):
        self.ptx = int(
            self.x
            + self.width
            * (self._value - self._minimum)
            / (self._maximum - self._minimum)
        )
        self.pty = int(self.y)

    @value.setter
    def value(self, newval):
        self._value = min(self._maximum, max(self._minimum, newval))
        self.update_value_pos()

    def set_position(self, x, y, width):
        self.x = x
        self.y = y
        self.width = width
        self.update_value_pos()

    def update_according_to_pos(self, x, y):
        if x < self.x:
            x = self.x
        if x > self.x + self.width:
            x = self.x + self.width
        newvalue = self._minimum + int(
            round((self._maximum - self._minimum) * (x - self.x) / self.width, 0)
        )
        # print(f"Update from {self._value} to {newvalue}")
        self.value = newvalue

    def process_draw(self, gc: wx.GraphicsContext):
        """
        Widget-Routine to draw the different elements on the provided GraphicContext
        """
        gc.PushState()
        s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
        offset = self.magnification * self.pt_offset / s

        mypen = wx.Pen(wx.LIGHT_GREY)
        sx = get_gc_scale(gc)
        linewidth = 1 / sx
        try:
            mypen.SetWidth(linewidth)
        except TypeError:
            mypen.SetWidth(int(linewidth))
        gc.SetPen(mypen)
        gc.DrawLines(
            [(int(self.x), int(self.y)), (int(self.x + self.width), int(self.y))]
        )
        gc.DrawLines(
            [
                (int(self.x), int(self.y - offset / 2)),
                (int(self.x), int(self.y + offset / 2)),
            ]
        )
        gc.DrawLines(
            [
                (int(self.x + self.width), int(self.y - offset / 2)),
                (int(self.x + self.width), int(self.y + offset / 2)),
            ]
        )
        gc.SetBrush(wx.RED_BRUSH)
        mypen.SetColour(wx.RED)
        gc.SetPen(mypen)
        gc.DrawEllipse(
            int(self.ptx - offset),
            int(self.pty - offset),
            int(offset * 2),
            int(offset * 2),
        )
        symbol = str(self._value)
        if self.trailer:
            if not self.trailer.startswith("%"):
                symbol += " "
            symbol += _(self.trailer)
        font_size = 10 * self.magnification / s
        if font_size < 1.0:
            font_size = 1.0
        try:
            font = wx.Font(
                font_size,
                wx.FONTFAMILY_SWISS,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        except TypeError:
            font = wx.Font(
                int(font_size),
                wx.FONTFAMILY_SWISS,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        gc.SetFont(font, wx.Colour(red=255, green=0, blue=0))
        (t_width, t_height) = gc.GetTextExtent(symbol)
        x = self.x + self.width + 1.5 * offset
        y = self.y - t_height / 2
        # print(f"y={y}, self.y={self.y}, height={t_height}, label='{symbol}', font_size={font_size}")
        gc.DrawText(symbol, int(x), int(y))

        gc.PopState()

    def hit(self, xpos, ypos):
        s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
        offset = self.magnification * self.pt_offset / s
        inside = bool(abs(self.ptx - xpos) <= offset and abs(self.pty - ypos) <= offset)
        return inside


class ParameterTool(ToolWidget):
    """
    Parameter Tool displays parameter points and values of selected elements
    and allows to change them visually.
    """

    def __init__(self, scene, mode=None):
        ToolWidget.__init__(self, scene)
        self.element = None
        self.params = []
        self.paramtype = []
        self.sliders = []
        self._functions = {}
        self.active_slider = None
        self.mode = None
        self.point_index = -1
        self.slider_index = -1
        self.read_functions()
        # Establish the scaling function of the underlying GUI
        self.magnification = dip_size(scene.gui, 100, 100)[1] / 100
        self.pt_offset = 5
        self.is_hovering = False
        self.pin_box = None
        self.pin_box = SimpleCheckbox(-1, self.scene, 0, 0, _("Pin"), magnification=self.magnification)
        self.pinned = False
        self.is_moving = False
        self.slider_size = 200

    def read_functions(self):
        self._functions.clear()
        for func, m, sname in self.scene.context.kernel.find("element_update"):
            # function, path, shortname
            self._functions[sname.lower()] = func

    def reset(self):
        self.params.clear()
        self.paramtype.clear()
        self.sliders.clear()
        self.element = None
        self.mode = None
        self.point_index = -1
        self.active_slider = None

    def update_and_draw_sliders(self, gc):
        if self.element is None:
            return
        bb = self.element.bounds
        if bb is None:
            return
        if len(self.sliders) == 0:
            return
        s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
        offset = self.magnification * self.pt_offset / s
        width = self.slider_size / s
        if self.pinned:
            x = offset
            y = offset + 3 * offset * (len(self.sliders) + 1)
        else:
            x = bb[0]
            y = bb[1]
        for slider in self.sliders:
            y -= 3 * offset
            if not self.is_moving:
                slider.set_position(x, y, width)
        y -= 3 * offset
        self.pin_box.value = self.pinned
        if not self.is_moving:
            self.pin_box.set_position(x, y)

        # Now draw everything
        for slider in self.sliders:
            slider.process_draw(gc)
        self.pin_box.process_draw(gc)

    def establish_parameters(self, node):
        self.reset()
        self.element = node
        if self.element is None:
            return
        parameters = self.element.functional_parameter
        if parameters is None or len(parameters) < 3:
            return
        self.mode = parameters[0].lower()
        idx = 1
        p_idx = 0
        while idx < len(parameters):
            self.paramtype.append(parameters[idx])
            if parameters[idx] == 0:
                # point, needs to be translated into scene coordinates
                pt = (parameters[idx + 1], parameters[idx + 2])
                try:
                    new_pt = self.element.matrix.point_in_matrix_space(pt)
                except AttributeError:
                    new_pt = pt
                self.params.append(new_pt)
                idx += 1
            elif parameters[idx] == 1:
                self.params.append(parameters[idx + 1])
                # int, we use a simple slider
                minval = 0
                maxval = 100
                info = ""
                if self.mode in self._functions:
                    info = self._functions[self.mode][1]
                    if str(p_idx) in info:
                        gui_info = info[str(p_idx)]
                        if len(gui_info) > 0:
                            info = gui_info[0]
                        if len(gui_info) > 1:
                            minval = gui_info[1]
                        if len(gui_info) > 2:
                            maxval = gui_info[2]
                slider = SimpleSlider(
                    p_idx, self.scene, minval, maxval, 0, 0, self.slider_size, info, magnification=self.magnification
                )
                self.sliders.append(slider)
                slider.value = parameters[idx + 1]
            elif parameters[idx] == 2:
                self.params.append(parameters[idx + 1])
                # percentage, we use a simple slider
                info = ""
                minval = 0
                maxval = 100
                if self.mode in self._functions:
                    info = self._functions[self.mode][1]
                    if str(p_idx) in info:
                        gui_info = info[str(p_idx)]
                        if len(gui_info) > 0:
                            info = gui_info[0]
                        if len(gui_info) > 1:
                            minval = gui_info[1]
                        if len(gui_info) > 2:
                            maxval = gui_info[2]
                info = "% " + info
                slider = SimpleSlider(
                    p_idx, self.scene, minval, maxval, 0, 0, self.slider_size, info, magnification=self.magnification
                )
                self.sliders.append(slider)
                slider.value = int(100.0 * parameters[idx + 1])
            else:
                self.params.append(parameters[idx + 1])
            idx += 2
            p_idx += 1
        if parameters[0] not in self._functions:
            # That's not necessarily a bad thing as some node types don't
            # need a helper function
            # print("No function defined...")
            pass
        self.scene.pane.tool_active = True
        self.scene.pane.modif_active = True
        self.scene.pane.ignore_snap = False

    def update_parameter(self):
        if self.element is None:
            return False
        parameter = [self.mode]
        for d_type, d_data in zip(self.paramtype, self.params):
            parameter.append(d_type)
            if d_type == 0:
                # The point coordinates need to be brought back
                # to the original coordinate system
                try:
                    newpt = self.element.matrix.point_in_inverse_space(d_data)
                except AttributeError:
                    newpt = d_data
                parameter.append(newpt[0])
                parameter.append(newpt[1])
            else:
                parameter.append(d_data)
        changes = False
        old_parameter = self.element.functional_parameter
        if len(parameter) != len(old_parameter):
            changes = True
        else:
            for np, op in zip(parameter, old_parameter):
                if np != op:
                    changes = True
                    break
        if changes:
            self.element.functional_parameter = parameter
        return changes

    def sync_parameter(self):
        if self.element is None:
            return
        param = self.element.functional_parameter
        idx = 1
        p_idx = 0
        while idx < len(param):
            # self.paramtype[p_idx] = param[idx]
            if param[idx] == 0:
                pt = (param[idx + 1], param[idx + 2])
                try:
                    new_pt = self.element.matrix.point_in_matrix_space(pt)
                except AttributeError:
                    new_pt = pt
                # print(f"sync {p_idx}: {self.params[p_idx]} - {new_pt}")
                self.params[p_idx] = new_pt
                idx += 1
            else:
                # print(f"sync {p_idx}: {self.params[p_idx]} - {param[idx + 1]}")
                self.params[p_idx] = param[idx + 1]

            p_idx += 1
            idx += 2

    def process_draw(self, gc: wx.GraphicsContext):
        """
        Widget-Routine to draw the different elements on the provided GraphicContext
        """
        self.update_and_draw_sliders(gc)
        gc.PushState()
        s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
        offset = self.magnification * self.pt_offset / s
        mypen = wx.Pen(wx.RED)
        linewidth = 1 / s
        try:
            mypen.SetWidth(linewidth)
        except TypeError:
            mypen.SetWidth(int(linewidth))
        gc.SetPen(mypen)
        gc.SetBrush(wx.RED_BRUSH)
        for ptype, pdata in zip(self.paramtype, self.params):
            if ptype == 0:
                ptx = pdata[0]
                pty = pdata[1]
                gc.DrawEllipse(ptx - offset, pty - offset, offset * 2, offset * 2)
        gc.PopState()

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

        offset = self.magnification * 5
        s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
        offset /= s
        self.is_moving = False
        if event_type == "hover_start":
            return RESPONSE_CHAIN
        elif event_type == "hover_end" or event_type == "lost":
            if self.is_hovering:
                self.scene.context.signal("statusmsg", "")
                self.is_hovering = False
            return RESPONSE_CHAIN
        elif event_type == "hover":
            if space_pos is None:
                return RESPONSE_CHAIN
            xp = space_pos[0]
            yp = space_pos[1]
            w = offset * 4
            h = offset * 4

            message = ""
            p_idx = -1
            idx = 0
            for d_type, d_entry in zip(self.paramtype, self.params):
                d_entry = self.params[idx]
                if d_type == 0:
                    ptx, pty = d_entry
                    x = ptx - 2 * offset
                    y = pty - 2 * offset
                    if x <= xp <= x + w and y <= yp <= y + h:
                        p_idx = idx
                        break
                else:
                    for slider in self.sliders:
                        # hh = slider.hit(xp, yp)
                        # print(f"Check {idx} vs {slider.identifier}: {hh}")
                        if slider.identifier == idx and slider.hit(xp, yp):
                            # print(f"Found slider: {slider.identifier}")
                            p_idx = idx
                            break
                    if p_idx >= 0:
                        break

                idx += 1
            if p_idx >= 0:
                if self.mode in self._functions:
                    info = self._functions[self.mode][1]
                    if str(p_idx) in info:
                        gui_info = info[str(p_idx)]
                        if len(gui_info) > 0:
                            message = gui_info[0]
            else:
                if self.pin_box.hit(xp, yp):
                    message = _("Pin the parameter section to the top of the screen")
            self.is_hovering = len(message) > 0
            self.scene.context.signal("statusmsg", message)
            return RESPONSE_CHAIN
        elif event_type == "leftdown":
            self.is_moving = True
            xp = space_pos[0]
            yp = space_pos[1]
            self.point_index = -1
            self.slider_index = -1
            self.active_slider = None
            w = offset * 4
            h = offset * 4
            idx = 0
            for d_type, d_entry in zip(self.paramtype, self.params):
                d_entry = self.params[idx]
                # print(f"Checking {idx}, {d_type}, {d_entry}")
                if d_type == 0:
                    ptx, pty = d_entry
                    x = ptx - 2 * offset
                    y = pty - 2 * offset
                    if x <= xp <= x + w and y <= yp <= y + h:
                        # print("Found point")
                        self.point_index = idx
                        break
                else:
                    for slider in self.sliders:
                        # hh = slider.hit(xp, yp)
                        # print(f"Check {idx} vs {slider.identifier}: {hh}")
                        if slider.identifier == idx and slider.hit(xp, yp):
                            # print(f"Found slider: {slider.identifier}")
                            self.slider_index = idx
                            self.active_slider = slider
                            self.scene.pane.ignore_snap = True
                            break
                    if self.slider_index >= 0:
                        break

                idx += 1
            if (
                self.point_index < 0
                and self.slider_index < 0
                and self.pin_box.hit(xp, yp)
            ):
                self.pinned = not self.pinned
                self.pin_box.value = self.pinned

                self.is_moving = False
                self.scene.refresh_scene()
            return RESPONSE_CONSUME
        elif event_type == "move":
            if "m_middle" in modifiers:
                return RESPONSE_CHAIN
            # print(f"Move: {self.point_index}, {self.slider_index}")
            self.is_moving = True
            self.scene.pane.ignore_snap = False

            if self.point_index >= 0:
                # We need to reverse the point in the element matrix
                if nearest_snap is None:
                    pt = (space_pos[0], space_pos[1])
                else:
                    pt = (nearest_snap[0], nearest_snap[1])
                self.params[self.point_index] = pt
                if self.update_parameter():
                    if self.mode in self._functions:
                        # print(f"Update after pt for {self.mode}: {self.params}")
                        func = self._functions[self.mode][0]
                        if func is not None:
                            func(self.element)
                    self.sync_parameter()
                    self.scene.refresh_scene()
            elif self.slider_index >= 0:
                if self.active_slider is not None:
                    self.scene.pane.ignore_snap = True
                    self.active_slider.update_according_to_pos(
                        space_pos[0], space_pos[1]
                    )
                    value = self.active_slider.value
                    if self.paramtype[self.slider_index] == 2:
                        # Percentage
                        value /= 100.0
                    self.params[self.slider_index] = value
                    if self.update_parameter():
                        if self.mode in self._functions:
                            # print(f"Update after slide for {self.mode}: {self.params}")
                            func = self._functions[self.mode][0]
                            if func is not None:
                                func(self.element)
                        self.sync_parameter()
                        self.scene.refresh_scene()
            return RESPONSE_CONSUME
        elif event_type == "leftup":
            self.scene.pane.ignore_snap = False
            doit = (
                self.point_index >= 0
                and self.scene.context.snap_points
                and "shift" not in modifiers
            )
            if doit:
                matrix = self.scene.widget_root.scene_widget.matrix
                gap = self.scene.context.action_attract_len / get_matrix_scale(matrix)
                this_point = (
                    self.params[self.point_index][0]
                    + 1j * self.params[self.point_index][1]
                )
                found_pt = None
                smallest_gap = float("inf")
                for e in self.scene.context.elements.elems():
                    if e.emphasized:
                        # We care about other points, not our own
                        continue
                    if not hasattr(e, "as_geometry"):
                        continue
                    geom = e.as_geometry()
                    last = None
                    for seg in geom.segments[: geom.index]:
                        start = seg[0]
                        seg_type = geom._segtype(seg)
                        end = seg[4]
                        if seg_type in NON_GEOMETRY_TYPES:
                            continue
                        if np.isnan(start) or np.isnan(end):
                            print (f"Strange, encountered within toolparameter a segment with type: {seg_type} and start={start}, end={end} - coming from element type {e.type}\nPlease inform the developers")
                            continue

                        if start != last:
                            delta = abs(start - this_point)
                            if delta < smallest_gap:
                                smallest_gap = delta
                                found_pt = start
                        delta = abs(end - this_point)
                        if delta < smallest_gap:
                            smallest_gap = delta
                            found_pt = end

                if smallest_gap < gap:
                    pt = (found_pt.real, found_pt.imag)
                    self.params[self.point_index] = pt
                    if self.update_parameter():
                        if self.mode in self._functions:
                            # print(f"Update after pt for {self.mode}: {self.params}")
                            func = self._functions[self.mode][0]
                            if func is not None:
                                func(self.element)
                        self.sync_parameter()
                        self.scene.refresh_scene()
            self.is_moving = False
            return RESPONSE_CONSUME
        elif event_type == "rightdown":
            # We stop
            self.done()
            return RESPONSE_CONSUME
        return RESPONSE_CHAIN

    def done(self):
        self.scene.pane.tool_active = False
        self.scene.pane.modif_active = False
        self.scene.pane.ignore_snap = False
        self.scene.pane.suppress_selection = False
        self.reset()
        if self.is_hovering:
            self.scene.context.signal("statusmsg", "")
            self.is_hovering = False
        self.is_moving = False
        self.scene.context("tool none\n")

    def _tool_change(self):
        selected_node = None
        elements = self.scene.context.elements.elem_branch
        for node in elements.flat(emphasized=True):
            if (
                hasattr(node, "functional_parameter")
                and node.functional_parameter is not None
            ):
                if node.lock:
                    continue
                selected_node = node
                break
        self.scene.pane.suppress_selection = selected_node is not None
        self.establish_parameters(selected_node)
        self.scene.request_refresh()

    def signal(self, signal, *args, **kwargs):
        """
        Signal routine for stuff that's passed along within a scene,
        does not receive global signals
        """
        if signal == "tool_changed":
            if len(args[0]) > 1 and args[0][1] == "parameter":
                self._tool_change()
            else:
                self.reset()
        elif signal == "emphasized":
            self._tool_change()

    def init(self, context):
        return

    def final(self, context):
        self.scene.pane.tool_active = False
        self.scene.pane.modif_active = False
        self.scene.pane.ignore_snap = False
        self.scene.pane.suppress_selection = False
