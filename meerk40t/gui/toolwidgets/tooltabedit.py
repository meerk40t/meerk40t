import math
import numpy as np
import wx

from meerk40t.core.units import UNITS_PER_MM, Length
from meerk40t.tools.geomstr import Geomstr

from meerk40t.gui.scene.sceneconst import (
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
    RESPONSE_DROP,
)
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.gui.wxutils import get_gc_scale

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
        self.no_value_display = False

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
        offset = self.pt_offset / s

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
        if self.no_value_display:
            symbol = ""
        else:
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
        x = self.x + self.width + 1.5 * offset
        y = self.y - t_height / 2
        gc.DrawText(symbol, int(x), int(y))

        gc.PopState()

    def hit(self, xpos, ypos):
        s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
        offset = self.pt_offset / s
        inside = bool(abs(self.ptx - xpos) <= offset and abs(self.pty - ypos) <= offset)
        return inside


class TabEditTool(ToolWidget):
    """
    The Tab Edit Tool allows the manipulation of the tabs of a given element
    """

    def __init__(self, scene, mode=None):
        ToolWidget.__init__(self, scene)
        self.points = list()
        self.point_len = list()
        self.node = None
        self.node_length = 0
        self.total_points = list()
        self.total_distances = list()
        self.is_moving = False
        self.pt_offset = 5
        self.point_index = None
        self.current_pos = complex(0, 0)
        info = ""
        minval = 0
        maxval = 50 # 5mm
        self.slider_size = 200
        self.active_slider = None
        self.sliders = []
        slider = SimpleSlider(0, self.scene, minval, maxval, 0, 0, self.slider_size, info )
        slider.no_value_display = True
        self.sliders.append(slider)

    def reset(self):
        self.points.clear()
        self.point_len.clear()
        self.total_distances.clear()
        self.total_points.clear()
        self.point_index = None
        self.node_length = 0
        self.node = None
        self.is_moving = False

    def done(self):
        self.scene.pane.tool_active = False
        self.scene.pane.modif_active = False
        self.scene.pane.ignore_snap = False
        self.scene.pane.suppress_selection = False
        self.reset()
        self.scene.context("tool none\n")
        self.scene.context.signal("statusmsg", "")

    def set_node(self, node):

        self.reset()
        self.node = node
        self.node_length = 0
        geom_transformed = node.as_geometry()
        # 0.1 mm is enough for this purpose...
        interval = int(UNITS_PER_MM / 10)

        # We need to go through all segments...
        total_length = 0
        for segments in geom_transformed.as_interpolated_segments(interpolate=interval):
            points = []
            distances = []
            last = None
            _remainder = 0
            for pt in segments:
                if last is not None:
                    x0 = last.real
                    y0 = last.imag
                    x1 = pt.real
                    y1 = pt.imag
                    distance_change = abs(last - pt)
                    positions = 1 - _remainder
                    # Circumvent a div by zero error
                    try:
                        intervals = distance_change / interval
                    except ZeroDivisionError:
                        intervals = 1
                    # print (f"Will go through {intervals} intervals starting with {positions}")
                    while positions <= intervals:
                        amount = positions / intervals
                        tx = amount * (x1 - x0) + x0
                        ty = amount * (y1 - y0) + y0
                        total_length += interval
                        distances.append(total_length)
                        points.append(complex(tx, ty))
                        positions += 1
                    if len(points):
                        self.total_points.extend(points)
                        self.total_distances.extend(distances)
                        points = []
                        distances = []
                    _remainder += intervals
                    _remainder %= 1
                last = pt
            if len(points):
                self.total_points.extend(points)
                self.total_distances.extend(distances)

        self.node_length = total_length
        self.calculate_tabs()

    def calculate_tabs(self):

        def calculate_from_str(tabpos) -> list:
            positions = list()
            sub_comma = tabpos.split(",")
            if tabpos.startswith("*"):
                # Special case:
                # '*4' means 4 tabs equidistant, all remaining parameters will be ignored
                sub_spaces = sub_comma[0].split()
                s = sub_spaces[0][1:]
                try:
                    value = int(s)
                    if value > 0:
                        for i in range(value):
                            val = (i + 0.5) * 100 / value
                            positions.append(val)
                except ValueError:
                    pass
            else:
                for entry in sub_comma:
                    sub_spaces = entry.split()
                    for s in sub_spaces:
                        try:
                            value = float(s)
                            if value < 0:
                                value = 0
                            elif value > 100:
                                value = 100
                        except ValueError:
                            continue
                        positions.append(value)
            return positions

        tabpos = self.node.mktabpositions
        if tabpos and len(self.total_points):
            # We do split the points
            if isinstance(tabpos, str):
                positions = calculate_from_str(tabpos)
            else:
                positions = list(tabpos, )
            positions.sort()
            dx = 0
            index_pt = 0
            for index, pos in enumerate(positions):
                dx = self.total_distances[index_pt]
                pos_length = pos / 100.0 * self.node_length
                if dx >= pos_length:
                    self.points.append(self.total_points[index_pt])
                    self.point_len.append(pos)
                    continue
                while index_pt < len(self.total_points) - 1 and dx < pos_length:
                    index_pt += 1
                    dx = self.total_distances[index_pt]
                if dx >= pos_length:
                    self.points.append(self.total_points[index_pt])
                    self.point_len.append(pos)
                    continue

    def find_nearest_point(self, target_point):
        _distances = np.abs(np.array(self.total_points) - target_point)
        _nearest = np.argmin(_distances)
        c_point = self.total_points[_nearest]
        c_len = self.total_distances[_nearest]
        _distance = _distances[_nearest]
        return c_point, c_len, _distance

    def write_node(self):
        if self.node is None:
            return
        posi = ""
        for p in self.point_len:
            if posi:
                posi += " "
            posi += f"{p:.3f}"

        self.node.mktabpositions = posi
        self.node.empty_cache()
        self.scene.request_refresh()
        self.scene.context.signal("element_property_update", self.node)
        self.scene.context.signal("modified_by_tool")

    def clear_all_tabs(self):
        if self.node is None:
            return
        self.points.clear()
        self.point_len.clear()
        self.write_node()

    def delete_current_tab(self):
        if self.node is None or self.point_index is None:
            return
        self.point_len.pop(self.point_index)
        self.points.pop(self.point_index)
        self.point_index = None
        self.write_node()

    def update_and_draw_sliders(self, gc):
        if self.node is None:
            return
        value = round(Length(self.node.mktablength).mm * 10, 0)
        self.sliders[0].value = value
        self.sliders[0].trailer = Length(self.node.mktablength, digits=1).length_mm
        bb = self.node.bounds
        if bb is None:
            return
        if len(self.sliders) == 0:
            return
        s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
        offset = self.pt_offset / s
        width = self.slider_size / s
        x = bb[0]
        y = bb[1]
        for slider in self.sliders:
            y -= 3 * offset
            if not self.is_moving:
                slider.set_position(x, y, width)

        # Now draw everything
        for slider in self.sliders:
            slider.process_draw(gc)

    def process_draw(self, gc: wx.GraphicsContext):
        """
        Widget-Routine to draw the different elements on the provided GraphicContext
        """
        gc.PushState()
        s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
        offset = self.pt_offset / s
        gc.SetPen(wx.RED_PEN)
        gc.SetBrush(wx.RED_BRUSH)
        for index, g in enumerate(self.points):
            ptx = g.real
            pty = g.imag
            if index == self.point_index:
                fact = 1.5
            else:
                fact = 1
            gc.DrawEllipse(ptx - fact * offset, pty - fact * offset, offset * 2 * fact, offset * 2 * fact)
        self.update_and_draw_sliders(gc)
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
        # We don't need nearest snap
        pos = complex(*space_pos[:2])
        self.current_pos = pos

        if event_type == "leftdown":
            if self.node is None:
                return RESPONSE_CHAIN
            self.scene.pane.tool_active = True
            self.scene.pane.modif_active = True
            offset = self.pt_offset
            s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
            offset /= s
            xp = space_pos[0]
            yp = space_pos[1]
            self.point_index = None
            self.slider_index = -1
            w = offset * 4
            h = offset * 4
            for idx, pt in enumerate(self.points):
                ptx = pt.real
                pty = pt.imag
                x = ptx - 2 * offset
                y = pty - 2 * offset
                if x <= xp <= x + w and y <= yp <= y + h:
                    # print("Found point")
                    self.point_index = idx
            if self.point_index is None:
                for idx, slider in enumerate(self.sliders):
                    # hh = slider.hit(xp, yp)
                    # print(f"Check {idx} vs {slider.identifier}: {hh}")
                    if slider.hit(xp, yp):
                        # print(f"Found slider: {slider.identifier}")
                        self.slider_index = idx
                        self.active_slider = slider
                        break
                if self.slider_index >= 0:
                    return RESPONSE_CONSUME

            if self.point_index is None and self.node_length:
                # Outside of given points
                c_point, c_len, distance = self.find_nearest_point(self.current_pos)
                if distance < 2 * offset:
                    seg_len = 100 * c_len / self.node_length
                    self.points.append(c_point)
                    self.point_len.append(seg_len)
                    self.write_node()
            elif self.point_index is not None and "shift" in modifiers:
                self.delete_current_tab()
            self.scene.request_refresh()
            return RESPONSE_CONSUME
        if event_type == "move":
            if "m_middle" in modifiers:
                return RESPONSE_CHAIN
            if self.node is None:
                return RESPONSE_CHAIN
            self.is_moving = True
            idx = self.point_index
            if idx is not None:
                c_point, c_len, distance = self.find_nearest_point(self.current_pos)
                seg_len = 100 * c_len / self.node_length
                self.points[idx] = c_point
                self.point_len[idx] = seg_len
                self.scene.request_refresh()
            elif self.slider_index >= 0 and self.active_slider is not None:
                self.active_slider.update_according_to_pos(
                    space_pos[0], space_pos[1]
                )
                self.node.mktablength = float(Length(f"{self.active_slider.value / 10.0}mm"))
                # We wait
                self.node.empty_cache()
                self.scene.request_refresh()
                self.scene.context.signal("element_property_update", self.node)
                self.scene.context.signal("modified_by_tool")
            return RESPONSE_CONSUME
        if event_type == "leftup":
            if self.is_moving:
                self.write_node()
            self.is_moving = False
            return RESPONSE_CONSUME
        if event_type == "lost" or (event_type == "key_up" and modifiers == "escape"):
            if self.scene.pane.tool_active:
                self.scene.pane.tool_active = False
                self.scene.request_refresh()
                response = RESPONSE_CONSUME
            else:
                response = RESPONSE_CHAIN
            self.done()
            return response
        if event_type == "rightdown":
            # We stop
            self.done()
            return RESPONSE_CONSUME
        if event_type == "key_up" and modifiers=="shift+delete":
            self.clear_all_tabs()
            return RESPONSE_CONSUME
        if event_type == "key_up" and modifiers=="delete":
            self.delete_current_tab()
            return RESPONSE_CONSUME
        # if event_type == "key_up":
        #     print (f"{event_type}: {modifiers} {keycode}")
        #     return RESPONSE_CHAIN
        return RESPONSE_CHAIN

    def tool_change(self):
        self.reset()
        for node in self.scene.context.elements.flat(emphasized=True):
            if not hasattr(node, "as_geometry") or not hasattr(node, "mktabpositions"):
                continue
            self.set_node(node)
        # self.scene.pane.suppress_selection = len(self.points) > 0
        self.scene.pane.ignore_snap = True
        self.scene.pane.suppress_selection = True
        self.scene.request_refresh()
        self.scene.context.signal("statusmsg", _("Drag existing tabs around or add one by clicking on the shape,\nShift-Click/Delete removes current, Shift+Delete removes all"))

    def signal(self, signal, *args, **kwargs):
        """
        Signal routine for stuff that's passed along within a scene,
        does not receive global signals
        """
        if signal == "tool_changed":
            if len(args[0]) > 1 and args[0][1] == "tabedit":
                self.tool_change()
            else:
                self.reset()
        elif signal == "emphasized":
            self.tool_change()
        elif signal == "tabs_updated" and self.node is not None:
            self.set_node(self.node)
