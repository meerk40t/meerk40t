import math

import wx

from meerk40t.gui.scene.sceneconst import RESPONSE_CHAIN, RESPONSE_CONSUME
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget

_ = wx.GetTranslation


class SimpleSlider:
    def __init__(self, index, scene, minimum, maximum, x, y, width, trailer):
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
            (self._maximum - self._minimum) * (x - self.x) / self.width
        )
        # print(f"Update from {self._value} to {newvalue}")
        self.value = newvalue

    def process_draw(self, gc: wx.GraphicsContext):
        """
        Widget-Routine to draw the different elements on the provided GraphicContext
        """
        gc.PushState()
        s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
        offset = self.pt_offset / s
        gc.SetPen(wx.LIGHT_GREY_PEN)
        gc.DrawLines([(self.x, self.y), (self.x + self.width, self.y)])
        gc.DrawLines(
            [(self.x, int(self.y - offset / 2)), (self.x, int(self.y + offset / 2))]
        )
        gc.DrawLines(
            [
                (self.x + self.width, int(self.y - offset / 2)),
                (self.x + self.width, int(self.y + offset / 2)),
            ]
        )
        gc.SetBrush(wx.RED_BRUSH)
        gc.SetPen(wx.RED_PEN)
        gc.DrawEllipse(self.ptx - offset, self.pty - offset, offset * 2, offset * 2)
        symbol = str(self._value)
        if self.trailer:
            if not self.trailer.startswith("%"):
                symbol += " "
            symbol += _(self.trailer)
        font_size = 10 / s
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
        x = self.x + self.width + offset
        y = self.y - t_height / 2
        gc.DrawText(symbol, x, y)

        gc.PopState()

    def hit(self, xpos, ypos):
        s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
        offset = self.pt_offset / s
        inside = bool(abs(self.ptx - xpos) <= offset and abs(self.pty - ypos) <= offset)
        # print(
        #     f"{self.identifier}: {inside} (offset={offset:.0f}) <- ({xpos:.0f}, {ypos:.0f}) to (({self.ptx:.0f}, {self.pty:.0f}))\n"
        #     + f"dx={abs(self.ptx - xpos):.0f}, dy={abs(self.pty - ypos):.0f}"
        # )
        return inside


class ParameterTool(ToolWidget):
    """
    Parameter Tool displays parameter points and values of selected elements
    and allows to change them visually.
    """

    def __init__(self, scene):
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
        self.pt_offset = 5
        self.is_hovering = False

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
        s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
        offset = self.pt_offset / s
        width = 100 / s
        x = bb[0]
        y = bb[1]
        for slider in self.sliders:
            y -= 3 * offset
            slider.set_position(x, y, width)
            slider.process_draw(gc)

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
                new_pt = self.element.matrix.point_in_matrix_space(pt)
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
                    p_idx, self.scene, minval, maxval, 0, 0, 100, info
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
                    p_idx, self.scene, minval, maxval, 0, 0, 100, info
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

    def update_parameter(self):
        if self.element is None:
            return False
        parameter = [self.mode]
        for d_type, d_data in zip(self.paramtype, self.params):
            parameter.append(d_type)
            if d_type == 0:
                # The point coordinates need to be brought back
                # to the original coordinate system
                newpt = self.element.matrix.point_in_inverse_space(d_data)
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
                new_pt = self.element.matrix.point_in_matrix_space(pt)
                self.params[p_idx] = new_pt
                idx += 1
            else:
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
        offset = self.pt_offset / s
        gc.SetPen(wx.RED_PEN)
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

        offset = 5
        s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
        offset /= s
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
            self.is_hovering = len(message) > 0
            self.scene.context.signal("statusmsg", message)
            return RESPONSE_CHAIN
        elif event_type == "leftdown":
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
                            break
                    if self.slider_index >= 0:
                        break

                idx += 1
            # print(
            #     f"Established: {self.point_index}, {self.slider_index}, {self.paramtype}"
            # )
            return RESPONSE_CONSUME
        elif event_type == "move":
            # print(f"Move: {self.point_index}, {self.slider_index}")
            if self.point_index >= 0:
                # We need to reverse the point in the element matrix
                pt = (space_pos[0], space_pos[1])
                self.params[self.point_index] = pt
                if self.update_parameter():
                    if self.mode in self._functions:
                        # print(f"Update after pt for {self.mode}: {self.params}")
                        func = self._functions[self.mode][0]
                        if func is not None:
                            func(self.element)
                            self.sync_parameter()
                    else:
                        self.sync_parameter()
                    self.scene.refresh_scene()
            elif self.slider_index >= 0:
                if self.active_slider is not None:
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
                        else:
                            # print(f"No Routine for {self.mode}")
                            self.sync_parameter()
                        self.scene.refresh_scene()
            return RESPONSE_CONSUME
        elif event_type == "leftup":
            return RESPONSE_CONSUME
        elif event_type == "rightdown":
            # We stop
            self.done()
            return RESPONSE_CONSUME
        return RESPONSE_CHAIN

    def done(self):
        self.scene.pane.tool_active = False
        self.scene.pane.modif_active = False
        self.scene.pane.suppress_selection = False
        self.reset()
        if self.is_hovering:
            self.scene.context.signal("statusmsg", "")
            self.is_hovering = False
        self.scene.context("tool none\n")

    def signal(self, signal, *args, **kwargs):
        """
        Signal routine for stuff that's passed along within a scene,
        does not receive global signals
        """
        selected_node = None
        if signal == "tool_changed":
            if len(args[0]) > 1 and args[0][1] == "parameter":
                for node in self.scene.context.elements.elems(emphasized=True):
                    if node.functional_parameter is not None:
                        selected_node = node
                        break
                if selected_node is None:
                    self.scene.pane.suppress_selection = False
                else:
                    self.scene.pane.suppress_selection = True
                self.establish_parameters(selected_node)
                self.scene.request_refresh()
            else:
                self.reset()
            return
        elif signal == "emphasized":
            for node in self.scene.context.elements.elems(emphasized=True):
                if node.functional_parameter is not None:
                    selected_node = node
                    break
            if selected_node is None:
                self.scene.pane.suppress_selection = False
            else:
                self.scene.pane.suppress_selection = True
            self.establish_parameters(selected_node)
            self.scene.request_refresh()

    def init(self, context):
        return

    def final(self, context):
        self.scene.pane.tool_active = False
        self.scene.pane.modif_active = False
        self.scene.pane.suppress_selection = False
